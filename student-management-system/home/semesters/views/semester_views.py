from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q, Count
from django.db import transaction
from ..models import Semester, Batch, SemesterSubject, SemesterEnrollment, SubjectEnrollment
from department.models import Department
from subjects.models import Subject
from teachers.models import Teacher
from student.models import Student
from .utils import create_notification, is_admin
import logging
from django.core.paginator import Paginator


logger = logging.getLogger(__name__)

@login_required
def semester_list(request):
    """List all semesters with filtering and search"""
    semesters = Semester.objects.select_related('department', 'created_by').prefetch_related(
        'semester_subjects__teacher',
        'semester_subjects__subject',
        'semester_enrollments',
        'batches'
    ).annotate(
        student_count=Count('semester_enrollments', filter=Q(semester_enrollments__status='active')),
        subject_count=Count('semester_subjects'),
        batch_count=Count('batches')
    )
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        semesters = semesters.filter(status=status_filter)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        semesters = semesters.filter(
            Q(semester_name__icontains=search_query) |
            Q(department__department_name__icontains=search_query) |
            Q(academic_year__icontains=search_query) |
            Q(semester_id__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(semesters, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_choices': Semester.STATUS_CHOICES,
        'current_status': status_filter,
        'search_query': search_query,
    }
    return render(request, 'semesters/semester_list.html', context)

@login_required
def semester_detail(request, slug):
    """Detailed view of a semester with all related data"""
    semester = get_object_or_404(
        Semester.objects.select_related('department', 'created_by')
        .prefetch_related(
            'semester_subjects__subject',
            'semester_subjects__teacher',
            'semester_subjects__subject_enrollments__student__user',
            'semester_enrollments__student__user',
            'semester_enrollments__batch',
            'batches'
        ),
        slug=slug
    )
    
    # Get semester statistics
    active_enrollments = semester.semester_enrollments.filter(status='active')
    semester_subjects = semester.semester_subjects.all()
    batches = semester.batches.all()
    
    # Get subjects with enrollment counts
    subjects_data = []
    for subject in semester_subjects:
        enrolled_count = subject.subject_enrollments.filter(status='active').count()
        subjects_data.append({
            'semester_subject': subject,
            'enrolled_count': enrolled_count,
            'available_spots': subject.get_available_spots()
        })
    
    # Get batches with enrollment counts
    batches_data = []
    for batch in batches:
        enrolled_count = batch.enrollments.filter(status='active').count()
        batches_data.append({
            'batch': batch,
            'enrolled_count': enrolled_count,
            'available_spots': batch.get_available_spots()
        })
    
    context = {
        'semester': semester,
        'active_enrollments': active_enrollments,
        'subjects_data': subjects_data,
        'batches_data': batches_data,
        'student_count': active_enrollments.count(),
        'subject_count': semester_subjects.count(),
        'teacher_count': semester_subjects.filter(teacher__isnull=False).values('teacher').distinct().count(),
        'batch_count': batches.count(),
    }
    return render(request, 'semesters/semester_detail.html', context)

@login_required
@user_passes_test(is_admin, login_url='index')
def add_semester(request):
    """Add a new semester"""
    if request.method == 'POST':
        semester_name = request.POST.get('semester_name', '').strip()
        academic_year = request.POST.get('academic_year', '').strip()
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        status = request.POST.get('status', 'upcoming')
        description = request.POST.get('description', '').strip()
        department_id = request.POST.get('department')
        
        if not all([semester_name, academic_year, department_id]):
            messages.error(request, "Please fill in all required fields.")
            return render(request, 'semesters/add_semester.html', {
                'departments': Department.objects.all(),
                'semester_status_choices': Semester.STATUS_CHOICES,
            })
        
        try:
            with transaction.atomic():
                department = get_object_or_404(Department, id=department_id)
                
                # Check for duplicate
                if Semester.objects.filter(
                    semester_name=semester_name,
                    academic_year=academic_year,
                    department=department
                ).exists():
                    messages.error(request, "A semester with this name and year already exists in this department.")
                    return render(request, 'semesters/add_semester.html', {
                        'departments': Department.objects.all(),
                        'semester_status_choices': Semester.STATUS_CHOICES,
                    })
                
                semester = Semester.objects.create(
                    semester_name=semester_name,
                    academic_year=academic_year,
                    start_date=start_date or None,
                    end_date=end_date or None,
                    status=status,
                    description=description,
                    department=department,
                    created_by=request.user
                )
                
                create_notification(request.user, f"Created semester: {semester.semester_name}")
                messages.success(request, f"Semester '{semester.semester_name}' created successfully!")
                logger.info("Created semester: %s by user: %s", semester.semester_name, request.user.username)
                
                return redirect('semesters:semester_detail', slug=semester.slug)
                
        except Exception as e:
            messages.error(request, f"Error creating semester: {str(e)}")
            logger.exception("Error creating semester: %s", str(e))
    
    context = {
        'departments': Department.objects.all(),
        'semester_status_choices': Semester.STATUS_CHOICES,
    }
    return render(request, 'semesters/add_semester.html', context)

@login_required
@user_passes_test(is_admin, login_url='index')
def edit_semester(request, slug):
    """Edit an existing semester"""
    semester = get_object_or_404(Semester, slug=slug)
    
    if request.method == 'POST':
        semester_name = request.POST.get('semester_name', '').strip()
        academic_year = request.POST.get('academic_year', '').strip()
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        status = request.POST.get('status')
        description = request.POST.get('description', '').strip()
        department_id = request.POST.get('department')
        
        if not all([semester_name, academic_year, department_id]):
            messages.error(request, "Please fill in all required fields.")
            return render(request, 'semesters/edit_semester.html', {
                'semester': semester,
                'departments': Department.objects.all(),
                'semester_status_choices': Semester.STATUS_CHOICES,
            })
        
        try:
            with transaction.atomic():
                department = get_object_or_404(Department, id=department_id)
                
                # Check for duplicate (excluding current semester)
                if Semester.objects.filter(
                    semester_name=semester_name,
                    academic_year=academic_year,
                    department=department
                ).exclude(id=semester.id).exists():
                    messages.error(request, "A semester with this name and year already exists in this department.")
                    return render(request, 'semesters/edit_semester.html', {
                        'semester': semester,
                        'departments': Department.objects.all(),
                        'semester_status_choices': Semester.STATUS_CHOICES,
                    })
                
                semester.semester_name = semester_name
                semester.academic_year = academic_year
                semester.start_date = start_date or None
                semester.end_date = end_date or None
                semester.status = status
                semester.description = description
                semester.department = department
                semester.save()
                
                create_notification(request.user, f"Updated semester: {semester.semester_name}")
                messages.success(request, f"Semester '{semester.semester_name}' updated successfully!")
                logger.info("Updated semester: %s by user: %s", semester.semester_name, request.user.username)
                
                return redirect('semesters:semester_detail', slug=semester.slug)
                
        except Exception as e:
            messages.error(request, f"Error updating semester: {str(e)}")
            logger.exception("Error updating semester %s: %s", semester.semester_name, str(e))
    
    context = {
        'semester': semester,
        'departments': Department.objects.all(),
        'semester_status_choices': Semester.STATUS_CHOICES,
    }
    return render(request, 'semesters/edit_semester.html', context)

@login_required
@user_passes_test(is_admin, login_url='index')
def delete_semester(request, slug):
    """Delete a semester and all related data (AJAX)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)
    
    semester = get_object_or_404(Semester, slug=slug)
    
    try:
        with transaction.atomic():
            semester_name = semester.semester_name
            
            # Delete related enrollments
            SemesterEnrollment.objects.filter(semester=semester).delete()
            SubjectEnrollment.objects.filter(semester_subject__semester=semester).delete()
            
            # Delete related subjects and batches
            SemesterSubject.objects.filter(semester=semester).delete()
            Batch.objects.filter(semester=semester).delete()
            
            # Delete the semester
            semester.delete()
            
            create_notification(request.user, f"Deleted semester: {semester_name}")
            logger.info("Deleted semester: %s and all related data by user: %s", semester_name, request.user.username)
            
            return JsonResponse({
                'success': True,
                'message': f'Semester "{semester_name}" and all associated data deleted successfully'
            })
            
    except Exception as e:
        logger.exception("Error deleting semester %s: %s", semester.semester_name, str(e))
        return JsonResponse({
            'success': False,
            'error': f'Error deleting semester: {str(e)}'
        }, status=500)

@login_required
@user_passes_test(is_admin, login_url='index')
def bulk_enroll_students(request, slug):
    """Bulk enroll students to semester"""
    semester = get_object_or_404(Semester, slug=slug)
    
    if request.method == 'POST':
        student_emails = request.POST.get('student_emails', '').strip()
        batch_id = request.POST.get('batch_id')
        
        if not student_emails or not batch_id:
            messages.error(request, "Please provide student emails and select a batch.")
            return redirect('semesters:semester_detail', slug=slug)
        
        batch = get_object_or_404(Batch, id=batch_id, semester=semester)
        
        # Parse emails
        emails = [email.strip() for email in student_emails.split(',') if email.strip()]
        
        if not emails:
            messages.error(request, "Please provide valid email addresses.")
            return redirect('semesters:semester_detail', slug=slug)
        
        try:
            with transaction.atomic():
                enrolled_count = 0
                errors = []
                already_enrolled = []
                not_found = []
                
                for email in emails:
                    try:
                        # Find student by email
                        student = Student.objects.select_related('user').get(
                            user__email=email,
                            is_active=True
                        )
                        
                        # Check if already enrolled
                        if SemesterEnrollment.objects.filter(
                            semester=semester,
                            student=student,
                            status='active'
                        ).exists():
                            already_enrolled.append(email)
                            continue
                        
                        # Check batch capacity
                        if not batch.can_enroll_student():
                            errors.append(f"Batch {batch.batch_name} is full")
                            break
                        
                        # Enroll student
                        SemesterEnrollment.objects.create(
                            semester=semester,
                            student=student,
                            batch=batch,
                            enrolled_by=request.user,
                            status='active'
                        )
                        enrolled_count += 1
                        
                        # Notify student
                        if student.user:
                            create_notification(
                                student.user,
                                f"You have been enrolled in {semester.semester_name}"
                            )
                    
                    except Student.DoesNotExist:
                        not_found.append(email)
                    except Exception as e:
                        errors.append(f"Error enrolling {email}: {str(e)}")
                
                # Create summary message
                message_parts = []
                if enrolled_count > 0:
                    message_parts.append(f"Successfully enrolled {enrolled_count} students")
                
                if already_enrolled:
                    message_parts.append(f"{len(already_enrolled)} students were already enrolled")
                
                if not_found:
                    message_parts.append(f"{len(not_found)} students not found")
                
                if errors:
                    message_parts.append(f"{len(errors)} errors occurred")
                
                if enrolled_count > 0:
                    messages.success(request, ". ".join(message_parts))
                    create_notification(
                        request.user,
                        f"Bulk enrolled {enrolled_count} students in {semester.semester_name}"
                    )
                else:
                    messages.warning(request, ". ".join(message_parts))
                
                logger.info("Bulk enrollment in %s: enrolled=%d, errors=%s", 
                          semester.semester_name, enrolled_count, errors)
                
        except Exception as e:
            messages.error(request, f"Error during bulk enrollment: {str(e)}")
            logger.exception("Error in bulk enrollment for %s: %s", semester.semester_name, str(e))
    
    return redirect('semesters:semester_detail', slug=slug)