# school/urls.py (Updated)
from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.index, name="index"),
    
    # Dashboards
    path('dashboard/', views.dashboard, name='dashboard'),  # Student dashboard
    path('teacher-dashboard/', views.teacher_dashboard, name='teacher_dashboard'),  # Teacher dashboard
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),  # Admin dashboard
    
    # Notifications
    path('notification/mark-as-read/', views.mark_notification_as_read, name='mark_notification_as_read'),
    path('notification/clear-all/', views.clear_all_notification, name="clear_all_notification"),
    path('notification/data/', views.get_notification_data, name="get_notification_data"),

]