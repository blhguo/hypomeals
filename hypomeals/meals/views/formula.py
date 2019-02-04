import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404

from meals.forms import FormulaFormset
from meals.models import Sku
from meals.models import SkuIngredient

logger = logging.getLogger(__name__)


@login_required
def edit_formula(request, sku_number):
    sku = get_object_or_404(Sku, pk=sku_number)
    in_flow = request.GET.get("in_flow", "0") == "1"
    if request.method == "POST":
        logger.debug("Raw POST data: %s", request.POST)
        formset = FormulaFormset(request.POST, form_kwargs={"sku": sku})
        if formset.is_valid():
            logger.info("Cleaned data: %s", formset.cleaned_data)
            saved = []
            with transaction.atomic():
                SkuIngredient.objects.filter(sku_number=sku).delete()
                for form, data in zip(formset.forms, formset.cleaned_data):
                    if "DELETE" not in data or data["DELETE"]:
                        continue
                    saved.append(form.save(commit=False))
                if saved:
                    SkuIngredient.objects.bulk_create(saved)
            messages.info(request, f"Successfully inserted {len(saved)} ingredients.")
            return redirect("sku")
    else:
        formulas = SkuIngredient.objects.filter(sku_number=sku_number)
        initial_data = [
            {"ingredient": formula.ingredient_number.name, "quantity": formula.quantity}
            for formula in formulas
        ]
        formset = FormulaFormset(initial=initial_data, form_kwargs={"sku": sku})
    return render(
        request,
        template_name="meals/formula/edit_formula.html",
        context={"sku": sku, "formset": formset, "in_flow": in_flow},
    )
