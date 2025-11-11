from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = "recruiting"

urlpatterns = [
    path("", views.rh_dashboard, name="dashboard"),

    # Offers
    path("offers/", views.offer_list, name="offer_list"),
    path("offers/new/", views.offer_create, name="offer_create"),
    path("offers/<int:pk>/edit/", views.offer_edit, name="offer_edit"),
    path("offers/<int:pk>/close/", views.offer_close, name="offer_close"),

    # Applications for an offer
    path("offers/<int:offer_id>/applications/", views.offer_applications, name="offer_apps"),
    path("applications/<int:app_id>/status/", views.application_update_status, name="app_update_status"),

    # Feedback on an application
    path("applications/<int:app_id>/feedback/new/", views.feedback_create, name="feedback_create"),
    path('', TemplateView.as_view(template_name="home.html"), name="home"),
]