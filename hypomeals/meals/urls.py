from django.conf.urls import url
from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    # Normal views
    path("", views.index, name="index"),
    # SKU views
    # Import/export views
    # Account management views
    url(r"^login/$", auth_views.LoginView.as_view(), name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("import-page/", views.import_page, name="import_page"),
]
