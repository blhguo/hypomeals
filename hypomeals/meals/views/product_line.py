import json
import logging
import time

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET

from meals import auth
from meals.forms import EditProductLineForm
from meals.models import ProductLine

logger = logging.getLogger(__name__)


@login_required
def product_line(request):
    start = time.time()
    product_lines = ProductLine.objects.all()
    end = time.time()
    return render(
        request,
        template_name="meals/product_line/product_line.html",
        context={
            "product_lines": product_lines,
            "duration": "{:0.3f}".format(end - start),
        },
    )


@login_required
@auth.user_is_admin_ajax(msg="Only an administrator may edit product lines.")
def edit_product_line(request, product_line_name):
    instance = get_object_or_404(ProductLine, name=product_line_name)
    if request.method == "POST":
        form = EditProductLineForm(request.POST, instance=instance)
        if form.is_valid():
            instance = form.save()
            messages.info(request, f"Successfully saved Product Line #{instance.pk}")
            return redirect("product_line")
    else:
        form = EditProductLineForm(instance=instance)
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
@auth.user_is_admin_ajax(msg="Only an administrator may add a new product line.")
def add_product_line(request):
    if request.method == "POST":
        form = EditProductLineForm(request.POST)
        if form.is_valid():
            instance = form.save()
            message = f"Product Line '{instance.name}' added successfully"
            if request.is_ajax():
                resp = {"error": None, "resp": None, "success": True, "alert": message}
                return JsonResponse(resp)
            messages.info(request, message)
            return redirect("product_line")
    else:
        form = EditProductLineForm()

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
@auth.user_is_admin_ajax(msg="Only administrators may delete product lines.")
def remove_product_lines(request):
    to_remove = set(map(int, json.loads(request.GET.get("toRemove", "[]"))))
    num_deleted, result = ProductLine.objects.filter(pk__in=to_remove).delete()
    logger.info("removed %d Product Lines: %s", num_deleted, result)
    return JsonResponse(
        {
            "error": None,
            "resp": f"Successfully removed {result['meals.ProductLine']} Product Lines",
        }
    )


@login_required
@require_GET
def view_pl_skus(request, pk):
    queryset = ProductLine.objects.filter(pk=pk)
    if queryset.exists():
        pl = queryset[0]
        skus = pl.sku_set.all()
        resp = render_to_string(
            template_name="meals/sku/view_sku.html",
            context={"pl_skus": skus},
            request=request,
        )
        error = None
    else:
        error = f"Product Line with ID '{pk}' not found."
        resp = error
    return JsonResponse({"error": error, "resp": resp})
