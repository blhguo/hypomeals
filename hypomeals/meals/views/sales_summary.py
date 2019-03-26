import logging
import datetime
import json
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F
from django.core.paginator import Paginator
from django.shortcuts import render

from meals.bulk_export import export_sales_summary
from meals.forms import ProductLineFilterForm
from meals.models import ProductLine, Customer, Sku, Sale, GoalItem
from meals.constants import MINUTES_PER_SKU

logger = logging.getLogger(__name__)


def sku_summary(sku, rev_sum, num_sales, sku_info):
    activities_sku = GoalItem.objects.filter(sku=sku)
    manufacture_run_size = Decimal(0)
    for activity in activities_sku:
        manufacture_run_size += activity.quantity
    if activities_sku:
        avg_run_size = manufacture_run_size / Decimal(len(activities_sku))
    else:
        avg_run_size = sku.manufacturing_rate * Decimal(10.0)
    setup_cost_per_case = sku.setup_cost / avg_run_size
    run_cost_per_case = sku.run_cost
    ingredient_cost_per_case = sku.formula.ingredient_cost * sku.formula_scale
    cogs = setup_cost_per_case + run_cost_per_case + ingredient_cost_per_case
    if num_sales == 0:
        avg_rev_per_case = Decimal(0)
    else:
        avg_rev_per_case = rev_sum / num_sales
    avg_profit_per_case = avg_rev_per_case - cogs
    profit_margin = avg_rev_per_case / cogs - 1
    return (
        sku.number,
        sku.name,
        rev_sum,
        avg_run_size,
        ingredient_cost_per_case,
        setup_cost_per_case,
        run_cost_per_case,
        cogs,
        avg_rev_per_case,
        avg_profit_per_case,
        profit_margin,
        sku_info,
    )


def sku_ready():
    skus = Sku.objects.all()
    ready = True
    for sku in skus:
        ready &= sku.sales_ready
    return ready


def time_estimate():
    cnt = 0
    for sku in Sku.objects.all():
        if not sku.sales_ready:
            cnt += 1
    return cnt * MINUTES_PER_SKU


@login_required
def sales_summary(request):
    export = request.GET.get("export", "0") == "1"
    if not sku_ready():
        return render(
            request,
            template_name="meals/sales_summary/sku_not_ready.html",
            context={"time_estimate": time_estimate()},
        )

    if request.method == "POST":
        form = ProductLineFilterForm(request.POST)
        if form.is_valid():
            product_lines, customers = form.query()
        else:
            product_lines, customers = (
                Paginator(Sku.objects.all(), 50),
                Customer.objects.all(),
            )
    else:
        params = {
            "product_lines": "",
            "customers": "",
            "formulas": "",
            "page_num": 1,
            "num_per_page": 50,
            "sort_by": "name",
            "keyword": "",
        }
        if "product_lines" in request.GET:
            target_pls = set(
                map(int, json.loads(request.GET.get("product_lines", "[]")))
            )
            pls = ProductLine.objects.filter(pk__in=target_pls)
            pl_names = [pl.name for pl in pls]
            params["product_lines"] = ",".join(pl_names)

        if "formula" in request.GET:
            formula_name = request.GET["formula"]
            params["formulas"] = formula_name

        form = ProductLineFilterForm(params)
        if form.is_valid():
            product_lines, customers = form.query()
        else:
            product_lines, customers = (
                Paginator(ProductLine.objects.all(), 50),
                Customer.objects.all(),
            )

    page = getattr(form, "cleaned_data", {"page_num": 1}).get("page_num", 1)
    if page > product_lines.num_pages:
        # For whatever reason, if the page being requested is larger than the actual
        # number of pages, just start over from the first page.
        page = 1
        form.initial["page_num"] = 1
    sales_summary_result = []
    for pl in product_lines.page(page):
        logger.info("PL Name: %s", pl.name)
        skus = Sku.objects.filter(product_line=pl)
        now = datetime.datetime.now()
        end_year = now.year
        begin_year = end_year - 9
        pl_summary_report = []
        for sku in skus:
            sku_ten_year = []
            rev_sum = Decimal(0)
            num_sales = Decimal(0)
            sales_all = (
                Sale.objects.filter(
                    sku=sku, customer__in=customers, year__gte=begin_year
                )
                .order_by("year")
                .values("year")
                .annotate(revenue=Sum(F("sales") * F("price")), count=Sum(F("sales")))
            )
            for sales_per_year in sales_all:
                year = sales_per_year["year"]
                sales_tot = sales_per_year["revenue"]
                num_tot = sales_per_year["count"]
                sku_ten_year.append(
                    (year, sku.number, sku.name, sales_tot, sales_tot / num_tot)
                )
                rev_sum += sales_tot
                num_sales += num_tot
            sku_summary_report = sku_summary(sku, rev_sum, num_sales, sku_ten_year)
            pl_summary_report.append(sku_summary_report)
        sales_summary_result.append((pl.name, pl_summary_report))
    if export:
        return export_sales_summary(sales_summary_result)
    drilldown_params = "?customer=" + form.data["customers"]
    return render(
        request,
        template_name="meals/sales_summary/sales_summary.html",
        context={
            "sales_summary": sales_summary_result,
            "form": form,
            "drilldown_params": drilldown_params,
        },
    )
