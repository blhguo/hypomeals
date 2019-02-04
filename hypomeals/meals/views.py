import functools
import logging
import time

import jsonpickle
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction, DatabaseError
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from meals.forms import FormulaFormset
from meals.forms import IngredientFilterForm, EditIngredientForm
from meals.forms import SkuFilterForm, EditSkuForm
from meals.models import Sku, Ingredient, ProductLine
from meals.models import SkuIngredient
from .bulk_export import export_skus, export_ingredients
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
def logout_view(request):
    logout(request)
    return redirect("index")


########################### Ingredient Views ###########################
@login_required
def ingredient(request):
    start = time.time()
    export = request.GET.get("export", "0") == "1"
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
    if export:
        return export_ingredients(ingredients.object_list)
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
@require_POST
def remove_ingredients(request):
    to_remove = jsonpickle.loads(request.POST.get("to_remove", "[]"))
    try:
        with transaction.atomic():
            num_deleted, _ = Ingredient.objects.filter(pk__in=to_remove).delete()
        return JsonResponse(
            {"error": None, "resp": f"Successfully removed {num_deleted} Ingredients"}
        )
    except DatabaseError as e:
        return JsonResponse({"error": str(e), "resp": "Not removed"})


@login_required
def add_ingredient(request):
    if request.method == "POST":
        form = EditIngredientForm(request.POST)
        if form.is_valid():
            instance = form.save()
            message = f"Ingredient '{instance.name}' added successfully"
            if request.is_ajax():
                resp = {"error": None, "resp": None, "success": True, "alert": message}
                return JsonResponse(resp)
            messages.info(request, message)
            return redirect("ingredient")
    else:
        form = EditIngredientForm()

    form_html = render_to_string(
        template_name="meals/ingredients/edit_ingredient_form.html",
        context={"form": form},
        request=request,
    )

    if request.is_ajax():
        resp = {"error": "Invalid form", "resp": form_html}
        return JsonResponse(resp)
    return render(
        request,
        template_name="meals/ingredients/edit_ingredient.html",
        context={"form": form, "form_html": form_html},
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

    form_html = render_to_string(
        template_name="meals/ingredients/edit_ingredient_form.html",
        context={"form": form, "editing": True, "ingredient": instance},
        request=request,
    )
    return render(
        request,
        template_name="meals/ingredients/edit_ingredient.html",
        context={"form": form, "form_html": form_html, "editing": True},
    )


############################  SKU Views  ###############################
@login_required
def sku(request):
    start = time.time()
    export = request.GET.get("export", "0") == "1"
    export_formulas = request.GET.get("formulas", "0") == "1"
    export_product_lines = request.GET.get("pl", "0") == "1"
    logger.info(
        "Exporting [SKU Formulas Product Lines] = [%s %s %s]",
        export,
        export_formulas,
        export_product_lines,
    )
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
        return export_skus(
            skus.object_list,
            include_formulas=export_formulas,
            include_product_lines=export_product_lines,
        )
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
@require_POST
def remove_skus(request):
    to_remove = jsonpickle.loads(request.POST.get("to_remove", "[]"))
    try:
        with transaction.atomic():
            num_deleted, _ = Sku.objects.filter(pk__in=to_remove).delete()
        return JsonResponse(
            {"error": None, "resp": f"Successfully removed {num_deleted} SKUs"}
        )
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
