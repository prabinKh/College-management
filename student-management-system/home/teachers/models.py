from django.db import models
from django.utils.text import slugify
from django.conf import settings
import random
import string

def generate_teacher_id():
    """Generate a unique teacher ID in the format Teacher-XXXXX."""
    while True:
        random_digits = ''.join(random.choices(string.digits, k=5))
        teacher_id = f"Teacher-{random_digits}"
        if not Teacher.objects.filter(teacher_id=teacher_id).exists():
            return teacher_id

class Teacher(models.Model):
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Others', 'Others'),
    ]
    
    teacher_id = models.CharField(max_length=20, unique=True, default=generate_teacher_id)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    date_of_birth = models.DateField()
    mobile = models.CharField(max_length=15)
    joining_date = models.DateField()
    qualification = models.CharField(max_length=200)
    
    # Login Details
    username = models.CharField(max_length=100, unique=True)
    email = models.EmailField(max_length=255, unique=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    
    # Address
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=10)
    country = models.CharField(max_length=100)
    
    # Additional fields
    teacher_image = models.ImageField(upload_to='teachers/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.first_name}-{self.last_name}-{self.teacher_id}")
        super(Teacher, self).save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.teacher_id})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"