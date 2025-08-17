from django.db import models
from django.utils.text import slugify
from django.conf import settings
from django.contrib.auth.models import User
from department.models import Department
from subjects.models import Subject
from teachers.models import Teacher
from student.models import Student
import random
import string
from django.db.models.signals import pre_save
from django.dispatch import receiver


def generate_semester_id():
    """Generate a unique semester ID in the format SEM-XXXXX."""
    while True:
        random_digits = ''.join(random.choices(string.digits, k=5))
        semester_id = f"SEM-{random_digits}"
        if not Semester.objects.filter(semester_id=semester_id).exists():
            return semester_id

def generate_batch_id():
    """Generate a unique batch ID in the format BATCH-XXXXX."""
    while True:
        random_digits = ''.join(random.choices(string.digits, k=5))
        batch_id = f"BATCH-{random_digits}"
        if not Batch.objects.filter(batch_id=batch_id).exists():
            return batch_id

class Semester(models.Model):
    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    semester_id = models.CharField(max_length=20, unique=True, default=generate_semester_id)
    semester_name = models.CharField(max_length=200)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='semesters')
    academic_year = models.CharField(max_length=20, help_text="e.g., 2024-2025")
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.semester_name}-{self.semester_id}")
        super().save(*args, **kwargs)
        
        # Auto-create default batch if it doesn't exist
        if not hasattr(self, '_skip_batch_creation') and not self.batches.exists():
            self.create_auto_batch()
    
    def create_auto_batch(self):
        """Automatically create a batch for this semester"""
        batch_name = f"{self.semester_name} - Default Batch"
        Batch.objects.create(
            semester=self,
            batch_name=batch_name,
            academic_year=self.academic_year,
            is_default=True
        )
    
    def get_student_count(self):
        """Get total students enrolled in this semester"""
        return SemesterEnrollment.objects.filter(semester=self, status='active').count()
    
    def get_subject_count(self):
        """Get total subjects in this semester"""
        return self.semester_subjects.count()
    
    def get_teacher_count(self):
        """Get unique teachers in this semester"""
        return self.semester_subjects.filter(teacher__isnull=False).values('teacher').distinct().count()
    
    def get_batch_count(self):
        """Get total batches in this semester"""
        return self.batches.count()
    
    def __str__(self):
        return f"{self.semester_name} ({self.academic_year})"
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['semester_name', 'academic_year', 'department']

class Batch(models.Model):
    batch_id = models.CharField(max_length=20, unique=True, default=generate_batch_id)
    batch_name = models.CharField(max_length=200)
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='batches')
    academic_year = models.CharField(max_length=20)
    max_students = models.PositiveIntegerField(default=50)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.batch_name}-{self.batch_id}")
        super().save(*args, **kwargs)
    
    def get_enrolled_count(self):
        """Get number of students enrolled in this batch"""
        return self.enrollments.filter(status='active').count()
    
    def get_available_spots(self):
        """Get available spots in this batch"""
        return max(0, self.max_students - self.get_enrolled_count())
    
    def can_enroll_student(self):
        """Check if batch can accept more students"""
        return self.get_enrolled_count() < self.max_students

    def __str__(self):
        return f"{self.batch_name} ({self.batch_id})"
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['batch_name', 'semester']

class SemesterSubject(models.Model):
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='semester_subjects')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='semester_assignments')
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True, related_name='semester_teachings')
    credits = models.PositiveIntegerField(default=1)
    hours_per_week = models.PositiveIntegerField(default=3)
    max_students = models.PositiveIntegerField(default=0, help_text="0 means no limit")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    assigned_date = models.DateTimeField(auto_now_add=True, null=True, blank=True)  # 👈 Add this

    def get_enrolled_count(self):
        """Get number of students enrolled in this subject"""
        return self.subject_enrollments.filter(status='active').count()
    
    def get_available_spots(self):
        """Get available spots for this subject"""
        if self.max_students == 0:
            return float('inf')  # No limit
        return max(0, self.max_students - self.get_enrolled_count())
    
    def can_enroll_student(self):
        """Check if subject can accept more students"""
        return self.max_students == 0 or self.get_enrolled_count() < self.max_students
    
    def __str__(self):
        teacher_name = self.teacher.get_full_name() if self.teacher else "No Teacher Assigned"
        return f"{self.subject.subject_name} - {teacher_name} ({self.semester.semester_name})"
    
    class Meta:
        unique_together = ['semester', 'subject']
        ordering = ['subject__subject_name']

class SemesterEnrollment(models.Model):
    """Students enrolled in a semester (through batches)"""
    ENROLLMENT_STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('dropped', 'Dropped'),
        ('completed', 'Completed'),
    ]
    
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='semester_enrollments')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='semester_enrollments')
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='enrollments',    null=True,blank=True)
    enrollment_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=ENROLLMENT_STATUS_CHOICES, default='active')
    enrolled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.student} enrolled in {self.semester.semester_name} (Batch: {self.batch.batch_name})"
    
    class Meta:
        unique_together = ['semester', 'student']
        ordering = ['-enrollment_date']

class SubjectEnrollment(models.Model):
    """Students enrolled in specific subjects within a semester"""
    ENROLLMENT_STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('dropped', 'Dropped'),
        ('completed', 'Completed'),
    ]
    
    semester_subject = models.ForeignKey(SemesterSubject, on_delete=models.CASCADE, related_name='subject_enrollments')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='subject_enrollments')
    semester_enrollment = models.ForeignKey(SemesterEnrollment, on_delete=models.CASCADE, related_name='subject_enrollments',   null=True,)
    enrollment_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=ENROLLMENT_STATUS_CHOICES, default='active')
    enrolled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.student} enrolled in {self.semester_subject.subject.subject_name} ({self.semester_subject.semester.semester_name})"
    
    class Meta:
        unique_together = ['semester_subject', 'student']
        ordering = ['-enrollment_date']

# Signal to ensure subject enrollments are linked to semester enrollments

@receiver(pre_save, sender=SubjectEnrollment)
def ensure_semester_enrollment(sender, instance, **kwargs):
    """Ensure student is enrolled in semester before enrolling in subject"""
    if not instance.semester_enrollment_id:
        semester_enrollment = SemesterEnrollment.objects.filter(
            semester=instance.semester_subject.semester,
            student=instance.student,
            status='active'
        ).first()
        
        if semester_enrollment:
            instance.semester_enrollment = semester_enrollment
        else:
            raise ValueError(f"Student {instance.student} must be enrolled in semester {instance.semester_subject.semester} before enrolling in subjects")