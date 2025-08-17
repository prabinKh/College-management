from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import HttpResponseForbidden
from .models import Teacher
from school.models import Notification
from home_auth.models import CustomUser
from django.contrib.auth.hashers import make_password
from django.utils.dateparse import parse_date
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test


def is_admin(user):
    return user.is_authenticated and user.is_admin

def create_notification(user, message):
    if user.is_authenticated:
        Notification.objects.create(user=user, message=message)


@login_required
@user_passes_test(is_admin, login_url='index')
def teacher_list(request):
    if not request.user.is_admin:
        messages.error(request, 'Access denied. Admin access required')
        return redirect('index')
    teachers = Teacher.objects.all()
    unread_notification = request.user.notification_set.filter(is_read=False) if request.user.is_authenticated else []
    context = {
        'teachers': teachers,
        'unread_notification': unread_notification
    }
    return render(request, "teachers/teachers.html", context)


@login_required
@user_passes_test(is_admin, login_url='index')
def add_teacher(request):
    if not request.user.is_admin:
        messages.error(request, 'Access denied. Admin access required')
        return redirect('index')
    if request.method == "POST":
        # Collect form data
        form_data = {
            'first_name': request.POST.get('first_name', '').strip(),
            'last_name': request.POST.get('last_name', '').strip(),
            'gender': request.POST.get('gender', '').strip(),
            'date_of_birth': request.POST.get('date_of_birth', '').strip(),
            'mobile': request.POST.get('mobile', '').strip(),
            'joining_date': request.POST.get('joining_date', '').strip(),
            'qualification': request.POST.get('qualification', '').strip(),
            'username': request.POST.get('username', '').strip(),
            'email': request.POST.get('email', '').strip(),
            'password': request.POST.get('password', '').strip(),
            'repeat_password': request.POST.get('repeat_password', '').strip(),
            'address': request.POST.get('address', '').strip(),
            'city': request.POST.get('city', '').strip(),
            'state': request.POST.get('state', '').strip(),
            'zip_code': request.POST.get('zip_code', '').strip(),
            'country': request.POST.get('country', '').strip(),
            'teacher_image': request.FILES.get('teacher_image')
        }

        # Initialize error dictionary
        errors = {}

        # Validation
        if not form_data['first_name']:
            errors['first_name'] = "First name is required"

        if not form_data['last_name']:
            errors['last_name'] = "Last name is required"

        if not form_data['gender']:
            errors['gender'] = "Gender is required"

        date_of_birth = parse_date(form_data['date_of_birth'])
        if not form_data['date_of_birth']:
            errors['date_of_birth'] = "Date of birth is required"
        elif not date_of_birth:
            errors['date_of_birth'] = "Invalid date of birth format"

        if not form_data['mobile']:
            errors['mobile'] = "Mobile number is required"

        joining_date = parse_date(form_data['joining_date'])
        if not form_data['joining_date']:
            errors['joining_date'] = "Joining date is required"
        elif not joining_date:
            errors['joining_date'] = "Invalid joining date format"

        if not form_data['qualification']:
            errors['qualification'] = "Qualification is required"

        if not form_data['username']:
            errors['username'] = "Username is required"
        elif Teacher.objects.filter(username=form_data['username']).exists():
            errors['username'] = "Username already exists"

        if not form_data['email']:
            errors['email'] = "Email is required"
        elif Teacher.objects.filter(email=form_data['email']).exists():
            errors['email'] = "Email already exists in Teacher records"
        elif CustomUser.objects.filter(email=form_data['email']).exists():
            errors['email'] = "Email already exists in user accounts"

        if not form_data['password']:
            errors['password'] = "Password is required"
        elif len(form_data['password']) < 8:
            errors['password'] = "Password must be at least 8 characters"

        if form_data['password'] != form_data['repeat_password']:
            errors['repeat_password'] = "Passwords do not match"

        if not form_data['address']:
            errors['address'] = "Address is required"

        if not form_data['city']:
            errors['city'] = "City is required"

        if not form_data['state']:
            errors['state'] = "State is required"

        if not form_data['zip_code']:
            errors['zip_code'] = "Zip code is required"

        if not form_data['country']:
            errors['country'] = "Country is required"

        # If there are errors, render the form with errors and form data
        if errors:
            context = {
                'errors': errors,
                'form_data': form_data
            }
            return render(request, "teachers/add-teacher.html", context)

        # If no errors, create teacher
        try:
            teacher = Teacher(
                first_name=form_data['first_name'],
                last_name=form_data['last_name'],
                gender=form_data['gender'],
                date_of_birth=date_of_birth,
                mobile=form_data['mobile'],
                joining_date=joining_date,
                qualification=form_data['qualification'],
                username=form_data['username'],
                email=form_data['email'],
                address=form_data['address'],
                city=form_data['city'],
                state=form_data['state'],
                zip_code=form_data['zip_code'],
                country=form_data['country'],
                teacher_image=form_data['teacher_image']
            )

            # Create user account for teacher
            user = CustomUser.objects.create_user(
                username=form_data['username'],
                email=form_data['email'],
                first_name=form_data['first_name'],
                last_name=form_data['last_name'],
                password=form_data['password'],
                is_teacher=True
            )

            # Link the CustomUser to the Teacher
            teacher.user = user
            teacher.save()

            create_notification(request.user, f"Added Teacher: {str(teacher)}")
            messages.success(request, "Teacher added successfully")
            return redirect("teacher_list")

        except Exception as e:
            if 'teacher' in locals():
                teacher.delete()  # Delete teacher if user creation fails
            messages.error(request, f"Error creating user account: {str(e)}")
            context = {
                'errors': errors,
                'form_data': form_data
            }
            return render(request, "teachers/add-teacher.html", context)

    # GET request: render empty form
    return render(request, "teachers/add-teacher.html", {'form_data': {}, 'errors': {}})


