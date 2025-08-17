
# semesters/views/teacher_views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.db import transaction
from django.contrib.auth import get_user_model
from teachers.models import Teacher
from .utils import create_notification, is_admin
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

@login_required
def search_teachers(request):
    """Search teachers by email, name (AJAX)"""
    query = request.GET.get('q', '').strip()
    subject_id = request.GET.get('subject_id')
    
    if len(query) < 2:
        return JsonResponse({'teachers': []})
    
    try:
        teachers = Teacher.objects.filter(
            Q(email__icontains=query) | 
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query),
            is_active=True
        ).select_related('user')
        
        # Exclude current teacher if editing subject
        if subject_id:
            try:
                from ..models import SemesterSubject
                semester_subject = SemesterSubject.objects.get(id=subject_id)
                if semester_subject.teacher:
                    teachers = teachers.exclude(id=semester_subject.teacher.id)
            except SemesterSubject.DoesNotExist:
                pass
        
        # Limit results
        teachers = teachers[:15]
        
        teacher_list = [
            {
                'id': teacher.id,
                'email': teacher.email,
                'name': teacher.get_full_name(),
                'qualification': teacher.qualification or 'N/A'
            } for teacher in teachers
        ]
        
        logger.debug("Found %d teachers for query: %s", len(teacher_list), query)
        return JsonResponse({'teachers': teacher_list})
        
    except Exception as e:
        logger.exception("Error searching teachers: %s", str(e))
        return JsonResponse({'error': f'Error searching teachers: {str(e)}'}, status=500)

@login_required
@user_passes_test(is_admin, login_url='index')
def add_teacher(request):
    """Add a new teacher"""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        qualification = request.POST.get('qualification', '').strip()
        
        if not all([email, first_name, last_name]):
            messages.error(request, "Please fill in all required fields.")
            return render(request, 'semesters/add_teacher.html')
        
        try:
            with transaction.atomic():
                # Check if teacher already exists
                if Teacher.objects.filter(email=email).exists():
                    messages.error(request, f"A teacher with email {email} already exists.")
                    return render(request, 'semesters/add_teacher.html')
                
                # Create or get user
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        'username': email,
                        'first_name': first_name,
                        'last_name': last_name,
                        'is_active': True
                    }
                )
                
                if created:
                    user.set_password('teacher123')  # Default password
                    user.save()
                
                # Create teacher
                teacher = Teacher.objects.create(
                    user=user,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    qualification=qualification,
                    is_active=True
                )
                
                create_notification(request.user, f"Created teacher: {teacher.get_full_name()}")
                messages.success(request, f"Teacher '{teacher.get_full_name()}' created successfully!")
                logger.info("Created teacher: %s by user: %s", teacher.get_full_name(), request.user.username)
                
                return redirect('semesters:semester_list')  # Redirect to appropriate page
                
        except Exception as e:
            messages.error(request, f"Error creating teacher: {str(e)}")
            logger.exception("Error creating teacher: %s", str(e))
    
    return render(request, 'semesters/add_teacher.html')

@login_required
@user_passes_test(is_admin, login_url='index')
def edit_teacher(request, teacher_id):
    """Edit an existing teacher"""
    teacher = get_object_or_404(Teacher, id=teacher_id)
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        qualification = request.POST.get('qualification', '').strip()
        
        if not all([first_name, last_name]):
            messages.error(request, "Please fill in all required fields.")
            return render(request, 'semesters/edit_teacher.html', {'teacher': teacher})
        
        try:
            with transaction.atomic():
                teacher.first_name = first_name
                teacher.last_name = last_name
                teacher.qualification = qualification
                teacher.save()
                
                # Update user name if exists
                if teacher.user:
                    teacher.user.first_name = first_name
                    teacher.user.last_name = last_name
                    teacher.user.save()
                
                create_notification(request.user, f"Updated teacher: {teacher.get_full_name()}")
                messages.success(request, f"Teacher '{teacher.get_full_name()}' updated successfully!")
                logger.info("Updated teacher: %s by user: %s", teacher.get_full_name(), request.user.username)
                
                return redirect('semesters:semester_list')  # Redirect to appropriate page
                
        except Exception as e:
            messages.error(request, f"Error updating teacher: {str(e)}")
            logger.exception("Error updating teacher %s: %s", teacher.get_full_name(), str(e))
    
    context = {'teacher': teacher}
    return render(request, 'semesters/edit_teacher.html', context)

@login_required
@user_passes_test(is_admin, login_url='index')
def delete_teacher(request, teacher_id):
    """Delete (deactivate) a teacher (AJAX)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)
    
    teacher = get_object_or_404(Teacher, id=teacher_id)
    
    try:
        with transaction.atomic():
            # Check if teacher has active assignments
            from ..models import SemesterSubject
            active_assignments = SemesterSubject.objects.filter(
                teacher=teacher,
                is_active=True
            ).count()
            
            if active_assignments > 0:
                return JsonResponse({
                    'success': False, 
                    'error': f'Cannot delete teacher with {active_assignments} active subject assignments. Please remove from all subjects first.'
                }, status=400)
            
            teacher_name = teacher.get_full_name()
            teacher.is_active = False
            teacher.save()
            
            # Deactivate user as well
            if teacher.user:
                teacher.user.is_active = False
                teacher.user.save()
            
            create_notification(request.user, f"Deactivated teacher: {teacher_name}")
            logger.info("Deactivated teacher: %s by user: %s", teacher_name, request.user.username)
            
            return JsonResponse({
                'success': True, 
                'message': f'Teacher "{teacher_name}" deactivated successfully'
            })
            
    except Exception as e:
        logger.exception("Error deactivating teacher %s: %s", teacher.get_full_name(), str(e))
        return JsonResponse({
            'success': False, 
            'error': f'Error deactivating teacher: {str(e)}'
        }, status=500)