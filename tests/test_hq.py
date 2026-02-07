"""
test_hq.py - Unit tests for the HQ dashboard and turn cycle system.

Tests cover:
- Weekly advance turn cycle (week counter, payroll deduction, summaries)
- Payroll calculation (5,000 C-Bills per active MechWarrior)
- Status text generation (contextual info for status bar)
- Game-over trigger after advance when C-Bills go negative
- Edge cases (no pilots, all KIA, empty company)
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
from game.hq import (
    advance_week,
    get_status_text,
    WEEKLY_PAYROLL_PER_PILOT,
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
        _make_mech(name="Wolverine WVR-6R"),
        _make_mech(name="Shadow Hawk SHD-2H"),
        _make_mech(name="Hunchback HBK-4G"),
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


# ── Weekly Payroll Constant Tests ───────────────────────────────────

class TestPayrollConstant(unittest.TestCase):
    """Tests for the weekly payroll constant."""

    def test_payroll_is_5000(self):
        """Weekly payroll per pilot should be 5,000 C-Bills as specified."""
        self.assertEqual(WEEKLY_PAYROLL_PER_PILOT, 5_000)


# ── Advance Week Tests ──────────────────────────────────────────────

class TestAdvanceWeek(unittest.TestCase):
    """Tests for the advance_week() turn cycle function."""

    def test_week_counter_increments(self):
        """Advancing a week increments the company week counter by 1."""
        company = _make_full_company()
        self.assertEqual(company.week, 1)
        advance_week(company)
        self.assertEqual(company.week, 2)

    def test_week_counter_increments_multiple(self):
        """Multiple advances increment week counter correctly."""
        company = _make_full_company()
        for i in range(5):
            advance_week(company)
        self.assertEqual(company.week, 6)

    def test_payroll_deducted_for_active_pilots(self):
        """Active pilots cost 5,000 C-Bills each per week."""
        company = _make_full_company()
        initial_balance = company.c_bills
        summary = advance_week(company)
        expected_payroll = 4 * WEEKLY_PAYROLL_PER_PILOT
        self.assertEqual(summary["payroll_cost"], expected_payroll)
        self.assertEqual(company.c_bills, initial_balance - expected_payroll)

    def test_kia_pilots_not_charged(self):
        """KIA pilots should not be charged payroll."""
        company = _make_full_company()
        company.mechwarriors[0].status = PilotStatus.KIA
        company.mechwarriors[1].status = PilotStatus.KIA
        initial_balance = company.c_bills
        summary = advance_week(company)
        expected_payroll = 2 * WEEKLY_PAYROLL_PER_PILOT  # Only 2 active
        self.assertEqual(summary["payroll_cost"], expected_payroll)
        self.assertEqual(company.c_bills, initial_balance - expected_payroll)
        self.assertEqual(summary["active_pilots"], 2)

    def test_injured_pilots_still_charged(self):
        """Injured pilots still cost payroll (they're not KIA)."""
        company = _make_full_company()
        company.mechwarriors[0].status = PilotStatus.INJURED
        initial_balance = company.c_bills
        summary = advance_week(company)
        expected_payroll = 4 * WEEKLY_PAYROLL_PER_PILOT
        self.assertEqual(summary["payroll_cost"], expected_payroll)
        self.assertEqual(company.c_bills, initial_balance - expected_payroll)

    def test_no_pilots_no_payroll(self):
        """A company with no pilots has zero payroll."""
        company = _make_company()
        initial_balance = company.c_bills
        summary = advance_week(company)
        self.assertEqual(summary["payroll_cost"], 0)
        self.assertEqual(summary["active_pilots"], 0)
        self.assertEqual(company.c_bills, initial_balance)

    def test_summary_contains_week_before_and_after(self):
        """Summary reports week_before and week_after correctly."""
        company = _make_full_company()
        company.week = 10
        summary = advance_week(company)
        self.assertEqual(summary["week_before"], 10)
        self.assertEqual(summary["week_after"], 11)

    def test_summary_contains_balance_before_and_after(self):
        """Summary reports balance_before and balance_after correctly."""
        company = _make_full_company()
        company.c_bills = 100_000
        summary = advance_week(company)
        self.assertEqual(summary["balance_before"], 100_000)
        self.assertEqual(
            summary["balance_after"],
            100_000 - 4 * WEEKLY_PAYROLL_PER_PILOT,
        )

    def test_damaged_mechs_tracked_in_summary(self):
        """Damaged mechs are listed in the repairs_progressed summary."""
        company = _make_full_company()
        company.mechs[0].status = MechStatus.DAMAGED
        company.mechs[2].status = MechStatus.DAMAGED
        summary = advance_week(company)
        self.assertEqual(len(summary["repairs_progressed"]), 2)
        self.assertIn("Wolverine WVR-6R", summary["repairs_progressed"])
        self.assertIn("Hunchback HBK-4G", summary["repairs_progressed"])

    def test_status_changes_for_damaged_mechs(self):
        """Status changes list includes notes about damaged mechs."""
        company = _make_full_company()
        company.mechs[0].status = MechStatus.DAMAGED
        summary = advance_week(company)
        self.assertEqual(len(summary["status_changes"]), 1)
        self.assertIn("Wolverine WVR-6R", summary["status_changes"][0])

    def test_no_damaged_mechs_empty_status_changes(self):
        """No status changes when all mechs are ready."""
        company = _make_full_company()
        summary = advance_week(company)
        self.assertEqual(len(summary["status_changes"]), 0)
        self.assertEqual(len(summary["repairs_progressed"]), 0)

    def test_balance_can_go_negative(self):
        """Advancing a week can push balance below zero (bankruptcy)."""
        company = _make_full_company()
        company.c_bills = 10_000  # Very low balance
        summary = advance_week(company)
        self.assertLess(company.c_bills, 0)
        self.assertLess(summary["balance_after"], 0)

    def test_all_kia_no_payroll(self):
        """Company with all KIA pilots has zero payroll."""
        company = _make_full_company()
        for mw in company.mechwarriors:
            mw.status = PilotStatus.KIA
        summary = advance_week(company)
        self.assertEqual(summary["payroll_cost"], 0)
        self.assertEqual(summary["active_pilots"], 0)


# ── Game Over Condition Tests ───────────────────────────────────────

class TestGameOverCondition(unittest.TestCase):
    """Tests for game-over condition after advance."""

    def test_negative_balance_triggers_bankruptcy(self):
        """Company with negative balance after advance should be bankrupt."""
        from data.finance import is_bankrupt
        company = _make_full_company()
        company.c_bills = 5_000  # Will go negative after payroll
        advance_week(company)
        self.assertTrue(is_bankrupt(company))

    def test_positive_balance_not_bankrupt(self):
        """Company with positive balance after advance is fine."""
        from data.finance import is_bankrupt
        company = _make_full_company()
        company.c_bills = 500_000
        advance_week(company)
        self.assertFalse(is_bankrupt(company))

    def test_zero_balance_not_bankrupt(self):
        """Exactly zero balance is not bankruptcy."""
        from data.finance import is_bankrupt
        company = _make_company(c_bills=0)  # No pilots = no payroll
        advance_week(company)
        self.assertFalse(is_bankrupt(company))


# ── Status Text Tests ───────────────────────────────────────────────

class TestStatusText(unittest.TestCase):
    """Tests for get_status_text() contextual status bar."""

    def test_all_operational_status(self):
        """Status text shows 'All mechs operational' when no damage."""
        company = _make_full_company()
        status = get_status_text(company)
        self.assertIn("All mechs operational", status)
        self.assertIn("STATUS:", status)

    def test_damaged_mech_shown(self):
        """Status text shows damaged mech count."""
        company = _make_full_company()
        company.mechs[0].status = MechStatus.DAMAGED
        status = get_status_text(company)
        self.assertIn("1 mech(s) damaged", status)

    def test_destroyed_mech_shown(self):
        """Status text shows destroyed mech count."""
        company = _make_full_company()
        company.mechs[0].status = MechStatus.DESTROYED
        status = get_status_text(company)
        self.assertIn("1 mech(s) destroyed", status)

    def test_injured_pilot_shown(self):
        """Status text shows injured pilot count."""
        company = _make_full_company()
        company.mechwarriors[0].status = PilotStatus.INJURED
        status = get_status_text(company)
        self.assertIn("1 pilot(s) injured", status)

    def test_kia_pilot_shown(self):
        """Status text shows KIA pilot count."""
        company = _make_full_company()
        company.mechwarriors[0].status = PilotStatus.KIA
        status = get_status_text(company)
        self.assertIn("1 pilot(s) KIA", status)

    def test_no_active_contract(self):
        """Status text shows 'No active contract' by default."""
        company = _make_full_company()
        status = get_status_text(company)
        self.assertIn("No active contract", status)

    def test_multiple_damaged_mechs(self):
        """Status text correctly counts multiple damaged mechs."""
        company = _make_full_company()
        company.mechs[0].status = MechStatus.DAMAGED
        company.mechs[1].status = MechStatus.DAMAGED
        company.mechs[2].status = MechStatus.DESTROYED
        status = get_status_text(company)
        self.assertIn("2 mech(s) damaged", status)
        self.assertIn("1 mech(s) destroyed", status)


# ── Advance Week Consistency Tests ──────────────────────────────────

class TestAdvanceWeekConsistency(unittest.TestCase):
    """Tests for internal consistency of the advance_week summary."""

    def test_balance_after_equals_company_balance(self):
        """Summary balance_after matches actual company c_bills."""
        company = _make_full_company()
        summary = advance_week(company)
        self.assertEqual(summary["balance_after"], company.c_bills)

    def test_payroll_equals_active_pilots_times_rate(self):
        """Payroll cost equals active_pilots * WEEKLY_PAYROLL_PER_PILOT."""
        company = _make_full_company()
        company.mechwarriors[0].status = PilotStatus.KIA
        summary = advance_week(company)
        expected = summary["active_pilots"] * WEEKLY_PAYROLL_PER_PILOT
        self.assertEqual(summary["payroll_cost"], expected)

    def test_balance_arithmetic(self):
        """balance_after = balance_before - payroll_cost."""
        company = _make_full_company()
        summary = advance_week(company)
        self.assertEqual(
            summary["balance_after"],
            summary["balance_before"] - summary["payroll_cost"],
        )


if __name__ == "__main__":
    unittest.main()
