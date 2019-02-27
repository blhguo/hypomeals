import logging
import time

import jsonpickle
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db import transaction, DatabaseError
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET, require_POST

from meals import auth
from meals.forms import FormulaFormset, FormulaFilterForm, FormulaNameForm
from meals.models import FormulaIngredient
from meals.models import Formula
from ..bulk_export import export_formulas

logger = logging.getLogger(__name__)


@login_required
@auth.user_is_admin_ajax(msg="Only an administrator may add a new formula.")
def add_formula(request):
    in_flow = False
    if request.method == "POST":
        formset = FormulaFormset(request.POST)
        form = FormulaNameForm(request.POST)
        if form.is_valid() and formset.is_valid():
            saved = []
            with transaction.atomic():
                instance = form.save()
                for form, data in zip(formset.forms, formset.cleaned_data):
                    if "DELETE" not in data or data["DELETE"]:
                        continue
                    saved.append(form.save(instance, commit=False))
                if saved:
                    FormulaIngredient.objects.bulk_create(saved)
            messages.info(request, f"Successfully inserted {len(saved)} ingredients.")
            message = f"Formula '{instance.name}' added successfully"
            if request.is_ajax():
                resp = {
                    "error": None,
                    "resp": None,
                    "success": True,
                    "alert": message,
                    "name": "test",
                }
                return JsonResponse(resp)
            return redirect("formula")
    else:
        formset = FormulaFormset()
        form = FormulaNameForm()

    form_html = render_to_string(
        template_name="meals/formula/edit_formula_form.html",
        context={"formset": formset, "form": form, "in_flow": in_flow, "edit": False},
        request=request,
    )

    if request.is_ajax():
        resp = {"error": None, "resp": form_html}
        return JsonResponse(resp)

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
    if request.method == "POST":
        form = FormulaFilterForm(request.POST)
        if form.is_valid():
            formulas = form.query()
        else:
            formulas = Paginator(Formula.objects.all(), 50)
    else:
        form = FormulaFilterForm()
        formulas = Paginator(Formula.objects.all(), 50)
    page = getattr(form, "cleaned_data", {"page_num": 1}).get("page_num", 1)
    if page > formulas.num_pages:
        page = 1
        form.intial["page_num"] = 1
    end = time.time()
    if export:
        return export_formulas(formulas.object_list)
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
@auth.user_is_admin_ajax(msg="Only an administrator may edit a new formula.")
def edit_formula(request, formula_number):
    formula = get_object_or_404(Formula, pk=formula_number)
    in_flow = request.GET.get("in_flow", "0") == "1"
    if request.method == "POST":
        logger.debug("Raw POST data: %s", request.POST)
        formset = FormulaFormset(request.POST)
        form = FormulaNameForm(request.POST, instance=formula)
        if form.is_valid() and formset.is_valid():
            formula.name = form.cleaned_data["name"]
            formula.comment = form.cleaned_data["comment"]
            formula.save()
            logger.info("Cleaned data: %s", formset.cleaned_data)
            saved = []
            FormulaIngredient.objects.filter(formula=formula).delete()
            with transaction.atomic():
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
            {
                "ingredient": formula.ingredient.name,
                "quantity": formula.quantity,
                "unit": formula.unit.symbol,
            }
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
        error = f"Formula with number '{formula_number}' not found."
        resp = error
    return JsonResponse({"error": error, "resp": resp})


@login_required
@require_POST
@auth.user_is_admin_ajax(msg="Only an administrator may add a new formula.")
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
