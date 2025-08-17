from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.db import transaction
from django.contrib.auth import get_user_model
from ..models import Semester, Batch, SemesterEnrollment, SubjectEnrollment
from student.models import Student
from .utils import create_notification, is_admin
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

@login_required
def batch_detail(request, batch_slug):
    """Detailed view of a batch"""
    batch = get_object_or_404(
        Batch.objects.select_related('semester')
        .prefetch_related('enrollments__student__user'),
        slug=batch_slug
    )
    
    # Get enrolled students
    enrolled_students = batch.enrollments.filter(status='active').select_related(
        'student__user'
    )
    
    # Get available students (not enrolled in any batch of this semester, active users only)
    enrolled_student_ids = SemesterEnrollment.objects.filter(
        semester=batch.semester,
        status='active'
    ).values_list('student_id', flat=True)
    
    available_students = Student.objects.filter(
        user__is_active=True
    ).exclude(
        id__in=enrolled_student_ids
    ).select_related('user')[:20]  # Limit for performance
    
    context = {
        'batch': batch,
        'semester': batch.semester,
        'enrolled_count': enrolled_students.count(),
        'available_spots': batch.get_available_spots(),
        'can_enroll_more': batch.can_enroll_student(),
    }
    return render(request, 'semesters/batch_detail.html', context)

@login_required
def manage_batches(request, slug):
    """Manage batches for a semester"""
    semester = get_object_or_404(Semester, slug=slug)
    batches = semester.batches.all().prefetch_related('enrollments')
    
    # Get batch statistics
    batches_data = []
    for batch in batches:
        enrolled_count = batch.enrollments.filter(status='active').count()
        batches_data.append({
            'batch': batch,
            'enrolled_count': enrolled_count,
            'available_spots': batch.get_available_spots(),
            'utilization_percentage': round((enrolled_count / batch.max_students * 100), 1) if batch.max_students > 0 else 0
        })
    
    context = {
        'semester': semester,
        'batches_data': batches_data,
        'total_batches': len(batches_data),
        'total_students': sum(b['enrolled_count'] for b in batches_data),
    }
    return render(request, 'semesters/manage_batches.html', context)

@login_required
@user_passes_test(is_admin, login_url='index')
def add_batch(request, slug):
    """Add a new batch to a semester"""
    semester = get_object_or_404(Semester, slug=slug)
    
    if request.method == 'POST':
        batch_name = request.POST.get('batch_name', '').strip()
        max_students = request.POST.get('max_students', 50)
        
        if not batch_name:
            messages.error(request, "Please provide a batch name.")
            return render(request, 'semesters/add_batch.html', {'semester': semester})
        
        try:
            with transaction.atomic():
                # Check for duplicate batch name in same semester
                if Batch.objects.filter(semester=semester, batch_name=batch_name).exists():
                    messages.error(request, f"A batch with name '{batch_name}' already exists in this semester.")
                    return render(request, 'semesters/add_batch.html', {'semester': semester})
                
                batch = Batch.objects.create(
                    semester=semester,
                    batch_name=batch_name,
                    academic_year=semester.academic_year,
                    max_students=int(max_students) if max_students else 50
                )
                
                create_notification(
                    request.user,
                    f"Created batch {batch.batch_name} for {semester.semester_name}"
                )
                
                messages.success(request, f"Batch '{batch.batch_name}' created successfully!")
                logger.info("Created batch %s for %s by user: %s", 
                          batch.batch_name, semester.semester_name, request.user.username)
                
                return redirect('semesters:batch_detail', batch_slug=batch.slug)
                
        except Exception as e:
            messages.error(request, f"Error creating batch: {str(e)}")
            logger.exception("Error creating batch for %s: %s", semester.semester_name, str(e))
    
    context = {'semester': semester}
    return render(request, 'semesters/add_batch.html', context)

