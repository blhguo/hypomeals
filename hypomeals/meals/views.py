import operator
import time

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

from meals.forms import SkuFilterForm, EditSkuForm, FormulaFormset
from meals.models import Sku, Ingredient, ProductLine, SkuIngredient

import logging


logger = logging.getLogger(__name__)


def index(request):
    return render(request, template_name="meals/index.html")


@login_required
def logout_view(request):
    logout(request)
    return redirect("index")


############################  SKU Views  ###############################
@login_required
def sku(request):
    start = time.time()
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
            {
                "ingredient": formula.ingredient_number.name,
                "quantity": formula.quantity,
            }
            for formula in formulas
        ]
        formset = FormulaFormset(initial=initial_data, form_kwargs={"sku": sku})
    return render(
        request,
        template_name="meals/formula/edit_formula.html",
        context={"sku": sku, "formset": formset, "in_flow": in_flow},
    )


@login_required
def autocomplete_ingredients(request):
    term = request.GET.get("term", "")
    ingredients = list(
        map(
            operator.attrgetter("name"),
            Ingredient.objects.filter(name__istartswith=term),
        )
    )
    return JsonResponse(ingredients, safe=False)


@login_required
def autocomplete_product_lines(request):
    term = request.GET.get("term", "")
    ingredients = list(
        map(
            operator.attrgetter("name"),
            ProductLine.objects.filter(name__istartswith=term),
        )
    )
    return JsonResponse(ingredients, safe=False)


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
