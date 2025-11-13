from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from api.views import (
    ApplicationViewSet, ProfileViewSet, OfferViewSet, ranked_candidates,
    CertificationViewSet, UniversityViewSet, ScoreHistoryViewSet,
    replace_fakes_api, FeedbackViewSet, RegisterView, EmailTokenObtainPairView,
    approve_user, pending_users, html_jwt_login, html_jwt_register, CompanyViewSet, html_logout, SkillViewSet
)

router = DefaultRouter()
router.register(r'applications', ApplicationViewSet, basename='applications')
router.register(r'profiles', ProfileViewSet, basename='profile')
router.register(r'offers', OfferViewSet, basename='offer')
router.register(r'certifications', CertificationViewSet, basename='certifications')
router.register(r'universities', UniversityViewSet, basename='universities')
router.register(r'score-history', ScoreHistoryViewSet, basename='score-history')
router.register(r'feedbacks', FeedbackViewSet, basename='feedbacks')
router.register(r'skills', SkillViewSet, basename='skills')
router.register(r"universities", UniversityViewSet)


urlpatterns = [
    path('', include(router.urls)),
    path('offers/<int:offer_id>/ranked_candidates/', ranked_candidates),
    path('offers/<int:offer_id>/replace_fakes/', replace_fakes_api),
    path("approve-user/<int:user_id>/", approve_user),
    path("pending-users/", pending_users),
    path("offers/my-company/", OfferViewSet.as_view({"get": "my_company"})),

    # JWT API endpoints
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", EmailTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # HTML pages
    path("auth/logout/", html_logout, name="html_logout"),

    path("auth/jwt-login/", html_jwt_login, name="html_jwt_login"),
    path("auth/jwt-register/", html_jwt_register, name="html_jwt_register"),

]