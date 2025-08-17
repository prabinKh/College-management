# semesters/views/subject_views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.db import transaction
from django.contrib.auth import get_user_model
from django.urls import reverse
from ..models import Semester, SemesterSubject, SubjectEnrollment, SemesterEnrollment
from subjects.models import Subject
from teachers.models import Teacher
from student.models import Student
from .utils import create_notification, is_admin
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

@login_required
def subject_detail(request, slug, subject_id):
    """Detailed view of a subject within a semester"""
    semester = get_object_or_404(Semester, slug=slug)
    semester_subject = get_object_or_404(
        SemesterSubject.objects.select_related('subject', 'teacher', 'semester')
        .prefetch_related('subject_enrollments__student__user'),
        id=subject_id,
        semester=semester
    )
    
    # Get enrolled students
    enrolled_students = semester_subject.subject_enrollments.filter(status='active').select_related(
        'student__user', 'semester_enrollment__batch'
    )
    
    # Get available students (enrolled in semester but not in this subject)
    semester_student_ids = SemesterEnrollment.objects.filter(
        semester=semester,
        status='active'
    ).values_list('student_id', flat=True)
    
    subject_student_ids = enrolled_students.values_list('student_id', flat=True)
    
    available_students = Student.objects.filter(
        id__in=semester_student_ids
    ).exclude(
        id__in=subject_student_ids
    ).select_related('user')[:20]  # Limit for performance
    
    context = {
        'semester': semester,
        'semester_subject': semester_subject,
        'enrolled_students': enrolled_students,
        'available_students': available_students,
        'enrolled_count': enrolled_students.count(),
        'available_count': available_students.count(),
        'can_enroll_more': semester_subject.can_enroll_student(),
    }
    return render(request, 'semesters/subject_detail.html', context)

@login_required
@user_passes_test(is_admin, login_url='index')
def add_semester_subject(request, slug):
    """Add a subject to a semester"""
    semester = get_object_or_404(Semester, slug=slug)
    
    if request.method == 'POST':
        subject_id = request.POST.get('subject')
        teacher_email = request.POST.get('teacher_email', '').strip()
        credits = request.POST.get('credits', 1)
        hours_per_week = request.POST.get('hours_per_week', 3)
        max_students = request.POST.get('max_students', 0)
        
        if not subject_id:
            messages.error(request, "Please select a subject.")
            return render(request, 'semesters/add_subject.html', {
                'semester': semester,
                'subjects': Subject.objects.filter(is_active=True),
            })
        
        try:
            with transaction.atomic():
                subject = get_object_or_404(Subject, id=subject_id)
                teacher = None
                
                # Check if subject already exists in semester
                if SemesterSubject.objects.filter(semester=semester, subject=subject).exists():
                    messages.error(request, f"Subject '{subject.subject_name}' is already added to this semester.")
                    return render(request, 'semesters/add_subject.html', {
                        'semester': semester,
                        'subjects': Subject.objects.filter(is_active=True),
                    })
                
                # Find teacher if email provided
                if teacher_email:
                    try:
                        teacher = Teacher.objects.get(email=teacher_email, is_active=True)
                    except Teacher.DoesNotExist:
                        messages.error(request, f"Teacher with email '{teacher_email}' not found.")
                        return render(request, 'semesters/add_subject.html', {
                            'semester': semester,
                            'subjects': Subject.objects.filter(is_active=True),
                        })
                
                # Create semester subject
                semester_subject = SemesterSubject.objects.create(
                    semester=semester,
                    subject=subject,
                    teacher=teacher,
                    credits=int(credits) if credits else 1,
                    hours_per_week=int(hours_per_week) if hours_per_week else 3,
                    max_students=int(max_students) if max_students else 0
                )
                
                # Notify teacher if assigned
                if teacher and teacher.user:
                    create_notification(
                        teacher.user,
                        f"You have been assigned to teach {subject.subject_name} in {semester.semester_name}"
                    )
                
                create_notification(
                    request.user,
                    f"Added subject {subject.subject_name} to {semester.semester_name}"
                )
                
                messages.success(request, f"Subject '{subject.subject_name}' added successfully!")
                logger.info("Added subject %s to %s by user: %s", 
                          subject.subject_name, semester.semester_name, request.user.username)
                
                return redirect('semesters:subject_detail', slug=slug, subject_id=semester_subject.id)
                
        except Exception as e:
            messages.error(request, f"Error adding subject: {str(e)}")
            logger.exception("Error adding subject to %s: %s", semester.semester_name, str(e))
    
    # Get subjects not already in this semester
    existing_subject_ids = semester.semester_subjects.values_list('subject_id', flat=True)
    available_subjects = Subject.objects.filter(is_active=True).exclude(id__in=existing_subject_ids)
    
    context = {
        'semester': semester,
        'subjects': available_subjects,
    }
    return render(request, 'semesters/add_subject.html', context)

