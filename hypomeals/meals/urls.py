from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import TemplateView

from . import views

urlpatterns = [
    # Normal views
    path("", views.index, name="index"),
    path("error", TemplateView.as_view(template_name="meals/error.html"), name="error"),
    path("admin/settings", views.admin_settings, name="admin_settings"),
    # Product Line Views
    path("product-lines", views.product_line, name="product_line"),
    path(
        "remove-product-lines", views.remove_product_lines, name="remove_product_lines"
    ),
    path("add-product-line", views.add_product_line, name="add_product_line"),
    path(
        "edit-product-line/<int:pk>", views.edit_product_line, name="edit_product_line"
    ),
    path("view-pl-skus/<int:pk>", views.view_pl_skus, name="view_pl_skus"),
    path("generate_report", views.generate_sales_report, name="generate_sales_report"),
    # Sales
    path("sales/summary/", views.sales_summary, name="sales_summary"),
    path("sales/drilldown/<int:sku_pk>", views.sales_drilldown, name="drilldown"),
    path("sales/sales-projection", views.sales_projection, name="sales_projection"),
    path("ac-customers", views.autocomplete_customers, name="autocomplete_customers"),
    # SKU views
    path("sku", views.sku, name="sku"),
    path("sku/remove", views.remove_skus, name="remove_skus"),
    path("sku/add", views.add_sku, name="add_sku"),
    path("sku/edit/<int:sku_number>", views.edit_sku, name="edit_sku"),
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
    path("ac-customers", views.autocomplete_customers, name="autocomplete_customers"),
    path("ac-formulas", views.autocomplete_formulas, name="autocomplete_formulas"),
    path("ac-users", views.autocomplete_users, name="autocomplete_users"),
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
    path(
        "edit-formula-name/<str:formula_name>",
        views.edit_formula_name,
        name="edit_formula_name",
    ),
    path("add-formula", views.add_formula, name="add_formula"),
    path("view-formula/<int:formula_number>", views.view_formula, name="view_formula"),
    path("formula", views.formula, name="formula"),
    path("remove-formulas", views.remove_formulas, name="remove_formulas"),
    path("view-lines", views.view_lines, name="view_lines"),
    path("edit-lines", views.edit_lines, name="edit_lines"),
    # Import/export views
    path("import/", views.import_page, name="import"),
    path("import/success/", views.import_success, name="import_success"),
    path("import/collision/", views.collision, name="collision"),
    # Manufacturing goal views
    path("goal/new/", views.edit_goal, name="add_goal"),
    path("goal/<int:goal_id>", views.edit_goal, name="edit_goal"),
    path("goals/enable", views.enable_goals, name="enable_goals"),
    path("goals/disable", views.disable_goals, name="disable_goals"),
    path("goals", views.goals, name="goals"),
    path("goal/export/csv/<int:goal_id>", views.export_csv, name="export_goal_csv"),
    path(
        "goal/calculation/view/<int:goal_id>",
        views.view_calculations,
        name="view_calculation",
    ),
    path(
        "goal/calculation/csv/<int:goal_id>",
        views.generate_calculation_csv,
        name="export_calculation_csv",
    ),
    path("goals/schedule", views.schedule, name="schedule"),
    path("goals/schedule/report/", views.schedule_report, name="schedule_report"),
    path("filter_skus/", views.filter_skus, name="filter_skus"),
    # Manufacturing line views
    path("lines/", views.lines, name="lines"),
    path("lines/edit/<int:pk>", views.edit_line, name="edit_line"),
    path("lines/add/", views.add_line, name="add_line"),
    path("lines/remove", views.remove_lines, name="remove_lines"),
    # Account management views
    path("accounts/", views.users, name="users"),
    path("accounts/add/", views.add_user, name="add_user"),
    path("accounts/remove/", views.remove_users, name="remove_users"),
    path("accounts/edit/<int:pk>", views.edit_user, name="edit_user"),
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(template_name="meals/accounts/login.html"),
        name="login",
    ),
    path("accounts/logout/", views.logout_view, name="logout"),
    path("accounts/sso/authorize", views.sso_start, name="sso"),
    path("accounts/sso", views.sso_landing, name="sso_landing"),
]