@login_required
@user_passes_test(is_admin, login_url='index')
def view_teacher(request, slug):
    if not request.user.is_admin:
        messages.error(request, 'Access denied. Admin login required')
    teacher = get_object_or_404(Teacher, slug=slug)
    context = {
        'teacher': teacher
    }
    return render(request, "teachers/teacher-details.html", context)


User = get_user_model()

@login_required
@user_passes_test(is_admin, login_url='index')
def edit_teacher(request, slug):
    if not request.user.is_admin:
        messages.error(request, 'Access denied. Admin login required')
        return redirect('index')
    teacher = get_object_or_404(Teacher, slug=slug)

    try:
        user = User.objects.get(email=teacher.email)
    except User.DoesNotExist:
        user = None

    if request.method == 'POST':
        # Collect form data
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        gender = request.POST.get('gender', '').strip()
        dob = parse_date(request.POST.get('date_of_birth', ''))
        mobile = request.POST.get('mobile', '').strip()
        jdate = parse_date(request.POST.get('joining_date', ''))
        qualification = request.POST.get('qualification', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        address = request.POST.get('address', '').strip()
        city = request.POST.get('city', '').strip()
        state = request.POST.get('state', '').strip()
        zip_code = request.POST.get('zip_code', '').strip()
        country = request.POST.get('country', '').strip()
        teacher_image = request.FILES.get('teacher_image')

        # Validation
        errors = {}
        if not first_name:
            errors['first_name'] = "First name is required"
        if not last_name:
            errors['last_name'] = "Last name is required"
        if not gender:
            errors['gender'] = "Gender is required"
        if not dob:
            errors['date_of_birth'] = "Date of birth is required"
        if not mobile:
            errors['mobile'] = "Mobile number is required"
        if not jdate:
            errors['joining_date'] = "Joining date is required"
        if not qualification:
            errors['qualification'] = "Qualification is required"
        if not username:
            errors['username'] = "Username is required"
        elif username != teacher.username and Teacher.objects.filter(username=username).exists():
            errors['username'] = "Username already exists"
        if not email:
            errors['email'] = "Email is required"
        elif email != teacher.email and (Teacher.objects.filter(email=email).exists() or CustomUser.objects.filter(email=email).exists()):
            errors['email'] = "Email already exists"
        if not address:
            errors['address'] = "Address is required"
        if not city:
            errors['city'] = "City is required"
        if not state:
            errors['state'] = "State is required"
        if not zip_code:
            errors['zip_code'] = "Zip code is required"
        if not country:
            errors['country'] = "Country is required"

        pw1 = request.POST.get('password1', '').strip()
        pw2 = request.POST.get('password2', '').strip()
        if pw1 or pw2:
            if pw1 != pw2:
                errors['password2'] = "Passwords do not match"
            elif len(pw1) < 8:
                errors['password1'] = "Password must be at least 8 characters"

        if errors:
            form_data = request.POST.dict()
            return render(request, 'teachers/edit-teacher.html', {'teacher': teacher, 'form_data': form_data, 'errors': errors})

        # Update teacher
        teacher.first_name = first_name
        teacher.last_name = last_name
        teacher.gender = gender
        teacher.date_of_birth = dob
        teacher.mobile = mobile
        teacher.joining_date = jdate
        teacher.qualification = qualification
        teacher.username = username
        teacher.email = email
        teacher.address = address
        teacher.city = city
        teacher.state = state
        teacher.zip_code = zip_code
        teacher.country = country
        if teacher_image:
            teacher.teacher_image = teacher_image
        teacher.save()

        if user:
            user.username = username
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            if pw1 and pw2 and pw1 == pw2 and len(pw1) >= 8:
                user.password = make_password(pw1)
            user.save()

        messages.success(request, "Teacher updated successfully!")
        return redirect('teacher_list')

    # GET – ensure dates are formatted as YYYY-MM-DD
    form_data = {
        'first_name': teacher.first_name,
        'last_name': teacher.last_name,
        'gender': teacher.gender,
        'date_of_birth': teacher.date_of_birth.isoformat() if teacher.date_of_birth else '',
        'mobile': teacher.mobile,
        'joining_date': teacher.joining_date.isoformat() if teacher.joining_date else '',
        'qualification': teacher.qualification,
        'username': teacher.username,
        'email': teacher.email,
        'address': teacher.address,
        'city': teacher.city,
        'state': teacher.state,
        'zip_code': teacher.zip_code,
        'country': teacher.country,
    }

    return render(request, 'teachers/edit-teacher.html', {'teacher': teacher, 'form_data': form_data, 'errors': {}})


@login_required
@user_passes_test(is_admin, login_url='index')
def delete_teacher(request, slug):
    if not request.user.is_admin:
        messages.error(request, 'Access denied. Admin access required')
        return redirect('index')
    if request.method == "POST":
        teacher = get_object_or_404(Teacher, slug=slug)
        teacher_name = str(teacher)
        
        # Delete associated user account
        try:
            user = CustomUser.objects.get(email=teacher.email)
            user.delete()
        except CustomUser.DoesNotExist:
            pass
        
        teacher.delete()
        create_notification(request.user, f"Deleted Teacher: {teacher_name}")
        messages.success(request, "Teacher deleted successfully")
        return redirect('teacher_list')
    
    return HttpResponseForbidden()