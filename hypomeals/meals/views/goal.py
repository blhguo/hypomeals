import csv
import logging
import operator
import tempfile
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.datetime_safe import datetime

from meals.constants import END_OF_DAY
from meals.forms import SkuQuantityFormset, GoalForm
from meals.models import Sku, ProductLine, Goal, GoalItem
from meals.utils import SortedDefaultDict

logger = logging.getLogger(__name__)


def _get_goal(request, goal_id):
    """
    Retrieves a goal from a goal_id
    :param request: the HttpRequest instance
    :param goal_id: the ID of a goal
    :return: a Goal object, if one exists, and the current user has permission to view
        it. Raises PermissionDenied otherwise.
    """
    goal = get_object_or_404(Goal, pk=goal_id)
    if request.user.is_superuser or request.user.groups.filter(name="Admins").exists():
        # User is admin, grant access
        logger.info("Granting admin access for goal %d", goal_id)
        return goal
    if request.user == goal.user:
        # User created this goal, grant access
        logger.info("Granting owner access for goal %d", goal_id)
        return goal
    messages.error(
        request, "You do not have permission to view this goal. Did you create it?"
    )
    raise PermissionDenied


@login_required
def edit_goal(request, goal_id=-1):
    if goal_id != -1:
        goal_obj = get_object_or_404(Goal, pk=goal_id)
    else:
        goal_obj = None
    logger.info("Goal: %s", repr(goal_obj))
    if request.method == "POST":
        formset = SkuQuantityFormset(request.POST)
        form = GoalForm(request.POST)
        if form.is_valid() and formset.is_valid():
            logger.info("Cleaned data: %s\n%s", form.cleaned_data, formset.cleaned_data)
            with transaction.atomic():
                if not goal_obj:
                    goal_obj = Goal.objects.create(
                        user=request.user,
                        name=form.cleaned_data["name"],
                        deadline=form.cleaned_data["deadline"],
                    )
                else:
                    goal_obj.name = form.cleaned_data["name"]
                    goal_obj.deadline = form.cleaned_data["deadline"]
                    goal_obj.save_time = datetime.now()
                    goal_obj.save()
                saved = []
                deleted = GoalItem.objects.filter(goal=goal_obj).delete()
                logger.info("Deleted: %s", deleted)
                for form, data in zip(formset.forms, formset.cleaned_data):
                    if "DELETE" not in data or data["DELETE"]:
                        continue
                    saved.append(
                        GoalItem(
                            goal=goal_obj, sku=data["sku"], quantity=data["quantity"]
                        )
                    )
                if saved:
                    GoalItem.objects.bulk_create(saved)
                    logger.info("Saved %d GoalItems", len(saved))
            messages.info(request, f"Successfully saved goal {goal_obj.name}")
            return redirect("goals")

    else:
        if goal_obj:
            items = GoalItem.objects.filter(goal=goal_obj)
            initial = [
                {"sku": item.sku.verbose_name, "quantity": item.quantity.normalize}
                for item in items
            ]
            formset = SkuQuantityFormset(initial=initial)
            form = GoalForm(
                initial={"name": goal_obj.name, "deadline": goal_obj.deadline}
            )
        else:
            formset = SkuQuantityFormset()
            form = GoalForm()

    # Product line filters
    product_lines = (
        ProductLine.objects.filter(sku__count__gt=0)
        .distinct()
        .values_list("name", flat=True)
    )

    return render(
        request,
        "meals/goal/edit_goal.html",
        context={
            "editing": bool(goal_obj),
            "goal": goal_obj,
            "formset": formset,
            "form": form,
            "product_lines": product_lines,
        },
    )


@login_required
def export_csv(request, goal_id):
    goal = _get_goal(request, goal_id)
    items = goal.details.all()
    tf = tempfile.mktemp()
    with open(tf, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["SKU#", "SKU Name", "SKU Quantity"])
        for item in items:
            writer.writerow([item.sku.number, item.sku.name, item.quantity])
    resp = HttpResponse(open(tf).read(), content_type="text/csv")
    resp["Content-Disposition"] = f"attachment;filename=goal_{goal.name}.csv"
    return resp


def _calculate_report(goal):
    result = SortedDefaultDict(lambda: Decimal(0.0), key=operator.attrgetter("pk"))
    for item in goal.details.all():
        for formula_item in item.sku.formula.formulaingredient_set.all():
            result[formula_item.ingredient] += (
                formula_item.quantity * item.sku.formula_scale
            )
    logger.info("Report: %s", result)
    return result


@login_required
def view_calculations(request, goal_id):
    to_print = request.GET.get("print", "0") == "1"
    goal = _get_goal(request, goal_id)
    report = _calculate_report(goal)
    return render(
        request,
        template_name="meals/goal/report.html",
        context={"report": report.items(), "goal": goal, "print": to_print},
    )


def _generate_calculation(request, goal_id, output_format="csv"):
    goal = _get_goal(request, goal_id)
    report = _calculate_report(goal)
    if output_format.casefold() == "csv":
        tf = tempfile.mktemp()
        with open(tf, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Ingr#", "Name", "Amount (packages)", "Amount"])
            for ingr, amount in report.items():
                total_amount = round(amount * ingr.size, 2)
                writer.writerow(
                    [ingr.number, ingr.name, round(amount, 2), total_amount]
                )
        response = HttpResponse(open(tf).read(), content_type="text/csv")
        response["Content-Disposition"] = f"attachment;filename={goal.name}_report.csv"
    else:
        messages.error(request, f"Unsupported format: {output_format}")
        return redirect("error")
    return response


generate_calculation_csv = login_required(_generate_calculation)


@login_required
def goals(request):
    if request.user.is_admin:
        all_goals = Goal.objects.order_by("-save_time").all()
    else:
        all_goals = request.user.goals.order_by("-save_time")
    for g in all_goals:
        g.deadline = datetime.combine(g.deadline, END_OF_DAY)
    return render(
        request, template_name="meals/goal/goal.html", context={"all_goals": all_goals}
    )


@login_required
def filter_skus(request):
    pd = request.GET.get("product_line", None)
    skus = Sku.objects.filter(product_line__name=pd)
    result = {"error": None, "resp": [sku.verbose_name for sku in skus]}
    return JsonResponse(result)
