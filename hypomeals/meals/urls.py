from django.conf.urls import url
from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    # Normal views
    path("", views.index, name="index"),
    # SKU views
    path("sku", views.sku, name="sku"),
    path("remove-skus", views.remove_skus, name="remove_skus"),
    path("query-skus", views.query_skus, name="query_skus"),
    path(
        "ac-ingredients",
        views.autocomplete_ingredients,
        name="autocomplete_ingredients",
    ),
    path(
        "ac-product-lines",
        views.autocomplete_product_lines,
        name="autocomplete_product_lines",
    ),
    # Import/export views
    # Account management views
    path("accounts/login/", auth_views.LoginView.as_view(), name="login"),
    path("accounts/logout/", views.logout_view, name="logout"),
]
