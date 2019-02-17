import logging
import csv
import tempfile

from django.contrib import messages
from django.db import transaction
from django.utils.datetime_safe import datetime
from reportlab.lib.pagesizes import letter, inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from django.core.files import File

from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse

from meals.forms import SkuQuantityForm, SkuQuantityFormset, GoalForm
from meals.models import Sku, ProductLine, Goal, GoalItem, Ingredient
from meals.models import FormulaIngredient

logger = logging.getLogger(__name__)


def find_goal(goal_id, user):
    goal = Goal.objects.filter(pk=goal_id)
    goal = goal[0]
    sku_quantities = GoalItem.objects.filter(name=goal)
    request = {}
    request["name"] = goal.name
    skus = set()
    for index, sku_quantity in enumerate(sku_quantities):
        sku_name = "sku_" + str(index)
        quantity_name = "quantity_" + str(index)
        request[sku_name] = sku_quantity.sku
        request[quantity_name] = sku_quantity.quantity
        skus.add(sku_quantity.sku)
    request["skus"] = skus
    request["user"] = user
    return request


@login_required
@permission_required("meals.add_goal", "meals.change_goal")
def edit_goal(request, goal_id=-1):
    if goal_id != -1:
        goal_obj = get_object_or_404(Goal, pk=goal_id)
    else:
        goal_obj = None
    if request.method == "POST":
        formset = SkuQuantityFormset(request.POST)
        form = GoalForm(request.POST)
        if form.is_valid() and formset.is_valid():
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
                GoalItem.objects.filter(goal=goal_obj).delete()
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
            messages.info(request, f"Successfully saved goal {goal_obj.name}")
            return redirect("edit_goal", goal_obj.pk)

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
def goal(request, goal_id=-1):
    errors = ""
    message = ""
    if request.method == "POST":
        form = SkuQuantityForm(request.POST)
        if form.is_valid():
            file = generate_csv_file(request.POST)
            form.save_file(request, file)
            name = request.POST["name"]
            message = "You form has been saved successfully to %s" % (name,)
        else:
            errors = form.errors
    else:
        form_content = ""
        if goal_id != -1:
            form_content = find_goal(goal_id, request.user)
            form = SkuQuantityForm(form_content)
        else:
            form = SkuQuantityForm()
    product_lines = ProductLine.objects.all()
    return render(
        request,
        template_name="meals/goal/edit_goal.html",
        context={
            "form": form,
            "errors": errors,
            "message": message,
            "product_lines": product_lines,
        },
    )


@login_required
def generate_report(request):
    report = {}
    cnt = 0
    while True:
        sku_index = "sku_" + str(cnt)
        quantity_index = "quantity_" + str(cnt)
        if sku_index in request.POST and quantity_index in request.POST:
            sku_name = request.POST[sku_index]
            quantity4sku = request.POST[quantity_index]
            sku = Sku.from_name(sku_name)
            if sku is None:
                cnt += 1
                continue
            sku_ingredient_pairs = FormulaIngredient.objects.filter(sku_number=sku)
            for sku_ingredient_pair in sku_ingredient_pairs:
                ingredient_number = sku_ingredient_pair.ingredient_number
                if ingredient_number not in report:
                    report[ingredient_number] = 0
                try:
                    report[ingredient_number] += float(
                        sku_ingredient_pair.quantity
                    ) * float(quantity4sku)
                except ValueError:
                    pass
        else:
            break
        cnt += 1
    return render(
        request, template_name="meals/calculation.html", context={"report": report}
    )


def generate_csv_file(entries):
    cnt = 0
    tf = tempfile.mktemp()
    with open(tf, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["SKU#", "SKU Name", "SKU Quantity"])
        while True:
            sku_index = "sku_" + str(cnt)
            quantity_index = "quantity_" + str(cnt)
            if sku_index in entries and quantity_index in entries:
                sku_name = entries[sku_index]
                sku = Sku.from_name(name=sku_name)
                quantity4sku = entries[quantity_index]
                writer.writerow([sku.number, sku_name, quantity4sku])
            else:
                break
            cnt += 1
    file = File(open(tf, "rb"))
    return file


@login_required
def save_goal(request):
    file = generate_csv_file(request.POST)
    form = SkuQuantityForm(request.POST)
    form.clean()
    form.save_file(request, file)
    name = request.POST["name"]
    return render(
        request, template_name="meals/goal/save_succeed.html", context={"name": name}
    )


@login_required
def download_goal(request):
    save_goal(request)
    goal = Goal.objects.filter(name=request.POST["name"]).order_by("-save_time")
    if goal:
        response = HttpResponse(goal[0].file)
    else:
        response = HttpResponse()
    response["content_type"] = "text/csv"
    response["Content-Disposition"] = "attachment;filename=manufacture_goal.csv"
    return response


@login_required
def download_calculation(request):
    tf = tempfile.mktemp()
    with open(tf, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Ingr#", "Ingredient Name", "Ingredient Quantity"])
        for k, v in request.POST.items():
            if k == "csrfmiddlewaretoken":
                continue
            ingr = Ingredient.objects.get(name=k)
            writer.writerow([ingr.number, k, v])
    file = File(open(tf, "rb"))
    response = HttpResponse(file)
    response["content_type"] = "text/csv"
    response["Content-Disposition"] = "attachment;filename=manufacture_goal.csv"
    return response


@login_required
def generate_calculation_pdf(request):
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "attachment;filename=calculation_goal.pdf"
    doc = SimpleDocTemplate(response, pagesize=letter)
    # container for the 'Flowable' objects
    elements = []
    n = len(request.POST)
    data = []
    data.append(["Ingr#", "Ingredient Name", "Ingredient Quantity"])
    cnt = 0
    for k, v in request.POST.items():
        if k == "csrfmiddlewaretoken":
            continue
        ingr = Ingredient.objects.get(name=k)
        cnt += 1
        data.append([ingr.number, k, v])
    t = Table(data, 3 * [2 * inch], n * [0.4 * inch])
    t.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
            ]
        )
    )
    elements.append(t)
    doc.build(elements)
    return response


@login_required
def goals(request):
    all_goals = Goal.objects.filter(user=request.user).order_by("-save_time")
    return render(
        request,
        template_name="meals/goal/show_all_goals.html",
        context={"all_goals": all_goals},
    )


@login_required
def filter_skus(request):
    pd = request.GET.get("product_line", None)
    skus = Sku.objects.filter(product_line__name=pd)
    result = {"error": None, "resp": [sku.verbose_name for sku in skus]}
    return JsonResponse(result)
