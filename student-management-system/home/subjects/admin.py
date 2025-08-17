from django.contrib import admin
from .models import Subject

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('subject_id', 'subject_name', 'class_name', 'credits', 'is_active')
    list_filter = ('class_name', 'is_active')
    search_fields = ('subject_id', 'subject_name', 'class_name')
    prepopulated_fields = {'slug': ('subject_name',)}
    readonly_fields = ('subject_id', 'created_at', 'updated_at')