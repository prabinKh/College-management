from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.dateparse import parse_date
import logging

from .models import Department
from teachers.models import Teacher
from school.models import Notification

logger = logging.getLogger(__name__)

# -------- Utility -------- #
def is_admin(user):
    return user.is_authenticated and getattr(user, 'is_admin', False)

def create_notification(user, message):
    """Creates a notification if user is authenticated."""
    if user.is_authenticated:
        Notification.objects.create(user=user, message=message)


# -------- List Departments -------- #
def department_list(request):
    departments = Department.objects.select_related('head_of_department').all()
    unread_notification = request.user.notification_set.filter(is_read=False) if request.user.is_authenticated else []
    context = {
        'departments': departments,
        'unread_notification': unread_notification
    }
    return render(request, "departments/departments.html", context)


# -------- Add Department -------- #
@login_required
@user_passes_test(is_admin, login_url='index')
def add_department(request):
    teachers = Teacher.objects.filter(is_active=True)

    if request.method == "POST":
        department_id_input = request.POST.get('department_id_input', '').strip()
        department_name = request.POST.get('department_name', '').strip()
        head_of_department_id = request.POST.get('head_of_department', '')
        department_start_date = request.POST.get('department_start_date', '').strip()
        description = request.POST.get('description', '').strip()

        # Validation
        if not department_id_input:
            messages.error(request, "Department ID input is required")
        elif not department_name:
            messages.error(request, "Department name is required")
        elif Department.objects.filter(department_name=department_name).exists():
            messages.error(request, "Department name already exists")
        elif not department_start_date:
            messages.error(request, "Start date is required")
        elif not parse_date(department_start_date):
            messages.error(request, "Invalid date format")
        else:
            head_of_department = None
            if head_of_department_id:
                head_of_department = get_object_or_404(Teacher, id=head_of_department_id)

            try:
                department = Department(
                    department_name=department_name,
                    head_of_department=head_of_department,
                    department_start_date=parse_date(department_start_date),
                    description=description
                )
                department.save(user_input=department_id_input)
                create_notification(request.user, f"Added Department: {department.department_name}")
                messages.success(request, "Department added successfully")
                return redirect("department_list")
            except Exception as e:
                messages.error(request, f"Error creating department: {str(e)}")

        # If validation fails, re-render form with previous data
        return render(request, "departments/add-department.html", {
            'teachers': teachers,
            'form_data': request.POST
        })

    return render(request, "departments/add-department.html", {
        'teachers': teachers,
        'form_data': {}
    })


# -------- View Department -------- #
def view_department(request, slug):
    department = get_object_or_404(Department, slug=slug)
    return render(request, "departments/department-details.html", {
        'department': department
    })


# -------- Edit Department -------- #
@login_required
@user_passes_test(is_admin, login_url='index')
def edit_department(request, slug):
    department = get_object_or_404(Department, slug=slug)
    teachers = Teacher.objects.filter(is_active=True)

    if request.method == "POST":
        department_name = request.POST.get('department_name', '').strip()
        head_of_department_id = request.POST.get('head_of_department', '').strip()
        department_start_date = request.POST.get('department_start_date', '').strip()
        description = request.POST.get('description', '').strip()

        # Log POST data for debugging
        logger.debug(f"POST data: {request.POST}")

        # Validation
        if not department_name:
            messages.error(request, "Department name is required")
        elif Department.objects.filter(department_name=department_name).exclude(slug=slug).exists():
            messages.error(request, "Department name already exists")
        elif not department_start_date:
            messages.error(request, "Start date is required")
        elif not parse_date(department_start_date):
            messages.error(request, f"Invalid date format for {department_start_date}. Please use YYYY-MM-DD.")
        else:
            head_of_department = None
            if head_of_department_id:
                head_of_department = get_object_or_404(Teacher, id=head_of_department_id)

            try:
                # Update department fields
                department.department_name = department_name
                department.head_of_department = head_of_department
                department.department_start_date = parse_date(department_start_date)
                department.description = description
                department.save()
                create_notification(request.user, f"Updated Department: {department.department_name}")
                messages.success(request, "Department updated successfully")
                return redirect("department_list")
            except Exception as e:
                logger.error(f"Error updating department: {str(e)}")
                messages.error(request, f"Error updating department: {str(e)}")

        # If validation fails, re-render form with posted data
        form_data = {
            'department_name': department_name,
            'head_of_department': head_of_department_id,
            'department_start_date': department_start_date,
            'description': description
        }
        logger.debug(f"Validation failed, re-rendering with form_data: {form_data}")
        return render(request, "departments/edit-department.html", {
            'department': department,
            'teachers': teachers,
            'form_data': form_data
        })

    # Initial GET request → prefill form
    form_data = {
        'department_name': department.department_name or '',
        'head_of_department': department.head_of_department.id if department.head_of_department else '',
        'department_start_date': department.department_start_date.isoformat() if department.department_start_date else '',
        'description': department.description or ''
    }
    logger.debug(f"GET form_data: {form_data}")
    return render(request, "departments/edit-department.html", {
        'department': department,
        'teachers': teachers,
        'form_data': form_data
    })
# -------- Delete Department -------- #
@login_required
@user_passes_test(is_admin, login_url='index')
def delete_department(request, slug):
    if request.method == "POST":
        department = get_object_or_404(Department, slug=slug)
        department_name = department.department_name
        department.delete()
        create_notification(request.user, f"Deleted Department: {department_name}")
        messages.success(request, "Department deleted successfully")
        return redirect('department_list')

    return HttpResponseForbidden()
