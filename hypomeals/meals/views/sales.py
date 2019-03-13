import json
import logging
import time

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_list_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_GET

from meals import auth
from meals.forms import SaleFilterForm
from meals.models import Sale, Sku

from urllib.parse import urlencode

logger = logging.getLogger(__name__)


@login_required
@require_GET
def sales_drilldown(request, sku_pk):
    start = time.time()
    if request.method == "POST":
        form = SaleFilterForm(request.POST)
        if form.is_valid():
            sales = form.query()
        else:
            sales = Paginator(Sale.objects.all(), 50)
    else:
        params = {
            "sku": sku_pk,
            "customer": "",
            "page_num": 1,
            "num_per_page": 50,
        }
        if "customer" in request.GET:
            customer_name = request.GET["customer"]
            params["customer"] = customer_name

        form = SaleFilterForm(params)
        if form.is_valid():
            sales = form.query()
        else:
            # TODO throw an error, since no SKU was specified (shouldnt ever happen)
            sales = Paginator(Sale.objects.all(), 50)
    page = getattr(form, "cleaned_data", {"page_num": 1}).get("page_num", 1)
    if page > sales.num_pages:
        # For whatever reason, if the page being requested is larger than the actual
        # number of pages, just start over from the first page.
        page = 1
        form.initial["page_num"] = 1
    end = time.time()
    return render(
        request,
        template_name="meals/sales/drilldown.html",
        context={
            "sku_pk": sku_pk,
            "sales": sales.page(page),
            "form": form,
            "pages": range(1, sales.num_pages + 1),
            "current_page": page,
            "duration": "{:0.3f}".format(end - start),
        },
    )
