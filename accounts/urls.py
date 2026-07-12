from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from accounts.forms import EmailAuthenticationForm
from accounts.views import *

app_name = "accounts"


urlpatterns = [
    path("login/",LoginView.as_view(template_name="registration/login.html",authentication_form=EmailAuthenticationForm,redirect_authenticated_user=True,),name="login"),
    path("logout/",LogoutView.as_view(),name="logout",),
    path("",account_list,name="account_list",),
    path("add/",account_create,name="account_create",),
]