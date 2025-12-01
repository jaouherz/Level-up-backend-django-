from django.urls import path
from . import views

app_name = "admin"

urlpatterns = [
    path("", views.admin_dashboard, name="dashboard"),
    path("users", views.users, name="users"),
    path("offers", views.offers, name="offers"),
    path("companies", views.companies, name="companies"),
    path("universities", views.universities, name="universities"),
]
