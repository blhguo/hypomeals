from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.urls import path
from django.views.generic import TemplateView

from . import views

urlpatterns = [
    # Normal views
    path("", views.index, name="index"),
    path("error", TemplateView.as_view(template_name="meals/error.html"), name="error"),
    # Product Line Views
    path("product-lines", views.product_line, name="product_line"),
    path("remove-product-lines",
         views.remove_product_lines, name="remove_product_lines"),
    path("add-product-line", views.add_product_line, name="add_product_line"),
    path("edit-product-line/<str:product_line_name>",
         views.edit_product_line, name="edit_product_line"),
    path("view-pl-skus/<str:product_line_name>",
         views.view_pl_skus, name="view_pl_skus"),
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
        "ac-manufacturing-lines",
        views.autocomplete_manufacturing_lines,
        name="autocomplete_manufacturing_lines",
    ),
    path(
        "ac-product-lines",
        views.autocomplete_product_lines,
        name="autocomplete_product_lines",
    ),
    path("ingredient", views.ingredient, name="ingredient"),
    path("remove-ingredient", views.remove_ingredients, name="remove_ingredients"),
    path("add-ingredient", views.add_ingredient, name="add_ingredient"),
    path(
        "edit-ingredient/<int:ingredient_number>",
        views.edit_ingredient,
        name="edit_ingredient",
    ),
    path("ac-sku", views.autocomplete_skus, name="autocomplete_skus"),
    path("edit-formula/<int:formula_number>", views.edit_formula, name="edit_formula"),
    path("add-formula", views.add_formula, name="add_formula"),
    path("view-formula/<int:formula_number>", views.view_formula, name="view_formula"),
    path("formula", views.formula, name="formula"),
    path("remove_formulas", views.remove_formulas, name="remove_formulas"),
    # Import/export views
    path("import/", views.import_page, name="import"),
    path("import/success/", views.import_success, name="import_success"),
    path("import/collision/", views.collision, name="collision"),
    # Manufacturer Goal views
    path("goal/new/", views.edit_goal, name="add_goal"),
    path("goal/<int:goal_id>", views.edit_goal, name="edit_goal"),
    path("goals", views.goals, name="goals"),
    path("generate_report/", views.generate_report, name="result"),
    path(
        "download_calculation/", views.download_calculation, name="download_calculation"
    ),
    path("save_goal/", login_required(views.save_goal), name="save_goal"),
    path("download_goal/", views.download_goal, name="download_goal"),
    path(
        "generate_calculation_pdf/",
        views.generate_calculation_pdf,
        name="generate_calculation_pdf",
    ),
    path("find_product_line/", views.find_product_line, name="find_product_line"),
    # Account management views
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(template_name="meals/accounts/login.html"),
        name="login",
    ),
    path("accounts/logout/", views.logout_view, name="logout"),
    path("accounts/sso/authorize", views.sso_start, name="sso"),
    path("accounts/sso", views.sso_landing, name="sso_landing"),
]
