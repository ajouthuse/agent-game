"""
test_finance.py - Unit tests for Iron Contract financial management system.

Tests cover:
- Pilot salary calculation (scales with skill level)
- Mech maintenance calculation (scales with weight class)
- Repair cost estimation (based on missing armor/structure)
- Mech repair (restores armor and structure to max)
- Monthly upkeep calculation (full report generation)
- Upkeep application (deducts costs, applies repairs)
- Bankruptcy detection
- Repair toggle mechanics (defer repairs to save money)
- Edge cases (KIA pilots, destroyed mechs, empty company)
"""

import sys
import os

# Add the project root to path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest

from data.models import (
    BattleMech,
    Company,
    MechStatus,
    MechWarrior,
    PilotStatus,
    WeightClass,
)
from data.finance import (
    PILOT_BASE_SALARY,
    PILOT_SKILL_BONUS,
    MECH_MAINTENANCE_BASE,
    REPAIR_COST_PER_ARMOR,
    REPAIR_COST_PER_STRUCTURE,
    PilotSalaryLine,
    MechMaintenanceLine,
    RepairLine,
    UpkeepReport,
    calculate_pilot_salary,
    calculate_mech_maintenance,
    calculate_repair_cost,
    repair_mech,
    calculate_monthly_upkeep,
    apply_upkeep,
    is_bankrupt,
    _recalculate_totals,
)


# ── Test Helpers ─────────────────────────────────────────────────────

def _make_pilot(**overrides):
    """Helper to create a pilot with sensible defaults."""
    defaults = {
        "name": "Test Pilot",
        "callsign": "Ace",
        "gunnery": 4,
        "piloting": 4,
        "morale": 75,
        "injuries": 0,
        "experience": 0,
        "status": PilotStatus.ACTIVE,
        "assigned_mech": None,
    }
    defaults.update(overrides)
    return MechWarrior(**defaults)


def _make_mech(**overrides):
    """Helper to create a mech with sensible defaults."""
    defaults = {
        "name": "Wolverine WVR-6R",
        "weight_class": WeightClass.MEDIUM,
        "tonnage": 55,
        "armor_current": 136,
        "armor_max": 136,
        "structure_current": 48,
        "structure_max": 48,
        "firepower": 6,
        "speed": 6,
        "status": MechStatus.READY,
    }
    defaults.update(overrides)
    return BattleMech(**defaults)


def _make_company(**overrides):
    """Helper to create a company with sensible defaults."""
    defaults = {
        "name": "Test Company",
        "c_bills": 500_000,
        "reputation": 15,
        "week": 1,
        "contracts_completed": 0,
        "mechwarriors": [],
        "mechs": [],
    }
    defaults.update(overrides)
    return Company(**defaults)


def _make_full_company():
    """Create a company with a standard lance for testing."""
    mechs = [
        _make_mech(name="Wolverine WVR-6R", weight_class=WeightClass.MEDIUM, tonnage=55),
        _make_mech(name="Shadow Hawk SHD-2H", weight_class=WeightClass.MEDIUM, tonnage=55),
        _make_mech(name="Hunchback HBK-4G", weight_class=WeightClass.MEDIUM, tonnage=50),
        _make_mech(name="Commando COM-2D", weight_class=WeightClass.LIGHT, tonnage=25),
    ]
    pilots = [
        _make_pilot(name="Marcus Steiner", callsign="Ace", gunnery=3, piloting=4),
        _make_pilot(name="Nadia Kurita", callsign="Raven", gunnery=4, piloting=3),
        _make_pilot(name="Gideon Davion", callsign="Bulldog", gunnery=3, piloting=5),
        _make_pilot(name="Jade Liao", callsign="Ghost", gunnery=4, piloting=3),
    ]
    for pilot, mech in zip(pilots, mechs):
        pilot.assigned_mech = mech.name

    return _make_company(mechs=mechs, mechwarriors=pilots)


# ── Pilot Salary Tests ───────────────────────────────────────────────

