# recruiting/urls.py

from django.urls import path
from . import views

app_name = "recruiting"

urlpatterns = [
    path("", views.recruiter_dashboard, name="dashboard"),
    path("offers/", views.recruiter_offers_list, name="offer_list"),
    path("offers/create/", views.recruiter_create_offer, name="offer_create"),
    path("offers/<int:offer_id>/", views.recruiter_offer_detail, name="offer_detail"),
]
