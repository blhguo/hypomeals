import logging
import time

import jsonpickle
from django.contrib import messages
from django.contrib.auth.decorators import (
    login_required,
    permission_required,
)
from django.core.paginator import Paginator
from django.db import transaction, DatabaseError
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from meals import auth
from meals.forms import IngredientFilterForm, EditIngredientForm
from meals.models import Ingredient
from ..bulk_export import export_ingredients

logger = logging.getLogger(__name__)


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
@permission_required("meals.add_ingredient", raise_exception=True)
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
@auth.permission_required_ajax(perm="meals.edit_ingredient")
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


@login_required
@require_POST
@auth.permission_required_ajax(perm="meals.remove_ingredient")
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