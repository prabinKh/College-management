from django.contrib import admin

# Register your models here.
# semesters/admin.py
from django.contrib import admin
from .models import Semester, Batch, SemesterSubject, SemesterEnrollment

@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ('semester_name', 'department', 'academic_year', 'status', 'start_date', 'end_date', 'created_at')
    list_filter = ('status', 'department', 'academic_year', 'created_at')
    search_fields = ('semester_name', 'department__department_name', 'academic_year')
    readonly_fields = ('semester_id', 'slug', 'created_at', 'updated_at')
    filter_horizontal = ()
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('semester_name', 'semester_id', 'department', 'academic_year', 'status')
        }),
        ('Schedule', {
            'fields': ('start_date', 'end_date')
        }),
        ('Details', {
            'fields': ('description', 'slug')
        }),
        ('Tracking', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing existing object
            return self.readonly_fields + ('semester_id',)
        return self.readonly_fields

@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ('batch_name', 'batch_id', 'semester', 'academic_year', 'max_students', 'is_active')
    list_filter = ('is_active', 'academic_year', 'semester__department')
    search_fields = ('batch_name', 'batch_id', 'semester__semester_name')
    readonly_fields = ('batch_id', 'slug', 'created_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('batch_name', 'batch_id', 'semester', 'academic_year')
        }),
        ('Settings', {
            'fields': ('max_students', 'is_active')
        }),
        ('Metadata', {
            'fields': ('slug', 'created_at'),
            'classes': ('collapse',)
        })
    )

class SemesterSubjectInline(admin.TabularInline):
    model = SemesterSubject
    extra = 1
    fields = ('subject', 'teacher', 'credits', 'hours_per_week', 'is_active')
    autocomplete_fields = ('subject', 'teacher')

class SemesterEnrollmentInline(admin.TabularInline):
    model = SemesterEnrollment
    extra = 0
    fields = ('student', 'status', 'enrollment_date', 'enrolled_by')
    readonly_fields = ('enrollment_date',)
    autocomplete_fields = ('student', 'enrolled_by')

@admin.register(SemesterSubject)
class SemesterSubjectAdmin(admin.ModelAdmin):
    list_display = ('semester', 'subject', 'teacher', 'credits', 'hours_per_week', 'is_active', 'assigned_date')
    list_filter = ('is_active', 'credits', 'semester__status', 'semester__department')
    search_fields = ('semester__semester_name', 'subject__subject_name', 'teacher__first_name', 'teacher__last_name')
    readonly_fields = ('assigned_date',)
    autocomplete_fields = ('semester', 'subject', 'teacher')
    
    fieldsets = (
        ('Assignment Details', {
            'fields': ('semester', 'subject', 'teacher')
        }),
        ('Course Details', {
            'fields': ('credits', 'hours_per_week', 'is_active')
        }),
        ('Tracking', {
            'fields': ('assigned_date',),
            'classes': ('collapse',)
        })
    )

@admin.register(SemesterEnrollment)
class SemesterEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'semester', 'status', 'enrollment_date', 'enrolled_by')
    list_filter = ('status', 'semester__status', 'semester__department', 'enrollment_date')
    search_fields = ('student__first_name', 'student__last_name', 'student__student_id', 'semester__semester_name')
    readonly_fields = ('enrollment_date',)
    autocomplete_fields = ('semester', 'student', 'enrolled_by')
    
    fieldsets = (
        ('Enrollment Details', {
            'fields': ('semester', 'student', 'status')
        }),
        ('Tracking', {
            'fields': ('enrollment_date', 'enrolled_by', 'notes')
        })
    )
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('semester', 'student', 'enrolled_by')

# Customize the admin site header
admin.site.site_header = "School Management System"
admin.site.site_title = "SMS Admin"
admin.site.index_title = "Semester Management"