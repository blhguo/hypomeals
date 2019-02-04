from django.conf.urls import url
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
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
    path("ingredient", views.ingredient, name="ingredient"),
    path("remove-ingredient", views.remove_ingredients, name="remove_ingredients"),
    path("add-ingredient", views.add_ingredient, name="add_ingredient"),
    path("edit-ingredient/<int:ingredient_number>",
         views.edit_ingredient,
         name="edit_ingredient"),
    path("ac-sku", views.autocomplete_skus, name="autocomplete_skus"),
    path("edit-formula/<int:sku_number>", views.edit_formula, name="edit_formula"),
    # Import/export views
    path("import-page/", views.import_page, name="import_page"),
    path("import_landing/", views.import_landing, name="import_landing"),
    path("export/", views.export_test, name="export"),
    # Account management views
    url(r"^login/$", auth_views.LoginView.as_view(), name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("show_one_goal/", login_required(views.show_one_goal), name="show_one_goal"),
    path("show_one_goal/<int:goal_id>", login_required(views.show_one_goal),
         name="show_one_goal"),
    path("generate_report/", views.generate_report, name="result"),
    path("download_calculation/", views.download_calculation,
         name="download_calculation"),
    path("save_goal/", login_required(views.save_goal), name="save_goal"),
    path("show_all_goals/", views.show_all_goals, name="show_all_goals"),
    path("download_goal/", views.download_goal, name="download_goal"),
    path("generate_calculation_pdf/", views.generate_calculation_pdf,
         name="generate_calculation_pdf"),
]
