from django.http import HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from .models import Student, Parent
from django.contrib import messages
from school.models import Notification
from django.contrib.auth.decorators import login_required, user_passes_test
from home_auth.models import CustomUser
from django.utils.crypto import get_random_string
from django.core.exceptions import ValidationError
from django.db.models import Q
from datetime import datetime

def is_admin(user):
    return user.is_authenticated and user.is_admin

def create_notification(user, message):
    if user and user.is_authenticated:
        Notification.objects.create(user=user, message=message)

@login_required
@user_passes_test(is_admin, login_url='index')
def add_student(request):
    if not request.user.is_admin:
        messages.error(request, 'Access denied. Admin access required.')
        return redirect('index')
    if request.method == "POST":
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        gender = request.POST.get('gender')
        date_of_birth = request.POST.get('date_of_birth')
        student_class = request.POST.get('student_class')
        religion = request.POST.get('religion')
        joining_date = request.POST.get('joining_date')
        mobile_number = request.POST.get('mobile_number')
        admission_number = request.POST.get('admission_number')
        section = request.POST.get('section')
        student_image = request.FILES.get('student_image')
        student_email = request.POST.get('student_email')
        father_name = request.POST.get('father_name')
        father_occupation = request.POST.get('father_occupation')
        father_mobile = request.POST.get('father_mobile')
        father_email = request.POST.get('father_email')
        mother_name = request.POST.get('mother_name')
        mother_occupation = request.POST.get('mother_occupation')
        mother_mobile = request.POST.get('mother_mobile')
        mother_email = request.POST.get('mother_email')
        present_address = request.POST.get('present_address')
        permanent_address = request.POST.get('permanent_address')

        # Validate date fields
        try:
            if date_of_birth:
                datetime.strptime(date_of_birth, '%Y-%m-%d')
            else:
                messages.error(request, "Date of Birth is required.")
                return render(request, "students/add-student.html")
            if joining_date:
                datetime.strptime(joining_date, '%Y-%m-%d')
            else:
                messages.error(request, "Joining Date is required.")
                return render(request, "students/add-student.html")
        except ValueError:
            messages.error(request, "Invalid date format. Please use YYYY-MM-DD.")
            return render(request, "students/add-student.html")

        if not student_email:
            messages.error(request, "Student email is required.")
            return render(request, "students/add-student.html")

        # Find or create the associated CustomUser using student_email
        user = CustomUser.objects.filter(email=student_email).first()
        if not user:
            user = CustomUser.objects.create_user(
                username=student_email,
                email=student_email,
                password='student@1234',
                is_student=True,
                first_name=first_name,
                last_name=last_name
            )
        else:
            user.is_student = True
            user.set_password('student@1234')
            user.save()

        # Save parent information
        parent = Parent.objects.create(
            father_name=father_name,
            father_occupation=father_occupation,
            father_mobile=father_mobile,
            father_email=father_email,
            mother_name=mother_name,
            mother_occupation=mother_occupation,
            mother_mobile=mother_mobile,
            mother_email=mother_email,
            present_address=present_address,
            permanent_address=permanent_address
        )

        # Save student information
        student = Student.objects.create(
            user=user,
            first_name=first_name,
            last_name=last_name,
            gender=gender,
            date_of_birth=date_of_birth,
            student_class=student_class,
            religion=religion,
            joining_date=joining_date,
            mobile_number=mobile_number,
            admission_number=admission_number,
            section=section,
            student_image=student_image,
            email=student_email,
            parent=parent
        )

        create_notification(request.user, f"Added Student: {student.first_name} {student.last_name}")
        create_notification(user, f"Welcome, {student.first_name}! Your student profile has been created. Default password: student@1234. Please change it after login.")
        messages.success(request, "Student added successfully")
        return redirect("students:student_list")

    return render(request, "students/add-student.html")

@login_required
@user_passes_test(is_admin, login_url='index')
def student_list(request):
    if not request.user.is_admin:
        messages.error(request, 'Access denied. Admin access required.')
        return redirect('index')
    
    # Get search query from GET parameters
    query = request.GET.get('q', '').strip()
    student_list = Student.objects.select_related('parent').all()
    
    if query:
        # Split query into parts for first and last name
        query_parts = query.split()
        if len(query_parts) >= 2:
            # Assume first part is for first_name, second for last_name
            first_name_query = query_parts[0]
            last_name_query = query_parts[1]
            student_list = student_list.filter(
                Q(first_name__icontains=first_name_query) &
                Q(last_name__icontains=last_name_query)
            )
        else:
            # Single query searches student_id or email
            student_list = student_list.filter(
                Q(student_id__icontains=query) |
                Q(email__icontains=query)
            )
        if not student_list:
            messages.info(request, f"No students found matching '{query}'.")
    
    context = {'student_list': student_list}
    return render(request, "students/students.html", context)

