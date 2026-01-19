from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Department, EmployeeAllowance, EmployeeDeduction


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'head', 'created_at']
    search_fields = ['name', 'code']
    list_filter = ['created_at']


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'first_name', 'last_name', 'department', 'role', 'employment_status', 'is_active']
    list_filter = ['role', 'employment_status', 'employment_type', 'department', 'is_active']
    search_fields = ['email', 'first_name', 'last_name', 'employee_number', 'kra_pin']
    ordering = ['first_name', 'last_name']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone_number', 'national_id')}),
        ('Employment', {
            'fields': (
                'employee_number', 'department', 'job_title', 'role',
                'employment_status', 'employment_type', 'date_joined_company',
                'date_left', 'reports_to'
            )
        }),
        ('Statutory', {'fields': ('kra_pin', 'nssf_number', 'nhif_number', 'has_disability')}),
        ('Banking', {'fields': ('bank_name', 'bank_branch', 'bank_account_number')}),
        ('Payroll', {'fields': ('basic_salary',)}),
        ('Azure AD', {'fields': ('azure_ad_id',)}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Important Dates', {'fields': ('last_login',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )


@admin.register(EmployeeAllowance)
class EmployeeAllowanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'allowance_type', 'amount', 'is_taxable', 'effective_from', 'effective_to']
    list_filter = ['allowance_type', 'is_taxable']
    search_fields = ['employee__first_name', 'employee__last_name', 'employee__email']
    raw_id_fields = ['employee']


@admin.register(EmployeeDeduction)
class EmployeeDeductionAdmin(admin.ModelAdmin):
    list_display = ['employee', 'deduction_type', 'name', 'amount', 'is_pretax', 'effective_from']
    list_filter = ['deduction_type', 'is_pretax']
    search_fields = ['employee__first_name', 'employee__last_name', 'name']
    raw_id_fields = ['employee']
