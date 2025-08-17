from django.db import models
from django.utils.text import slugify
from teachers.models import Teacher
import random
import string

class Department(models.Model):
    department_id = models.CharField(max_length=50, unique=True)
    department_name = models.CharField(max_length=200)
    head_of_department = models.ForeignKey(
        Teacher, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='headed_departments'
    )
    department_start_date = models.DateField()
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    
    def generate_department_id(self, user_input):
        """Generate a unique department_id in the format TechAI-<user_input>-<5-digit-integer>"""
        while True:
            random_digits = ''.join(random.choices(string.digits, k=5))
            department_id = f"TechAI-{user_input}-{random_digits}"
            if not Department.objects.filter(department_id=department_id).exists():
                return department_id
    
    def save(self, *args, **kwargs):
        if not self.department_id:
            # Assuming user_input is passed via kwargs or context; for now, use department_name as fallback
            user_input = kwargs.pop('user_input', self.department_name[:10])  # Limit to avoid overly long IDs
            self.department_id = self.generate_department_id(user_input)
        if not self.slug:
            self.slug = slugify(f"{self.department_name}-{self.department_id}")
        super(Department, self).save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.department_name} ({self.department_id})"
    
    class Meta:
        ordering = ['department_name']