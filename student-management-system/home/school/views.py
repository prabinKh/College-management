# school/views.py (Updated)
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import Notification
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.contrib import messages

# Create your views here.

def index(request):
    return render(request, "authentication/login.html")

@login_required
def dashboard(request):
    """Student Dashboard"""
    if not request.user.is_student:
        messages.error(request, 'Access denied. Student access required.')
        return redirect('index')
    
    unread_notification = Notification.objects.filter(user=request.user, is_read=False)
    unread_notification_count = unread_notification.count()
    
    context = {
        'unread_notification': unread_notification,
        'unread_notification_count': unread_notification_count,
        'user': request.user
    }
    return render(request, "students/student-dashboard.html", context)

@login_required
def teacher_dashboard(request):
    """Teacher Dashboard"""
    if not request.user.is_teacher:
        messages.error(request, 'Access denied. Teacher access required.')
        return redirect('index')
    
    unread_notification = Notification.objects.filter(user=request.user, is_read=False)
    unread_notification_count = unread_notification.count()
    
    context = {
        'unread_notification': unread_notification,
        'unread_notification_count': unread_notification_count,
        'user': request.user
    }
    return render(request, "teachers/teacher-dashboard.html", context)

@login_required
def admin_dashboard(request):
    """Admin Dashboard"""
    if not request.user.is_admin:
        messages.error(request, 'Access denied. Admin access required.')
        return redirect('index')
    
    unread_notification = Notification.objects.filter(user=request.user, is_read=False)
    unread_notification_count = unread_notification.count()
    
    # Get some statistics for admin dashboard
    from student.models import Student
    from teachers.models import Teacher
    # try:
        # from department.models import Department
        # from subjects.models import Subject
        # total_departments = Department.objects.count()
        # total_subjects = Subject.objects.count()
    # except ImportError:
        # total_departments = 0
        # total_subjects = 0
    
    total_students = Student.objects.count()
    total_teachers = Teacher.objects.count() if 'teachers' in locals() else 0
    
    context = {
        'unread_notification': unread_notification,
        'unread_notification_count': unread_notification_count,
        'user': request.user,
        'total_students': total_students,
        'total_teachers': total_teachers,
        # 'total_departments': total_departments,
        # 'total_subjects': total_subjects,
    }
    return render(request, "Home/index.html", context)

def mark_notification_as_read(request):
    if request.method == 'POST':
        notification = Notification.objects.filter(user=request.user, is_read=False)
        notification.update(is_read=True)
        return JsonResponse({'status': 'success'})
    return HttpResponseForbidden()

def clear_all_notification(request):
    if request.method == "POST":
        notification = Notification.objects.filter(user=request.user)
        notification.delete()
        return JsonResponse({'status': 'success'})
    return HttpResponseForbidden()

@login_required
def get_notification_data(request):
    unread_notification = Notification.objects.filter(user=request.user, is_read=False)
    notifications_data = [
        {
            'username': n.user.username,
            'message': n.message,
            'created_at': n.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
        for n in unread_notification
    ]
    return JsonResponse({
        'count': unread_notification.count(),
        'notifications': notifications_data
    })