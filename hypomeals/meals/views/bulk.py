# pylint: disable-msg=protected-access
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models.fields.related import RelatedField
from django.shortcuts import render, redirect
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from meals import auth
from meals.bulk_import import (
    has_ongoing_transaction,
    get_transaction,
    clear_transaction,
    force_save,
)
from meals.importers import CollisionOccurredException, CollisionException
from ..forms import ImportForm

logger = logging.getLogger(__name__)


def _render_collision(collision: CollisionException):
    """Renders a collision as two table entries (<td>s)"""
    old, new = collision.old_instance, collision.new_instance
    if not new.pk:
        new.pk = "<Autogenerated>"
    differences = {}
    for field in old._meta.fields:
        if field.primary_key:
            continue
        old_value = getattr(old, field.name, None)
        new_value = getattr(new, field.name, None)
        if isinstance(field, RelatedField):
            old_value = str(old_value)
            new_value = str(new_value)
        if old_value != new_value:
            differences[field.verbose_name] = (old_value, new_value)

    old_ul = ""
    new_ul = ""
    for field_name, (old_value, new_value) in differences.items():
        if not old_value:
            old_value = "<empty>"
        if not new_value:
            new_value = "<empty>"
        old_ul += format_html("<li>{}</li>", f"{field_name}: {old_value}")
        new_ul += format_html("<li>{}</li>", f"{field_name}: {new_value}")
    old_ul = format_html("<ul>{}</ul>", mark_safe(old_ul))
    new_ul = format_html("<ul>{}</ul>", mark_safe(new_ul))
    return format_html(
        "<td>{}</td><td>{}</td><td>{}</td>",
        old.pk,
        mark_safe(old_ul),
        mark_safe(new_ul),
    )


@login_required
@auth.permission_required_ajax(
    perm=(
        "meals.change_sku",
        "meals.change_ingredient",
        "meals.change_formula",
        "meals.change_formulaingredient",
        "meals.change_productline",
        "meals.change_manufacturingline",
        "meals.change_skumanufacturingline",
        "meals.change_productline",
    ),
    msg="You do not have permission to import data, ",
    reason="Only Product Managers may bulk import.",
)
def import_page(request):

    if request.method == "POST":
        file_form = ImportForm(
            request.POST, request.FILES, session_key=request.session.session_key
        )
        if file_form.has_changed():
            try:
                if not file_form.is_valid():
                    return render(
                        request,
                        template_name="meals/import/import.html",
                        context={"file_form": file_form},
                    )
            except CollisionOccurredException:
                redirect("collision")
            if file_form.imported:
                inserted, ignored = file_form.cleaned_data
                return import_success(request, inserted=inserted, ignored=ignored)
            return redirect("collision")

    clear_transaction(request.session.session_key)
    logger.info("Cleared transaction cache")
    file_form = ImportForm(session_key=request.session.session_key)
    return render(
        request,
        template_name="meals/import/import.html",
        context={"file_form": file_form},
    )


@login_required
def collision(request):
    if not has_ongoing_transaction(request.session.session_key):
        logger.warning("Session has no ongoing transaction. Redirecting to import.")
        return redirect("import")
    force = request.GET.get("force", "0") == "1"
    if not force:
        transaction = get_transaction(request.session.session_key)
        rendered_transaction = []
        total_conflicts = 0
        for filename in sorted(transaction.keys()):
            collisions = transaction[filename].collisions
            total_conflicts += len(collisions)
            rendered_transaction.append(
                (filename, [_render_collision(c) for c in collisions])
            )

        return render(
            request,
            template_name="meals/import/collisions.html",
            context={
                "transaction": rendered_transaction,
                "total_conflicts": total_conflicts,
            },
        )
    inserted, updated, ignored = force_save(
        session_key=request.session.session_key, force=force
    )
    if inserted or updated:
        return import_success(request, inserted, updated, ignored)
    messages.error(
        request, "Unable to finish import. Please contact the administrator."
    )
    return redirect("error")


@login_required
@auth.permission_required_ajax(
    perm=(
        "meals.change_sku",
        "meals.change_ingredient",
        "meals.change_formula",
        "meals.change_formulaingredient",
        "meals.change_productline",
        "meals.change_manufacturingline",
        "meals.change_skumanufacturingline",
        "meals.change_productline",
    ),
    msg="You do not have permission to import data, ",
    reason="Only Product Managers may bulk import.",
)
def import_success(request, inserted=None, updated=None, ignored=None):
    if inserted is None:
        inserted = {}
    if updated is None:
        updated = {}
    if ignored is None:
        ignored = {}
    response = render(
        request,
        template_name="meals/import/import_success.html",
        context={
            "inserted": inserted.items(),
            "updated": updated.items(),
            "ignored": ignored.items(),
        },
    )
    return response
