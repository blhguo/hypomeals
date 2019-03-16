import json
import jsonpickle
import logging
import time
import datetime

from dateutil import relativedelta

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
from meals.models import Sale, Sku, Customer

from urllib.parse import urlencode

logger = logging.getLogger(__name__)


@login_required
def sales_drilldown(request, sku_pk):
    start = time.time()
    if request.method == "POST":
        sku = Sku.objects.get(pk=sku_pk)
        body = request.POST.copy()
        body["sku"] = sku.number
        print(body)
        form = SaleFilterForm(body)
        print(request.POST)
        print("made it")
        print(form)
        if form.is_valid():
            print("in here")
            sales = form.query()
            print(sales)
        else:
            print("not valid")
            sales = Paginator(Sale.objects.all(), 50)
    else:
        sku = Sku.objects.get(pk=sku_pk)
        #print(sku.name)
        cust_input = ''
        for cust in Customer.objects.all():
            cust_input += cust.name + ", "
        params = {
            "sku": sku.number,
            "customer": cust_input,
            "page_num": 1,
            "num_per_page": 50,
            "start": datetime.datetime.now() - relativedelta.relativedelta(years=1),
            "end": datetime.datetime.now(),
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
    revenues = [sale.price * sale.sales for sale in sales.page(page)]
    xret = []
    yret = []
    labelret = []
    for sale, revenue in zip(sales.page(page), revenues):
        if str(sale.week) + '/' + str(sale.year) not in xret:
            yret.append(str(revenue))
            xret.append(str(sale.week) + '/' + str(sale.year))
        else:
            index = xret.index(str(sale.week) + '/' + str(sale.year))
            yret[index] = str(float(yret[index]) + float(revenue))
        labelret.append(str(sale.customer.name))
    end = time.time()
    return render(
        request,
        template_name="meals/sales/drilldown.html",
        context={
            "sku_pk": sku_pk,
            "sales": zip(sales.page(page), revenues),
            "chart_data_x": jsonpickle.encode(xret),
            "chart_data_y": jsonpickle.encode(yret),
            "chart_data_labels": jsonpickle.encode(labelret),
            "form": form,
            "pages": range(1, sales.num_pages + 1),
            "current_page": page,
            "duration": "{:0.3f}".format(end - start),
        },
    )
