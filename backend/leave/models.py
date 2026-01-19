"""
Leave management models for HRS - Payroll and Leave Management System
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from core.models import BaseModel


class LeaveType(BaseModel):
    """
    Types of leave available in the organization.
    """

    class AccrualMethod(models.TextChoices):
        ANNUAL = 'annual', 'Annual Allocation'
        MONTHLY = 'monthly', 'Monthly Accrual'
        NONE = 'none', 'No Accrual (Fixed)'

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True)

    # Leave entitlement
    days_per_year = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Annual leave days entitlement'
    )
    accrual_method = models.CharField(
        max_length=20,
        choices=AccrualMethod.choices,
        default=AccrualMethod.ANNUAL
    )

    # Rules
    requires_approval = models.BooleanField(default=True)
    requires_documentation = models.BooleanField(
        default=False,
        help_text='Requires supporting documents (e.g., medical certificate)'
    )
    max_consecutive_days = models.IntegerField(
        null=True,
        blank=True,
        help_text='Maximum consecutive days allowed'
    )
    min_notice_days = models.IntegerField(
        default=0,
        help_text='Minimum days notice required before leave'
    )
    can_carry_forward = models.BooleanField(
        default=False,
        help_text='Can unused days be carried to next year'
    )
    max_carry_forward_days = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Maximum days that can be carried forward'
    )

    # Applicability
    is_paid = models.BooleanField(default=True)
    applies_to_probation = models.BooleanField(
        default=False,
        help_text='Available during probation period'
    )
    gender_specific = models.CharField(
        max_length=10,
        choices=[('all', 'All'), ('male', 'Male Only'), ('female', 'Female Only')],
        default='all'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class LeaveBalance(BaseModel):
    """
    Tracks leave balance for each employee per leave type per year.
    """

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='leave_balances'
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.CASCADE,
        related_name='balances'
    )
    year = models.IntegerField()

    # Balance tracking
    entitled_days = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Total days entitled for the year'
    )
    carried_forward = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Days carried from previous year'
    )
    accrued_days = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Days accrued so far this year'
    )
    used_days = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Days used this year'
    )
    pending_days = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Days in pending leave requests'
    )

    class Meta:
        unique_together = ['employee', 'leave_type', 'year']
        ordering = ['employee', 'leave_type', '-year']

    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.leave_type.name} ({self.year})"

    @property
    def available_days(self):
        """Calculate available leave days."""
        return self.entitled_days + self.carried_forward + self.accrued_days - self.used_days - self.pending_days

    @property
    def total_entitlement(self):
        """Total entitlement including carried forward."""
        return self.entitled_days + self.carried_forward


class LeaveRequest(BaseModel):
    """
    Employee leave request with approval workflow.
    """

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PENDING_HOD = 'pending_hod', 'Pending HOD Approval'
        PENDING_HR = 'pending_hr', 'Pending HR Approval'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        CANCELLED = 'cancelled', 'Cancelled'

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='leave_requests'
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name='requests'
    )

    # Leave dates
    start_date = models.DateField()
    end_date = models.DateField()
    days_requested = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text='Number of working days'
    )
    is_half_day = models.BooleanField(default=False)
    half_day_period = models.CharField(
        max_length=10,
        choices=[('morning', 'Morning'), ('afternoon', 'Afternoon')],
        blank=True
    )

    # Request details
    reason = models.TextField(blank=True)
    contact_during_leave = models.CharField(max_length=100, blank=True)
    handover_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='handover_requests'
    )
    handover_notes = models.TextField(blank=True)

    # Supporting documents
    document = models.FileField(
        upload_to='leave_documents/%Y/%m/',
        blank=True,
        null=True
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    # HOD Approval
    hod_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leave_hod_approved'
    )
    hod_approved_at = models.DateTimeField(null=True, blank=True)
    hod_comments = models.TextField(blank=True)

    # HR Approval
    hr_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leave_hr_approved'
    )
    hr_approved_at = models.DateTimeField(null=True, blank=True)
    hr_comments = models.TextField(blank=True)

    # Rejection details
    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leave_rejected'
    )
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.leave_type.name} ({self.start_date} to {self.end_date})"

    def calculate_days(self):
        """Calculate working days between start and end date."""
        from datetime import timedelta

        if self.is_half_day:
            return 0.5

        # Simple calculation - can be enhanced with public holidays
        total_days = 0
        current_date = self.start_date

        while current_date <= self.end_date:
            # Exclude weekends (Saturday=5, Sunday=6)
            if current_date.weekday() < 5:
                total_days += 1
            current_date += timedelta(days=1)

        return total_days

    def submit(self):
        """Submit leave request for approval."""
        if self.status != self.Status.DRAFT:
            raise ValueError("Only draft requests can be submitted")

        self.days_requested = self.calculate_days()
        self.status = self.Status.PENDING_HOD
        self.save()

        # Update pending days in balance
        balance = LeaveBalance.objects.get(
            employee=self.employee,
            leave_type=self.leave_type,
            year=self.start_date.year
        )
        balance.pending_days += self.days_requested
        balance.save()

    def approve_hod(self, approver, comments=''):
        """HOD approval."""
        if self.status != self.Status.PENDING_HOD:
            raise ValueError("Request is not pending HOD approval")

        self.hod_approved_by = approver
        self.hod_approved_at = timezone.now()
        self.hod_comments = comments
        self.status = self.Status.PENDING_HR
        self.save()

    def approve_hr(self, approver, comments=''):
        """HR final approval."""
        from django.utils import timezone

        if self.status != self.Status.PENDING_HR:
            raise ValueError("Request is not pending HR approval")

        self.hr_approved_by = approver
        self.hr_approved_at = timezone.now()
        self.hr_comments = comments
        self.status = self.Status.APPROVED
        self.save()

        # Update balance - move from pending to used
        balance = LeaveBalance.objects.get(
            employee=self.employee,
            leave_type=self.leave_type,
            year=self.start_date.year
        )
        balance.pending_days -= self.days_requested
        balance.used_days += self.days_requested
        balance.save()

    def reject(self, rejector, reason):
        """Reject leave request."""
        from django.utils import timezone

        if self.status not in [self.Status.PENDING_HOD, self.Status.PENDING_HR]:
            raise ValueError("Request cannot be rejected in current status")

        self.rejected_by = rejector
        self.rejected_at = timezone.now()
        self.rejection_reason = reason
        self.status = self.Status.REJECTED
        self.save()

        # Remove from pending days
        balance = LeaveBalance.objects.get(
            employee=self.employee,
            leave_type=self.leave_type,
            year=self.start_date.year
        )
        balance.pending_days -= self.days_requested
        balance.save()

    def cancel(self):
        """Cancel leave request."""
        if self.status == self.Status.APPROVED:
            # Move days back from used to available
            balance = LeaveBalance.objects.get(
                employee=self.employee,
                leave_type=self.leave_type,
                year=self.start_date.year
            )
            balance.used_days -= self.days_requested
            balance.save()
        elif self.status in [self.Status.PENDING_HOD, self.Status.PENDING_HR]:
            # Remove from pending
            balance = LeaveBalance.objects.get(
                employee=self.employee,
                leave_type=self.leave_type,
                year=self.start_date.year
            )
            balance.pending_days -= self.days_requested
            balance.save()

        self.status = self.Status.CANCELLED
        self.save()


class PublicHoliday(BaseModel):
    """
    Public holidays - excluded from leave day calculations.
    """

    name = models.CharField(max_length=100)
    date = models.DateField(unique=True)
    is_recurring = models.BooleanField(
        default=False,
        help_text='Repeats every year on same date'
    )

    class Meta:
        ordering = ['date']

    def __str__(self):
        return f"{self.name} ({self.date})"