class TestPilotSalary(unittest.TestCase):
    """Tests for calculate_pilot_salary()."""

    def test_base_salary_worst_skills(self):
        """A pilot with gunnery 6 / piloting 6 gets only the base salary."""
        pilot = _make_pilot(gunnery=6, piloting=6)
        salary = calculate_pilot_salary(pilot)
        self.assertEqual(salary, PILOT_BASE_SALARY)

    def test_salary_scales_with_gunnery(self):
        """Better gunnery (lower number) increases salary."""
        pilot_bad = _make_pilot(gunnery=6, piloting=6)
        pilot_good = _make_pilot(gunnery=1, piloting=6)
        self.assertGreater(
            calculate_pilot_salary(pilot_good),
            calculate_pilot_salary(pilot_bad),
        )

    def test_salary_scales_with_piloting(self):
        """Better piloting (lower number) increases salary."""
        pilot_bad = _make_pilot(gunnery=6, piloting=6)
        pilot_good = _make_pilot(gunnery=6, piloting=1)
        self.assertGreater(
            calculate_pilot_salary(pilot_good),
            calculate_pilot_salary(pilot_bad),
        )

    def test_best_pilot_salary(self):
        """A gunnery 1 / piloting 1 pilot gets maximum salary."""
        pilot = _make_pilot(gunnery=1, piloting=1)
        expected = PILOT_BASE_SALARY + 5 * PILOT_SKILL_BONUS + 5 * PILOT_SKILL_BONUS
        self.assertEqual(calculate_pilot_salary(pilot), expected)

    def test_mid_skill_pilot_salary(self):
        """A gunnery 4 / piloting 4 pilot gets moderate salary."""
        pilot = _make_pilot(gunnery=4, piloting=4)
        expected = PILOT_BASE_SALARY + 2 * PILOT_SKILL_BONUS + 2 * PILOT_SKILL_BONUS
        self.assertEqual(calculate_pilot_salary(pilot), expected)

    def test_kia_pilot_costs_nothing(self):
        """A KIA pilot has zero salary."""
        pilot = _make_pilot(status=PilotStatus.KIA)
        self.assertEqual(calculate_pilot_salary(pilot), 0)

    def test_injured_pilot_still_costs(self):
        """An injured pilot still costs their full salary."""
        pilot = _make_pilot(gunnery=3, piloting=4, status=PilotStatus.INJURED)
        self.assertGreater(calculate_pilot_salary(pilot), 0)

    def test_salary_always_positive(self):
        """Salary should always be positive for non-KIA pilots."""
        for gun in range(1, 7):
            for plt in range(1, 7):
                pilot = _make_pilot(gunnery=gun, piloting=plt)
                self.assertGreater(calculate_pilot_salary(pilot), 0)


# ── Mech Maintenance Tests ───────────────────────────────────────────

