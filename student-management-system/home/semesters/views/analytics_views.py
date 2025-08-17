# semesters/views/analytics_views.py
from django.shortcuts import get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Q
from ..models import Semester, SemesterSubject, SemesterEnrollment, SubjectEnrollment
from .utils import is_admin
import csv
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@login_required
@user_passes_test(is_admin, login_url='index')
def export_semester_data(request, slug):
    """Export semester data to CSV"""
    semester = get_object_or_404(Semester, slug=slug)
    
    try:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{semester.slug}_data_{datetime.now().strftime("%Y%m%d")}.csv"'
        
        writer = csv.writer(response)
        
        # Write header
        writer.writerow([
            'Subject Name', 'Subject Code', 'Credits', 'Hours/Week', 'Max Students',
            'Teacher Name', 'Teacher Email', 'Teacher Qualification',
            'Student Name', 'Student ID', 'Student Email', 'Student Class',
            'Batch Name', 'Enrollment Date', 'Status'
        ])
        
        # Get all semester subjects with related data
        semester_subjects = semester.semester_subjects.select_related(
            'subject', 'teacher'
        ).prefetch_related(
            'subject_enrollments__student__user',
            'subject_enrollments__semester_enrollment__batch'
        ).all()
        
        for semester_subject in semester_subjects:
            subject_enrollments = semester_subject.subject_enrollments.filter(
                status='active'
            ).select_related(
                'student__user', 'semester_enrollment__batch'
            )
            
            if subject_enrollments.exists():
                for enrollment in subject_enrollments:
                    writer.writerow([
                        semester_subject.subject.subject_name,
                        getattr(semester_subject.subject, 'subject_code', ''),
                        semester_subject.credits,
                        semester_subject.hours_per_week,
                        semester_subject.max_students if semester_subject.max_students > 0 else 'Unlimited',
                        semester_subject.teacher.get_full_name() if semester_subject.teacher else '',
                        semester_subject.teacher.email if semester_subject.teacher else '',
                        getattr(semester_subject.teacher, 'qualification', '') if semester_subject.teacher else '',
                        enrollment.student.get_full_name(),
                        enrollment.student.student_id,
                        enrollment.student.user.email if enrollment.student.user else '',
                        enrollment.student.student_class or '',
                        enrollment.semester_enrollment.batch.batch_name,
                        enrollment.enrollment_date.strftime('%Y-%m-%d %H:%M:%S'),
                        enrollment.status
                    ])
            else:
                # Subject with no enrollments
                writer.writerow([
                    semester_subject.subject.subject_name,
                    getattr(semester_subject.subject, 'subject_code', ''),
                    semester_subject.credits,
                    semester_subject.hours_per_week,
                    semester_subject.max_students if semester_subject.max_students > 0 else 'Unlimited',
                    semester_subject.teacher.get_full_name() if semester_subject.teacher else '',
                    semester_subject.teacher.email if semester_subject.teacher else '',
                    getattr(semester_subject.teacher, 'qualification', '') if semester_subject.teacher else '',
                    '', '', '', '', '', '', ''
                ])
        
        logger.info("Exported semester data for %s by user: %s", semester.semester_name, request.user.username)
        return response
        
    except Exception as e:
        logger.exception("Error exporting semester data: %s", str(e))
        return JsonResponse({'success': False, 'error': f'Export error: {str(e)}'}, status=500)

