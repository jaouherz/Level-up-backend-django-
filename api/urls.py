from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views import ApplicationViewSet, ProfileViewSet, OfferViewSet, ranked_candidates
# Create a router for all ViewSets
router = DefaultRouter()
router.register(r'applications', ApplicationViewSet, basename='applications')

router.register(r'profiles', ProfileViewSet, basename='profile')
router.register(r'offers', OfferViewSet, basename='offer')
urlpatterns = [
    path('', include(router.urls)),
    path('offers/<int:offer_id>/ranked_candidates/', ranked_candidates),
]
