"""
Payroll Calculator Service
Implements Kenyan statutory deductions: PAYE, NSSF, SHA, Housing Levy
Based on Kenya Revenue Authority tax rates (2024/2025)
"""
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger('payroll')


@dataclass
class PayrollResult:
    """Result of payroll calculation for an employee."""
    # Earnings
    basic_salary: Decimal
    taxable_allowances: Decimal
    non_taxable_allowances: Decimal
    gross_pay: Decimal

    # Pre-tax deductions
    pension_contribution: Decimal
    pension_deductible: Decimal  # Limited to max allowed
    owner_occupied_interest: Decimal

    # Tax calculation
    taxable_income: Decimal
    tax_charged: Decimal
    personal_relief: Decimal
    insurance_relief: Decimal
    disability_exemption: Decimal
    paye: Decimal

    # Statutory deductions
    nssf: Decimal
    sha: Decimal
    housing_levy: Decimal

    # Other deductions
    loan_deductions: Decimal
    sacco_deductions: Decimal
    other_deductions: Decimal

    # Totals
    total_deductions: Decimal
    net_pay: Decimal

    # Details for breakdown
    allowance_details: dict
    deduction_details: dict


class PayrollCalculator:
    """
    Calculator for Kenyan payroll with all statutory deductions.

    Tax Calculation Steps:
    1. Calculate Gross Pay = Basic + Allowances + Benefits
    2. Calculate NSSF (Tier I + Tier II)
    3. Calculate taxable income = Gross - Pension - Mortgage Interest - NSSF
    4. Calculate tax on taxable income using tax bands
    5. Apply reliefs (Personal, Insurance, Disability)
    6. PAYE = Tax Charged - Reliefs
    7. Calculate SHA (2.75% of gross)
    8. Calculate Housing Levy (1.5% of gross)
    9. Net Pay = Gross - PAYE - NSSF - SHA - Housing Levy - Other Deductions
    """

    # Default tax configuration (2024/2025 Kenya)
    DEFAULT_CONFIG = {
        # PAYE Tax Bands (Monthly)
        'band_1_limit': Decimal('24000'),
        'band_1_rate': Decimal('0.10'),
        'band_2_limit': Decimal('32333'),
        'band_2_rate': Decimal('0.25'),
        'band_3_limit': Decimal('500000'),
        'band_3_rate': Decimal('0.30'),
        'band_4_limit': Decimal('800000'),
        'band_4_rate': Decimal('0.325'),
        'band_5_rate': Decimal('0.35'),

        # Reliefs
        'personal_relief': Decimal('2400'),
        'insurance_relief_rate': Decimal('0.15'),
        'insurance_relief_max': Decimal('5000'),
        'disability_exemption': Decimal('150000'),

        # NSSF (New rates)
        'nssf_tier1_limit': Decimal('7000'),
        'nssf_tier1_rate': Decimal('0.06'),
        'nssf_tier2_limit': Decimal('36000'),
        'nssf_tier2_rate': Decimal('0.06'),

        # SHA (Social Health Authority)
        'sha_rate': Decimal('0.0275'),

        # Housing Levy
        'housing_levy_rate': Decimal('0.015'),

        # Pension limits
        'pension_max_deduction': Decimal('20000'),
        'mortgage_interest_max': Decimal('25000'),
    }

    def __init__(self, config: Optional[dict] = None):
        """
        Initialize calculator with tax configuration.

        Args:
            config: Tax configuration dict. Uses DEFAULT_CONFIG if not provided.
        """
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}

    def _round(self, value: Decimal) -> Decimal:
        """Round to 2 decimal places."""
        return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def calculate_nssf(self, gross_pay: Decimal) -> Decimal:
        """
        Calculate NSSF contribution (employee portion).

        New NSSF rates (Tier I + Tier II):
        - Tier I: 6% of first KES 7,000
        - Tier II: 6% of KES 7,001 to KES 36,000

        Args:
            gross_pay: Monthly gross pay

        Returns:
            Total NSSF contribution
        """
        tier1_limit = self.config['nssf_tier1_limit']
        tier1_rate = self.config['nssf_tier1_rate']
        tier2_limit = self.config['nssf_tier2_limit']
        tier2_rate = self.config['nssf_tier2_rate']

        # Tier I contribution
        tier1_pensionable = min(gross_pay, tier1_limit)
        tier1_contribution = self._round(tier1_pensionable * tier1_rate)

        # Tier II contribution
        if gross_pay > tier1_limit:
            tier2_pensionable = min(gross_pay, tier2_limit) - tier1_limit
            tier2_contribution = self._round(tier2_pensionable * tier2_rate)
        else:
            tier2_contribution = Decimal('0')

        total_nssf = tier1_contribution + tier2_contribution
        logger.debug(f"NSSF: Tier1={tier1_contribution}, Tier2={tier2_contribution}, Total={total_nssf}")

        return total_nssf

    def calculate_sha(self, gross_pay: Decimal) -> Decimal:
        """
        Calculate SHA (Social Health Authority) contribution.

        Rate: 2.75% of gross pay

        Args:
            gross_pay: Monthly gross pay

        Returns:
            SHA contribution
        """
        sha = self._round(gross_pay * self.config['sha_rate'])
        logger.debug(f"SHA: {sha} (2.75% of {gross_pay})")
        return sha

    def calculate_housing_levy(self, gross_pay: Decimal) -> Decimal:
        """
        Calculate Affordable Housing Levy.

        Rate: 1.5% of gross pay

        Args:
            gross_pay: Monthly gross pay

        Returns:
            Housing levy amount
        """
        levy = self._round(gross_pay * self.config['housing_levy_rate'])
        logger.debug(f"Housing Levy: {levy} (1.5% of {gross_pay})")
        return levy

    def calculate_tax(self, taxable_income: Decimal) -> Decimal:
        """
        Calculate tax charged using progressive tax bands.

        Monthly Tax Bands (2024/2025):
        - 0 - 24,000: 10%
        - 24,001 - 32,333: 25%
        - 32,334 - 500,000: 30%
        - 500,001 - 800,000: 32.5%
        - Above 800,000: 35%

        Args:
            taxable_income: Monthly taxable income after deductions

        Returns:
            Tax charged before reliefs
        """
        if taxable_income <= 0:
            return Decimal('0')

        tax = Decimal('0')
        remaining = taxable_income

        bands = [
            (self.config['band_1_limit'], self.config['band_1_rate']),
            (self.config['band_2_limit'], self.config['band_2_rate']),
            (self.config['band_3_limit'], self.config['band_3_rate']),
            (self.config['band_4_limit'], self.config['band_4_rate']),
            (None, self.config['band_5_rate']),  # No upper limit
        ]

        previous_limit = Decimal('0')

        for limit, rate in bands:
            if remaining <= 0:
                break

            if limit is None:
                # Top band - no limit
                band_income = remaining
            else:
                band_income = min(remaining, limit - previous_limit)

            band_tax = self._round(band_income * rate)
            tax += band_tax
            remaining -= band_income

            logger.debug(f"Tax Band: income={band_income}, rate={rate}, tax={band_tax}")

            if limit is not None:
                previous_limit = limit

        logger.debug(f"Total Tax Charged: {tax}")
        return tax

    def calculate_insurance_relief(self, insurance_premium: Decimal) -> Decimal:
        """
        Calculate insurance relief.

        Relief: 15% of insurance premium, max KES 5,000/month

        Args:
            insurance_premium: Monthly insurance premium paid

        Returns:
            Insurance relief amount
        """
        relief = self._round(insurance_premium * self.config['insurance_relief_rate'])
        max_relief = self.config['insurance_relief_max']
        return min(relief, max_relief)

    def calculate(
        self,
        basic_salary: Decimal,
        allowances: Optional[dict] = None,
        deductions: Optional[dict] = None,
        pension_contribution: Decimal = Decimal('0'),
        mortgage_interest: Decimal = Decimal('0'),
        insurance_premium: Decimal = Decimal('0'),
        has_disability: bool = False,
    ) -> PayrollResult:
        """
        Calculate complete payroll for an employee.

        Args:
            basic_salary: Monthly basic salary
            allowances: Dict of allowances {'name': {'amount': x, 'taxable': bool}}
            deductions: Dict of deductions {'name': {'amount': x, 'type': str}}
            pension_contribution: Defined contribution retirement scheme
            mortgage_interest: Owner-occupied mortgage interest
            insurance_premium: Insurance premium for insurance relief
            has_disability: Whether employee qualifies for disability exemption

        Returns:
            PayrollResult with all computed values
        """
        allowances = allowances or {}
        deductions = deductions or {}

        # Step 1: Calculate allowances
        taxable_allowances = Decimal('0')
        non_taxable_allowances = Decimal('0')
        allowance_details = {}

        for name, details in allowances.items():
            amount = Decimal(str(details.get('amount', 0)))
            is_taxable = details.get('taxable', True)

            if is_taxable:
                taxable_allowances += amount
            else:
                non_taxable_allowances += amount

            allowance_details[name] = {
                'amount': float(amount),
                'taxable': is_taxable
            }

        # Step 2: Calculate Gross Pay
        gross_pay = basic_salary + taxable_allowances + non_taxable_allowances
        logger.info(f"Gross Pay: {gross_pay} (Basic: {basic_salary}, Taxable Allow: {taxable_allowances}, Non-Taxable: {non_taxable_allowances})")

        # Step 3: Calculate NSSF
        nssf = self.calculate_nssf(gross_pay)

        # Step 4: Calculate deductible pension (capped at max)
        pension_max = self.config['pension_max_deduction']
        pension_deductible = min(pension_contribution, pension_max)

        # Step 5: Calculate mortgage interest deduction (capped at max)
        mortgage_max = self.config['mortgage_interest_max']
        owner_occupied_interest = min(mortgage_interest, mortgage_max)

        # Step 6: Calculate Taxable Income
        # Taxable Income = Gross - NSSF - Pension Deductible - Mortgage Interest
        taxable_income = gross_pay - nssf - pension_deductible - owner_occupied_interest
        taxable_income = max(taxable_income, Decimal('0'))
        logger.info(f"Taxable Income: {taxable_income}")

        # Step 7: Calculate Tax Charged
        tax_charged = self.calculate_tax(taxable_income)

        # Step 8: Calculate Reliefs
        personal_relief = self.config['personal_relief']
        insurance_relief = self.calculate_insurance_relief(insurance_premium)

        # Disability exemption
        disability_exemption = Decimal('0')
        if has_disability:
            disability_exemption = self.config['disability_exemption']

        # Step 9: Calculate PAYE
        total_relief = personal_relief + insurance_relief + disability_exemption
        paye = max(tax_charged - total_relief, Decimal('0'))
        paye = self._round(paye)
        logger.info(f"PAYE: {paye} (Tax: {tax_charged}, Relief: {total_relief})")

        # Step 10: Calculate SHA and Housing Levy
        sha = self.calculate_sha(gross_pay)
        housing_levy = self.calculate_housing_levy(gross_pay)

        # Step 11: Process other deductions
        loan_deductions = Decimal('0')
        sacco_deductions = Decimal('0')
        other_deductions_total = Decimal('0')
        deduction_details = {}

        for name, details in deductions.items():
            amount = Decimal(str(details.get('amount', 0)))
            deduction_type = details.get('type', 'other')

            if deduction_type == 'loan':
                loan_deductions += amount
            elif deduction_type == 'sacco':
                sacco_deductions += amount
            else:
                other_deductions_total += amount

            deduction_details[name] = {
                'amount': float(amount),
                'type': deduction_type
            }

        # Step 12: Calculate Total Deductions and Net Pay
        total_deductions = (
            paye +
            nssf +
            sha +
            housing_levy +
            loan_deductions +
            sacco_deductions +
            other_deductions_total
        )

        net_pay = gross_pay - total_deductions
        net_pay = self._round(net_pay)

        logger.info(f"Net Pay: {net_pay} (Gross: {gross_pay}, Deductions: {total_deductions})")

        return PayrollResult(
            basic_salary=self._round(basic_salary),
            taxable_allowances=self._round(taxable_allowances),
            non_taxable_allowances=self._round(non_taxable_allowances),
            gross_pay=self._round(gross_pay),
            pension_contribution=self._round(pension_contribution),
            pension_deductible=self._round(pension_deductible),
            owner_occupied_interest=self._round(owner_occupied_interest),
            taxable_income=self._round(taxable_income),
            tax_charged=self._round(tax_charged),
            personal_relief=self._round(personal_relief),
            insurance_relief=self._round(insurance_relief),
            disability_exemption=self._round(disability_exemption),
            paye=paye,
            nssf=nssf,
            sha=sha,
            housing_levy=housing_levy,
            loan_deductions=self._round(loan_deductions),
            sacco_deductions=self._round(sacco_deductions),
            other_deductions=self._round(other_deductions_total),
            total_deductions=self._round(total_deductions),
            net_pay=net_pay,
            allowance_details=allowance_details,
            deduction_details=deduction_details,
        )
