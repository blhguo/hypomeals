import logging
import csv
import tempfile
from reportlab.lib.pagesizes import letter, inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from django.core.files import File

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse

from meals.forms import SkuQuantityForm
from meals.models import (
    Sku,
    Ingredient,
    ProductLine,
    ManufactureGoal,
    ManufactureDetail,
)
from meals.models import SkuIngredient

logger = logging.getLogger(__name__)


def find_goal(goal_id, user):
    goal = ManufactureGoal.objects.filter(pk=goal_id)
    goal = goal[0]
    sku_quantities = ManufactureDetail.objects.filter(form_name=goal)
    request = {}
    request["form_name"] = goal.form_name
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
def show_one_goal(request, goal_id=-1):
    errors = ""
    message = ""
    if request.method == "POST":
        form = SkuQuantityForm(request.POST)
        file = generate_csv_file(request.POST)
        if form.is_valid():
            form.clean()
            form.save_file(request, file)
            form_name = request.POST["form_name"]
            message = "You form has been saved successfully to %s" % (form_name,)
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
        template_name="meals/show_one_goal.html",
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
            sku = Sku.objects.filter(name=sku_name)
            if sku:
                sku = sku[0]
            else:
                cnt += 1
                continue
            sku_ingredient_pairs = SkuIngredient.objects.filter(sku_number=sku.number)
            for sku_ingredient_pair in sku_ingredient_pairs:
                ingredient_number = sku_ingredient_pair.ingredient_number
                if ingredient_number not in report:
                    report[ingredient_number] = 0
                report[ingredient_number] += float(
                    sku_ingredient_pair.quantity
                ) * float(quantity4sku)
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
        writer.writerow(["SKU Name", "SKU Quantity"])
        while True:
            sku_index = "sku_" + str(cnt)
            quantity_index = "quantity_" + str(cnt)
            if sku_index in entries and quantity_index in entries:
                sku_name = entries[sku_index]
                quantity4sku = entries[quantity_index]
                writer.writerow([sku_name, quantity4sku])
            else:
                break
            cnt += 1
    file = File(open(tf, "rb"))
    return file


@login_required
def save_goal(request):
    file = generate_csv_file(request.POST)
    form = SkuQuantityForm(request.POST)
    # form.clean()
    form.save_file(request, file)
    form_name = request.POST["form_name"]
    return render(
        request,
        template_name="meals/save_succeed.html",
        context={"form_name": form_name},
    )


@login_required
def download_goal(request):
    save_goal(request)
    goal = ManufactureGoal.objects.filter(form_name=request.POST["form_name"]).order_by(
        "-save_time"
    )
    response = HttpResponse(goal[0].file)
    response["content_type"] = "text/csv"
    response["Content-Disposition"] = "attachment;filename=manufacture_goal.csv"
    return response


@login_required
def download_calculation(request):
    tf = tempfile.mktemp()
    with open(tf, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Ingredient Name", "Ingredient Quantity"])
        for k, v in request.POST.items():
            if k == "csrfmiddlewaretoken":
                continue
            writer.writerow([k, v])
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
    data.append(["Ingredient Name", "Ingredient Quantity"])
    cnt = 0
    for k, v in request.POST.items():
        if k == "csrfmiddlewaretoken":
            continue
        cnt += 1
        data.append([k, v])
    t = Table(data, 2 * [3 * inch], n * [0.4 * inch])
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
def show_all_goals(request):
    all_goals = ManufactureGoal.objects.filter(user=request.user)
    return render(
        request,
        template_name="meals/show_all_goals.html",
        context={"all_goals": all_goals},
    )


@login_required
def find_product_line(request):
    pd = request.GET.get("product_line", None)
    ingredients = Sku.objects.filter(product_line__name=pd)
    result = {}
    result["ingredients"] = [ingredient.name for ingredient in ingredients]
    return JsonResponse(result)