@login_required
@user_passes_test(is_admin, login_url='index')
def edit_semester_subject(request, slug, subject_id):
    """Edit a subject in a semester"""
    semester = get_object_or_404(Semester, slug=slug)
    semester_subject = get_object_or_404(SemesterSubject, id=subject_id, semester=semester)
    
    if request.method == 'POST':
        teacher_email = request.POST.get('teacher_email', '').strip()
        credits = request.POST.get('credits', semester_subject.credits)
        hours_per_week = request.POST.get('hours_per_week', semester_subject.hours_per_week)
        max_students = request.POST.get('max_students', semester_subject.max_students)
        
        try:
            with transaction.atomic():
                old_teacher = semester_subject.teacher
                new_teacher = None
                
                # Handle teacher assignment
                if teacher_email:
                    try:
                        new_teacher = Teacher.objects.get(email=teacher_email, is_active=True)
                        if old_teacher and old_teacher.email == teacher_email:
                            messages.warning(request, f"{new_teacher.get_full_name()} is already assigned to this subject.")
                        else:
                            semester_subject.teacher = new_teacher
                    except Teacher.DoesNotExist:
                        messages.error(request, f"Teacher with email '{teacher_email}' not found.")
                        return redirect('semesters:subject_detail', slug=slug, subject_id=subject_id)
                else:
                    # Remove teacher if email is empty
                    semester_subject.teacher = None
                
                # Update other fields
                semester_subject.credits = int(credits) if credits else 1
                semester_subject.hours_per_week = int(hours_per_week) if hours_per_week else 3
                semester_subject.max_students = int(max_students) if max_students else 0
                semester_subject.save()
                
                # Notify teachers about changes
                if old_teacher and old_teacher != new_teacher and old_teacher.user:
                    create_notification(
                        old_teacher.user,
                        f"You have been removed from teaching {semester_subject.subject.subject_name} in {semester.semester_name}"
                    )
                
                if new_teacher and new_teacher != old_teacher and new_teacher.user:
                    create_notification(
                        new_teacher.user,
                        f"You have been assigned to teach {semester_subject.subject.subject_name} in {semester.semester_name}"
                    )
                
                create_notification(
                    request.user,
                    f"Updated subject {semester_subject.subject.subject_name} in {semester.semester_name}"
                )
                
                messages.success(request, f"Subject '{semester_subject.subject.subject_name}' updated successfully!")
                logger.info("Updated subject %s in %s by user: %s", 
                          semester_subject.subject.subject_name, semester.semester_name, request.user.username)
                
        except Exception as e:
            messages.error(request, f"Error updating subject: {str(e)}")
            logger.exception("Error updating subject %s: %s", semester_subject.subject.subject_name, str(e))
    
    return redirect('semesters:subject_detail', slug=slug, subject_id=subject_id)

