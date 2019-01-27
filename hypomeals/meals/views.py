from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

# Create your views here.


def index(request):
    return render(request, template_name="meals/index.html")


@login_required
def logout_view(request):
    logout(request)
    return redirect("index")
