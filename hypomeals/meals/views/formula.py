import logging
import time

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET, require_POST

from meals import auth
from meals.forms import FormulaFormset, FormulaFilterForm, FormulaNameForm
from meals.models import Sku
from meals.models import FormulaIngredient
from meals.models import Formula

logger = logging.getLogger(__name__)


@login_required
@permission_required("meals.add_formula", raise_exception=True)
def add_formula(request):
    in_flow = False
    if request.method == "POST":
        formset = FormulaFormset(request.POST)
        form = FormulaNameForm(request.POST)
        if form.is_valid() and formset.is_valid():
            saved = []
            instance = form.save()
            with transaction.atomic():
                for form, data in zip(formset.forms, formset.cleaned_data):
                    if "DELETE" not in data or data["DELETE"]:
                        continue
                    saved.append(form.save(instance, commit=False))
                if saved:
                    FormulaIngredient.objects.bulk_create(saved)
            messages.info(request, f"Successfully inserted {len(saved)} ingredients.")
            return redirect("formula")
    else:
        formset = FormulaFormset()
        form = FormulaNameForm()
        print("Succeed")

    return render(
        request,
        template_name="meals/formula/edit_formula.html",
        context={"formset": formset, "form": form, "in_flow": in_flow, "edit": False},
    )


@login_required
@permission_required("meals.view_formulaingredient", raise_exception=True)
def formula(request):
    start = time.time()
    export = request.GET.get("export", "0") == "1"
    report = request.GET.get("report", "0") == "1"
    if request.method == "POST":
        form = FormulaFilterForm(request.POST)
        if form.is_valid():
            formulas = form.query()
        else:
            formulas = Paginator(Ingredient.objects.all(), 50)
    else:
        form = FormulaFilterForm()
        formulas = Paginator(Formula.objects.all(), 50)
    page = getattr(form, "cleaned_data", {"page_num": 1}).get("page_num", 1)
    if page > formulas.num_pages:
        page = 1
        form.intial["page_num"] = 1
    end = time.time()
    return render(
        request,
        template_name="meals/formula/formula.html",
        context={
            "formulas": formulas.page(page),
            "form": form,
            "pages": range(1, formulas.num_pages + 1),
            "current_page": page,
            "duration": "{:0.3f}".format(end - start),
        },
    )


@login_required
@permission_required("meals.view_formulaingredient", raise_exception=True)
def edit_formula(request, formula_number):
    # sku = get_object_or_404(Sku, pk=sku_number)
    formula = get_object_or_404(Formula, pk=formula_number)
    in_flow = request.GET.get("in_flow", "0") == "1"
    if request.method == "POST":
        logger.debug("Raw POST data: %s", request.POST)
        formset = FormulaFormset(request.POST)
        form = FormulaNameForm(request.POST, instance=formula)
        if form.is_valid() and formset.is_valid():
            instance = form.save()
            logger.info("Cleaned data: %s", formset.cleaned_data)
            saved = []
            with transaction.atomic():
                FormulaIngredient.objects.filter(formula=formula).delete()
                for form, data in zip(formset.forms, formset.cleaned_data):
                    if "DELETE" not in data or data["DELETE"]:
                        continue
                    saved.append(form.save(formula, commit=False))
                if saved:
                    FormulaIngredient.objects.bulk_create(saved)
            messages.info(request, f"Successfully inserted {len(saved)} ingredients.")
            return redirect("formula")
    else:
        formulas = FormulaIngredient.objects.filter(formula=formula)
        initial_data = [
            {"ingredient": formula.ingredient.name, "quantity": formula.quantity}
            for formula in formulas
        ]
        formset = FormulaFormset(initial=initial_data)
        form = FormulaNameForm(instance=formula)

    return render(
        request,
        template_name="meals/formula/edit_formula.html",
        context={
            "form": form,
            "formula": formula,
            "formset": formset,
            "in_flow": in_flow,
            "edit": True,
        },
    )


@login_required
@require_GET
@auth.permission_required_ajax(perm="meals.view_formulaingredient")
def view_formula(request, formula_number):
    queryset = Formula.objects.filter(pk=formula_number)
    if queryset.exists():
        formula = queryset[0]
        formulas = FormulaIngredient.objects.filter(formula=formula)
        resp = render_to_string(
            template_name="meals/formula/view_formula.html",
            context={"formulas": formulas},
            request=request,
        )
        error = None
    else:
        error = f"SKU with number '{sku_number}' not found."
        resp = error
    print(resp)
    return JsonResponse({"error": error, "resp": resp})


@login_required
@require_POST
@auth.permission_required_ajax(perm="meals.delete_formula")
def remove_formulas(request):
    to_remove = jsonpickle.loads(request.POST.get("to_remove", "[]"))
    try:
        with transaction.atomic():
            num_deleted, result = Formula.objects.filter(pk__in=to_remove).delete()
            logger.info("removed %d Formulas: %s", num_deleted, result)
        return JsonResponse(
            {
                "error": None,
                "resp": f"Successfully removed {result['meals.Formula']} Formulas",
            }
        )
    except DatabaseError as e:
        return JsonResponse({"error": str(e), "resp": "Not removed"})