@login_required
@user_passes_test(is_admin, login_url='index')
def delete_semester_subject(request, slug, subject_id):
    """Delete a subject from semester (AJAX)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)
    
    logger.info("Delete subject request: slug=%s, subject_id=%s, user=%s", slug, subject_id, request.user.username)
    
    try:
        semester = get_object_or_404(Semester, slug=slug)
        semester_subject = get_object_or_404(SemesterSubject, id=subject_id, semester=semester)
    except Exception as e:
        logger.error("Subject or semester not found: %s", str(e))
        return JsonResponse({'success': False, 'error': 'Subject or semester not found'}, status=404)
    
    try:
        with transaction.atomic():
            subject_name = semester_subject.subject.subject_name
            teacher = semester_subject.teacher
            
            # Check for associated materials or assignments
            try:
                from materials.models import SubjectMaterial
                material_count = SubjectMaterial.objects.filter(subject=semester_subject).count()
            except ImportError:
                material_count = 0
                logger.debug("materials.models not found, skipping material check")
            
            try:
                from assignments.models import Assignment
                assignment_count = Assignment.objects.filter(subject=semester_subject).count()
            except ImportError:
                assignment_count = 0
                logger.debug("assignments.models not found, skipping assignment check")
            
            if material_count > 0 or assignment_count > 0:
                logger.warning("Cannot delete subject %s - has %d materials and %d assignments", 
                             subject_name, material_count, assignment_count)
                return JsonResponse({
                    'success': False,
                    'error': f'Subject has {material_count} materials and {assignment_count} assignments. Delete them first.'
                }, status=400)
            
            # Get all active enrollments for the subject
            active_enrollments = SubjectEnrollment.objects.filter(
                semester_subject=semester_subject,
                status='active'
            ).select_related('student__user')
            
            # Process each enrollment
            for enrollment in active_enrollments:
                student = enrollment.student
                # Delete the subject enrollment
                enrollment.delete()
                logger.info("Removed student %s from subject %s in semester %s",
                           student.get_full_name(), subject_name, semester.semester_name)
                
                # Check if student has other active subject enrollments in this semester
                remaining_subjects = SubjectEnrollment.objects.filter(
                    semester_enrollment__semester=semester,
                    student=student,
                    status='active'
                ).exists()
                
                if not remaining_subjects:
                    # No remaining subjects, remove semester enrollment
                    SemesterEnrollment.objects.filter(
                        semester=semester,
                        student=student,
                        status='active'
                    ).delete()
                    logger.info(
                        "Removed student %s from semester %s due to no remaining subject enrollments",
                        student.get_full_name(), semester.semester_name
                    )
                    if student.user:
                        create_notification(
                            student.user,
                            f'You have been removed from semester {semester.semester_name} due to no remaining subject enrollments'
                        )
                
                # Notify student about subject removal
                if student.user:
                    create_notification(
                        student.user,
                        f'You have been removed from {subject_name} in {semester.semester_name}'
                    )
            
            # Notify teacher if assigned
            if teacher and teacher.user:
                try:
                    create_notification(
                        teacher.user,
                        f"You have been unassigned from {subject_name} in {semester.semester_name}",
                        'warning'
                    )
                except Exception as e:
                    logger.error("Failed to notify teacher: %s", str(e))
            
            # Delete the subject
            semester_subject.delete()
            logger.info("Successfully deleted subject %s from semester %s", subject_name, semester.semester_name)
            
            # Notify admin
            try:
                create_notification(
                    request.user,
                    f"Deleted subject {subject_name} from {semester.semester_name}",
                    'info'
                )
            except Exception as e:
                logger.error("Failed to create admin notification: %s", str(e))
            
            return JsonResponse({
                'success': True,
                'message': f'Subject "{subject_name}" deleted successfully'
            })
            
    except Exception as e:
        logger.error(
            "Failed to delete subject %s from semester %s: %s",
            semester_subject.subject.subject_name if semester_subject else 'Unknown',
            semester.semester_name if semester else 'Unknown',
            str(e),
            exc_info=True
        )
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, status=500)

@login_required
@user_passes_test(is_admin, login_url='index')
def remove_teacher_from_subject(request, slug, subject_id):
    """Remove teacher from a subject (AJAX)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)
    
    semester = get_object_or_404(Semester, slug=slug)
    semester_subject = get_object_or_404(SemesterSubject, id=subject_id, semester=semester)
    
    try:
        with transaction.atomic():
            if not semester_subject.teacher:
                return JsonResponse({
                    'success': False, 
                    'error': 'No teacher is assigned to this subject'
                }, status=400)
            
            teacher_name = semester_subject.teacher.get_full_name()
            teacher_user = semester_subject.teacher.user
            
            semester_subject.teacher = None
            semester_subject.save()
            
            # Notify teacher
            if teacher_user:
                create_notification(
                    teacher_user,
                    f"You have been removed from teaching {semester_subject.subject.subject_name} in {semester.semester_name}"
                )
            
            create_notification(
                request.user,
                f"Removed teacher from {semester_subject.subject.subject_name} in {semester.semester_name}"
            )
            
            logger.info("Removed teacher %s from subject %s in %s by user: %s", 
                      teacher_name, semester_subject.subject.subject_name, 
                      semester.semester_name, request.user.username)
            
            return JsonResponse({
                'success': True, 
                'message': f'Teacher "{teacher_name}" removed successfully'
            })
            
    except Exception as e:
        logger.exception("Error removing teacher from subject %s: %s", 
                        semester_subject.subject.subject_name, str(e))
        return JsonResponse({
            'success': False, 
            'error': f'Error removing teacher: {str(e)}'
        }, status=500)

