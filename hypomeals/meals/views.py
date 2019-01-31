import operator
import time

import jsonpickle
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction, DatabaseError
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from meals.forms import SkuFilterForm, EditSkuForm,
    IngredientFilterForm, EditIngredientForm
from meals.models import Sku, Ingredient, ProductLine


def index(request):
    return render(request, template_name="meals/index.html")


@login_required
def logout_view(request):
    logout(request)
    return redirect("index")

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
    return render(request,
                  template_name="meals/ingredients/ingredient.html",
                  context={"ingredients":ingredients.page(page),
                           "form":form,
                           "pages": range(1, ingredients.num_pages + 1),
                           "current_page": page,
                           "duration": "{:0.3f}".format(end-start),
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
                {"error": None,
                 "resp": f"Removed {num_deleted} Ingredients"})
    except DatabaseError as e:
        return JsonResponse({"error": str(e), "resp": "Not removed"})

@login_required
def add_ingredient(request):
    if request.method == "POST":
        form = EditIngredientForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("ingredient")
    else:
        form = EditIngredientForm()
    return render(
        request,
        template_name="meals/ingredients/edit.html",
        context={"form": form})

@login_required
def edit_ingredient(request, ingredient_number):

    instance = get_object_or_404(Ingredient, number=ingredient_number)
    if request.method == "POST":
        form = EditIngredientForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return redirect("ingredient")
    else:
        form = EditIngredientForm(instance=instance)
    return render(
        request,
        template_name="meals/ingredients/edit.html",
        context={
            "form": form,
            "ingredient_number": ingredient_number,
            "ingredient_name": str(instance),
            "editing": True,
        }
    )

@login_required
def autocomplete_skus(request):
    term = request.GET.get("term", "")
    ingredients = list(
        map(
            operator.attrgetter("name"),
            Sku.objects.filter(name__istartswith=term),
        )
    )
    return JsonResponse(ingredients, safe=False)
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
            form.save()
            return redirect("sku")
    else:
        form = EditSkuForm(instance=instance)
    return render(
        request,
        template_name="meals/sku/edit.html",
        context={
            "form": form,
            "sku_number": sku_number,
            "sku_name": str(instance),
            "editing": True,
        },
    )


@login_required
def add_sku(request):
    if request.method == "POST":
        form = EditSkuForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("sku")
    else:
        form = EditSkuForm()
    return render(request, template_name="meals/sku/edit.html", context={"form": form})


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
