from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import HttpResponseForbidden
from .models import Subject
from school.models import Notification
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.dateparse import parse_date

def is_admin(user):
    return user.is_authenticated and user.is_admin

def create_notification(user, message):
    if user.is_authenticated:
        Notification.objects.create(user=user, message=message)

@login_required
@user_passes_test(is_admin, login_url='index')
def subject_list(request):
    if not request.user.is_admin:
        messages.error(request, 'Access denied. Admin access required')
        return redirect('index')
    subjects = Subject.objects.all()
    unread_notification = request.user.notification_set.filter(is_read=False) if request.user.is_authenticated else []
    context = {
        'subjects': subjects,
        'unread_notification': unread_notification
    }
    return render(request, "subjects/subjects.html", context)

@login_required
@user_passes_test(is_admin, login_url='index')
def add_subject(request):
    if not request.user.is_admin:
        messages.error(request, 'Access denied. Admin access required')
        return redirect('index')
    if request.method == "POST":
        form_data = {
            'subject_name': request.POST.get('subject_name', '').strip(),
            'class_name': request.POST.get('class_name', '').strip(),
            'description': request.POST.get('description', '').strip(),
            'credits': request.POST.get('credits', '').strip(),
        }

        errors = {}
        if not form_data['subject_name']:
            errors['subject_name'] = "Subject name is required"
        if not form_data['class_name']:
            errors['class_name'] = "Class name is required"
        try:
            credits = int(form_data['credits'])
            if credits < 1:
                errors['credits'] = "Credits must be at least 1"
        except ValueError:
            errors['credits'] = "Credits must be a valid number"

        if errors:
            context = {
                'errors': errors,
                'form_data': form_data
            }
            return render(request, "subjects/add-subject.html", context)

        try:
            subject = Subject(
                subject_name=form_data['subject_name'],
                class_name=form_data['class_name'],
                description=form_data['description'] or None,
                credits=int(form_data['credits'])
            )
            subject.save()
            create_notification(request.user, f"Added Subject: {str(subject)}")
            messages.success(request, "Subject added successfully")
            return redirect("subject_list")
        except Exception as e:
            messages.error(request, f"Error creating subject: {str(e)}")
            context = {
                'errors': errors,
                'form_data': form_data
            }
            return render(request, "subjects/add-subject.html", context)

    return render(request, "subjects/add-subject.html", {'form_data': {}, 'errors': {}})

@login_required
@user_passes_test(is_admin, login_url='index')
def view_subject(request, slug):
    if not request.user.is_admin:
        messages.error(request, 'Access denied. Admin login required')
        return redirect('index')
    subject = get_object_or_404(Subject, slug=slug)
    context = {
        'subject': subject
    }
    return render(request, "subjects/subject-details.html", context)

@login_required
@user_passes_test(is_admin, login_url='index')
def edit_subject(request, slug):
    if not request.user.is_admin:
        messages.error(request, 'Access denied. Admin login required')
        return redirect('index')
    subject = get_object_or_404(Subject, slug=slug)

    if request.method == 'POST':
        form_data = {
            'subject_name': request.POST.get('subject_name', '').strip(),
            'class_name': request.POST.get('class_name', '').strip(),
            'description': request.POST.get('description', '').strip(),
            'credits': request.POST.get('credits', '').strip(),
        }

        errors = {}
        if not form_data['subject_name']:
            errors['subject_name'] = "Subject name is required"
        if not form_data['class_name']:
            errors['class_name'] = "Class name is required"
        try:
            credits = int(form_data['credits'])
            if credits < 1:
                errors['credits'] = "Credits must be at least 1"
        except ValueError:
            errors['credits'] = "Credits must be a valid number"

        if errors:
            return render(request, 'subjects/edit-subject.html', {'subject': subject, 'form_data': form_data, 'errors': errors})

        subject.subject_name = form_data['subject_name']
        subject.class_name = form_data['class_name']
        subject.description = form_data['description'] or None
        subject.credits = int(form_data['credits'])
        subject.save()

        create_notification(request.user, f"Updated Subject: {str(subject)}")
        messages.success(request, "Subject updated successfully!")
        return redirect('subject_list')

    form_data = {
        'subject_name': subject.subject_name,
        'class_name': subject.class_name,
        'description': subject.description or '',
        'credits': subject.credits,
    }
    return render(request, 'subjects/edit-subject.html', {'subject': subject, 'form_data': form_data, 'errors': {}})

@login_required
@user_passes_test(is_admin, login_url='index')
def delete_subject(request, slug):
    if not request.user.is_admin:
        messages.error(request, 'Access denied. Admin access required')
        return redirect('index')
    if request.method == "POST":
        subject = get_object_or_404(Subject, slug=slug)
        subject_name = str(subject)
        subject.delete()
        create_notification(request.user, f"Deleted Subject: {subject_name}")
        messages.success(request, "Subject deleted successfully")
        return redirect('subject_list')
    return HttpResponseForbidden()