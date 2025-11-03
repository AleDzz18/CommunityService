from django.shortcuts import render

# Create your views here.

def homeDashboard(request):
    return render(request, 'homeDashboard.html')

def login(request):
    return render(request, 'login.html')