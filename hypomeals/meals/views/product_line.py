import json
import logging
import time

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_GET

from meals import auth
from meals.forms import EditProductLineForm
from meals.models import ProductLine

from urllib.parse import urlencode

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
def edit_product_line(request, pk):
    instance = get_object_or_404(ProductLine, pk=pk)
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
        context={"form": form, "editing": True, "product_line_number": instance.pk},
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


@login_required
def generate_sales_report(request):
    target_pls = set(map(int, json.loads(request.GET.get("toTarget", "[]"))))
    qs = ProductLine.objects.filter(pk__in=target_pls)
    num_targeted = qs.count()
    logger.info("Sales report generated on %d Product Lines", num_targeted)
    #TODO: This line needs to be edited to fit Alex's stuff
    base_url = reverse('ingredient')
    qs_names = [tmp.name for tmp in qs]
    query_string = urlencode({'product_lines': qs_names})
    url = '{}?{}'.format(base_url, query_string)
    # TODO: I"m not sure if it's normal or not, but the querystringis formatted strangely
    # looks like "/ingredient?product_lines=%5B%27CheesyCheese%27%2C+%27asdasdasdasd%27%5D"
    return redirect(url)