@login_required
@user_passes_test(is_admin, login_url='index')
def manage_subject_students(request, slug, subject_id):
    """
    Add or remove students from a subject (AJAX).
    Expects POST params:
        action   -> 'add' | 'remove'
        students -> list of student IDs (integers)
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required'}, status=405)

    semester = get_object_or_404(Semester, slug=slug)
    semester_subject = get_object_or_404(SemesterSubject, id=subject_id, semester=semester)
    action = request.POST.get('action')
    student_ids = request.POST.getlist('students') or []

    # Validation
    if not action or action not in {'add', 'remove'}:
        return JsonResponse({'success': False, 'error': 'Invalid action'}, status=400)
    if not student_ids:
        return JsonResponse({'success': False, 'error': 'No students selected'}, status=400)

    processed = 0
    errors = []

    with transaction.atomic():
        for sid in student_ids:
            try:
                student = Student.objects.get(id=sid, user__is_active=True)
                
                if action == 'add':
                    # Check if student is already enrolled
                    if SubjectEnrollment.objects.filter(
                        semester_subject=semester_subject,
                        student=student,
                        status='active'
                    ).exists():
                        errors.append(f'{student.get_full_name()} is already enrolled')
                        continue

                    # Check if subject has capacity
                    if not semester_subject.can_enroll_student():
                        errors.append('Subject is full')
                        break

                    # Find or create semester enrollment
                    sem_enroll, created = SemesterEnrollment.objects.get_or_create(
                        semester=semester,
                        student=student,
                        defaults={
                            'enrolled_by': request.user,
                            'status': 'active'
                        }
                    )

                    # Create subject enrollment
                    SubjectEnrollment.objects.create(
                        semester_subject=semester_subject,
                        student=student,
                        semester_enrollment=sem_enroll,
                        enrolled_by=request.user,
                        status='active'
                    )
                    processed += 1

                    # Notify student
                    if student.user:
                        create_notification(
                            student.user,
                            f'You have been enrolled in {semester_subject.subject.subject_name}'
                        )

                elif action == 'remove':
                    # Remove from subject
                    rows, _ = SubjectEnrollment.objects.filter(
                        semester_subject=semester_subject,
                        student=student,
                        status='active'
                    ).delete()
                    processed += rows

                    if rows > 0:  # Only proceed if a subject enrollment was actually deleted
                        # Check if student has any other active subject enrollments in this semester
                        remaining_subjects = SubjectEnrollment.objects.filter(
                            semester_enrollment__semester=semester,
                            student=student,
                            status='active'
                        ).exists()

                        if not remaining_subjects:
                            # No remaining subjects, remove semester enrollment
                            SemesterEnrollment.objects.filter(
                                semester=semester,
                                student=student,
                                status='active'
                            ).delete()
                            logger.info(
                                "Removed student %s from semester %s due to no remaining subject enrollments",
                                student.get_full_name(), semester.semester_name
                            )
                            if student.user:
                                create_notification(
                                    student.user,
                                    f'You have been removed from semester {semester.semester_name} due to no remaining subject enrollments'
                                )

                    # Notify student about subject removal
                    if student.user:
                        create_notification(
                            student.user,
                            f'You have been removed from {semester_subject.subject.subject_name}'
                        )

            except Student.DoesNotExist:
                errors.append(f'Student ID {sid} not found')
            except Exception as e:
                errors.append(f'Error processing student ID {sid}: {str(e)}')

    return JsonResponse({
        'success': True if processed > 0 else False,
        'message': f'{processed} student(s) {action}ed',
        'errors': errors
    })

@login_required
def get_subject_students(request, slug, subject_id):
    """Get students enrolled in a subject (AJAX)"""
    semester = get_object_or_404(Semester, slug=slug)
    semester_subject = get_object_or_404(SemesterSubject, id=subject_id, semester=semester)
    
    try:
        # Get enrolled students
        enrolled_students = SubjectEnrollment.objects.filter(
            semester_subject=semester_subject,
            status='active'
        ).select_related('student__user', 'semester_enrollment__batch')

        # Get ALL active students (not just those in semester)
        available_students = Student.objects.filter(
            user__is_active=True
        ).select_related('user')

        # Apply search filter if provided
        query = request.GET.get('q', '').strip()
        if query:
            enrolled_students = enrolled_students.filter(
                Q(student__user__email__icontains=query) |
                Q(student__first_name__icontains=query) |
                Q(student__last_name__icontains=query) |
                Q(student__student_id__icontains=query))
            
            available_students = available_students.filter(
                Q(user__email__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(student_id__icontains=query))

        # Format data
        enrolled_data = []
        for enrollment in enrolled_students:
            enrolled_data.append({
                'id': enrollment.student.id,
                'email': enrollment.student.user.email if enrollment.student.user else '',
                'name': enrollment.student.get_full_name(),
                'student_id': enrollment.student.student_id,
                'class': enrollment.student.student_class or 'N/A'
            })

        available_data = []
        enrolled_ids = [e['id'] for e in enrolled_data]
        for student in available_students:
            # Only show students not already enrolled
            if student.id not in enrolled_ids:
                available_data.append({
                    'id': student.id,
                    'email': student.user.email if student.user else '',
                    'name': student.get_full_name(),
                    'student_id': student.student_id,
                    'class': student.student_class or 'N/A'
                })

        return JsonResponse({
            'success': True,
            'subject_name': semester_subject.subject.subject_name,
            'enrolled_students': enrolled_data,
            'available_students': available_data,
            'enrolled_count': len(enrolled_data),
            'available_count': len(available_data),
            'can_enroll_more': semester_subject.can_enroll_student()
        })

    except Exception as e:
        logger.exception("Error fetching subject students: %s", str(e))
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, status=500)