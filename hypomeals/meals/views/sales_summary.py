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
            for year in range(begin_year, end_year+1):
                sales_in_year = Sale.objects.filter(customer__in=customers, year = year)
                sales_tot = Decimal(0)
                num_tot = Decimal(0)
                for sale in sales_in_year:
                    sales_tot += sale.price * sale.sales
                    num_tot += sale.sales
                sku_ten_year.append((year, sku.number, sku.name, sales_tot, sales_tot/num_tot))
            activities_sku = GoalItem.objects.filter(sku=sku)
            manufacture_run_size = Decimal(0)
            for activity in activities_sku:
                manufacture_run_size += activity.quantity
            avg_run_size = manufacture_run_size / len(activities_sku)
            # Fake Data For Now
            setup_cost_per_case = 1000
            run_cost_per_case = 20
            ingredient_cost_per_case = sku.formula.ingredient_cost * sku.formula_scale
            cogs = setup_cost_per_case + run_cost_per_case + ingredient_cost_per_case

            
            sales_summary_result.append((pl.name, sku_ten_year))

    return render(
        request,
        template_name="meals/sales_summary/sales_summary.html",
        context={
            "sales_summary": sales_summary_result,
        },
    )
