from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    # Normal views
    path("", views.index, name="index"),
    # SKU views
    path("sku", views.sku, name="sku"),
    path("remove-skus", views.remove_skus, name="remove_skus"),
    path("add-sku", views.add_sku, name="add_sku"),
    path("edit-sku/<int:sku_number>", views.edit_sku, name="edit_sku"),
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
    path("edit-formula/<int:sku_number>", views.edit_formula, name="edit_formula"),
    # Import/export views
    # Account management views
    path("accounts/login/", auth_views.LoginView.as_view(), name="login"),
    path("accounts/logout/", views.logout_view, name="logout"),
]
