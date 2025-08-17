# department/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("", views.department_list, name='department_list'),
    path("add/", views.add_department, name="add_department"),
    path('view/<str:slug>/', views.view_department, name='view_department'),
    path('edit/<str:slug>/', views.edit_department, name='edit_department'),
    path('delete/<str:slug>/', views.delete_department, name='delete_department'),
]