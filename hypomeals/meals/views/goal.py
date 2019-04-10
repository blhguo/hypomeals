# pylint: disable-msg=unexpected-keyword-arg

import csv
import json
import logging
import operator
import tempfile
import time
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.utils.datetime_safe import datetime

from meals import auth
from meals import utils
from meals.constants import WORK_HOURS_END
from meals.forms import (
    SkuQuantityFormset,
    GoalForm,
    GoalFilterForm,
    GoalScheduleFormset,
)
from meals.models import (
    Sku,
    ProductLine,
    Goal,
    GoalItem,
    GoalSchedule,
    FormulaIngredient,
    ManufacturingLine,
)
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
    if request.user.is_admin:
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
    messages.error(request, "You may only view goals created by yourself.")
    raise PermissionDenied


@login_required
@auth.permission_required_ajax(
    perm=("meals.change_goal",),
    msg="You do not have permission to edit manufacturing goals,",
    reason="Only business managers may edit manufacturing goals",
)
def edit_goal(request, goal_id=-1):
    if goal_id != -1:
        goal_obj = _get_goal(request, goal_id)
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
@auth.permission_required_ajax(
    perm=("meals.view_goal",),
    msg="You do not have permission to the manufacturing calculator,",
    reason="Only analysts may use the manufacturing calculator",
)
def export_csv(request, goal_id):
    goal = _get_goal(request, goal_id)
    items = goal.details.all()
    tf = tempfile.mktemp()
    with open(tf, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["SKU#", "SKU Name", "SKU Quantity"])
        for item in items:
            writer.writerow([item.sku.number, item.sku.verbose_name, item.quantity])
    resp = HttpResponse(open(tf).read(), content_type="text/csv")
    resp["Content-Disposition"] = f"attachment;filename=goal_{goal.name}.csv"
    return resp


def _calculate_report(goal, result=None):
    # Result is always in packages
    if result is None:
        result = SortedDefaultDict(lambda: Decimal(0.0), key=operator.attrgetter("pk"))
    for item in goal.details.all():
        for formula_item in item.sku.formula.formulaingredient_set.all():
            unit_scale = (
                formula_item.unit.scale_factor
                / formula_item.ingredient.unit.scale_factor
            )
            result[formula_item.ingredient] += (
                formula_item.quantity
                * item.sku.formula_scale
                * unit_scale
                * item.quantity
            )
    logger.info("Report: %s", result)
    return result


@login_required
@auth.permission_required_ajax(
    perm=("meals.view_goal",),
    msg="You do not have permission to the manufacturing calculator,",
    reason="Only analysts may use the manufacturing calculator",
)
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
                    [
                        ingr.number,
                        ingr.name,
                        round(amount, 2),
                        f"{total_amount} {ingr.unit.symbol}",
                    ]
                )
        response = HttpResponse(open(tf).read(), content_type="text/csv")
        response["Content-Disposition"] = f"attachment;filename={goal.name}_report.csv"
    else:
        messages.error(request, f"Unsupported format: {output_format}")
        return redirect("error")
    return response


generate_calculation_csv = login_required(
    auth.permission_required_ajax(
        perm=("meals.view_goal",),
        msg="You do not have permission to view manufacturing goals,",
        reason="Only analysts may view manufacturing goals",
    )(_generate_calculation)
)


@login_required
@auth.permission_required_ajax(
    perm=("meals.view_goal",),
    msg="You do not have permission to view manufacturing goals,",
    reason="Only analysts may view manufacturing goals",
)
def goals(request):
    start = time.time()

    if request.method == "POST":
        form = GoalFilterForm(request.POST)
    else:
        form = GoalFilterForm()

    if form.is_valid():
        all_goals = form.query(request.user)
    else:
        if request.user.is_admin:
            all_goals = Goal.objects.all()
        else:
            all_goals = Goal.objects.filter(user=request.user).all()

    for g in all_goals:
        g.deadline = datetime.combine(g.deadline, WORK_HOURS_END)
    end = time.time()
    return render(
        request,
        template_name="meals/goal/goal.html",
        context={
            "all_goals": all_goals,
            "form": form,
            "seconds": f"{end - start:6.3f}",
        },
    )


@login_required
def filter_skus(request):
    pd = request.GET.get("product_line", None)
    skus = Sku.objects.filter(product_line__name=pd)
    result = {"error": None, "resp": [sku.verbose_name for sku in skus]}
    return JsonResponse(result)


def _enable_goals(request, is_enabled=False):
    raw = request.GET.get("g", "[]")
    logger.debug("Raw GET: %r", raw)
    try:
        goal_ids = set(map(int, json.loads(raw)))
    except ValueError as e:
        return JsonResponse(
            {
                "error": "Unable to parse the following goal IDs: "
                f"'{raw}', because {str(e)}",
                "resp": None,
            }
        )
    logger.info("Got %d goal IDs: %s", len(goal_ids), goal_ids)
    if not goal_ids:
        return JsonResponse({"error": None, "resp": "No Goal ID was found in request."})

    goal_objs = Goal.objects.filter(pk__in=goal_ids)
    found = set(goal_objs.values_list("pk", flat=True))
    logger.info("Found %d goals", len(found))
    missing = goal_ids - found
    if missing:
        return JsonResponse(
            {
                "error": (
                    "The following goal ID cannot be found: "
                    f"'{', '.join(map(str, goal_ids))}'"
                ),
                "resp": None,
            }
        )
    goal_objs.update(is_enabled=is_enabled)
    return JsonResponse(
        {
            "error": None,
            "resp": f"Successfully {'enabled' if is_enabled else 'disabled'} "
            f"{len(goal_objs)} goals",
        }
    )


