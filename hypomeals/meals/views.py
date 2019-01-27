from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from .forms import ImportFileForm, ImportZipForm
from .utils import process_files
from django.shortcuts import render, redirect

# Create your views here.

def index(request):
    return render(request, template_name="meals/index.html")

@login_required
def import_page(request):
    template = "meals/import.html"

    if request.method == "GET":
        form1 = ImportFileForm()
        form2 = ImportZipForm()
        return render(request, template, {'form1':form1, 'form2':form2})
    csv_file = request.FILES
    #print(csv_file)
    process_files(csv_file)
    return redirect("import_landing")

@login_required
def import_landing(request):
    response = render(request, template_name="meals/import_landing.html")
    return response

@login_required
def logout_view(request):
    logout(request)
    return redirect("index")
