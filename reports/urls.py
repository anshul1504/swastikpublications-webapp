from django.urls import path
from . import views

app_name = 'reports'  # 👈 IMPORTANT LINE
urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
]
