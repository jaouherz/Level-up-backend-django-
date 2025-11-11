from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views import (
    ApplicationViewSet,ProfileViewSet, OfferViewSet, ranked_candidates,
    CertificationViewSet, UniversityViewSet, ScoreHistoryViewSet,
    replace_fakes_api, FeedbackViewSet, RegisterView, EmailTokenObtainPairView
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

router = DefaultRouter()
router.register(r'applications', ApplicationViewSet, basename='applications')
router.register(r'profiles', ProfileViewSet, basename='profile')
router.register(r'offers', OfferViewSet, basename='offer')
router.register(r'certifications', CertificationViewSet, basename='certifications')
router.register(r'universities', UniversityViewSet, basename='universities')
router.register(r'score-history', ScoreHistoryViewSet, basename='score-history')
router.register(r'feedbacks', FeedbackViewSet, basename='feedbacks')

urlpatterns = [
    path('', include(router.urls)),

    path('offers/<int:offer_id>/ranked_candidates/', ranked_candidates),
    path('offers/<int:offer_id>/replace_fakes/', replace_fakes_api),

    path("register/", RegisterView.as_view(), name="register"),             # public
    path("login/", EmailTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),     # public
]
