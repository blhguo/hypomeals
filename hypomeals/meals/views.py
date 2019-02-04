import functools
import logging
import time
import csv
import tempfile
import io
from reportlab.lib.pagesizes import letter, inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from django.core.files import File

import jsonpickle
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction, DatabaseError
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import HttpResponse, FileResponse

from meals.forms import FormulaFormset
from meals.forms import IngredientFilterForm, EditIngredientForm
from meals.forms import SkuFilterForm, EditSkuForm
from meals.forms import SkuQuantityForm
from meals.models import Sku, Ingredient, ProductLine, ManufactureGoal, ManufactureDetail
from meals.models import SkuIngredient
from .bulk_export import export_skus
from .forms import ImportCsvForm, ImportZipForm

logger = logging.getLogger(__name__)


def index(request):
    return render(request, template_name="meals/index.html")


@login_required
def import_page(request):
    template = "meals/import/import.html"

    if request.method == "POST":
        csv_file_form = ImportCsvForm(request.POST, request.FILES)
        zip_file_form = ImportZipForm(request.POST, request.FILES)
        if (csv_file_form.has_changed() and csv_file_form.is_valid()) or (
            zip_file_form.has_changed() and zip_file_form.is_valid()
        ):
            return redirect("import_landing")
        return render(
            request,
            template_name=template,
            context={"csv_form": csv_file_form, "zip_form": zip_file_form},
        )
    csv_file_form = ImportCsvForm()
    zip_file_form = ImportZipForm()
    return render(
        request, template, {"csv_form": csv_file_form, "zip_form": zip_file_form}
    )


@login_required
def import_landing(request):
    response = render(request, template_name="meals/import/import_landing.html")
    return response


@login_required
def export_test(request):
    response = render(request, template_name="meals/index.html")
    if request:
        response = export_skus(Sku.objects.all())
    return response


@login_required
def logout_view(request):
    logout(request)
    return redirect("index")


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


def show_one_goal(request, goal_id = -1):
    errors = ""
    message = ""
    if request.method == 'POST':
        form = SkuQuantityForm(request.POST)
        file = generate_csv_file(request.POST)
        if form.is_valid():
            form.clean()
            form.save(request, file)
            form_name = request.POST["form_name"]
            message = "You form has been saved successfully to %s" % (form_name,)
            return render(
                request,
                template_name="meals/show_one_goal.html",
                context={"form": form,
                         "errors": errors,
                         "message": message
                         },
            )
        else:
            errors = form.errors
    else:
        form_content = ""
        if goal_id != -1:
            form_content = find_goal(goal_id, request.user)
            form = SkuQuantityForm(form_content)
        else:
            form = SkuQuantityForm()
    return render(request,
                  template_name="meals/show_one_goal.html",
                  context = {"form": form,
                             "errors": errors,
                             "message": message
                             })

def generate_report(request):
    if request.method == "POST":
        cnt = 0
        data = []
        report = {}
        while True:
            sku_index = "sku_" + str(cnt)
            quantity_index = "quantity_" + str(cnt)
            if sku_index in request.POST and quantity_index in request.POST:
                sku_name = request.POST[sku_index]
                quantity4sku = request.POST[quantity_index]
                sku = Sku.objects.filter(name=sku_name)
                if (len(sku) > 0):
                    sku = sku[0]
                else:
                    cnt += 1
                    continue
                sku_ingredient_pairs = SkuIngredient.objects.filter(
                    sku_number=sku.number
                )
                for sku_ingredient_pair in sku_ingredient_pairs:
                    ingredient_number = sku_ingredient_pair.ingredient_number
                    if ingredient_number not in report:
                        report[ingredient_number] = 0
                    report[ingredient_number] += float(sku_ingredient_pair.quantity) * float(quantity4sku)
            else:
                break
            cnt += 1

        # with open('test.csv', 'w', newline='') as csvfile:
        #     writer = csv.writer(csvfile)
        #     writer.writerow(["Ingredient Name", "Ingredient Quantity"])
        #     for key, value in report.items():
        #         writer.writerow([key, value])

        return render(request, template_name="meals/calculation.html", context = {"report": report})

def generate_csv_file(entries):
    cnt = 0
    data = []
    report = {}
    tf = tempfile.mktemp()
    with open(tf, "w", newline='') as f:
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

def save_goal(request):
    file = generate_csv_file(request.POST)
    form = SkuQuantityForm(request.POST)
    # form.clean()
    form.save(request, file)
    form_name = request.POST["form_name"]
    return render(
        request,
        template_name="meals/save_succeed.html",
        context={"form_name": form_name},
    )