@login_required
@user_passes_test(is_admin, login_url='index')
def edit_batch(request, slug, batch_id):
    """Edit a batch"""
    semester = get_object_or_404(Semester, slug=slug)
    batch = get_object_or_404(Batch, id=batch_id, semester=semester)
    
    if request.method == 'POST':
        batch_name = request.POST.get('batch_name', '').strip()
        max_students = request.POST.get('max_students', batch.max_students)
        
        if not batch_name:
            messages.error(request, "Please provide a batch name.")
            return render(request, 'semesters/edit_batch.html', {
                'semester': semester,
                'batch': batch
            })
        
        try:
            with transaction.atomic():
                # Check for duplicate batch name (excluding current batch)
                if Batch.objects.filter(
                    semester=semester, 
                    batch_name=batch_name
                ).exclude(id=batch.id).exists():
                    messages.error(request, f"A batch with name '{batch_name}' already exists in this semester.")
                    return render(request, 'semesters/edit_batch.html', {
                        'semester': semester,
                        'batch': batch
                    })
                
                # Check if new max_students is less than current enrollments
                current_enrollments = batch.enrollments.filter(status='active').count()
                new_max_students = int(max_students) if max_students else 50
                
                if new_max_students < current_enrollments:
                    messages.error(request, f"Cannot set maximum students to {new_max_students}. Current enrollments: {current_enrollments}")
                    return render(request, 'semesters/edit_batch.html', {
                        'semester': semester,
                        'batch': batch
                    })
                
                batch.batch_name = batch_name
                batch.max_students = new_max_students
                batch.save()
                
                create_notification(
                    request.user,
                    f"Updated batch {batch.batch_name} in {semester.semester_name}"
                )
                
                messages.success(request, f"Batch '{batch.batch_name}' updated successfully!")
                logger.info("Updated batch %s in %s by user: %s", 
                          batch.batch_name, semester.semester_name, request.user.username)
                
                return redirect('semesters:batch_detail', batch_slug=batch.slug)
                
        except Exception as e:
            messages.error(request, f"Error updating batch: {str(e)}")
            logger.exception("Error updating batch %s: %s", batch.batch_name, str(e))
    
    context = {
        'semester': semester,
        'batch': batch
    }
    return render(request, 'semesters/edit_batch.html', context)

@login_required
@user_passes_test(is_admin, login_url='index')
def delete_batch(request, slug, batch_id):
    """Delete a batch (AJAX)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)
    
    semester = get_object_or_404(Semester, slug=slug)
    batch = get_object_or_404(Batch, id=batch_id, semester=semester)
    
    try:
        with transaction.atomic():
            # Check if batch has enrollments
            enrolled_count = batch.enrollments.filter(status='active').count()
            if enrolled_count > 0:
                return JsonResponse({
                    'success': False, 
                    'error': f'Cannot delete batch with {enrolled_count} enrolled students. Please remove students first.'
                }, status=400)
            
            # Check if it's the only batch in semester
            if semester.batches.count() <= 1:
                return JsonResponse({
                    'success': False, 
                    'error': 'Cannot delete the last batch in a semester.'
                }, status=400)
            
            batch_name = batch.batch_name
            batch.delete()
            
            create_notification(
                request.user,
                f"Deleted batch {batch_name} from {semester.semester_name}"
            )
            
            logger.info("Deleted batch %s from %s by user: %s", 
                      batch_name, semester.semester_name, request.user.username)
            
            return JsonResponse({
                'success': True, 
                'message': f'Batch "{batch_name}" deleted successfully'
            })
            
    except Exception as e:
        logger.exception("Error deleting batch %s: %s", batch.batch_name, str(e))
        return JsonResponse({
            'success': False, 
            'error': f'Error deleting batch: {str(e)}'
        }, status=500)

@login_required
@user_passes_test(is_admin, login_url='index')
def add_student_to_batch(request, slug, batch_id):
    """Add students to a batch (AJAX)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)
    
    semester = get_object_or_404(Semester, slug=slug)
    batch = get_object_or_404(Batch, id=batch_id, semester=semester)
    
    student_data = request.POST.getlist('students')  # List of student IDs
    
    if not student_data:
        return JsonResponse({'success': False, 'error': 'No students provided'}, status=400)
    
    try:
        with transaction.atomic():
            enrolled_count = 0
            errors = []
            already_enrolled = []
            not_found = []
            batch_full = False
            
            for student_id in student_data:
                try:
                    # Check batch capacity first
                    if not batch.can_enroll_student():
                        batch_full = True
                        break
                    
                    # Find student by ID
                    student = Student.objects.filter(id=student_id, user__is_active=True).first()
                    
                    if not student:
                        not_found.append(student_id)
                        continue
                    
                    # Check if student is already enrolled in this semester
                    existing_enrollment = SemesterEnrollment.objects.filter(
                        semester=semester,
                        student=student,
                        status='active'
                    ).first()
                    
                    if existing_enrollment:
                        already_enrolled.append(student.user.email or student_id)
                        continue
                    
                    # Enroll student in semester through this batch
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
                            f"You have been enrolled in {semester.semester_name} (Batch: {batch.batch_name})"
                        )
                
                except Exception as e:
                    logger.exception("Error processing student %s: %s", student_id, str(e))
                    errors.append(f"Error processing student ID {student_id}: {str(e)}")
                    continue
            
            # Prepare response
            response_data = {'success': enrolled_count > 0}
            
            if enrolled_count > 0:
                response_data['message'] = f'Successfully enrolled {enrolled_count} student(s)'
                response_data['enrolled_count'] = enrolled_count
                
                create_notification(
                    request.user,
                    f"Enrolled {enrolled_count} student(s) in batch {batch.batch_name}"
                )
            else:
                response_data['error'] = 'No students were enrolled'
            
            # Add warnings
            warnings = []
            if batch_full:
                warnings.append(f"Batch reached maximum capacity ({batch.max_students} students)")
            if already_enrolled:
                warnings.append(f"Students already enrolled in semester: {', '.join(already_enrolled)}")
            if not_found:
                warnings.append(f"Students not found: {', '.join(not_found)}")
            if errors:
                warnings.extend(errors)
            
            if warnings:
                response_data['warnings'] = warnings
            
            logger.info("Added students to batch %s: enrolled=%d, warnings=%s", 
                       batch.batch_name, enrolled_count, len(warnings))
            
            return JsonResponse(response_data)
            
    except Exception as e:
        logger.exception("Error in add_student_to_batch: %s", str(e))
        return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'}, status=500)

