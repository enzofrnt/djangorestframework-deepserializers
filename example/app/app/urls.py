"""
URL configuration for app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from deepserializer_app.models import HighSchool, Student, Class
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.urls import path, include
from rest_framework import routers
from deepserializers import DeepViewSet
from deepserializer_app.views import SimpleStudentViewSet

router = routers.DefaultRouter()
DeepViewSet.init_router(router, [
    HighSchool,
    Student,
    Class,
])

router.register("simple-student", SimpleStudentViewSet, basename="simple-student")

urlpatterns = [
    path('', include(router.urls)),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("doc/",SpectacularSwaggerView.as_view(), name="swagger-ui"),
]
