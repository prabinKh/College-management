from django.urls import path
from . import views

urlpatterns = [
    path('', views.subject_list, name='subject_list'),
    path('add/', views.add_subject, name='add_subject'),
    path('view/<slug:slug>/', views.view_subject, name='view_subject'),
    path('edit/<slug:slug>/', views.edit_subject, name='edit_subject'),
    path('delete/<slug:slug>/', views.delete_subject, name='delete_subject'),
]