def download_goal(request):
    save_goal(request)
    goal = ManufactureGoal.objects.filter(form_name = request.POST["form_name"]).order_by('-save_time',)
    response = HttpResponse(goal[0].file)
    response['content_type'] = 'text/csv'
    response['Content-Disposition'] = 'attachment;filename=manufacture_goal.csv'
    return response

def download_calculation(request):
    tf = tempfile.mktemp()
    with open(tf, "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Ingredient Name", "Ingredient Quantity"])
        for k,v in request.POST.items():
            if (k == "csrfmiddlewaretoken"):
                continue
            writer.writerow([k, v])
    file = File(open(tf, "rb"))
    response = HttpResponse(file)
    response['content_type'] = 'text/csv'
    response['Content-Disposition'] = 'attachment;filename=manufacture_goal.csv'
    return response

def generate_calculation_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename=calculation_goal.pdf'
    doc = SimpleDocTemplate(response, pagesize=letter)
    # container for the 'Flowable' objects
    elements = []
    n = len(request.POST)
    data = []
    data.append(["Ingredient Name", "Ingredient Quantity"])
    cnt = 0
    for k, v in request.POST.items():
        if (k == "csrfmiddlewaretoken"):
            continue
        cnt += 1
        data.append([k, v])
    t=Table(data, 2*[3*inch], n*[0.4*inch])
    t.setStyle(TableStyle([('BOX', (0,0), (-1,-1), 0.25, colors.black), ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),]))
    elements.append(t)
    doc.build(elements)
    return response


def show_all_goals(request):
    all_goals = ManufactureGoal.objects.filter(user=request.user)
    return render(
        request,
        template_name="meals/show_all_goals.html",
        context={"all_goals": all_goals},
    )

########################### Ingredient Views ###########################
@login_required
def ingredient(request):
    start = time.time()
    if request.method == "POST":
        form = IngredientFilterForm(request.POST)
        if form.is_valid():
            ingredients = form.query()
        else:
            ingredients = Paginator(Ingredient.objects.all(), 50)
    else:
        form = IngredientFilterForm()
        ingredients = Paginator(Ingredient.objects.all(), 50)
    page = getattr(form, "cleaned_data", {"page_num": 1}).get("page_num", 1)
    if page > ingredients.num_pages:
        page = 1
        form.intial["page_num"] = 1
    end = time.time()
    return render(
        request,
        template_name="meals/ingredients/ingredient.html",
        context={
            "ingredients": ingredients.page(page),
            "form": form,
            "pages": range(1, ingredients.num_pages + 1),
            "current_page": page,
            "duration": "{:0.3f}".format(end - start),
        },
    )


@login_required
@csrf_exempt
@require_POST
def remove_ingredients(request):
    to_remove = jsonpickle.loads(request.POST.get("to_remove", "[]"))
    try:
        with transaction.atomic():
            num_deleted, _ = Ingredient.objects.filter(pk__in=to_remove).delete()
            return JsonResponse(
                {"error": None, "resp": f"Removed {num_deleted} Ingredients"}
            )
    except DatabaseError as e:
        return JsonResponse({"error": str(e), "resp": "Not removed"})


@login_required
def add_ingredient(request):
    if request.method == "POST":
        form = EditIngredientForm(request.POST)
        if form.is_valid():
            instance = form.save()
            messages.info(request, f"Ingredient '{instance.name}' added successfully")
            return redirect("ingredient")
    else:
        form = EditIngredientForm()
    return render(
        request,
        template_name="meals/ingredients/edit_ingredient.html",
        context={"form": form},
    )


@login_required
def edit_ingredient(request, ingredient_number):

    instance = get_object_or_404(Ingredient, number=ingredient_number)
    if request.method == "POST":
        form = EditIngredientForm(request.POST, instance=instance)
        if form.is_valid():
            instance = form.save()
            messages.info(request, f"Successfully saved {instance.name}")
            return redirect("ingredient")
    else:
        form = EditIngredientForm(instance=instance)
    return render(
        request,
        template_name="meals/ingredients/edit_ingredient.html",
        context={
            "form": form,
            "ingredient_number": ingredient_number,
            "ingredient_name": str(instance),
            "editing": True,
        },
    )


