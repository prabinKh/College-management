# semesters/urls.py
from django.urls import path
from .views.semester_views import (
    semester_list, semester_detail, add_semester, edit_semester, delete_semester, bulk_enroll_students
)
from .views.subject_views import (
    subject_detail, add_semester_subject, edit_semester_subject, delete_semester_subject, 
    remove_teacher_from_subject, manage_subject_students, get_subject_students
)
from .views.teacher_views import search_teachers, add_teacher, edit_teacher, delete_teacher
from .views.student_views import search_students, add_student, edit_student, delete_student
from .views.batch_views import (
    batch_detail, manage_batches, add_batch, edit_batch, delete_batch, 
    add_student_to_batch, remove_student_from_batch, move_students_between_batches
)
from .views.analytics_views import get_semester_analytics, export_semester_data

app_name = 'semesters'

urlpatterns = [
    # Semester Management URLs (most specific first)
    path('add/', add_semester, name='add_semester'),
    path('', semester_list, name='semester_list'),
    
    # Global Search URLs (before semester-specific patterns)
    path('api/teachers/search/', search_teachers, name='search_teachers'),
    path('api/students/search/', search_students, name='search_students'),
    
    # Global Teacher Management URLs
    path('teachers/add/', add_teacher, name='add_teacher'),
    path('teachers/<int:teacher_id>/edit/', edit_teacher, name='edit_teacher'),
    path('teachers/<int:teacher_id>/delete/', delete_teacher, name='delete_teacher'),
    
    # Global Student Management URLs
    path('students/add/', add_student, name='add_student'),
    path('students/<int:student_id>/edit/', edit_student, name='edit_student'),
    path('students/<int:student_id>/delete/', delete_student, name='delete_student'),
    
    # Global Batch Detail URL (by batch slug)
    path('batches/<slug:batch_slug>/', batch_detail, name='batch_detail'),
    
    # Semester-specific URLs (slug patterns)
    path('<slug:slug>/', semester_detail, name='semester_detail'),
    path('<slug:slug>/edit/', edit_semester, name='edit_semester'),
    path('<slug:slug>/delete/', delete_semester, name='delete_semester'),
    
    # Semester Bulk Operations
    path('<slug:slug>/bulk-enroll/', bulk_enroll_students, name='bulk_enroll_students'),
    
    # Analytics and Export URLs
    path('<slug:slug>/analytics/', get_semester_analytics, name='get_semester_analytics'),
    path('<slug:slug>/export/', export_semester_data, name='export_semester_data'),
    
    # Subject Management URLs
    path('<slug:slug>/subjects/add/', add_semester_subject, name='add_semester_subject'),
    path('<slug:slug>/subjects/<int:subject_id>/', subject_detail, name='subject_detail'),
    path('<slug:slug>/subjects/<int:subject_id>/edit/', edit_semester_subject, name='edit_semester_subject'),
    path('<slug:slug>/subjects/<int:subject_id>/delete/', delete_semester_subject, name='delete_semester_subject'),
    path('<slug:slug>/subjects/<int:subject_id>/remove-teacher/', remove_teacher_from_subject, name='remove_teacher_from_subject'),
    
    # Subject Student Management (AJAX APIs)
    path('<slug:slug>/subjects/<int:subject_id>/students/', get_subject_students, name='get_subject_students'),
    path('<slug:slug>/subjects/<int:subject_id>/manage-students/', manage_subject_students, name='manage_subject_students'),
    
    # Batch Management URLs
    path('<slug:slug>/batches/', manage_batches, name='manage_batches'),
    path('<slug:slug>/batches/add/', add_batch, name='add_batch'),
    path('<slug:slug>/batches/<int:batch_id>/edit/', edit_batch, name='edit_batch'),
    path('<slug:slug>/batches/<int:batch_id>/delete/', delete_batch, name='delete_batch'),
    
    # Batch Student Management (AJAX APIs)
    path('<slug:slug>/batches/<int:batch_id>/add-students/', add_student_to_batch, name='add_student_to_batch'),
    path('<slug:slug>/batches/<int:batch_id>/remove-students/', remove_student_from_batch, name='remove_student_from_batch'),
    path('<slug:slug>/batches/move-students/', move_students_between_batches, name='move_students_between_batches'),
]