class TestMechMaintenance(unittest.TestCase):
    """Tests for calculate_mech_maintenance()."""

    def test_light_mech_cheapest(self):
        """Light mechs have the lowest maintenance cost."""
        mech = _make_mech(weight_class=WeightClass.LIGHT)
        cost = calculate_mech_maintenance(mech)
        self.assertEqual(cost, MECH_MAINTENANCE_BASE[WeightClass.LIGHT])

    def test_medium_mech_cost(self):
        """Medium mechs cost more than light mechs."""
        light = _make_mech(weight_class=WeightClass.LIGHT)
        medium = _make_mech(weight_class=WeightClass.MEDIUM)
        self.assertGreater(
            calculate_mech_maintenance(medium),
            calculate_mech_maintenance(light),
        )

    def test_heavy_mech_cost(self):
        """Heavy mechs cost more than medium mechs."""
        medium = _make_mech(weight_class=WeightClass.MEDIUM)
        heavy = _make_mech(weight_class=WeightClass.HEAVY)
        self.assertGreater(
            calculate_mech_maintenance(heavy),
            calculate_mech_maintenance(medium),
        )

    def test_assault_mech_most_expensive(self):
        """Assault mechs have the highest maintenance cost."""
        heavy = _make_mech(weight_class=WeightClass.HEAVY)
        assault = _make_mech(weight_class=WeightClass.ASSAULT)
        self.assertGreater(
            calculate_mech_maintenance(assault),
            calculate_mech_maintenance(heavy),
        )

    def test_destroyed_mech_reduced_cost(self):
        """Destroyed mechs cost 50% of normal maintenance."""
        mech = _make_mech(weight_class=WeightClass.MEDIUM, status=MechStatus.DESTROYED)
        expected = MECH_MAINTENANCE_BASE[WeightClass.MEDIUM] // 2
        self.assertEqual(calculate_mech_maintenance(mech), expected)

    def test_damaged_mech_full_cost(self):
        """Damaged mechs still cost full maintenance."""
        mech_ready = _make_mech(weight_class=WeightClass.MEDIUM)
        mech_damaged = _make_mech(
            weight_class=WeightClass.MEDIUM,
            status=MechStatus.DAMAGED,
            armor_current=50,
        )
        self.assertEqual(
            calculate_mech_maintenance(mech_ready),
            calculate_mech_maintenance(mech_damaged),
        )

    def test_weight_class_ordering(self):
        """Maintenance costs should increase with weight class."""
        costs = []
        for wc in [WeightClass.LIGHT, WeightClass.MEDIUM, WeightClass.HEAVY, WeightClass.ASSAULT]:
            mech = _make_mech(weight_class=wc)
            costs.append(calculate_mech_maintenance(mech))
        self.assertEqual(costs, sorted(costs))


# ── Repair Cost Tests ────────────────────────────────────────────────

class TestRepairCost(unittest.TestCase):
    """Tests for calculate_repair_cost()."""

    def test_ready_mech_no_cost(self):
        """A ready mech has zero repair cost."""
        mech = _make_mech()
        self.assertEqual(calculate_repair_cost(mech), 0)

    def test_destroyed_mech_no_cost(self):
        """A destroyed mech cannot be field-repaired (zero cost)."""
        mech = _make_mech(status=MechStatus.DESTROYED, armor_current=0, structure_current=0)
        self.assertEqual(calculate_repair_cost(mech), 0)

    def test_armor_damage_only(self):
        """Repair cost for armor damage only."""
        mech = _make_mech(
            armor_current=100,
            armor_max=136,
            status=MechStatus.DAMAGED,
        )
        expected = (136 - 100) * REPAIR_COST_PER_ARMOR
        self.assertEqual(calculate_repair_cost(mech), expected)

    def test_structure_damage(self):
        """Repair cost includes structure damage at higher rate."""
        mech = _make_mech(
            armor_current=0,
            armor_max=136,
            structure_current=30,
            structure_max=48,
            status=MechStatus.DAMAGED,
        )
        armor_cost = 136 * REPAIR_COST_PER_ARMOR
        structure_cost = (48 - 30) * REPAIR_COST_PER_STRUCTURE
        self.assertEqual(calculate_repair_cost(mech), armor_cost + structure_cost)

    def test_structure_more_expensive_than_armor(self):
        """Structure repairs should cost more per point than armor."""
        self.assertGreater(REPAIR_COST_PER_STRUCTURE, REPAIR_COST_PER_ARMOR)

    def test_full_damage_cost(self):
        """Cost for fully stripped mech (0 armor, minimal structure)."""
        mech = _make_mech(
            armor_current=0,
            armor_max=136,
            structure_current=1,
            structure_max=48,
            status=MechStatus.DAMAGED,
        )
        expected = 136 * REPAIR_COST_PER_ARMOR + 47 * REPAIR_COST_PER_STRUCTURE
        self.assertEqual(calculate_repair_cost(mech), expected)


# ── Repair Mech Tests ────────────────────────────────────────────────

