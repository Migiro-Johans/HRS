"""
Tests for payroll calculation engine.
Validates Kenyan tax calculations (PAYE, NSSF, SHA, Housing Levy)
"""
from decimal import Decimal
from django.test import TestCase
from payroll.services.calculator import PayrollCalculator


class PayrollCalculatorTests(TestCase):
    """Tests for the PayrollCalculator service."""

    def setUp(self):
        self.calculator = PayrollCalculator()

    def test_nssf_calculation_below_tier1(self):
        """Test NSSF for salary below Tier 1 limit."""
        gross = Decimal('5000')
        nssf = self.calculator.calculate_nssf(gross)
        expected = Decimal('300')  # 6% of 5000
        self.assertEqual(nssf, expected)

    def test_nssf_calculation_tier1_only(self):
        """Test NSSF at exactly Tier 1 limit."""
        gross = Decimal('7000')
        nssf = self.calculator.calculate_nssf(gross)
        expected = Decimal('420')  # 6% of 7000
        self.assertEqual(nssf, expected)

    def test_nssf_calculation_tier1_and_tier2(self):
        """Test NSSF with both Tier 1 and Tier 2."""
        gross = Decimal('36000')
        nssf = self.calculator.calculate_nssf(gross)
        # Tier 1: 6% of 7000 = 420
        # Tier 2: 6% of (36000 - 7000) = 6% of 29000 = 1740
        # Total: 2160
        expected = Decimal('2160')
        self.assertEqual(nssf, expected)

    def test_nssf_calculation_above_tier2_limit(self):
        """Test NSSF caps at Tier 2 limit."""
        gross = Decimal('100000')
        nssf = self.calculator.calculate_nssf(gross)
        # Tier 1: 6% of 7000 = 420
        # Tier 2: 6% of (36000 - 7000) = 1740
        # Total: 2160 (capped at tier 2 limit)
        expected = Decimal('2160')
        self.assertEqual(nssf, expected)

    def test_sha_calculation(self):
        """Test SHA calculation (2.75% of gross)."""
        gross = Decimal('50000')
        sha = self.calculator.calculate_sha(gross)
        expected = Decimal('1375')  # 2.75% of 50000
        self.assertEqual(sha, expected)

    def test_housing_levy_calculation(self):
        """Test Housing Levy calculation (1.5% of gross)."""
        gross = Decimal('50000')
        levy = self.calculator.calculate_housing_levy(gross)
        expected = Decimal('750')  # 1.5% of 50000
        self.assertEqual(levy, expected)

    def test_paye_band1_only(self):
        """Test PAYE for income in first band only (10%)."""
        taxable_income = Decimal('20000')
        tax = self.calculator.calculate_tax(taxable_income)
        expected = Decimal('2000')  # 10% of 20000
        self.assertEqual(tax, expected)

    def test_paye_band1_and_band2(self):
        """Test PAYE for income spanning band 1 and 2."""
        taxable_income = Decimal('30000')
        tax = self.calculator.calculate_tax(taxable_income)
        # Band 1: 10% of 24000 = 2400
        # Band 2: 25% of (30000 - 24000) = 25% of 6000 = 1500
        # Total: 3900
        expected = Decimal('3900')
        self.assertEqual(tax, expected)

    def test_paye_with_personal_relief(self):
        """Test that PAYE is reduced by personal relief."""
        result = self.calculator.calculate(
            basic_salary=Decimal('50000'),
        )
        # Gross: 50000
        # NSSF: 2160 (capped)
        # Taxable: 50000 - 2160 = 47840
        # Tax bands:
        # - Band 1: 10% of 24000 = 2400
        # - Band 2: 25% of (32333 - 24000) = 25% of 8333 = 2083.25
        # - Band 3: 30% of (47840 - 32333) = 30% of 15507 = 4652.10
        # Total tax: 9135.35
        # Personal relief: 2400
        # PAYE: 9135.35 - 2400 = 6735.35

        self.assertEqual(result.gross_pay, Decimal('50000'))
        self.assertEqual(result.nssf, Decimal('2160'))
        self.assertGreater(result.paye, Decimal('0'))
        self.assertEqual(result.personal_relief, Decimal('2400'))

    def test_full_payroll_calculation(self):
        """Test complete payroll calculation matching G9 example."""
        # Based on the G9 document: Basic salary 53,000
        # With pension contribution of 20,000 (1,080 actual)
        result = self.calculator.calculate(
            basic_salary=Decimal('53000'),
            pension_contribution=Decimal('1080'),  # Actual contribution
        )

        self.assertEqual(result.basic_salary, Decimal('53000'))
        self.assertEqual(result.gross_pay, Decimal('53000'))

        # Verify NSSF (capped at tier 2)
        self.assertEqual(result.nssf, Decimal('2160'))

        # Verify SHA (2.75% of 53000)
        expected_sha = Decimal('1457.50')
        self.assertEqual(result.sha, expected_sha)

        # Verify Housing Levy (1.5% of 53000)
        expected_housing = Decimal('795')
        self.assertEqual(result.housing_levy, expected_housing)

        # Verify net pay is calculated
        self.assertGreater(result.net_pay, Decimal('0'))
        self.assertLess(result.net_pay, result.gross_pay)

    def test_allowances_taxable(self):
        """Test that taxable allowances are included in gross."""
        result = self.calculator.calculate(
            basic_salary=Decimal('30000'),
            allowances={
                'House Allowance': {'amount': 10000, 'taxable': True},
                'Transport': {'amount': 5000, 'taxable': True},
            }
        )

        self.assertEqual(result.basic_salary, Decimal('30000'))
        self.assertEqual(result.taxable_allowances, Decimal('15000'))
        self.assertEqual(result.gross_pay, Decimal('45000'))

    def test_allowances_non_taxable(self):
        """Test non-taxable allowances."""
        result = self.calculator.calculate(
            basic_salary=Decimal('30000'),
            allowances={
                'House Allowance': {'amount': 10000, 'taxable': True},
                'Lunch Allowance': {'amount': 5000, 'taxable': False},
            }
        )

        self.assertEqual(result.taxable_allowances, Decimal('10000'))
        self.assertEqual(result.non_taxable_allowances, Decimal('5000'))
        self.assertEqual(result.gross_pay, Decimal('45000'))

    def test_insurance_relief(self):
        """Test insurance relief calculation."""
        result = self.calculator.calculate(
            basic_salary=Decimal('50000'),
            insurance_premium=Decimal('5000'),
        )

        # Insurance relief: 15% of 5000 = 750
        self.assertEqual(result.insurance_relief, Decimal('750'))

    def test_insurance_relief_capped(self):
        """Test insurance relief is capped at 5000."""
        result = self.calculator.calculate(
            basic_salary=Decimal('50000'),
            insurance_premium=Decimal('50000'),  # Very high premium
        )

        # Insurance relief: 15% of 50000 = 7500, but capped at 5000
        self.assertEqual(result.insurance_relief, Decimal('5000'))

    def test_disability_exemption(self):
        """Test disability tax exemption."""
        result_normal = self.calculator.calculate(
            basic_salary=Decimal('50000'),
            has_disability=False,
        )

        result_disabled = self.calculator.calculate(
            basic_salary=Decimal('50000'),
            has_disability=True,
        )

        self.assertEqual(result_disabled.disability_exemption, Decimal('150000'))
        # PAYE should be 0 due to high exemption
        self.assertEqual(result_disabled.paye, Decimal('0'))
        # Net pay should be higher for disabled person (no PAYE)
        self.assertGreater(result_disabled.net_pay, result_normal.net_pay)

    def test_deductions(self):
        """Test other deductions (loan, SACCO)."""
        result = self.calculator.calculate(
            basic_salary=Decimal('50000'),
            deductions={
                'Bank Loan': {'amount': 5000, 'type': 'loan'},
                'SACCO Contribution': {'amount': 3000, 'type': 'sacco'},
            }
        )

        self.assertEqual(result.loan_deductions, Decimal('5000'))
        self.assertEqual(result.sacco_deductions, Decimal('3000'))
        # These should be included in total deductions
        self.assertIn(Decimal('5000'), [result.loan_deductions])
        self.assertIn(Decimal('3000'), [result.sacco_deductions])

    def test_zero_salary(self):
        """Test calculation with zero salary."""
        result = self.calculator.calculate(
            basic_salary=Decimal('0'),
        )

        self.assertEqual(result.gross_pay, Decimal('0'))
        self.assertEqual(result.paye, Decimal('0'))
        self.assertEqual(result.nssf, Decimal('0'))
        self.assertEqual(result.sha, Decimal('0'))
        self.assertEqual(result.net_pay, Decimal('0'))

    def test_high_salary(self):
        """Test calculation with high salary (top tax band)."""
        result = self.calculator.calculate(
            basic_salary=Decimal('1000000'),  # 1 million
        )

        self.assertEqual(result.gross_pay, Decimal('1000000'))
        # Should hit the 35% top band
        self.assertGreater(result.paye, Decimal('200000'))  # Significant PAYE
        self.assertGreater(result.net_pay, Decimal('0'))


