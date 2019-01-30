from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from .forms import ImportCsvForm, ImportZipForm
from .bulk_export import process_export
from .models import Sku

def index(request):
    return render(request, template_name="meals/index.html")


@login_required
def import_page(request):
    template = "meals/import/import.html"

    if request.method == "POST":
        csv_file_form = ImportCsvForm(request.POST, request.FILES)
        zip_file_form = ImportZipForm(request.POST, request.FILES)
        if (csv_file_form.has_changed() and csv_file_form.is_valid()) or (
            zip_file_form.has_changed() and zip_file_form.is_valid()
        ):
            return redirect("import_landing")
        return render(
            request,
            template_name=template,
            context={"csv_form": csv_file_form, "zip_form": zip_file_form},
        )
    csv_file_form = ImportCsvForm()
    zip_file_form = ImportZipForm()
    return render(
        request, template, {"csv_form": csv_file_form, "zip_form": zip_file_form}
    )


@login_required
def import_landing(request):
    response = render(request, template_name="meals/import/import_landing.html")
    return response

@login_required
def export_test(request):
    response = render(request, template_name="meals/index.html")
    if request :
        response = process_export(Sku.objects.all())
    return response


@login_required
def logout_view(request):
    logout(request)
    return redirect("index")
