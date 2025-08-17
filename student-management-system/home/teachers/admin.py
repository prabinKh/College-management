from django.contrib import admin
from .models import Teacher

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('teacher_id', 'first_name', 'last_name', 'email', 'is_active')
    search_fields = ('teacher_id', 'first_name', 'last_name', 'email')
    list_filter = ('is_active', 'gender')