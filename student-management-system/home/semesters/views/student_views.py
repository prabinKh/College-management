# semesters/views/student_views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.db import transaction
from django.contrib.auth import get_user_model
from student.models import Student
from .utils import create_notification, is_admin
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

@login_required

@login_required
def search_students(request, slug):
    """Search students by email, name, or ID (AJAX)"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'students': []})
    
    try:
        semester = get_object_or_404(Semester, slug=slug)
        
        # Get IDs of students already enrolled in the semester
        enrolled_student_ids = SemesterEnrollment.objects.filter(
            semester=semester,
            status='active'
        ).values_list('student_id', flat=True)
        
        # Search for students not already enrolled
        students = Student.objects.filter(
            Q(user__email__icontains=query) | 
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query) |
            Q(student_id__icontains=query),
            user__is_active=True
        ).exclude(
            id__in=enrolled_student_ids
        ).select_related('user')
        
        # Limit results
        students = students[:15]
        
        student_list = [
            {
                'id': student.id,
                'student_id': student.student_id or 'N/A',
                'email': student.user.email if student.user else student.email,
                'name': student.get_full_name(),
                'class': student.student_class or 'N/A'
            } for student in students
        ]
        
        logger.debug("Found %d students for query: %s in semester: %s", len(student_list), query, semester.semester_name)
        return JsonResponse({'students': student_list})
        
    except Exception as e:
        logger.exception("Error searching students: %s", str(e))
        return JsonResponse({'error': f'Error searching students: {str(e)}'}, status=500)
@login_required
@user_passes_test(is_admin, login_url='index')
def add_student(request):
    """Add a new student"""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        student_id = request.POST.get('student_id', '').strip()
        student_class = request.POST.get('student_class', '').strip()
        
        if not all([email, first_name, last_name, student_id]):
            messages.error(request, "Please fill in all required fields.")
            return render(request, 'semesters/add_student.html')
        
        try:
            with transaction.atomic():
                # Check if user already exists
                if User.objects.filter(email=email).exists():
                    messages.error(request, f"A user with email {email} already exists.")
                    return render(request, 'semesters/add_student.html')
                
                # Check if student ID already exists
                if Student.objects.filter(student_id=student_id).exists():
                    messages.error(request, f"A student with ID {student_id} already exists.")
                    return render(request, 'semesters/add_student.html')
                
                # Create user
                user = User.objects.create(
                    username=email,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=True
                )
                user.set_password('student123')  # Default password
                user.save()
                
                # Create student
                student = Student.objects.create(
                    user=user,
                    first_name=first_name,
                    last_name=last_name,
                    student_id=student_id,
                    student_class=student_class,
                    is_active=True
                )
                
                create_notification(request.user, f"Created student: {student.get_full_name()}")
                messages.success(request, f"Student '{student.get_full_name()}' created successfully!")
                logger.info("Created student: %s by user: %s", student.get_full_name(), request.user.username)
                
                return redirect('semesters:semester_list')  # Redirect to appropriate page
                
        except Exception as e:
            messages.error(request, f"Error creating student: {str(e)}")
            logger.exception("Error creating student: %s", str(e))
    
    return render(request, 'semesters/add_student.html')

@login_required
@user_passes_test(is_admin, login_url='index')
def edit_student(request, student_id):
    """Edit an existing student"""
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        student_class = request.POST.get('student_class', '').strip()
        
        if not all([first_name, last_name]):
            messages.error(request, "Please fill in all required fields.")
            return render(request, 'semesters/edit_student.html', {'student': student})
        
        try:
            with transaction.atomic():
                student.first_name = first_name
                student.last_name = last_name
                student.student_class = student_class
                student.save()
                
                # Update user name if exists
                if student.user:
                    student.user.first_name = first_name
                    student.user.last_name = last_name
                    student.user.save()
                
                create_notification(request.user, f"Updated student: {student.get_full_name()}")
                messages.success(request, f"Student '{student.get_full_name()}' updated successfully!")
                logger.info("Updated student: %s by user: %s", student.get_full_name(), request.user.username)
                
                return redirect('semesters:semester_list')  # Redirect to appropriate page
                
        except Exception as e:
            messages.error(request, f"Error updating student: {str(e)}")
            logger.exception("Error updating student %s: %s", student.get_full_name(), str(e))
    
    context = {'student': student}
    return render(request, 'semesters/edit_student.html', context)

@login_required
@user_passes_test(is_admin, login_url='index')
def delete_student(request, student_id):
    """Delete (deactivate) a student (AJAX)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)
    
    student = get_object_or_404(Student, id=student_id)
    
    try:
        with transaction.atomic():
            # Check if student has active enrollments
            from ..models import SemesterEnrollment
            active_enrollments = SemesterEnrollment.objects.filter(
                student=student,
                status='active'
            ).count()
            
            if active_enrollments > 0:
                return JsonResponse({
                    'success': False, 
                    'error': f'Cannot delete student with {active_enrollments} active enrollments. Please remove from all semesters first.'
                }, status=400)
            
            student_name = student.get_full_name()
            student.is_active = False
            student.save()
            
            # Deactivate user as well
            if student.user:
                student.user.is_active = False
                student.user.save()
            
            create_notification(request.user, f"Deactivated student: {student_name}")
            logger.info("Deactivated student: %s by user: %s", student_name, request.user.username)
            
            return JsonResponse({
                'success': True, 
                'message': f'Student "{student_name}" deactivated successfully'
            })
            
    except Exception as e:
        logger.exception("Error deactivating student %s: %s", student.get_full_name(), str(e))
        return JsonResponse({
            'success': False, 
            'error': f'Error deactivating student: {str(e)}'
        }, status=500)