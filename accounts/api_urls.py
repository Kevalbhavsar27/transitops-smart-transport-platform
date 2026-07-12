from django.urls import path
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)

from .api_views import (
    CurrentUserAPIView,
    CustomTokenObtainPairView,
    LogoutAPIView,
)


app_name = "accounts_api"


urlpatterns = [
    path(
        "token/",
        CustomTokenObtainPairView.as_view(),
        name="token",
    ),

    path(
        "token/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh",
    ),

    path(
        "token/verify/",
        TokenVerifyView.as_view(),
        name="token_verify",
    ),

    path(
        "me/",
        CurrentUserAPIView.as_view(),
        name="current_user",
    ),

    path(
        "logout/",
        LogoutAPIView.as_view(),
        name="logout",
    ),
]