class TestRepairMech(unittest.TestCase):
    """Tests for repair_mech()."""

    def test_repairs_armor_to_max(self):
        """Repairing a mech restores armor to maximum."""
        mech = _make_mech(armor_current=50, status=MechStatus.DAMAGED)
        repair_mech(mech)
        self.assertEqual(mech.armor_current, mech.armor_max)

    def test_repairs_structure_to_max(self):
        """Repairing a mech restores structure to maximum."""
        mech = _make_mech(
            armor_current=0,
            structure_current=20,
            status=MechStatus.DAMAGED,
        )
        repair_mech(mech)
        self.assertEqual(mech.structure_current, mech.structure_max)

    def test_sets_status_to_ready(self):
        """Repairing a damaged mech sets status to READY."""
        mech = _make_mech(armor_current=50, status=MechStatus.DAMAGED)
        repair_mech(mech)
        self.assertEqual(mech.status, MechStatus.READY)

    def test_returns_cost(self):
        """repair_mech returns the cost of the repair."""
        mech = _make_mech(armor_current=100, armor_max=136, status=MechStatus.DAMAGED)
        cost = repair_mech(mech)
        self.assertEqual(cost, 36 * REPAIR_COST_PER_ARMOR)

    def test_ready_mech_no_change(self):
        """Repairing a ready mech does nothing and costs nothing."""
        mech = _make_mech()
        cost = repair_mech(mech)
        self.assertEqual(cost, 0)
        self.assertEqual(mech.status, MechStatus.READY)

    def test_destroyed_mech_no_change(self):
        """Repairing a destroyed mech does nothing and costs nothing."""
        mech = _make_mech(
            status=MechStatus.DESTROYED,
            armor_current=0,
            structure_current=0,
        )
        cost = repair_mech(mech)
        self.assertEqual(cost, 0)
        self.assertEqual(mech.status, MechStatus.DESTROYED)


# ── Monthly Upkeep Report Tests ──────────────────────────────────────

