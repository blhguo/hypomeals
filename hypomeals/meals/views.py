from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render, get_list_or_404, redirect

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from meals import utils
from meals.forms import SkuFilterForm
from meals.models import User, Sku


def index(request):
    return render(request, template_name="meals/index.html")


@login_required
def logout_view(request):
    logout(request)
    return redirect("index")


############################  SKU Views  ###############################
@login_required
def sku(request):
    if request.method == "POST":
        form = SkuFilterForm(request.POST)
        if form.is_valid():
            skus = form.query()
        else:
            skus = Paginator(Sku.objects.all(), 50)
    else:
        form = SkuFilterForm()
        skus = Paginator(Sku.objects.all(), 50)
    page = int(request.GET.get("page", "1"))
    return render(
        request,
        template_name="meals/sku/sku.html",
        context={
            "skus": skus.page(page),
            "form": form,
            "pages": range(1, skus.num_pages + 1),
            "current_page": page,
        },
    )


@login_required
@csrf_exempt
@require_POST
@utils.exception_to_error
def query_skus(request):
    page_num = request.GET.get("page", 1)
    pages = Sku.query_from_request(request)
    return JsonResponse(pages.get_page(page_num), safe=False)


@login_required
@csrf_exempt
@require_POST
def remove_skus(request):
    print(request.POST.keys())
    return JsonResponse({"error": None, "resp": "Removed"})