@login_required
@auth.permission_required_ajax(
    perm=("meals.change_goal",),
    msg="You don't have permission to enable goals,",
    reason="Only business managers may enable goals.",
)
def enable_goals(request):
    return _enable_goals(request, True)


@login_required
@auth.permission_required_ajax(
    perm=("meals.change_goal",),
    msg="You don't have permission to disable goals,",
    reason="Only business managers may disable goals.",
)
def disable_goals(request):
    return _enable_goals(request, False)


@login_required
@auth.user_is_admin_ajax(msg="Only administrators may create a manufacturing schedule.")
def schedule(request):
    # TODO: Permission checking is more complicated here
    goal_items = GoalItem.objects.filter(
        Q(schedule__isnull=False) | Q(goal__is_enabled=True)
    )
    goal_objs = Goal.objects.filter(
        pk__in=set(goal_items.values_list("goal", flat=True).distinct())
    )
    if request.method == "POST":
        logger.info("raw POST=%s", request.POST)
        formset = GoalScheduleFormset(request.POST, goal_items=goal_items)
        if formset.is_valid():
            with transaction.atomic():
                instances = []
                deleted = 0
                for form in formset:
                    if not form.should_delete():
                        instances.append(form.save(commit=True))
                    else:
                        # Unschedule this goal item
                        num_deleted, _ = GoalSchedule.objects.filter(
                            goal_item=form.item
                        ).delete()
                        deleted += num_deleted
            msg = (
                f"Successfully scheduled {len(instances)} and "
                f"unscheduled {deleted} goals."
            )
            messages.info(request, msg)
            logger.info(msg)
            return redirect("schedule")
    else:
        formset = GoalScheduleFormset(goal_items=goal_items)

    return render(
        request,
        template_name="meals/goal/schedule.html",
        context={"formset": formset, "goals": goal_objs, "goal_items": goal_items},
    )


@login_required
@auth.permission_required_ajax(
    perm=("meals.view_goal",),
    msg="You do not have permission to the manufacturing report,",
    reason="Only analysts view the manufacturing report",
)
def schedule_report(request):
    line_shortname = request.GET.get("l", "")
    start = request.GET.get("s", "")
    end = request.GET.get("e", "")
    logger.info("Line: %s, start: %s, end: %s", line_shortname, start, end)
    qs = ManufacturingLine.objects.filter(shortname__iexact=line_shortname)
    if not qs.exists():
        messages.error(request, f"Invalid manufacturing line name: '{line_shortname}'")
        return redirect("error")

    query = Q(line=qs[0])
    try:
        if start:
            start = timezone.make_aware(datetime.strptime(start, "%Y-%m-%d"))
            query &= Q(start_time__gte=start)
        if end:
            end = timezone.make_aware(datetime.strptime(end, "%Y-%m-%d"))
            query &= Q(end_time__lte=end) | Q(end_time__isnull=True)
    except ValueError as e:
        messages.error(request, f"Invalid date: {str(e)}")
        return redirect("error")
    schedules = GoalSchedule.objects.filter(query)
    if schedules.count() == 0:
        messages.error(
            request,
            "Unable to generate report: no goal was scheduled on "
            f"'{line_shortname}' between the specified timespan.",
        )
        return redirect("error")
    formula_ids = set(schedules.values_list("goal_item__sku__formula", flat=True))
    ingredients = FormulaIngredient.objects.filter(formula_id__in=formula_ids)
    goal_ids = set(schedules.values_list("goal_item__goal", flat=True))
    goal_objs = Goal.objects.filter(pk__in=goal_ids)
    result = SortedDefaultDict(lambda: Decimal(0.0), key=operator.attrgetter("pk"))
    for goal in goal_objs:
        _calculate_report(goal, result=result)
    return render(
        request,
        template_name="meals/goal/schedule_report.html",
        context={
            "time": timezone.now(),
            "line": qs[0],
            "start": start,
            "end": end,
            "activities": schedules,
            "formulas": ingredients,
            "ingredients": result.items(),
        },
    )


@login_required
def completion_time(request):
    start_time = request.GET.get("start", "")
    hours = request.GET.get("hours", "")
    try:
        start_time = datetime.fromisoformat(start_time)
    except ValueError:
        return JsonResponse(
            {"error": "Invalid start time format. Expected ISO format.", "resp": None}
        )

    try:
        hours = int(hours)
    except ValueError:
        return JsonResponse(
            {"error": "Invalid number of hours. Expected an integer.", "resp": None}
        )
    end_time = utils.compute_end_time(start_time, hours)
    return JsonResponse({"error": None, "resp": end_time.isoformat()})
