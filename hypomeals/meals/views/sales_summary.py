import json
import logging
import datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET

from meals import auth
from meals.forms import EditProductLineForm
from meals.models import ProductLine, Customer, Sku, Sale, GoalItem, FormulaIngredient

logger = logging.getLogger(__name__)


def sku_summary(sku, rev_sum, num_sales):
    activities_sku = GoalItem.objects.filter(sku=sku)
    manufacture_run_size = Decimal(0)
    for activity in activities_sku:
        manufacture_run_size += activity.quantity
    if len(activities_sku) == 0:
        avg_run_size = 1
    else:
        avg_run_size = manufacture_run_size / Decimal(len(activities_sku))
    # Fake Data For Now
    setup_cost_per_case = Decimal(1000) / avg_run_size
    run_cost_per_case = Decimal(20)
    ingredient_cost_per_case = sku.formula.ingredient_cost * sku.formula_scale
    cogs = setup_cost_per_case + run_cost_per_case + ingredient_cost_per_case
    avg_rev_per_case = rev_sum / num_sales
    avg_profit_per_case = avg_rev_per_case - cogs
    profit_margin = avg_rev_per_case / cogs - 1
    return (sku.number, sku.name, rev_sum, avg_run_size, ingredient_cost_per_case,
            setup_cost_per_case, run_cost_per_case, cogs, avg_rev_per_case,
            avg_profit_per_case, profit_margin)


@login_required
def sales_summary(request):
    product_lines = ProductLine.objects.all()
    customers = Customer.objects.all()

    sales_summary_result = []
    for pl in product_lines:
        skus = Sku.objects.filter(product_line=pl)
        now = datetime.datetime.now()
        end_year = now.year
        begin_year = end_year - 9
        for sku in skus:
            sku_ten_year = []
            rev_sum = Decimal(0)
            num_sales = Decimal(0)
            for year in range(begin_year, end_year + 1):
                sales_in_year = Sale.objects.filter(customer__in=customers, year=year)
                sales_tot = Decimal(0)
                num_tot = Decimal(0)
                for sale in sales_in_year:
                    sales_tot += sale.price * sale.sales
                    num_tot += sale.sales
                sku_ten_year.append(
                    (year, sku.number, sku.name, sales_tot, sales_tot / num_tot))
                rev_sum += sales_tot
                num_sales += num_tot
            sku_summary_report = sku_summary(sku, rev_sum, num_sales)
            sales_summary_result.append((pl.name, sku_summary_report, sku_ten_year))

    return render(
        request,
        template_name="meals/sales_summary/sales_summary.html",
        context={
            "sales_summary": sales_summary_result,
        },
    )
