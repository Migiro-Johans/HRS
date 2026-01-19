from django.contrib import admin
from .models import LeaveType, LeaveBalance, LeaveRequest, PublicHoliday


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'days_per_year', 'accrual_method', 'is_paid', 'is_active']
    list_filter = ['accrual_method', 'is_paid', 'is_active', 'gender_specific']
    search_fields = ['name', 'code']


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'year', 'entitled_days', 'used_days', 'pending_days', 'available_days']
    list_filter = ['leave_type', 'year']
    search_fields = ['employee__first_name', 'employee__last_name', 'employee__email']
    raw_id_fields = ['employee']

    def available_days(self, obj):
        return obj.available_days
    available_days.short_description = 'Available'


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'start_date', 'end_date', 'days_requested', 'status', 'created_at']
    list_filter = ['status', 'leave_type', 'start_date']
    search_fields = ['employee__first_name', 'employee__last_name', 'employee__email']
    raw_id_fields = ['employee', 'handover_to', 'hod_approved_by', 'hr_approved_by', 'rejected_by']
    date_hierarchy = 'start_date'

    fieldsets = (
        (None, {'fields': ('employee', 'leave_type', 'status')}),
        ('Leave Period', {
            'fields': ('start_date', 'end_date', 'days_requested', 'is_half_day', 'half_day_period')
        }),
        ('Details', {
            'fields': ('reason', 'contact_during_leave', 'handover_to', 'handover_notes', 'document')
        }),
        ('HOD Approval', {
            'fields': ('hod_approved_by', 'hod_approved_at', 'hod_comments'),
            'classes': ('collapse',)
        }),
        ('HR Approval', {
            'fields': ('hr_approved_by', 'hr_approved_at', 'hr_comments'),
            'classes': ('collapse',)
        }),
        ('Rejection', {
            'fields': ('rejected_by', 'rejected_at', 'rejection_reason'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PublicHoliday)
class PublicHolidayAdmin(admin.ModelAdmin):
    list_display = ['name', 'date', 'is_recurring']
    list_filter = ['is_recurring']
    search_fields = ['name']
    date_hierarchy = 'date'
