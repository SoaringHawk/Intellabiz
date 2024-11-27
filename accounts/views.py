from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from .forms import SignUpForm, LoginForm
from django.conf import settings

def sign_up(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = SignUpForm()
    return render(request, 'accounts/signup.html', {'form': form, 'MEDIA_URL': settings.MEDIA_URL})

def log_in(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else:
        form = LoginForm()
    return render(request, 'accounts/signin.html', {'form': form, 'MEDIA_URL': settings.MEDIA_URL})

def log_out(request):
    if request.method == 'POST':
        logout(request)
        return redirect('home')
    return render(request, 'accounts/log_out.html', {'MEDIA_URL': settings.MEDIA_URL})


