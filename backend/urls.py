#from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
schema_view = get_schema_view(
    openapi.Info(
        title="LevelUp API",
        default_version='v1',
        description="Auto-generated documentation for all LevelUp endpoints",
        contact=openapi.Contact(email="jaouher2002@gmail.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)
urlpatterns = [
    #path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path("recruiting/", include("recruiting.urls", namespace="recruiting")),
    path("admin/", include("admin_side.urls", namespace="admin")),
    path('', TemplateView.as_view(template_name='api/home.html'), name='home'),

    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),

    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
]
