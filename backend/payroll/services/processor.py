"""
Payroll Processor Service
Handles payroll processing for all employees in a period.
"""
from decimal import Decimal
from typing import List, Optional
from django.utils import timezone
from django.db import transaction
import logging

from employees.models import User, EmployeeAllowance, EmployeeDeduction
from payroll.models import PayrollPeriod, PayrollEntry, TaxTable
from .calculator import PayrollCalculator

logger = logging.getLogger('payroll')


class PayrollProcessor:
    """
    Processes payroll for all active employees in a given period.
    """

    def __init__(self, payroll_period: PayrollPeriod):
        """
        Initialize processor for a specific payroll period.

        Args:
            payroll_period: The PayrollPeriod to process
        """
        self.payroll_period = payroll_period
        self.calculator = self._get_calculator()

    def _get_calculator(self) -> PayrollCalculator:
        """Get calculator with current tax table configuration."""
        tax_table = TaxTable.get_active()

        if tax_table:
            config = {
                'band_1_limit': tax_table.band_1_limit,
                'band_1_rate': tax_table.band_1_rate,
                'band_2_limit': tax_table.band_2_limit,
                'band_2_rate': tax_table.band_2_rate,
                'band_3_limit': tax_table.band_3_limit,
                'band_3_rate': tax_table.band_3_rate,
                'band_4_limit': tax_table.band_4_limit,
                'band_4_rate': tax_table.band_4_rate,
                'band_5_rate': tax_table.band_5_rate,
                'personal_relief': tax_table.personal_relief,
                'insurance_relief_rate': tax_table.insurance_relief_rate,
                'insurance_relief_max': tax_table.insurance_relief_max,
                'disability_exemption': tax_table.disability_exemption,
                'nssf_tier1_limit': tax_table.nssf_tier1_limit,
                'nssf_tier1_rate': tax_table.nssf_tier1_rate,
                'nssf_tier2_limit': tax_table.nssf_tier2_limit,
                'nssf_tier2_rate': tax_table.nssf_tier2_rate,
                'sha_rate': tax_table.sha_rate,
                'housing_levy_rate': tax_table.housing_levy_rate,
                'pension_max_deduction': tax_table.pension_max_deduction,
                'mortgage_interest_max': tax_table.mortgage_interest_max,
            }
            return PayrollCalculator(config)

        return PayrollCalculator()

    def get_active_employees(self) -> List[User]:
        """Get all active employees for payroll."""
        return User.objects.filter(
            employment_status=User.EmploymentStatus.ACTIVE,
            is_active=True
        ).select_related('department')

    def get_employee_allowances(self, employee: User, period_date) -> dict:
        """
        Get active allowances for an employee.

        Args:
            employee: The employee
            period_date: Date to check allowance validity

        Returns:
            Dict of allowances for calculator
        """
        allowances = EmployeeAllowance.objects.filter(
            employee=employee,
            effective_from__lte=period_date
        ).filter(
            models.Q(effective_to__isnull=True) | models.Q(effective_to__gte=period_date)
        )

        result = {}
        for allowance in allowances:
            name = allowance.name or allowance.get_allowance_type_display()
            result[name] = {
                'amount': float(allowance.amount),
                'taxable': allowance.is_taxable
            }

        return result

    def get_employee_deductions(self, employee: User, period_date) -> dict:
        """
        Get active deductions for an employee.

        Args:
            employee: The employee
            period_date: Date to check deduction validity

        Returns:
            Dict of deductions for calculator
        """
        from django.db import models

        deductions = EmployeeDeduction.objects.filter(
            employee=employee,
            effective_from__lte=period_date
        ).filter(
            models.Q(effective_to__isnull=True) | models.Q(effective_to__gte=period_date)
        )

        result = {}
        for deduction in deductions:
            result[deduction.name] = {
                'amount': float(deduction.amount),
                'type': deduction.deduction_type
            }

        return result

    def get_pension_contribution(self, employee: User, period_date) -> Decimal:
        """Get pension contribution for employee."""
        from django.db import models

        pension = EmployeeDeduction.objects.filter(
            employee=employee,
            deduction_type=EmployeeDeduction.DeductionType.PENSION,
            effective_from__lte=period_date,
            is_pretax=True
        ).filter(
            models.Q(effective_to__isnull=True) | models.Q(effective_to__gte=period_date)
        ).first()

        return Decimal(str(pension.amount)) if pension else Decimal('0')

    def get_insurance_premium(self, employee: User, period_date) -> Decimal:
        """Get insurance premium for insurance relief calculation."""
        from django.db import models

        insurance = EmployeeDeduction.objects.filter(
            employee=employee,
            deduction_type=EmployeeDeduction.DeductionType.INSURANCE,
            effective_from__lte=period_date
        ).filter(
            models.Q(effective_to__isnull=True) | models.Q(effective_to__gte=period_date)
        ).first()

        return Decimal(str(insurance.amount)) if insurance else Decimal('0')

    @transaction.atomic
    def process_employee(self, employee: User) -> PayrollEntry:
        """
        Process payroll for a single employee.

        Args:
            employee: The employee to process

        Returns:
            Created or updated PayrollEntry
        """
        import datetime

        period_date = datetime.date(self.payroll_period.year, self.payroll_period.month, 1)

        # Get allowances and deductions
        allowances = self.get_employee_allowances(employee, period_date)
        deductions = self.get_employee_deductions(employee, period_date)
        pension = self.get_pension_contribution(employee, period_date)
        insurance = self.get_insurance_premium(employee, period_date)

        # Calculate payroll
        result = self.calculator.calculate(
            basic_salary=employee.basic_salary,
            allowances=allowances,
            deductions=deductions,
            pension_contribution=pension,
            insurance_premium=insurance,
            has_disability=employee.has_disability,
        )

        # Create or update payroll entry
        entry, created = PayrollEntry.objects.update_or_create(
            payroll_period=self.payroll_period,
            employee=employee,
            defaults={
                'basic_salary': result.basic_salary,
                'taxable_allowances': result.taxable_allowances,
                'non_taxable_allowances': result.non_taxable_allowances,
                'gross_pay': result.gross_pay,
                'pension_contribution': result.pension_contribution,
                'owner_occupied_interest': result.owner_occupied_interest,
                'taxable_income': result.taxable_income,
                'tax_charged': result.tax_charged,
                'personal_relief': result.personal_relief,
                'insurance_relief': result.insurance_relief,
                'disability_exemption': result.disability_exemption,
                'paye': result.paye,
                'nssf': result.nssf,
                'sha': result.sha,
                'housing_levy': result.housing_levy,
                'loan_deductions': result.loan_deductions,
                'sacco_deductions': result.sacco_deductions,
                'other_deductions': result.other_deductions,
                'total_deductions': result.total_deductions,
                'net_pay': result.net_pay,
                'allowance_details': result.allowance_details,
                'deduction_details': result.deduction_details,
            }
        )

        action = 'Created' if created else 'Updated'
        logger.info(f"{action} payroll entry for {employee.get_full_name()}: Net Pay = {result.net_pay}")

        return entry

    @transaction.atomic
    def process_all(self, prepared_by: User) -> PayrollPeriod:
        """
        Process payroll for all active employees.

        Args:
            prepared_by: User who is preparing the payroll

        Returns:
            Updated PayrollPeriod with totals
        """
        employees = self.get_active_employees()
        logger.info(f"Processing payroll for {employees.count()} employees")

        for employee in employees:
            try:
                self.process_employee(employee)
            except Exception as e:
                logger.error(f"Error processing payroll for {employee.get_full_name()}: {e}")
                raise

        # Update payroll period
        self.payroll_period.prepared_by = prepared_by
        self.payroll_period.prepared_at = timezone.now()
        self.payroll_period.status = PayrollPeriod.Status.PENDING_HR
        self.payroll_period.calculate_totals()

        logger.info(
            f"Payroll processing complete. "
            f"Total Gross: {self.payroll_period.total_gross}, "
            f"Total Net: {self.payroll_period.total_net}"
        )

        return self.payroll_period

    @transaction.atomic
    def approve_hr(self, approved_by: User, comments: str = '') -> PayrollPeriod:
        """HR approval of payroll."""
        if self.payroll_period.status != PayrollPeriod.Status.PENDING_HR:
            raise ValueError("Payroll is not pending HR approval")

        self.payroll_period.hr_approved_by = approved_by
        self.payroll_period.hr_approved_at = timezone.now()
        self.payroll_period.hr_comments = comments
        self.payroll_period.status = PayrollPeriod.Status.PENDING_MANAGEMENT
        self.payroll_period.save()

        logger.info(f"Payroll HR approved by {approved_by.get_full_name()}")
        return self.payroll_period

    @transaction.atomic
    def approve_management(self, approved_by: User, comments: str = '') -> PayrollPeriod:
        """Management final approval of payroll."""
        if self.payroll_period.status != PayrollPeriod.Status.PENDING_MANAGEMENT:
            raise ValueError("Payroll is not pending management approval")

        self.payroll_period.mgmt_approved_by = approved_by
        self.payroll_period.mgmt_approved_at = timezone.now()
        self.payroll_period.mgmt_comments = comments
        self.payroll_period.status = PayrollPeriod.Status.APPROVED
        self.payroll_period.save()

        logger.info(f"Payroll management approved by {approved_by.get_full_name()}")
        return self.payroll_period

    @transaction.atomic
    def reject(self, rejected_by: User, comments: str) -> PayrollPeriod:
        """Reject payroll and return to draft."""
        self.payroll_period.status = PayrollPeriod.Status.DRAFT
        self.payroll_period.hr_approved_by = None
        self.payroll_period.hr_approved_at = None
        self.payroll_period.mgmt_approved_by = None
        self.payroll_period.mgmt_approved_at = None

        # Store rejection in comments
        if self.payroll_period.hr_comments:
            self.payroll_period.hr_comments += f"\n\nRejected by {rejected_by.get_full_name()}: {comments}"
        else:
            self.payroll_period.hr_comments = f"Rejected by {rejected_by.get_full_name()}: {comments}"

        self.payroll_period.save()

        logger.info(f"Payroll rejected by {rejected_by.get_full_name()}: {comments}")
        return self.payroll_period
