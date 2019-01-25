from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_list_or_404, redirect
from .forms import ImportFileForm
from django.http import HttpResponseRedirect
import csv
from django.contrib import messages
from .utils import process_files

# Create your views here.
from meals.models import User


def index(request):
    return render(request, template_name="meals/index.html")

@login_required
def import_page(request):
    template = "meals/import.html"

    if request.method == "GET":
        form = ImportFileForm()
        return render(request, template, {'form':form})
    form = ImportFileForm()
    csv_file = request.FILES
    process_files(csv_file)
    return render(request, 'meals/index.html', {'form':form})

    '''
    if request.method == 'POST':
        form = ImportFileForm(request.POST, request.FILES)
        if form.is_valid():
            return HttpResponseRedirect("index")
            #handle processing/validation has not been built yet, probably will be in a utils file
            #handle_import(request.FILES)
        else:
            return render(request, "meals/import.html", {'form': form})
    else:
        form = ImportFileForm()
        return render(request, "meals/import.html", {'form':form})
        '''

@login_required
def logout_view(request):
    logout(request)
    return redirect("index")
