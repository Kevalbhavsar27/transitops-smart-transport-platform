"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
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
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import LoginView
from django.urls import include, path

from accounts.forms import EmailAuthenticationForm


from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import LoginView
from django.urls import include, path

from accounts.forms import EmailAuthenticationForm


urlpatterns = [
    path(
        "admin/",
        admin.site.urls,
    ),

    # Root login page
    path(
        "",
        LoginView.as_view(
            template_name="registration/login.html",
            authentication_form=EmailAuthenticationForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),

    # Normal web application
    path(
        "accounts/",
        include("accounts.urls"),
    ),

    path(
        "dashboard/",
        include("dashboard.urls"),
    ),

    path(
        "fleet/",
        include("fleet.urls"),
    ),

    path(
        "operations/",
        include("operations.urls"),
    ),

    # REST APIs
    path(
        "api/v1/auth/",
        include("accounts.api_urls"),
    ),

    path(
        "api/v1/fleet/",
        include("fleet.api_urls"),
    ),

    path(
        "api/v1/operations/",
        include("operations.api_urls"),
    ),
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )



