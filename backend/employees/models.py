"""
Employee models for HRS - Payroll and Leave Management System
"""
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.core.validators import RegexValidator
from core.models import BaseModel


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email address is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.ADMIN)
        return self.create_user(email, password, **extra_fields)


class Department(BaseModel):
    """Department model for organizational structure."""

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True)
    head = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='departments_headed'
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class User(AbstractUser, BaseModel):
    """
    Custom User model for HRS.
    Uses email as the primary identifier (Microsoft 365 integration).
    """

    class Role(models.TextChoices):
        EMPLOYEE = 'employee', 'Employee'
        HOD = 'hod', 'Head of Department'
        HR = 'hr', 'Human Resource'
        ACCOUNTS = 'accounts', 'Accounts'
        MANAGEMENT = 'management', 'Management'
        ADMIN = 'admin', 'System Administrator'

    class EmploymentStatus(models.TextChoices):
        ACTIVE = 'active', 'Active'
        ON_LEAVE = 'on_leave', 'On Leave'
        SUSPENDED = 'suspended', 'Suspended'
        TERMINATED = 'terminated', 'Terminated'
        RESIGNED = 'resigned', 'Resigned'

    class EmploymentType(models.TextChoices):
        PERMANENT = 'permanent', 'Permanent'
        CONTRACT = 'contract', 'Contract'
        PROBATION = 'probation', 'Probation'
        INTERN = 'intern', 'Intern'

    # Remove username, use email instead
    username = None
    email = models.EmailField('email address', unique=True)

    # Personal Information
    employee_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    phone_regex = RegexValidator(
        regex=r'^\+?254?\d{9,12}$',
        message="Phone number must be in format: '+254712345678'"
    )
    phone_number = models.CharField(validators=[phone_regex], max_length=15, blank=True)
    national_id = models.CharField(max_length=20, blank=True)
    kra_pin = models.CharField(
        max_length=11,
        blank=True,
        help_text='KRA PIN (e.g., A012345678Z)'
    )
    nssf_number = models.CharField(max_length=20, blank=True)
    nhif_number = models.CharField(max_length=20, blank=True)  # Legacy, now SHA

    # Employment Details
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees'
    )
    job_title = models.CharField(max_length=100, blank=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.EMPLOYEE
    )
    employment_status = models.CharField(
        max_length=20,
        choices=EmploymentStatus.choices,
        default=EmploymentStatus.ACTIVE
    )
    employment_type = models.CharField(
        max_length=20,
        choices=EmploymentType.choices,
        default=EmploymentType.PERMANENT
    )
    date_joined_company = models.DateField(null=True, blank=True)
    date_left = models.DateField(null=True, blank=True)
    reports_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='direct_reports'
    )

    # Banking Information
    bank_name = models.CharField(max_length=100, blank=True)
    bank_branch = models.CharField(max_length=100, blank=True)
    bank_account_number = models.CharField(max_length=50, blank=True)

    # Payroll Information
    basic_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='Monthly basic salary in KES'
    )
    has_disability = models.BooleanField(
        default=False,
        help_text='Eligible for disability tax exemption'
    )

    # Microsoft Entra ID
    azure_ad_id = models.CharField(max_length=100, blank=True, unique=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    class Meta:
        ordering = ['first_name', 'last_name']
        verbose_name = 'Employee'
        verbose_name_plural = 'Employees'

    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email

    @property
    def is_hod(self):
        return self.role == self.Role.HOD or self.departments_headed.exists()

    @property
    def is_hr(self):
        return self.role in [self.Role.HR, self.Role.ADMIN]

    @property
    def is_accounts(self):
        return self.role in [self.Role.ACCOUNTS, self.Role.ADMIN]

    @property
    def is_management(self):
        return self.role in [self.Role.MANAGEMENT, self.Role.ADMIN]

    def can_approve_leave(self, employee):
        """Check if this user can approve leave for the given employee."""
        # HOD can approve for their department
        if self.is_hod and employee.department == self.department:
            return True
        # HR can approve any leave
        if self.is_hr:
            return True
        # Direct supervisor can approve
        if employee.reports_to == self:
            return True
        return False


class EmployeeAllowance(BaseModel):
    """
    Monthly allowances for employees.
    These are added to basic salary for gross pay calculation.
    """

    class AllowanceType(models.TextChoices):
        HOUSE = 'house', 'House Allowance'
        TRANSPORT = 'transport', 'Transport Allowance'
        MEDICAL = 'medical', 'Medical Allowance'
        AIRTIME = 'airtime', 'Airtime Allowance'
        LUNCH = 'lunch', 'Lunch Allowance'
        HARDSHIP = 'hardship', 'Hardship Allowance'
        RESPONSIBILITY = 'responsibility', 'Responsibility Allowance'
        OTHER = 'other', 'Other Allowance'

    employee = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='allowances'
    )
    allowance_type = models.CharField(
        max_length=20,
        choices=AllowanceType.choices
    )
    name = models.CharField(
        max_length=100,
        blank=True,
        help_text='Custom name for "Other" allowance type'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    is_taxable = models.BooleanField(
        default=True,
        help_text='Whether this allowance is subject to PAYE'
    )
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['employee', 'allowance_type']

    def __str__(self):
        name = self.name if self.allowance_type == self.AllowanceType.OTHER else self.get_allowance_type_display()
        return f"{self.employee.get_full_name()} - {name}: {self.amount}"


class EmployeeDeduction(BaseModel):
    """
    Recurring deductions for employees (loans, advances, SACCO, etc.).
    Statutory deductions (PAYE, NSSF, SHA, Housing Levy) are calculated automatically.
    """

    class DeductionType(models.TextChoices):
        LOAN = 'loan', 'Loan Repayment'
        ADVANCE = 'advance', 'Salary Advance'
        SACCO = 'sacco', 'SACCO Contribution'
        INSURANCE = 'insurance', 'Insurance Premium'
        PENSION = 'pension', 'Pension Contribution'
        OTHER = 'other', 'Other Deduction'

    employee = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='deductions'
    )
    deduction_type = models.CharField(
        max_length=20,
        choices=DeductionType.choices
    )
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    is_pretax = models.BooleanField(
        default=False,
        help_text='Deducted before tax calculation (e.g., pension contributions)'
    )
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Total loan/advance amount (for tracking balance)'
    )
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Remaining balance'
    )

    class Meta:
        ordering = ['employee', 'deduction_type']

    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.name}: {self.amount}"
