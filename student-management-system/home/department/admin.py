from django.contrib import admin
from .models import Department

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('department_name', 'department_id', 'head_of_department', 'department_start_date', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('department_name', 'department_id')
    readonly_fields = ('department_id', 'slug', 'created_at', 'updated_at')
    fields = ('department_id', 'department_name', 'head_of_department', 'department_start_date', 'description', 'is_active', 'slug')

    def get_readonly_fields(self, request, obj=None):
        # Make slug and department_id read-only when editing an existing object
        if obj:
            return self.readonly_fields
        return ('slug', 'created_at', 'updated_at')