@login_required
@user_passes_test(is_admin, login_url='index')
def edit_student(request, slug):
    student = get_object_or_404(Student, slug=slug)
    parent = student.parent if hasattr(student, 'parent') else None
    if request.method == "POST":
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        gender = request.POST.get('gender')
        date_of_birth = request.POST.get('date_of_birth')
        student_class = request.POST.get('student_class')
        religion = request.POST.get('religion')
        joining_date = request.POST.get('joining_date')
        mobile_number = request.POST.get('mobile_number')
        admission_number = request.POST.get('admission_number')
        section = request.POST.get('section')
        student_image = request.FILES.get('student_image') if request.FILES.get('student_image') else student.student_image
        student_email = request.POST.get('student_email')
        father_name = request.POST.get('father_name')
        father_occupation = request.POST.get('father_occupation')
        father_mobile = request.POST.get('father_mobile')
        father_email = request.POST.get('father_email')
        mother_name = request.POST.get('mother_name')
        mother_occupation = request.POST.get('mother_occupation')
        mother_mobile = request.POST.get('mother_mobile')
        mother_email = request.POST.get('mother_email')
        present_address = request.POST.get('present_address')
        permanent_address = request.POST.get('permanent_address')
        reset_password = request.POST.get('reset_password')

        # Validate date fields
        try:
            if date_of_birth:
                datetime.strptime(date_of_birth, '%Y-%m-%d')
            else:
                messages.error(request, "Date of Birth is required.")
                return render(request, "students/edit-student.html", {'student': student, 'parent': parent})
            if joining_date:
                datetime.strptime(joining_date, '%Y-%m-%d')
            else:
                messages.error(request, "Joining Date is required.")
                return render(request, "students/edit-student.html", {'student': student, 'parent': parent})
        except ValueError:
            messages.error(request, "Invalid date format. Please use YYYY-MM-DD.")
            return render(request, "students/edit-student.html", {'student': student, 'parent': parent})

        if parent:
            parent.father_name = father_name
            parent.father_occupation = father_occupation
            parent.father_mobile = father_mobile
            parent.father_email = father_email
            parent.mother_name = mother_name
            parent.mother_occupation = mother_occupation
            parent.mother_mobile = mother_mobile
            parent.mother_email = mother_email
            parent.present_address = present_address
            parent.permanent_address = permanent_address
            parent.save()

        student.first_name = first_name
        student.last_name = last_name
        student.gender = gender
        student.date_of_birth = date_of_birth
        student.student_class = student_class
        student.religion = religion
        student.joining_date = joining_date
        student.mobile_number = mobile_number
        student.admission_number = admission_number
        student.section = section
        student.student_image = student_image
        student.email = student_email

        if student.user:
            student.user.first_name = first_name
            student.user.last_name = last_name
            if student_email != student.user.email:
                student.user.username = student_email
                student.user.email = student_email
            if reset_password:
                student.user.set_password('student@1234')
                create_notification(student.user, "Your password has been reset to default: student@1234. Please change it after login.")
            student.user.save()

        try:
            student.save()
        except ValidationError as e:
            messages.error(request, f"Validation error: {e}")
            return render(request, "students/edit-student.html", {'student': student, 'parent': parent})

        create_notification(request.user, f"Updated Student: {student.first_name} {student.last_name}")
        if student.user:
            create_notification(student.user, f"Your profile has been updated: {student.first_name} {student.last_name}")
        messages.success(request, "Student updated successfully")
        return redirect("students:student_list")
    return render(request, "students/edit-student.html", {'student': student, 'parent': parent})

@login_required
@user_passes_test(is_admin, login_url='index')
def view_student(request, slug):
    if not request.user.is_admin:
        messages.error(request, 'Access denied. Admin access required.')
        return redirect('index')
    student = get_object_or_404(Student, slug=slug)
    context = {'student': student}
    return render(request, "students/student-details.html", context)

@login_required
@user_passes_test(is_admin, login_url='index')
def delete_student(request, slug):
    if not request.user.is_admin:
        messages.error(request, 'Access denied. Admin access required.')
        return redirect('index')
    if request.method == "POST":
        student = get_object_or_404(Student, slug=slug)
        student_name = f"{student.first_name} {student.last_name}"
        student_user = student.user
        student.delete()
        create_notification(request.user, f"Deleted student: {student_name}")
        if student_user:
            create_notification(student_user, f"Your student profile has been deleted: {student_name}")
        messages.success(request, "Student deleted successfully")
        return redirect('students:student_list')
    return HttpResponseForbidden()