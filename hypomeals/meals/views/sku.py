import logging
import time
import json

import jsonpickle
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db import transaction, DatabaseError
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from meals import auth
from meals.forms import SkuFilterForm, EditSkuForm
from meals.models import Sku, ManufacturingLine, SkuManufacturingLine
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
        params = {
            "key_word": "",
            "ingredients": "",
            "product_lines": "",
            "formulas": "",
            "page_num": 1,
            "num_per_page": 50,
            "sort_by": "name",
            "keyword": "",
        }
        if "formula" in request.GET:
            formula_name = request.GET["formula"]
            params["formulas"] = formula_name

        form = SkuFilterForm(params)
        if form.is_valid():
            skus = form.query()
        else:
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
            num_deleted, result = Sku.objects.filter(pk__in=to_remove).delete()
            logger.info("removed %d SKUs: %s", num_deleted, result)
        return JsonResponse(
            {"error": None, "resp": f"Successfully removed {result['meals.Sku']} SKUs"}
        )
    except DatabaseError as e:
        return JsonResponse({"error": str(e), "resp": "Not removed"})


@login_required
@auth.permission_required_ajax(perm="meals.delete_sku")
def view_lines(request):
    skus = json.loads(request.GET.get("skus", "[]"))
    all_set = set()
    partial_set = set()
    none_set = set()
    for ml in ManufacturingLine.objects.all():
        all_set.add(ml)
        none_set.add(ml)
    for sku in skus:
        sku = int(sku)
        sku_obj = Sku.objects.filter(number=sku)[0]
        all_mls = SkuManufacturingLine.objects.filter(sku=sku_obj)
        manufacturing_lines = {ml.line for ml in all_mls}
        all_set &= manufacturing_lines
        partial_set |= manufacturing_lines
    partial_set -= all_set
    none_set -= all_set
    none_set -= partial_set
    form_html = render_to_string(
        request=request,
        template_name="meals/sku/bulk_edit.html",
        context={
            "all_set": all_set,
            "partial_set": partial_set,
            "none_set": none_set,
            "sku_number": len(skus),
        },
    )

    if request.is_ajax():
        resp = {"error": "Success", "resp": form_html}
        return JsonResponse(resp)

    return render(
        request,
        template_name="meals/sku/bulk_edit.html",
        context={
            "all_set": all_set,
            "partial_set": partial_set,
            "none_set": none_set,
            "sku_number": len(skus),
        },
    )


@login_required
@auth.permission_required_ajax(perm="meals.delete_sku")
def edit_lines(request):
    skus = json.loads(request.GET.get("skus", "[]"))
    checked = json.loads(request.GET.get("checked", "[]"))
    unchecked = json.loads(request.GET.get("unchecked", "[]"))

    created = 0
    deleted = 0
    for sku_number in skus:
        sku = Sku.objects.filter(number=sku_number)[0]
        for ml_sn in checked:
            ml = ManufacturingLine.objects.filter(shortname=ml_sn)[0]
            exist = SkuManufacturingLine.objects.filter(sku=sku, line=ml).exists()
            if not exist:
                created += 1
                SkuManufacturingLine.objects.create(sku=sku, line=ml)
        for ml_sn in unchecked:
            ml = ManufacturingLine.objects.filter(shortname=ml_sn)[0]
            exist = SkuManufacturingLine.objects.filter(sku=sku, line=ml).exists()
            if exist:
                deleted += 1
                SkuManufacturingLine.objects.filter(sku=sku, line=ml).delete()

    resp = {
        "error": f"Success in creating {created} new mappings, deleting {deleted} old mappings"
    }
    return JsonResponse(resp)
