import logging
import time

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
from meals.forms import Product_LineFilterForm, EditProduct_LineForm
from meals.models import ProductLine

logger = logging.getLogger(__name__)


@login_required
def product_line(request):
    start = time.time()
    if request.method == "POST":
        form = Product_LineFilterForm(request.POST)
        if form.is_valid():
            product_lines = form.query()
        else:
            product_lines = Paginator(ProductLine.objects.all(), 50)
    else:
        form = Product_LineFilterForm()
        product_lines = Paginator(ProductLine.objects.all(), 50)
    page = getattr(form, "cleaned_data", {"page_num": 1}).get("page_num", 1)
    if page > product_lines.num_pages:
        # For whatever reason, if the page being requested is larger than the actual
        # number of pages, just start over from the first page.
        page = 1
        form.initial["page_num"] = 1
    end = time.time()
    return render(
        request,
        template_name="meals/product_line/product_line.html",
        context={
            "product_lines": product_lines.page(page),
            "form": form,
            "pages": range(1, product_lines.num_pages + 1),
            "current_page": page,
            "duration": "{:0.3f}".format(end - start),
        },
    )


@login_required
@permission_required("meals.change_product_line", raise_exception=True)
def edit_product_line(request, product_line_name):
    instance = get_object_or_404(ProductLine, name=product_line_name)
    if request.method == "POST":
        form = EditProduct_LineForm(request.POST, instance=instance)
        if form.is_valid():
            instance = form.save()
            messages.info(request, f"Successfully saved Product Line #{instance.pk}")
            return redirect("product_line")
    else:
        form = EditProduct_LineForm(instance=instance)
    form_html = render_to_string(
        template_name="meals/product_line/edit_product_line_form.html",
        context={"form": form, "editing": True, "product_line_name": instance.name},
        request=request,
    )
    return render(
        request,
        template_name="meals/product_line/edit_product_line.html",
        context={
            "form": form,
            "form_html": form_html,
            "product_line_name": instance.name,
            "editing": True,
        },
    )


@login_required
@permission_required("meals.add_product_line", raise_exception=True)
def add_product_line(request):
    if request.method == "POST":
        form = EditProduct_LineForm(request.POST)
        if form.is_valid():
            instance = form.save()
            message = f"Product_Line '{instance.name}' added successfully"
            if request.is_ajax():
                resp = {"error": None, "resp": None, "success": True, "alert": message}
                return JsonResponse(resp)
            messages.info(request, message)
            return redirect("product_line")
    else:
        form = EditProduct_LineForm()

    form_html = render_to_string(
        template_name="meals/product_line/edit_product_line_form.html",
        context={"form": form},
        request=request,
    )

    if request.is_ajax():
        resp = {"error": "Invalid form", "resp": form_html}
        return JsonResponse(resp)
    return render(
        request,
        template_name="meals/product_line/edit_product_line.html",
        context={"form": form, "form_html": form_html},
    )


@login_required
@require_POST
@auth.permission_required_ajax(perm="meals.delete_product_line")
def remove_product_lines(request):
    to_remove = jsonpickle.loads(request.POST.get("to_remove", "[]"))
    try:
        with transaction.atomic():
            num_deleted, result = ProductLine.objects.filter(pk__in=to_remove).delete()
            logger.info("removed %d Product Lines: %s", num_deleted, result)
        return JsonResponse(
            {"error": None, "resp": f"Successfully removed {result['meals.ProductLine']} Product Liness"}
        )
    except DatabaseError as e:
        return JsonResponse({"error": str(e), "resp": "Not removed"})
