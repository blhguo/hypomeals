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
from meals.forms import SkuFilterForm, EditSkuForm
from meals.models import Sku, Ingredient, ProductLine

from .bulk_export import process_export
from .forms import ImportCsvForm, ImportZipForm
from .models import Sku


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
    if request :
        response = process_export(Sku.objects.all())
    return response


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
