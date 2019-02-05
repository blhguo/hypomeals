import logging
import time

import jsonpickle
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db import transaction, DatabaseError
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from meals import auth
from meals.forms import SkuFilterForm, EditSkuForm
from meals.models import Sku
from ..bulk_export import export_skus

logger = logging.getLogger(__name__)


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
@permission_required("meals.change_sku", raise_exception=True)
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
@permission_required("meals.add_sku", raise_exception=True)
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
@auth.permission_required_ajax(perm="meals.delete_sku")
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
