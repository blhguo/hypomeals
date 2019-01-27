from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from .forms import ImportFileForm, ImportZipForm
from .utils import process_files


# Create your views here.


def index(request):
    return render(request, template_name="meals/index.html")


@login_required
def import_page(request):
    template = "meals/import/import.html"

    if request.method == "GET":
        csv_file_form = ImportFileForm()
        zip_file_form = ImportZipForm()
        return render(
            request, template, {"csv_form": csv_file_form, "zip_form": zip_file_form}
        )
    process_files(request.FILES)
    return redirect("import_landing")


@login_required
def import_landing(request):
    response = render(request, template_name="meals/import/import_landing.html")
    return response


@login_required
def logout_view(request):
    logout(request)
    return redirect("index")
