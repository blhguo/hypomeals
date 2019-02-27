import json
import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string

from meals import auth, utils
from meals.exceptions import UserFacingException
from meals.forms import ManufacturingLineForm
from meals.models import ManufacturingLine

logger = logging.getLogger(__name__)


@login_required
def lines(request):
    line_objs = ManufacturingLine.objects.all()
    return render(
        request,
        template_name="meals/manufacturing/line.html",
        context={"lines": line_objs},
    )


@login_required
@auth.user_is_admin_ajax(msg="Only administrators may edit a manufacturing line.")
@utils.ajax_view
def edit_line(request, pk):
    line = get_object_or_404(ManufacturingLine, pk=pk)
    if request.method == "POST":
        form = ManufacturingLineForm(request.POST, instance=line)
        if form.is_valid():
            instance, _ = form.save(commit=True)
            return {
                "resp": f"Successfully saved Manufacturing Line #{instance.pk}",
                "success": True,
                "error": None,
            }
    else:
        form = ManufacturingLineForm(instance=line)
    return {
        "resp": render_to_string(
            request=request,
            template_name="meals/manufacturing/edit_line.html",
            context={"form": form, "editing": True, "line": line},
        ),
        "error": None,
        "success": False,
    }


@login_required
@auth.user_is_admin_ajax(msg="Only administrators may create new manufacturing lines.")
@utils.ajax_view
def add_line(request):
    if request.method == "POST":
        form = ManufacturingLineForm(request.POST)
        if form.is_valid():
            instance, _ = form.save(commit=True)
            return {
                "resp": f"Successfully created Manufacturing Line #{instance.pk}",
                "success": True,
                "error": None,
            }
    else:
        form = ManufacturingLineForm()
    return {
        "resp": render_to_string(
            request=request,
            template_name="meals/manufacturing/edit_line.html",
            context={"form": form, "editing": False},
        ),
        "error": None,
        "success": False,
    }


@login_required
@auth.user_is_admin_ajax(msg="Only administrators may remove manufacturing lines.")
@utils.ajax_view
def remove_lines(request):
    try:
        line_ids = set(map(int, json.loads(request.GET.get("toRemove", "[]"))))
    except ValueError as e:
        raise UserFacingException(f"Invalid Manufacturing Line IDs: '{e:s}'")
    _, deleted = ManufacturingLine.objects.filter(pk__in=line_ids).delete()
    return (
        f"Successfully deleted {deleted.get('meals.ManufacturingLine', 0)} "
        "Manufacturing Line(s)"
    )
