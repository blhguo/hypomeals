from django.conf.urls import url
from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    # Normal views
    path("", views.index, name="index"),
    # SKU views
    # Import/export views
    path("import-page/", views.import_page, name="import_page"),
    path("import_landing/", views.import_landing, name="import_landing"),
    path("export/", views.export_test, name="export"),
    # Account management views
    url(r"^login/$", auth_views.LoginView.as_view(), name="login"),
    path("logout/", views.logout_view, name="logout"),

]
