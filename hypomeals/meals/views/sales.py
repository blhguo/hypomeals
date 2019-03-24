import json
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render

from meals.forms import SaleFilterForm
from meals.models import Sku
from ..bulk_export import export_drilldown

logger = logging.getLogger(__name__)

GRAPH_DATA_POINTS = 10


@login_required
def sales_drilldown(request, sku_pk):
    start = time.time()
    export = request.GET.get("export", "0") == "1"
    if request.method == "POST":
        sku = Sku.objects.get(pk=sku_pk)
        body = request.POST.copy()
        body["sku"] = sku.number
        form = SaleFilterForm(body)
        if form.is_valid():
            sales = form.query()
        else:
            sales = Paginator([], 50)
    else:
        sku = Sku.objects.get(pk=sku_pk)
        params = {
            "sku": sku.number,
            "customer": "",
            "page_num": 1,
            "num_per_page": 50,
            "start": datetime.now() - timedelta(days=365),
            "end": datetime.now(),
        }
        if "customer" in request.GET:
            customer_name = request.GET["customer"]
            params["customer"] = customer_name

        form = SaleFilterForm(params)
        if form.is_valid():
            sales = form.query()
        else:
            sales = Paginator([], 50)
    page = getattr(form, "cleaned_data", {"page_num": 1}).get("page_num", 1)
    if page > sales.num_pages:
        page = 1
        form.initial["page_num"] = 1
    revenues = defaultdict(lambda: Decimal(0))
    for sale in sales.object_list:
        iso_week = f"{sale.year}/{sale.week}"
        revenues[iso_week] += sale.revenue
    end = time.time()
    if export:
        return export_drilldown(sales.object_list)
    page_start = max(page - 3, 1)
    page_end = min(page + 4, sales.num_pages + 1)

    x_axis, y_axis = list(revenues.keys()), list(revenues.values())
    if len(x_axis) > GRAPH_DATA_POINTS:
        x_axis = x_axis[:: int(len(x_axis) / GRAPH_DATA_POINTS)]
        y_axis = y_axis[:: int(len(y_axis) / GRAPH_DATA_POINTS)]
    return render(
        request,
        template_name="meals/sales/drilldown.html",
        context={
            "sku": sku,
            "sales": sales.page(page),
            "chart_data_x": json.dumps(x_axis),
            "chart_data_y": json.dumps([str(y) for y in y_axis]),
            "form": form,
            "pages": range(page_start, page_end),
            "current_page": page,
            "duration": "{:0.3f}".format(end - start),
        },
    )
