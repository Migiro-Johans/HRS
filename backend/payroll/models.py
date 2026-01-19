"""
Payroll models for HRS - Payroll and Leave Management System
Implements Kenyan statutory deductions (PAYE, NSSF, SHA, Housing Levy)
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal
from core.models import BaseModel


class PayrollPeriod(BaseModel):
    """
    Represents a payroll period (typically monthly).
    All payroll entries for a period are grouped here.
    """

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PENDING_HR = 'pending_hr', 'Pending HR Approval'
        PENDING_MANAGEMENT = 'pending_mgmt', 'Pending Management Approval'
        APPROVED = 'approved', 'Approved'
        PAID = 'paid', 'Paid'
        CANCELLED = 'cancelled', 'Cancelled'

    year = models.IntegerField()
    month = models.IntegerField()
    name = models.CharField(max_length=50, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    payment_date = models.DateField(null=True, blank=True)

    # Approval workflow
    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='payroll_prepared'
    )
    prepared_at = models.DateTimeField(null=True, blank=True)

    hr_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payroll_hr_approved'
    )
    hr_approved_at = models.DateTimeField(null=True, blank=True)
    hr_comments = models.TextField(blank=True)

    mgmt_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payroll_mgmt_approved'
    )
    mgmt_approved_at = models.DateTimeField(null=True, blank=True)
    mgmt_comments = models.TextField(blank=True)

    # Totals (computed)
    total_gross = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_net = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_paye = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_nssf = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_sha = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_housing_levy = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        unique_together = ['year', 'month']
        ordering = ['-year', '-month']

    def __str__(self):
        return f"{self.get_month_name()} {self.year}"

    def get_month_name(self):
        months = [
            '', 'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        return months[self.month]

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = f"{self.get_month_name()} {self.year}"
        super().save(*args, **kwargs)

    def calculate_totals(self):
        """Recalculate totals from all entries."""
        entries = self.entries.all()
        self.total_gross = sum(e.gross_pay for e in entries)
        self.total_net = sum(e.net_pay for e in entries)
        self.total_paye = sum(e.paye for e in entries)
        self.total_nssf = sum(e.nssf for e in entries)
        self.total_sha = sum(e.sha for e in entries)
        self.total_housing_levy = sum(e.housing_levy for e in entries)
        self.save()


class PayrollEntry(BaseModel):
    """
    Individual payroll entry for an employee in a payroll period.
    Contains all earnings, deductions, and computed values.
    """

    payroll_period = models.ForeignKey(
        PayrollPeriod,
        on_delete=models.CASCADE,
        related_name='entries'
    )
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='payroll_entries'
    )

    # Earnings
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    taxable_allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    non_taxable_allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    benefits_in_kind = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    overtime = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Gross pay
    gross_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Pre-tax deductions (reduce taxable income)
    pension_contribution = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='Defined contribution retirement scheme'
    )
    owner_occupied_interest = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='Mortgage interest deduction (max 25,000/month)'
    )

    # Taxable income and PAYE
    taxable_income = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_charged = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    personal_relief = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=2400,
        help_text='Monthly personal relief (KES 2,400)'
    )
    insurance_relief = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='15% of insurance premiums, max KES 5,000/month'
    )
    disability_exemption = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='Disability tax exemption (KES 150,000/month)'
    )
    paye = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='Pay As You Earn tax after reliefs'
    )

    # Statutory deductions
    nssf = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='NSSF contribution (Tier I + Tier II)'
    )
    sha = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='Social Health Authority (2.75% of gross)'
    )
    housing_levy = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='Affordable Housing Levy (1.5% of gross)'
    )

    # Other deductions
    loan_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sacco_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Net pay
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Allowance breakdown (stored as JSON for flexibility)
    allowance_details = models.JSONField(default=dict, blank=True)
    deduction_details = models.JSONField(default=dict, blank=True)

    # Payslip
    payslip_generated = models.BooleanField(default=False)
    payslip_file = models.CharField(max_length=500, blank=True)

    class Meta:
        unique_together = ['payroll_period', 'employee']
        ordering = ['employee__first_name', 'employee__last_name']
        verbose_name_plural = 'Payroll Entries'

    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.payroll_period}"


class TaxTable(BaseModel):
    """
    PAYE tax bands configuration.
    Allows updating tax rates without code changes.
    """

    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    # Tax bands (monthly amounts in KES)
    band_1_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=24000,
        help_text='Upper limit for 10% band'
    )
    band_1_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal('0.10')
    )

    band_2_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=32333,
        help_text='Upper limit for 25% band'
    )
    band_2_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal('0.25')
    )

    band_3_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=500000,
        help_text='Upper limit for 30% band'
    )
    band_3_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal('0.30')
    )

    band_4_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=800000,
        help_text='Upper limit for 32.5% band'
    )
    band_4_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal('0.325')
    )

    band_5_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal('0.35'),
        help_text='Rate for income above band 4'
    )

    # Reliefs
    personal_relief = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=2400
    )
    insurance_relief_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal('0.15')
    )
    insurance_relief_max = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=5000
    )
    disability_exemption = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=150000
    )

    # NSSF rates
    nssf_tier1_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=7000
    )
    nssf_tier1_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal('0.06')
    )
    nssf_tier2_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=36000
    )
    nssf_tier2_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal('0.06')
    )

    # SHA rate
    sha_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal('0.0275')
    )

    # Housing Levy rate
    housing_levy_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal('0.015')
    )

    # Pension limits
    pension_max_deduction = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=20000,
        help_text='Maximum pension contribution deductible from taxable income'
    )
    mortgage_interest_max = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=25000,
        help_text='Maximum mortgage interest deduction per month'
    )

    class Meta:
        ordering = ['-effective_from']

    def __str__(self):
        return f"Tax Table from {self.effective_from}"

    @classmethod
    def get_active(cls, date=None):
        """Get the active tax table for a given date."""
        from django.utils import timezone
        if date is None:
            date = timezone.now().date()

        return cls.objects.filter(
            is_active=True,
            effective_from__lte=date
        ).filter(
            models.Q(effective_to__isnull=True) | models.Q(effective_to__gte=date)
        ).first()


class BankFile(BaseModel):
    """
    Generated bank file for salary payments.
    """

    class FileFormat(models.TextChoices):
        CSV = 'csv', 'CSV'
        EXCEL = 'excel', 'Excel'
        EFT = 'eft', 'EFT'

    payroll_period = models.ForeignKey(
        PayrollPeriod,
        on_delete=models.CASCADE,
        related_name='bank_files'
    )
    file_format = models.CharField(
        max_length=10,
        choices=FileFormat.choices,
        default=FileFormat.CSV
    )
    file_path = models.CharField(max_length=500)
    generated_at = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2)
    employee_count = models.IntegerField()

    def __str__(self):
        return f"Bank file for {self.payroll_period} ({self.file_format})"
