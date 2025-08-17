from django.db import models
from django.utils.text import slugify
import random
import string

def generate_subject_id():
    """Generate a unique subject ID in the format Subject-XXXXX."""
    while True:
        random_digits = ''.join(random.choices(string.digits, k=5))
        subject_id = f"Subject-{random_digits}"
        if not Subject.objects.filter(subject_id=subject_id).exists():
            return subject_id

class Subject(models.Model):
    subject_id = models.CharField(max_length=20, unique=True, default=generate_subject_id)
    subject_name = models.CharField(max_length=200)
    class_name = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    credits = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.subject_name}-{self.subject_id}")
        super(Subject, self).save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.subject_name} ({self.class_name})"