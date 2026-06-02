from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.shortcuts import render, redirect
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth.decorators import login_required


@ensure_csrf_cookie
def user_login(request):
    """
    Force CSRF cookie on GET so login POST never fails.
    Also prevent logged-in users from seeing login page again.
    """
    # If user already logged in, redirect to dashboard
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect("dashboard")

        messages.error(request, "Invalid username or password!")

    return render(request, "accounts/login.html")


from django.views.decorators.csrf import ensure_csrf_cookie


@ensure_csrf_cookie
def signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        confirm = request.POST.get("confirm", "")


def user_logout(request):
    logout(request)
    return redirect("accounts:login")
