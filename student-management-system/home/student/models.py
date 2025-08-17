from django.db import models
from django.utils.text import slugify
import random
import string

def generate_student_id():
    """Generate a unique student ID in the format Student-XXXXXX."""
    while True:
        random_digits = ''.join(random.choices(string.digits, k=6))
        student_id = f"Student-{random_digits}"
        if not Student.objects.filter(student_id=student_id).exists():
            return student_id

class Parent(models.Model):
    father_name = models.CharField(max_length=100)
    father_occupation = models.CharField(max_length=100, blank=True)
    father_mobile = models.CharField(max_length=15)
    father_email = models.EmailField(max_length=100)
    mother_name = models.CharField(max_length=100)
    mother_occupation = models.CharField(max_length=100, blank=True)
    mother_mobile = models.CharField(max_length=15)
    mother_email = models.EmailField(max_length=100)
    present_address = models.TextField()
    permanent_address = models.TextField()

    def __str__(self):
        return f"{self.father_name} & {self.mother_name}"

class Student(models.Model):
    user = models.ForeignKey('home_auth.CustomUser', on_delete=models.SET_NULL, null=True, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    student_id = models.CharField(max_length=20, unique=True, default=generate_student_id)
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female'), ('Others', 'Others')])
    date_of_birth = models.DateField()
    student_class = models.CharField(max_length=50)
    religion = models.CharField(max_length=50)
    joining_date = models.DateField()
    mobile_number = models.CharField(max_length=15)
    admission_number = models.CharField(max_length=20)
    section = models.CharField(max_length=10)
    student_image = models.ImageField(upload_to='students/', blank=True, null=True)
    email = models.EmailField(max_length=255, unique=True,default="unknown@example.com")  # New field for student email
    parent = models.OneToOneField(Parent, on_delete=models.CASCADE)
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.first_name}-{self.last_name}-{self.student_id}")
        super(Student, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.student_id})"
    

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"