class TestMonthlyUpkeep(unittest.TestCase):
    """Tests for calculate_monthly_upkeep()."""

    def test_report_has_pilot_salaries(self):
        """Report includes salary lines for all non-KIA pilots."""
        company = _make_full_company()
        report = calculate_monthly_upkeep(company, 100_000)
        self.assertEqual(len(report.pilot_salaries), 4)

    def test_report_has_mech_maintenance(self):
        """Report includes maintenance lines for all mechs."""
        company = _make_full_company()
        report = calculate_monthly_upkeep(company, 100_000)
        self.assertEqual(len(report.mech_maintenance), 4)

    def test_report_contract_income(self):
        """Report records the contract income."""
        company = _make_full_company()
        report = calculate_monthly_upkeep(company, 150_000)
        self.assertEqual(report.contract_income, 150_000)

    def test_report_balance_before(self):
        """Report records the balance before upkeep."""
        company = _make_full_company()
        company.c_bills = 300_000
        report = calculate_monthly_upkeep(company, 100_000)
        self.assertEqual(report.balance_before, 300_000)

    def test_no_repairs_for_undamaged_lance(self):
        """No repair lines when all mechs are ready."""
        company = _make_full_company()
        report = calculate_monthly_upkeep(company, 100_000)
        self.assertEqual(len(report.repairs), 0)
        self.assertEqual(report.total_repairs, 0)

    def test_repairs_for_damaged_mechs(self):
        """Damaged mechs generate repair line items."""
        company = _make_full_company()
        company.mechs[0].armor_current = 50
        company.mechs[0].status = MechStatus.DAMAGED
        report = calculate_monthly_upkeep(company, 100_000)
        self.assertEqual(len(report.repairs), 1)
        self.assertGreater(report.repairs[0].cost, 0)

    def test_repairs_default_to_approved(self):
        """Repair lines default to repaired=True."""
        company = _make_full_company()
        company.mechs[0].armor_current = 50
        company.mechs[0].status = MechStatus.DAMAGED
        report = calculate_monthly_upkeep(company, 100_000)
        self.assertTrue(report.repairs[0].repaired)

    def test_net_change_positive(self):
        """Net change is positive when income exceeds expenses."""
        company = _make_full_company()
        report = calculate_monthly_upkeep(company, 1_000_000)
        self.assertGreater(report.net_change, 0)

    def test_net_change_negative(self):
        """Net change is negative when expenses exceed income."""
        company = _make_full_company()
        report = calculate_monthly_upkeep(company, 0)
        self.assertLess(report.net_change, 0)

    def test_total_expenses_sum(self):
        """Total expenses = salaries + maintenance + repairs."""
        company = _make_full_company()
        company.mechs[0].armor_current = 50
        company.mechs[0].status = MechStatus.DAMAGED
        report = calculate_monthly_upkeep(company, 100_000)
        expected = report.total_salaries + report.total_maintenance + report.total_repairs
        self.assertEqual(report.total_expenses, expected)

    def test_balance_after_correct(self):
        """Balance after = balance before + net change."""
        company = _make_full_company()
        report = calculate_monthly_upkeep(company, 200_000)
        self.assertEqual(
            report.balance_after,
            report.balance_before + report.net_change,
        )

    def test_kia_pilot_excluded_from_salaries(self):
        """KIA pilots don't appear in salary line items."""
        company = _make_full_company()
        company.mechwarriors[0].status = PilotStatus.KIA
        report = calculate_monthly_upkeep(company, 100_000)
        self.assertEqual(len(report.pilot_salaries), 3)

    def test_destroyed_mech_excluded_from_repairs(self):
        """Destroyed mechs have no repair line (cannot be field-repaired)."""
        company = _make_full_company()
        company.mechs[0].status = MechStatus.DESTROYED
        company.mechs[0].armor_current = 0
        company.mechs[0].structure_current = 0
        report = calculate_monthly_upkeep(company, 100_000)
        self.assertEqual(len(report.repairs), 0)

    def test_destroyed_mech_reduced_maintenance(self):
        """Destroyed mechs still show in maintenance at reduced cost."""
        company = _make_full_company()
        company.mechs[0].status = MechStatus.DESTROYED
        report = calculate_monthly_upkeep(company, 100_000)
        # The destroyed mech should have half maintenance
        destroyed_line = report.mech_maintenance[0]
        normal_cost = MECH_MAINTENANCE_BASE[WeightClass.MEDIUM]
        self.assertEqual(destroyed_line.cost, normal_cost // 2)


# ── Recalculate Totals Tests ─────────────────────────────────────────

class TestRecalculateTotals(unittest.TestCase):
    """Tests for _recalculate_totals()."""

    def test_toggle_repair_off_reduces_expenses(self):
        """Toggling a repair off reduces total expenses."""
        company = _make_full_company()
        company.mechs[0].armor_current = 50
        company.mechs[0].status = MechStatus.DAMAGED
        report = calculate_monthly_upkeep(company, 100_000)

        total_with_repair = report.total_expenses

        # Toggle repair off
        report.repairs[0].repaired = False
        _recalculate_totals(report)

        self.assertLess(report.total_expenses, total_with_repair)
        self.assertEqual(report.total_repairs, 0)

    def test_toggle_repair_on_increases_expenses(self):
        """Toggling a repair back on increases total expenses."""
        company = _make_full_company()
        company.mechs[0].armor_current = 50
        company.mechs[0].status = MechStatus.DAMAGED
        report = calculate_monthly_upkeep(company, 100_000)

        # Toggle off then on
        report.repairs[0].repaired = False
        _recalculate_totals(report)
        reduced = report.total_expenses

        report.repairs[0].repaired = True
        _recalculate_totals(report)
        self.assertGreater(report.total_expenses, reduced)

    def test_balance_after_updates_on_toggle(self):
        """Balance after updates when repair is toggled."""
        company = _make_full_company()
        company.mechs[0].armor_current = 50
        company.mechs[0].status = MechStatus.DAMAGED
        report = calculate_monthly_upkeep(company, 100_000)

        balance_with = report.balance_after

        report.repairs[0].repaired = False
        _recalculate_totals(report)

        self.assertGreater(report.balance_after, balance_with)


# ── Apply Upkeep Tests ───────────────────────────────────────────────

class TestApplyUpkeep(unittest.TestCase):
    """Tests for apply_upkeep()."""

    def test_balance_updated(self):
        """Company balance is set to balance_after."""
        company = _make_full_company()
        company.c_bills = 500_000
        report = calculate_monthly_upkeep(company, 200_000)
        apply_upkeep(company, report)
        self.assertEqual(company.c_bills, report.balance_after)

    def test_repaired_mech_restored(self):
        """Approved repair restores mech armor and structure to max."""
        company = _make_full_company()
        company.mechs[0].armor_current = 50
        company.mechs[0].structure_current = 30
        company.mechs[0].status = MechStatus.DAMAGED
        report = calculate_monthly_upkeep(company, 200_000)
        apply_upkeep(company, report)

        self.assertEqual(company.mechs[0].armor_current, company.mechs[0].armor_max)
        self.assertEqual(company.mechs[0].structure_current, company.mechs[0].structure_max)
        self.assertEqual(company.mechs[0].status, MechStatus.READY)

    def test_deferred_repair_stays_damaged(self):
        """Deferred repair leaves mech in DAMAGED state."""
        company = _make_full_company()
        company.mechs[0].armor_current = 50
        company.mechs[0].status = MechStatus.DAMAGED
        report = calculate_monthly_upkeep(company, 200_000)

        # Defer the repair
        report.repairs[0].repaired = False
        _recalculate_totals(report)
        apply_upkeep(company, report)

        self.assertEqual(company.mechs[0].armor_current, 50)
        self.assertEqual(company.mechs[0].status, MechStatus.DAMAGED)

    def test_deferred_repair_saves_money(self):
        """Deferring repair results in higher ending balance."""
        company1 = _make_full_company()
        company1.mechs[0].armor_current = 50
        company1.mechs[0].status = MechStatus.DAMAGED
        report1 = calculate_monthly_upkeep(company1, 100_000)
        apply_upkeep(company1, report1)

        company2 = _make_full_company()
        company2.mechs[0].armor_current = 50
        company2.mechs[0].status = MechStatus.DAMAGED
        report2 = calculate_monthly_upkeep(company2, 100_000)
        report2.repairs[0].repaired = False
        _recalculate_totals(report2)
        apply_upkeep(company2, report2)

        self.assertGreater(company2.c_bills, company1.c_bills)

    def test_multiple_repairs(self):
        """Multiple damaged mechs can be independently repaired."""
        company = _make_full_company()
        company.mechs[0].armor_current = 50
        company.mechs[0].status = MechStatus.DAMAGED
        company.mechs[1].armor_current = 80
        company.mechs[1].status = MechStatus.DAMAGED

        report = calculate_monthly_upkeep(company, 200_000)
        self.assertEqual(len(report.repairs), 2)

        # Repair first, defer second
        report.repairs[1].repaired = False
        _recalculate_totals(report)
        apply_upkeep(company, report)

        self.assertEqual(company.mechs[0].status, MechStatus.READY)
        self.assertEqual(company.mechs[1].status, MechStatus.DAMAGED)


# ── Bankruptcy Tests ─────────────────────────────────────────────────

class TestBankruptcy(unittest.TestCase):
    """Tests for is_bankrupt()."""

    def test_positive_balance_not_bankrupt(self):
        """Company with positive balance is not bankrupt."""
        company = _make_company(c_bills=100_000)
        self.assertFalse(is_bankrupt(company))

    def test_zero_balance_not_bankrupt(self):
        """Company with exactly zero balance is not bankrupt."""
        company = _make_company(c_bills=0)
        self.assertFalse(is_bankrupt(company))

    def test_negative_balance_is_bankrupt(self):
        """Company with negative balance is bankrupt."""
        company = _make_company(c_bills=-1)
        self.assertTrue(is_bankrupt(company))

    def test_deeply_negative_is_bankrupt(self):
        """Company deep in debt is bankrupt."""
        company = _make_company(c_bills=-500_000)
        self.assertTrue(is_bankrupt(company))

    def test_bankruptcy_after_expensive_month(self):
        """A company can go bankrupt after an expensive upkeep month."""
        company = _make_full_company()
        company.c_bills = 10_000  # Very low balance
        report = calculate_monthly_upkeep(company, 0)  # No contract income
        apply_upkeep(company, report)
        self.assertTrue(is_bankrupt(company))


# ── Edge Case Tests ──────────────────────────────────────────────────

class TestEdgeCases(unittest.TestCase):
    """Edge case tests for the financial system."""

    def test_empty_company(self):
        """A company with no mechs or pilots has zero upkeep."""
        company = _make_company()
        report = calculate_monthly_upkeep(company, 50_000)
        self.assertEqual(report.total_salaries, 0)
        self.assertEqual(report.total_maintenance, 0)
        self.assertEqual(report.total_repairs, 0)
        self.assertEqual(report.net_change, 50_000)

    def test_all_kia_pilots(self):
        """Company with all KIA pilots has zero salary costs."""
        company = _make_full_company()
        for mw in company.mechwarriors:
            mw.status = PilotStatus.KIA
        report = calculate_monthly_upkeep(company, 100_000)
        self.assertEqual(report.total_salaries, 0)
        self.assertEqual(len(report.pilot_salaries), 0)

    def test_all_mechs_destroyed(self):
        """Company with all destroyed mechs has reduced maintenance, no repairs."""
        company = _make_full_company()
        for mech in company.mechs:
            mech.status = MechStatus.DESTROYED
            mech.armor_current = 0
            mech.structure_current = 0
        report = calculate_monthly_upkeep(company, 100_000)
        self.assertEqual(len(report.repairs), 0)
        # Maintenance should be half of normal
        for mm in report.mech_maintenance:
            normal_cost = MECH_MAINTENANCE_BASE[WeightClass.MEDIUM]
            if mm.weight_class == "Light":
                normal_cost = MECH_MAINTENANCE_BASE[WeightClass.LIGHT]
            self.assertEqual(mm.cost, normal_cost // 2)

    def test_report_totals_consistency(self):
        """All report totals are internally consistent."""
        company = _make_full_company()
        company.mechs[0].armor_current = 50
        company.mechs[0].status = MechStatus.DAMAGED
        report = calculate_monthly_upkeep(company, 150_000)

        # Check salary total
        self.assertEqual(
            report.total_salaries,
            sum(ps.salary for ps in report.pilot_salaries),
        )
        # Check maintenance total
        self.assertEqual(
            report.total_maintenance,
            sum(mm.cost for mm in report.mech_maintenance),
        )
        # Check repair total
        self.assertEqual(
            report.total_repairs,
            sum(r.cost for r in report.repairs if r.repaired),
        )
        # Check expense total
        self.assertEqual(
            report.total_expenses,
            report.total_salaries + report.total_maintenance + report.total_repairs,
        )
        # Check net change
        self.assertEqual(
            report.net_change,
            report.contract_income - report.total_expenses,
        )
        # Check balance after
        self.assertEqual(
            report.balance_after,
            report.balance_before + report.net_change,
        )


# ── Salary Scaling Tests ─────────────────────────────────────────────

class TestSalaryScaling(unittest.TestCase):
    """Tests verifying that pilot salary properly scales with skill level."""

    def test_salary_ordering_by_total_skill(self):
        """Pilots with better combined skills cost more."""
        salaries = []
        for total_skill in [(1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6)]:
            pilot = _make_pilot(gunnery=total_skill[0], piloting=total_skill[1])
            salaries.append(calculate_pilot_salary(pilot))
        # Salaries should be in descending order (better pilots = more expensive)
        self.assertEqual(salaries, sorted(salaries, reverse=True))

    def test_gunnery_and_piloting_independently_affect_salary(self):
        """Gunnery and piloting each independently contribute to salary."""
        # Same total but different distribution
        pilot_a = _make_pilot(gunnery=1, piloting=6)
        pilot_b = _make_pilot(gunnery=6, piloting=1)
        # Both should have the same salary since total bonus is equal
        self.assertEqual(
            calculate_pilot_salary(pilot_a),
            calculate_pilot_salary(pilot_b),
        )


if __name__ == "__main__":
    unittest.main()
