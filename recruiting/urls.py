# recruiting/urls.py

from django.urls import path
from . import views
from .views import university_demands_page, university_students_page, university_student_detail_page

app_name = "recruiting"

urlpatterns = [
    path("", views.recruiter_dashboard, name="dashboard"),
    path("offers/", views.recruiter_offers_list, name="offer_list"),
    path("offers/create/", views.recruiter_create_offer, name="offer_create"),
    path("offers/<int:offer_id>/", views.recruiter_offer_detail, name="offer_detail"),
    path("university/demands/", university_demands_page, name="uni_demands"),
    path("university/students/", university_students_page, name="uni_students"),
    path("university/student/<int:id>/", university_student_detail_page, name="uni_student_detail"),




]