@login_required
@user_passes_test(is_admin, login_url='index')
def remove_student_from_batch(request, slug, batch_id):
    """Remove students from a batch (AJAX)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)
    
    semester = get_object_or_404(Semester, slug=slug)
    batch = get_object_or_404(Batch, id=batch_id, semester=semester)
    
    student_data = request.POST.getlist('students')  # List of student IDs
    
    if not student_data:
        return JsonResponse({'success': False, 'error': 'No students provided'}, status=400)
    
    try:
        with transaction.atomic():
            removed_count = 0
            errors = []
            not_enrolled = []
            not_found = []
            
            for student_id in student_data:
                try:
                    # Find student by ID
                    student = Student.objects.filter(id=student_id, user__is_active=True).first()
                    
                    if not student:
                        not_found.append(student_id)
                        continue
                    
                    # Find enrollment in this batch
                    enrollment = SemesterEnrollment.objects.filter(
                        semester=semester,
                        student=student,
                        batch=batch,
                        status='active'
                    ).first()
                    
                    if not enrollment:
                        not_enrolled.append(student.user.email or student_id)
                        continue
                    
                    # Remove from all subject enrollments first
                    SubjectEnrollment.objects.filter(
                        semester_enrollment=enrollment,
                        status='active'
                    ).delete()
                    
                    # Remove semester enrollment
                    enrollment.delete()
                    removed_count += 1
                    
                    # Notify student
                    if student.user:
                        create_notification(
                            student.user,
                            f"You have been removed from {semester.semester_name} (Batch: {batch.batch_name})"
                        )
                
                except Exception as e:
                    logger.exception("Error processing student %s: %s", student_id, str(e))
                    errors.append(f"Error processing student ID {student_id}: {str(e)}")
                    continue
            
            # Prepare response
            response_data = {'success': removed_count > 0}
            
            if removed_count > 0:
                response_data['message'] = f'Successfully removed {removed_count} student(s)'
                response_data['removed_count'] = removed_count
                
                create_notification(
                    request.user,
                    f"Removed {removed_count} student(s) from batch {batch.batch_name}"
                )
            else:
                response_data['error'] = 'No students were removed'
            
            # Add warnings
            warnings = []
            if not_enrolled:
                warnings.append(f"Students not enrolled in this batch: {', '.join(not_enrolled)}")
            if not_found:
                warnings.append(f"Students not found: {', '.join(not_found)}")
            if errors:
                warnings.extend(errors)
            
            if warnings:
                response_data['warnings'] = warnings
            
            logger.info("Removed students from batch %s: removed=%d, warnings=%s", 
                       batch.batch_name, removed_count, len(warnings))
            
            return JsonResponse(response_data)
            
    except Exception as e:
        logger.exception("Error in remove_student_from_batch: %s", str(e))
        return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'}, status=500)

@login_required
def search_students(request):
    """Search students for enrollment (AJAX)"""
    query = request.GET.get('q', '').strip()
    semester_id = request.GET.get('semester_id')
    batch_id = request.GET.get('batch_id')
    
    try:
        semester = Semester.objects.get(id=semester_id)
        batch = Batch.objects.get(id=batch_id, semester=semester)
        
        # Get enrolled student IDs for this semester
        enrolled_student_ids = SemesterEnrollment.objects.filter(
            semester=semester,
            status='active'
        ).values_list('student_id', flat=True)
        
        # Search students
        students = Student.objects.filter(
            user__is_active=True
        ).select_related('user')
        
        if query:
            students = students.filter(
                Q(user__email__icontains=query) |
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query) |
                Q(student_id__icontains=query)
            )
        
        available_students = students.exclude(id__in=enrolled_student_ids)[:20]
        enrolled_students = Student.objects.filter(
            id__in=SemesterEnrollment.objects.filter(
                batch=batch,
                status='active'
            ).values_list('student_id', flat=True)
        ).select_related('user')[:20]
        
        response_data = {
            'success': True,
            'available_students': [
                {
                    'id': student.id,
                    'name': f"{student.user.first_name} {student.user.last_name}".strip(),
                    'email': student.user.email
                } for student in available_students
            ],
            'enrolled_students': [
                {
                    'id': student.id,
                    'name': f"{student.user.first_name} {student.user.last_name}".strip(),
                    'email': student.user.email
                } for student in enrolled_students
            ]
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.exception("Error in search_students: %s", str(e))
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, status=500)

@login_required
@user_passes_test(is_admin, login_url='index')
def move_students_between_batches(request, slug):
    """Move students from one batch to another (AJAX)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)
    
    semester = get_object_or_404(Semester, slug=slug)
    
    from_batch_id = request.POST.get('from_batch_id')
    to_batch_id = request.POST.get('to_batch_id')
    student_data = request.POST.getlist('students')
    
    if not all([from_batch_id, to_batch_id, student_data]):
        return JsonResponse({'success': False, 'error': 'Missing required data'}, status=400)
    
    from_batch = get_object_or_404(Batch, id=from_batch_id, semester=semester)
    to_batch = get_object_or_404(Batch, id=to_batch_id, semester=semester)
    
    if from_batch == to_batch:
        return JsonResponse({'success': False, 'error': 'Source and destination batches cannot be the same'}, status=400)
    
    try:
        with transaction.atomic():
            moved_count = 0
            errors = []
            not_found = []
            batch_full = False
            
            for student_id in student_data:
                try:
                    # Check destination batch capacity
                    if not to_batch.can_enroll_student():
                        batch_full = True
                        break
                    
                    # Find student
                    student = Student.objects.filter(id=student_id, user__is_active=True).first()
                    
                    if not student:
                        not_found.append(student_id)
                        continue
                    
                    # Find enrollment in source batch
                    enrollment = SemesterEnrollment.objects.filter(
                        semester=semester,
                        student=student,
                        batch=from_batch,
                        status='active'
                    ).first()
                    
                    if not enrollment:
                        errors.append(f"Student ID {student_id} not found in source batch")
                        continue
                    
                    # Move to new batch
                    enrollment.batch = to_batch
                    enrollment.save()
                    moved_count += 1
                    
                    # Notify student
                    if student.user:
                        create_notification(
                            student.user,
                            f"You have been moved to {to_batch.batch_name} in {semester.semester_name}"
                        )
                
                except Exception as e:
                    logger.exception("Error moving student %s: %s", student_id, str(e))
                    errors.append(f"Error moving student ID {student_id}: {str(e)}")
                    continue
            
            # Prepare response
            response_data = {'success': moved_count > 0}
            
            if moved_count > 0:
                response_data['message'] = f'Successfully moved {moved_count} student(s) from {from_batch.batch_name} to {to_batch.batch_name}'
                response_data['moved_count'] = moved_count
                
                create_notification(
                    request.user,
                    f"Moved {moved_count} student(s) from {from_batch.batch_name} to {to_batch.batch_name}"
                )
            else:
                response_data['error'] = 'No students were moved'
            
            # Add warnings
            warnings = []
            if batch_full:
                warnings.append(f"Destination batch {to_batch.batch_name} reached maximum capacity")
            if not_found:
                warnings.append(f"Students not found: {', '.join(not_found)}")
            if errors:
                warnings.extend(errors)
            
            if warnings:
                response_data['warnings'] = warnings
            
            logger.info("Moved students between batches: moved=%d, warnings=%s", 
                       moved_count, len(warnings))
            
            return JsonResponse(response_data)
            
    except Exception as e:
        logger.exception("Error in move_students_between_batches: %s", str(e))
        return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'}, status=500)