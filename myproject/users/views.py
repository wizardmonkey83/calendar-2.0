from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .forms import SignUpForm, LoginForm
from django.contrib.auth.models import User
from .models import Profile


# Create your views here.
def signup_view(request):
    if request.method == "PSOT":
        form = SignUpForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            email = form.cleaned_data["email"]

            if User.objects.filter(username=username).exists() or User.objects.filter(email=email).exists():
                form.add_error(None, "Email or Username already exists")
            else:
                user = form.save()
                # creates profile model alongside the user
                Profile.objects.create(user=user)
                login(request, user)


def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                
                return redirect("problem_list_window")
            else:
                form.add_error(None, "Invalid Email or Password")
            
    else:
        form = LoginForm()
    
    return render(request, "accounts/login.html", {"form": form})