############################  SKU Views  ###############################
@login_required
def sku(request):
    start = time.time()
    export = request.GET.get("export", "0") == "1"
    export_formula = request.GET.get("formulas", "0") == "1"
    if request.method == "POST":
        form = SkuFilterForm(request.POST)
        if form.is_valid():
            skus = form.query()
        else:
            skus = Paginator(Sku.objects.all(), 50)
    else:
        form = SkuFilterForm()
        skus = Paginator(Sku.objects.all(), 50)
    page = getattr(form, "cleaned_data", {"page_num": 1}).get("page_num", 1)
    if page > skus.num_pages:
        # For whatever reason, if the page being requested is larger than the actual
        # number of pages, just start over from the first page.
        page = 1
        form.initial["page_num"] = 1
    end = time.time()
    if export:
        return export_skus(skus.object_list, include_formulas=export_formula)
    return render(
        request,
        template_name="meals/sku/sku.html",
        context={
            "skus": skus.page(page),
            "form": form,
            "pages": range(1, skus.num_pages + 1),
            "current_page": page,
            "duration": "{:0.3f}".format(end - start),
        },
    )


@login_required
def edit_sku(request, sku_number):
    instance = get_object_or_404(Sku, number=sku_number)
    if request.method == "POST":
        form = EditSkuForm(request.POST, instance=instance)
        if form.is_valid():
            instance = form.save()
            messages.info(request, f"Successfully saved SKU #{instance.pk}")
            return redirect("sku")
    else:
        form = EditSkuForm(instance=instance)
    return render(
        request,
        template_name="meals/sku/edit_sku.html",
        context={
            "form": form,
            "sku_number": sku_number,
            "sku_name": str(instance),
            "editing": True,
        },
    )


@login_required
def add_sku(request):
    skip = request.GET.get("skip", "0") == "1"

    if request.method == "POST":
        form = EditSkuForm(request.POST)
        if form.is_valid():
            instance = form.save()
            messages.info(request, f"SKU #{instance.pk} has been saved successfully.")
            if skip:
                return redirect("sku")
            return redirect("edit_formula", instance.pk)
    else:
        form = EditSkuForm()
    return render(
        request,
        template_name="meals/sku/edit_sku.html",
        context={"form": form, "editing": False},
    )


@login_required
@csrf_exempt
@require_POST
def remove_skus(request):
    to_remove = jsonpickle.loads(request.POST.get("to_remove", "[]"))
    try:
        with transaction.atomic():
            num_deleted, _ = Sku.objects.filter(pk__in=to_remove).delete()
            return JsonResponse({"error": None, "resp": f"Removed {num_deleted} SKUs"})
    except DatabaseError as e:
        return JsonResponse({"error": str(e), "resp": "Not removed"})


##################### Formula Views ########################
@login_required
def edit_formula(request, sku_number):
    sku = get_object_or_404(Sku, pk=sku_number)
    in_flow = request.GET.get("in_flow", "0") == "1"
    if request.method == "POST":
        logger.debug("Raw POST data: %s", request.POST)
        formset = FormulaFormset(request.POST, form_kwargs={"sku": sku})
        if formset.is_valid():
            logger.info("Cleaned data: %s", formset.cleaned_data)
            saved = []
            with transaction.atomic():
                SkuIngredient.objects.filter(sku_number=sku).delete()
                for form, data in zip(formset.forms, formset.cleaned_data):
                    if "DELETE" not in data or data["DELETE"]:
                        continue
                    saved.append(form.save(commit=False))
                if saved:
                    SkuIngredient.objects.bulk_create(saved)
            messages.info(request, f"Successfully inserted {len(saved)} ingredients.")
            return redirect("sku")
    else:
        formulas = SkuIngredient.objects.filter(sku_number=sku_number)
        initial_data = [
            {"ingredient": formula.ingredient_number.name, "quantity": formula.quantity}
            for formula in formulas
        ]
        formset = FormulaFormset(initial=initial_data, form_kwargs={"sku": sku})
    return render(
        request,
        template_name="meals/formula/edit_formula.html",
        context={"sku": sku, "formset": formset, "in_flow": in_flow},
    )


#################### Autocomplete #######################
def autocomplete(request, manager, key="name"):
    term = request.GET.get("term", "")
    items = list(
        manager.filter(name__istartswith=term).distinct().values_list(key, flat=True)
    )
    return JsonResponse(items, safe=False)


autocomplete_skus = login_required(functools.partial(autocomplete, manager=Sku.objects))
autocomplete_ingredients = login_required(
    functools.partial(autocomplete, manager=Ingredient.objects)
)
autocomplete_product_lines = login_required(
    functools.partial(autocomplete, manager=ProductLine.objects)
)