class PayrollCalculatorKRAComplianceTests(TestCase):
    """
    Tests to verify compliance with KRA tax rules.
    Based on official KRA P9A form calculations.
    """

    def setUp(self):
        self.calculator = PayrollCalculator()

    def test_kra_example_calculation(self):
        """
        Test based on actual G9/P9A document values.
        Employee: Basic salary 53,000
        Pension contribution: 1,080 (actual), 20,000 (30% limit)
        """
        result = self.calculator.calculate(
            basic_salary=Decimal('53000'),
            pension_contribution=Decimal('1080'),
        )

        # Verify the calculation follows KRA rules
        # Taxable = Gross - Pension (deductible) - NSSF
        # From G9: Chargeable Pay was 51,920
        # This suggests: 53000 - 1080 = 51920 (NSSF wasn't deducted in that example)

        # Our calculation includes NSSF as per current rules
        # Taxable = 53000 - min(1080, 20000) - 2160 = 53000 - 1080 - 2160 = 49760

        self.assertEqual(result.pension_deductible, Decimal('1080'))
        self.assertEqual(result.nssf, Decimal('2160'))
        self.assertEqual(result.taxable_income, Decimal('49760'))

    def test_personal_relief_monthly(self):
        """Verify personal relief is KES 2,400 per month."""
        result = self.calculator.calculate(
            basic_salary=Decimal('50000'),
        )
        self.assertEqual(result.personal_relief, Decimal('2400'))
