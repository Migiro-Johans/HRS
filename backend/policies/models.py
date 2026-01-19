"""
Policies and SOPs models for HRS - Payroll and Leave Management System
"""
from django.db import models
from django.conf import settings
from core.models import BaseModel


class PolicyCategory(BaseModel):
    """
    Categories for organizing policies and SOPs.
    """

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Policy Categories'

    def __str__(self):
        return self.name


class Policy(BaseModel):
    """
    Company policies and Standard Operating Procedures (SOPs).
    """

    class PolicyType(models.TextChoices):
        COMPANY_WIDE = 'company', 'Company-Wide Policy'
        DEPARTMENT = 'department', 'Department SOP'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        UNDER_REVIEW = 'review', 'Under Review'
        PUBLISHED = 'published', 'Published'
        ARCHIVED = 'archived', 'Archived'

    title = models.CharField(max_length=255)
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text='Unique policy reference code'
    )
    category = models.ForeignKey(
        PolicyCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='policies'
    )
    policy_type = models.CharField(
        max_length=20,
        choices=PolicyType.choices,
        default=PolicyType.COMPANY_WIDE
    )
    description = models.TextField(blank=True)

    # Document
    document = models.FileField(upload_to='policies/%Y/%m/')
    file_name = models.CharField(max_length=255, blank=True)
    file_size = models.IntegerField(default=0)

    # Version control
    version = models.CharField(max_length=20, default='1.0')
    effective_date = models.DateField()
    review_date = models.DateField(
        null=True,
        blank=True,
        help_text='Next scheduled review date'
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    # Access control
    departments = models.ManyToManyField(
        'employees.Department',
        blank=True,
        related_name='policies',
        help_text='Departments that can access this policy (empty = all departments)'
    )
    requires_acknowledgement = models.BooleanField(
        default=False,
        help_text='Employees must acknowledge reading this policy'
    )

    # Approval
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='policies_approved'
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-effective_date', 'title']
        verbose_name_plural = 'Policies'

    def __str__(self):
        return f"{self.code} - {self.title} (v{self.version})"

    def save(self, *args, **kwargs):
        if self.document:
            self.file_name = self.document.name.split('/')[-1]
            if hasattr(self.document, 'size'):
                self.file_size = self.document.size
        super().save(*args, **kwargs)


class PolicyVersion(BaseModel):
    """
    Version history for policies.
    Keeps track of all previous versions.
    """

    policy = models.ForeignKey(
        Policy,
        on_delete=models.CASCADE,
        related_name='versions'
    )
    version = models.CharField(max_length=20)
    document = models.FileField(upload_to='policies/archive/%Y/%m/')
    effective_date = models.DateField()
    archived_at = models.DateTimeField(auto_now_add=True)
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='policies_archived'
    )
    change_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-archived_at']
        unique_together = ['policy', 'version']

    def __str__(self):
        return f"{self.policy.code} v{self.version}"


class PolicyAcknowledgement(BaseModel):
    """
    Tracks employee acknowledgements of policies.
    """

    policy = models.ForeignKey(
        Policy,
        on_delete=models.CASCADE,
        related_name='acknowledgements'
    )
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='policy_acknowledgements'
    )
    acknowledged_at = models.DateTimeField(auto_now_add=True)
    policy_version = models.CharField(max_length=20)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        unique_together = ['policy', 'employee', 'policy_version']
        ordering = ['-acknowledged_at']

    def __str__(self):
        return f"{self.employee.get_full_name()} acknowledged {self.policy.code}"


class PolicyAccessLog(BaseModel):
    """
    Logs access to policies for audit purposes.
    """

    class ActionType(models.TextChoices):
        VIEW = 'view', 'Viewed'
        DOWNLOAD = 'download', 'Downloaded'

    policy = models.ForeignKey(
        Policy,
        on_delete=models.CASCADE,
        related_name='access_logs'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='policy_access_logs'
    )
    action = models.CharField(
        max_length=20,
        choices=ActionType.choices
    )
    accessed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-accessed_at']

    def __str__(self):
        return f"{self.user.get_full_name()} {self.action} {self.policy.code}"
