from django.contrib import admin
from .models import PayrollPeriod, PayrollEntry, TaxTable, BankFile


class PayrollEntryInline(admin.TabularInline):
    model = PayrollEntry
    extra = 0
    readonly_fields = ['employee', 'basic_salary', 'gross_pay', 'paye', 'nssf', 'sha', 'housing_levy', 'net_pay']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(PayrollPeriod)
class PayrollPeriodAdmin(admin.ModelAdmin):
    list_display = ['name', 'year', 'month', 'status', 'total_gross', 'total_net', 'prepared_by', 'created_at']
    list_filter = ['status', 'year']
    search_fields = ['name']
    readonly_fields = ['total_gross', 'total_net', 'total_paye', 'total_nssf', 'total_sha', 'total_housing_levy']
    inlines = [PayrollEntryInline]

    fieldsets = (
        (None, {'fields': ('year', 'month', 'name', 'status', 'payment_date')}),
        ('Totals', {
            'fields': ('total_gross', 'total_net', 'total_paye', 'total_nssf', 'total_sha', 'total_housing_levy'),
            'classes': ('collapse',)
        }),
        ('Approval Workflow', {
            'fields': (
                'prepared_by', 'prepared_at',
                'hr_approved_by', 'hr_approved_at', 'hr_comments',
                'mgmt_approved_by', 'mgmt_approved_at', 'mgmt_comments'
            ),
            'classes': ('collapse',)
        }),
    )


@admin.register(PayrollEntry)
class PayrollEntryAdmin(admin.ModelAdmin):
    list_display = ['employee', 'payroll_period', 'basic_salary', 'gross_pay', 'paye', 'net_pay']
    list_filter = ['payroll_period', 'payroll_period__year']
    search_fields = ['employee__first_name', 'employee__last_name', 'employee__email']
    raw_id_fields = ['employee', 'payroll_period']

    fieldsets = (
        (None, {'fields': ('payroll_period', 'employee')}),
        ('Earnings', {
            'fields': ('basic_salary', 'taxable_allowances', 'non_taxable_allowances', 'benefits_in_kind', 'overtime', 'bonus', 'gross_pay')
        }),
        ('Pre-Tax Deductions', {
            'fields': ('pension_contribution', 'owner_occupied_interest')
        }),
        ('PAYE Calculation', {
            'fields': ('taxable_income', 'tax_charged', 'personal_relief', 'insurance_relief', 'disability_exemption', 'paye')
        }),
        ('Statutory Deductions', {
            'fields': ('nssf', 'sha', 'housing_levy')
        }),
        ('Other Deductions', {
            'fields': ('loan_deductions', 'sacco_deductions', 'other_deductions')
        }),
        ('Net Pay', {
            'fields': ('total_deductions', 'net_pay')
        }),
    )


@admin.register(TaxTable)
class TaxTableAdmin(admin.ModelAdmin):
    list_display = ['effective_from', 'effective_to', 'is_active', 'personal_relief']
    list_filter = ['is_active']

    fieldsets = (
        (None, {'fields': ('effective_from', 'effective_to', 'is_active')}),
        ('PAYE Tax Bands', {
            'fields': (
                ('band_1_limit', 'band_1_rate'),
                ('band_2_limit', 'band_2_rate'),
                ('band_3_limit', 'band_3_rate'),
                ('band_4_limit', 'band_4_rate'),
                'band_5_rate'
            )
        }),
        ('Reliefs', {
            'fields': ('personal_relief', 'insurance_relief_rate', 'insurance_relief_max', 'disability_exemption')
        }),
        ('NSSF', {
            'fields': (('nssf_tier1_limit', 'nssf_tier1_rate'), ('nssf_tier2_limit', 'nssf_tier2_rate'))
        }),
        ('Other Statutory', {
            'fields': ('sha_rate', 'housing_levy_rate')
        }),
        ('Limits', {
            'fields': ('pension_max_deduction', 'mortgage_interest_max')
        }),
    )


@admin.register(BankFile)
class BankFileAdmin(admin.ModelAdmin):
    list_display = ['payroll_period', 'file_format', 'total_amount', 'employee_count', 'generated_at']
    list_filter = ['file_format', 'payroll_period__year']
    readonly_fields = ['generated_at']
