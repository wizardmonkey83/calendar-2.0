from django.urls import path
from .views import load_signup, load_login

urlpatterns = [
    path("signup/", load_signup, name="load_signup"),
    path("login/", load_login, name="load_login"),
]