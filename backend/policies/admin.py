from django.contrib import admin
from .models import PolicyCategory, Policy, PolicyVersion, PolicyAcknowledgement, PolicyAccessLog


@admin.register(PolicyCategory)
class PolicyCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'created_at']
    search_fields = ['name']
    ordering = ['order', 'name']


class PolicyVersionInline(admin.TabularInline):
    model = PolicyVersion
    extra = 0
    readonly_fields = ['version', 'effective_date', 'archived_at', 'archived_by']
    can_delete = False


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ['code', 'title', 'policy_type', 'category', 'version', 'status', 'effective_date']
    list_filter = ['policy_type', 'status', 'category', 'requires_acknowledgement']
    search_fields = ['code', 'title', 'description']
    filter_horizontal = ['departments']
    inlines = [PolicyVersionInline]
    date_hierarchy = 'effective_date'

    fieldsets = (
        (None, {'fields': ('title', 'code', 'category', 'policy_type', 'description')}),
        ('Document', {'fields': ('document', 'version', 'effective_date', 'review_date')}),
        ('Status', {'fields': ('status', 'approved_by', 'approved_at')}),
        ('Access Control', {'fields': ('departments', 'requires_acknowledgement')}),
    )


@admin.register(PolicyVersion)
class PolicyVersionAdmin(admin.ModelAdmin):
    list_display = ['policy', 'version', 'effective_date', 'archived_at', 'archived_by']
    list_filter = ['archived_at']
    search_fields = ['policy__code', 'policy__title']
    raw_id_fields = ['policy', 'archived_by']


@admin.register(PolicyAcknowledgement)
class PolicyAcknowledgementAdmin(admin.ModelAdmin):
    list_display = ['employee', 'policy', 'policy_version', 'acknowledged_at']
    list_filter = ['policy', 'acknowledged_at']
    search_fields = ['employee__first_name', 'employee__last_name', 'policy__code']
    raw_id_fields = ['employee', 'policy']
    date_hierarchy = 'acknowledged_at'


@admin.register(PolicyAccessLog)
class PolicyAccessLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'policy', 'action', 'accessed_at', 'ip_address']
    list_filter = ['action', 'accessed_at']
    search_fields = ['user__first_name', 'user__last_name', 'policy__code']
    raw_id_fields = ['user', 'policy']
    date_hierarchy = 'accessed_at'
