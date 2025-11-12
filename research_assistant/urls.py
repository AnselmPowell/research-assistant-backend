"""URL configuration for research_assistant project."""

from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework.response import Response
from rest_framework.views import APIView
import requests
from urllib.parse import urlparse
import re
import logging


schema_view = get_schema_view(
   openapi.Info(
      title="Research Assistant API",
      default_version='v1',
      description="API for the AI Research Assistant",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="contact@researchnote.local"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
