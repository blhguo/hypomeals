from django.shortcuts import render, get_list_or_404

# Create your views here.
from meals.models import User


def index(req):
    return render(req, template_name="meals/index.html")