@login_required
@user_passes_test(is_admin, login_url='index')
def get_semester_analytics(request, slug):
    """Get comprehensive analytics for a semester"""
    semester = get_object_or_404(Semester, slug=slug)
    
    try:
        # Basic semester info
        analytics_data = {
            'semester_info': {
                'id': semester.id,
                'name': semester.semester_name,
                'semester_id': semester.semester_id,
                'department': semester.department.department_name,
                'academic_year': semester.academic_year,
                'status': semester.get_status_display(),
                'start_date': semester.start_date.isoformat() if semester.start_date else None,
                'end_date': semester.end_date.isoformat() if semester.end_date else None,
                'created_at': semester.created_at.isoformat(),
            }
        }
        
        # Get enrollment statistics
        total_enrollments = SemesterEnrollment.objects.filter(
            semester=semester, status='active'
        ).count()
        
        # Get batch statistics
        batches = semester.batches.annotate(
            enrolled_count=Count('enrollments', filter=Q(enrollments__status='active'))
        ).all()
        
        batch_data = []
        total_capacity = 0
        for batch in batches:
            enrolled = batch.enrolled_count
            available = max(0, batch.max_students - enrolled)
            utilization = (enrolled / batch.max_students * 100) if batch.max_students > 0 else 0
            
            batch_data.append({
                'id': batch.id,
                'name': batch.batch_name,
                'max_students': batch.max_students,
                'enrolled_count': enrolled,
                'available_spots': available,
                'utilization_percentage': round(utilization, 1),
                'is_default': batch.is_default
            })
            total_capacity += batch.max_students
        
        # Get subject statistics
        subjects = semester.semester_subjects.annotate(
            enrolled_count=Count('subject_enrollments', filter=Q(subject_enrollments__status='active'))
        ).select_related('subject', 'teacher').all()
        
        subject_data = []
        total_credits = 0
        total_hours = 0
        subjects_with_teachers = 0
        subjects_without_students = 0
        
        for subject in subjects:
            enrolled = subject.enrolled_count
            available = subject.get_available_spots()
            
            if subject.teacher:
                subjects_with_teachers += 1
                
            if enrolled == 0:
                subjects_without_students += 1
            
            subject_data.append({
                'id': subject.id,
                'name': subject.subject.subject_name,
                'code': getattr(subject.subject, 'subject_code', ''),
                'credits': subject.credits,
                'hours_per_week': subject.hours_per_week,
                'max_students': subject.max_students,
                'enrolled_count': enrolled,
                'available_spots': available if available != float('inf') else 'Unlimited',
                'teacher': {
                    'id': subject.teacher.id if subject.teacher else None,
                    'name': subject.teacher.get_full_name() if subject.teacher else None,
                    'email': subject.teacher.email if subject.teacher else None,
                    'qualification': getattr(subject.teacher, 'qualification', '') if subject.teacher else None,
                } if subject.teacher else None,
                'utilization_percentage': round((enrolled / subject.max_students * 100), 1) if subject.max_students > 0 else None
            })
            
            total_credits += subject.credits
            total_hours += subject.hours_per_week
        
        # Calculate summary statistics
        avg_students_per_subject = round(total_enrollments / len(subject_data), 2) if subject_data else 0
        overall_capacity_utilization = round((total_enrollments / total_capacity * 100), 1) if total_capacity > 0 else 0
        
        analytics_data.update({
            'summary': {
                'total_students': total_enrollments,
                'total_subjects': len(subject_data),
                'total_batches': len(batch_data),
                'total_teachers': subjects_with_teachers,
                'total_credits': total_credits,
                'total_hours_per_week': total_hours,
                'subjects_with_teachers': subjects_with_teachers,
                'subjects_without_teachers': len(subject_data) - subjects_with_teachers,
                'subjects_without_students': subjects_without_students,
                'average_students_per_subject': avg_students_per_subject,
                'total_capacity': total_capacity,
                'available_capacity': max(0, total_capacity - total_enrollments),
                'capacity_utilization_percentage': overall_capacity_utilization,
            },
            'batches': batch_data,
            'subjects': subject_data,
        })
        
        # Add trend data if requested
        if request.GET.get('include_trends') == 'true':
            # Get enrollment trends over time (last 30 days)
            from django.utils import timezone
            from datetime import timedelta
            
            thirty_days_ago = timezone.now() - timedelta(days=30)
            
            # Daily enrollment counts
            daily_enrollments = SemesterEnrollment.objects.filter(
                semester=semester,
                enrollment_date__gte=thirty_days_ago
            ).extra({
                'date': 'DATE(enrollment_date)'
            }).values('date').annotate(
                count=Count('id')
            ).order_by('date')
            
            analytics_data['trends'] = {
                'daily_enrollments': list(daily_enrollments)
            }
        
        return JsonResponse(analytics_data)
        
    except Exception as e:
        logger.exception("Error getting semester analytics: %s", str(e))
        return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'}, status=500)

@login_required
@user_passes_test(is_admin, login_url='index')
def get_dashboard_stats(request):
    """Get overall dashboard statistics"""
    try:
        from django.db.models import Sum
        
        # Overall statistics
        total_semesters = Semester.objects.filter(is_active=True).count()
        active_semesters = Semester.objects.filter(status__in=['upcoming', 'running']).count()
        total_students = SemesterEnrollment.objects.filter(status='active').values('student').distinct().count()
        total_teachers = SemesterSubject.objects.filter(teacher__isnull=False, is_active=True).values('teacher').distinct().count()
        
        # Recent activity (last 7 days)
        from django.utils import timezone
        from datetime import timedelta
        
        seven_days_ago = timezone.now() - timedelta(days=7)
        
        recent_enrollments = SemesterEnrollment.objects.filter(
            enrollment_date__gte=seven_days_ago,
            status='active'
        ).count()
        
        recent_subjects = SemesterSubject.objects.filter(
            created_at__gte=seven_days_ago,
            is_active=True
        ).count()
        
        # Status distribution
        status_distribution = list(Semester.objects.values('status').annotate(
            count=Count('id')
        ).order_by('status'))
        
        dashboard_data = {
            'overview': {
                'total_semesters': total_semesters,
                'active_semesters': active_semesters,
                'total_students': total_students,
                'total_teachers': total_teachers,
            },
            'recent_activity': {
                'new_enrollments_7_days': recent_enrollments,
                'new_subjects_7_days': recent_subjects,
            },
            'semester_status_distribution': status_distribution,
            'last_updated': timezone.now().isoformat()
        }
        
        return JsonResponse(dashboard_data)
        
    except Exception as e:
        logger.exception("Error getting dashboard stats: %s", str(e))
        return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'}, status=500)