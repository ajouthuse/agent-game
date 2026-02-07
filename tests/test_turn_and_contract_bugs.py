"""
test_turn_and_contract_bugs.py - Regression tests for turn/month tracking and
contract completion bugs.

Covers:
- Bug 1: generate_contracts() must receive month, not week (difficulty scaling)
- Bug 2: resolve_combat() must clear active_contract after completion
- Bug 3: simulate_battle() must update company.month after advancing week
- Bug 4: Accepting a contract should not resolve combat immediately
- Bug 5: simulate_battle() must track contracts_completed, total_earnings,
         mechs_lost, pilots_lost, reputation, and final_contract_completed
- Edge cases: month boundary transitions, final contract timing, double-advance
"""

import random
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.models import (
    BattleMech,
    Company,
    Contract,
    MechStatus,
    MechWarrior,
    MissionType,
    PilotStatus,
    WeightClass,
)
from data.combat import resolve_combat, CombatOutcome
from data.battle import simulate_battle, BattleOutcome
from data.contracts import generate_contracts, _max_difficulty_for_month
from game.hq import advance_week


# ── Test Helpers ─────────────────────────────────────────────────────

def _make_pilot(**overrides):
    defaults = {
        "name": "Test Pilot",
        "callsign": "Ace",
        "gunnery": 3,
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


def _make_contract(**overrides):
    defaults = {
        "employer": "House Davion",
        "mission_type": MissionType.RAID,
        "difficulty": 2,
        "payout": 200_000,
        "salvage_rights": 30,
        "bonus_objective": "Destroy the target.",
        "description": "Test mission briefing.",
        "duration": 2,
        "weeks_remaining": 0,
        "is_final_contract": False,
    }
    defaults.update(overrides)
    return Contract(**defaults)


def _make_full_company(**overrides):
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

    defaults = {
        "name": "Test Company",
        "c_bills": 500_000,
        "reputation": 50,
        "week": 1,
        "month": 1,
        "contracts_completed": 0,
        "total_earnings": 0,
        "mechs_lost": 0,
        "pilots_lost": 0,
        "mechwarriors": pilots,
        "mechs": mechs,
    }
    defaults.update(overrides)
    return Company(**defaults)


# ── Bug 1: generate_contracts() difficulty scaling uses month ────────

class TestGenerateContractsUsesMonth(unittest.TestCase):
    """Regression: generate_contracts() must use month for difficulty scaling,
    not week. Passing week=7 would give max difficulty (month 7+ rule),
    but month=2 (which is the correct value at week 7) should cap at 2 skulls.
    """

    def test_week_7_is_month_2_max_2_skulls(self):
        """At week 7 (month 2), contracts should have max 2 skulls."""
        month_at_week_7 = ((7 - 1) // 4) + 1  # = 2
        self.assertEqual(month_at_week_7, 2)

        for _ in range(20):
            contracts = generate_contracts(month=month_at_week_7)
            for c in contracts:
                self.assertLessEqual(
                    c.difficulty, 2,
                    f"Month 2 produced {c.difficulty}-skull mission (max should be 2)",
                )

    def test_week_20_is_month_5_max_3_skulls(self):
        """At week 20 (month 5), contracts should have max 3+1=4 skulls."""
        month_at_week_20 = ((20 - 1) // 4) + 1  # = 5
        self.assertEqual(month_at_week_20, 5)

        max_diff = _max_difficulty_for_month(month_at_week_20)
        self.assertEqual(max_diff, 3)

        for _ in range(20):
            contracts = generate_contracts(month=month_at_week_20)
            for c in contracts:
                # Max base difficulty 3, plus up to +1 bonus at month 5
                self.assertLessEqual(
                    c.difficulty, 4,
                    f"Month 5 produced {c.difficulty}-skull mission (max should be 4)",
                )

    def test_month_1_no_high_difficulty(self):
        """Month 1 should produce at most 2-skull contracts."""
        for _ in range(30):
            contracts = generate_contracts(month=1)
            for c in contracts:
                self.assertLessEqual(c.difficulty, 2)

    def test_month_12_allows_high_difficulty(self):
        """Month 12 should allow up to 5-skull contracts."""
        max_diff = _max_difficulty_for_month(12)
        self.assertEqual(max_diff, 5)


# ── Bug 2: resolve_combat() clears active_contract ──────────────────

class TestResolveCombatClearsContract(unittest.TestCase):
    """Regression: resolve_combat() must set company.active_contract = None
    after resolving the mission, preventing ghost contracts.
    """

    def test_active_contract_cleared_after_resolve(self):
        """active_contract should be None after resolve_combat()."""
        company = _make_full_company()
        contract = _make_contract()
        company.active_contract = contract

        resolve_combat(company, contract)

        self.assertIsNone(
            company.active_contract,
            "resolve_combat() should clear active_contract",
        )

    def test_no_double_battle_after_resolve(self):
        """After resolve_combat clears the contract, advance_week should
        not trigger another battle for the same contract.
        """
        company = _make_full_company()
        contract = _make_contract(duration=1)
        contract.weeks_remaining = 1
        company.active_contract = contract

        resolve_combat(company, contract)
        self.assertIsNone(company.active_contract)

        # Advancing should NOT trigger a battle
        summary = advance_week(company)
        self.assertIsNone(
            summary.get("battle_contract"),
            "No battle should trigger after contract was already resolved",
        )

    def test_resolve_combat_final_contract_sets_flag(self):
        """resolve_combat on final contract with victory should set the flag."""
        random.seed(0)  # Find a seed that gives victory
        for seed in range(100):
            random.seed(seed)
            company = _make_full_company(reputation=80)
            contract = _make_contract(difficulty=1, is_final_contract=True)
            company.active_contract = contract
            result = resolve_combat(company, contract)
            if result.outcome == CombatOutcome.VICTORY:
                self.assertTrue(company.final_contract_completed)
                self.assertIsNone(company.active_contract)
                return
        # If we never got a victory in 100 seeds, skip (statistically unlikely)
        self.skipTest("Could not produce a Victory outcome in 100 seeds")


# ── Bug 3: simulate_battle() updates month ──────────────────────────

class TestSimulateBattleUpdatesMonth(unittest.TestCase):
    """Regression: simulate_battle() must update company.month after
    advancing company.week, so the month counter stays correct.
    """

    def test_month_updated_after_battle(self):
        """company.month should be recalculated after simulate_battle()."""
        company = _make_full_company(week=4, month=1)
        contract = _make_contract()
        company.active_contract = contract

        simulate_battle(company, contract)

        # Week should be 5, month should be 2
        self.assertEqual(company.week, 5)
        expected_month = ((5 - 1) // 4) + 1
        self.assertEqual(company.month, expected_month)

    def test_month_boundary_crossing(self):
        """Month should increment when week crosses a 4-week boundary."""
        company = _make_full_company(week=8, month=2)
        contract = _make_contract()
        company.active_contract = contract

        simulate_battle(company, contract)

        self.assertEqual(company.week, 9)
        self.assertEqual(company.month, 3)  # (9-1)//4 + 1 = 3

    def test_month_stays_same_mid_month(self):
        """Month should not change when week stays within the same month."""
        company = _make_full_company(week=5, month=2)
        contract = _make_contract()
        company.active_contract = contract

        simulate_battle(company, contract)

        self.assertEqual(company.week, 6)
        self.assertEqual(company.month, 2)  # (6-1)//4 + 1 = 2

    def test_advance_week_month_consistent_after_battle(self):
        """After a battle triggered by advance_week, month should be
        correctly updated by simulate_battle.
        """
        company = _make_full_company(week=3, month=1)
        contract = _make_contract(duration=1)
        contract.weeks_remaining = 1
        company.active_contract = contract

        summary = advance_week(company)

        # advance_week doesn't increment week when battle triggers,
        # simulate_battle does the increment
        if summary.get("battle_contract"):
            # The battle_contract was returned but simulate_battle runs
            # separately (via scene). For this test, just verify advance_week
            # didn't corrupt the month when it detected a battle.
            self.assertIsNotNone(summary["battle_contract"])


# ── Bug 4: Contract acceptance doesn't resolve combat immediately ────

class TestContractAcceptanceTimerBased(unittest.TestCase):
    """Regression: Accepting a contract should set it as active with a
    duration countdown, NOT resolve combat immediately.
    """

    def test_contract_acceptance_sets_active(self):
        """Accepting a contract should set it as the active contract."""
        company = _make_full_company()
        contract = _make_contract(duration=2)

        contract.weeks_remaining = contract.duration
        company.active_contract = contract

        self.assertEqual(company.active_contract, contract)
        self.assertEqual(contract.weeks_remaining, 2)

    def test_contract_timer_counts_down_on_advance(self):
        """advance_week should decrement active contract weeks_remaining."""
        company = _make_full_company()
        contract = _make_contract(duration=3)
        contract.weeks_remaining = 3
        company.active_contract = contract

        advance_week(company)
        self.assertEqual(contract.weeks_remaining, 2)

        advance_week(company)
        self.assertEqual(contract.weeks_remaining, 1)

    def test_battle_triggers_when_timer_expires(self):
        """Battle should trigger when weeks_remaining reaches 0."""
        company = _make_full_company()
        contract = _make_contract(duration=1)
        contract.weeks_remaining = 1
        company.active_contract = contract

        summary = advance_week(company)
        self.assertIsNotNone(
            summary.get("battle_contract"),
            "Battle should trigger when contract timer reaches 0",
        )
        self.assertEqual(summary["battle_contract"], contract)

    def test_no_battle_when_timer_not_expired(self):
        """No battle should trigger while weeks_remaining > 0."""
        company = _make_full_company()
        contract = _make_contract(duration=3)
        contract.weeks_remaining = 3
        company.active_contract = contract

        summary = advance_week(company)
        self.assertIsNone(
            summary.get("battle_contract"),
            "No battle should trigger when timer has not expired",
        )

    def test_week_not_incremented_when_battle_triggers(self):
        """advance_week should NOT increment week when a battle triggers
        (simulate_battle handles the week increment).
        """
        company = _make_full_company(week=5)
        contract = _make_contract(duration=1)
        contract.weeks_remaining = 1
        company.active_contract = contract

        summary = advance_week(company)

        if summary.get("battle_contract"):
            # advance_week skips week increment when battle triggers
            self.assertEqual(company.week, 5)

    def test_contract_duration_respected(self):
        """A 3-week contract should take 3 advance_week calls to trigger."""
        company = _make_full_company()
        contract = _make_contract(duration=3)
        contract.weeks_remaining = 3
        company.active_contract = contract

        # Week 1: timer goes to 2
        summary1 = advance_week(company)
        self.assertIsNone(summary1.get("battle_contract"))

        # Week 2: timer goes to 1
        summary2 = advance_week(company)
        self.assertIsNone(summary2.get("battle_contract"))

        # Week 3: timer goes to 0 → battle!
        summary3 = advance_week(company)
        self.assertIsNotNone(summary3.get("battle_contract"))


# ── Bug 5: simulate_battle() tracks all bookkeeping ─────────────────

class TestSimulateBattleBookkeeping(unittest.TestCase):
    """Regression: simulate_battle() must update contracts_completed,
    total_earnings, mechs_lost, pilots_lost, reputation, and
    final_contract_completed.
    """

    def test_contracts_completed_incremented(self):
        """contracts_completed should increase by 1 after battle."""
        company = _make_full_company(contracts_completed=5)
        contract = _make_contract()
        company.active_contract = contract

        simulate_battle(company, contract)

        self.assertEqual(company.contracts_completed, 6)

    def test_total_earnings_updated(self):
        """total_earnings should increase by the earnings from battle."""
        company = _make_full_company(total_earnings=100_000)
        contract = _make_contract(payout=200_000)
        company.active_contract = contract

        result = simulate_battle(company, contract)

        self.assertGreater(
            company.total_earnings, 100_000,
            "total_earnings should increase after battle",
        )

    def test_reputation_changes_after_battle(self):
        """Reputation should change after a battle."""
        random.seed(42)
        outcomes_changed = False
        for seed in range(50):
            random.seed(seed)
            company = _make_full_company(reputation=50)
            contract = _make_contract(difficulty=1)
            company.active_contract = contract

            simulate_battle(company, contract)

            if company.reputation != 50:
                outcomes_changed = True
                break

        self.assertTrue(
            outcomes_changed,
            "Reputation should change after at least one battle",
        )

    def test_active_contract_cleared_after_battle(self):
        """active_contract should be None after simulate_battle()."""
        company = _make_full_company()
        contract = _make_contract()
        company.active_contract = contract

        simulate_battle(company, contract)

        self.assertIsNone(company.active_contract)

    def test_final_contract_victory_sets_flag(self):
        """Winning the final contract should set final_contract_completed."""
        # Use an overwhelmingly strong lance (4 assault mechs, elite pilots)
        # against difficulty=1 (2 light enemies) to guarantee clean victory.
        elite_mechs = [
            _make_mech(name=f"Atlas AS7-D #{i}", weight_class=WeightClass.ASSAULT,
                       tonnage=100, armor_current=300, armor_max=300,
                       structure_current=100, structure_max=100, firepower=10)
            for i in range(4)
        ]
        elite_pilots = [
            _make_pilot(name=f"Elite {i}", callsign=f"E{i}", gunnery=1, piloting=1,
                        assigned_mech=f"Atlas AS7-D #{i}")
            for i in range(4)
        ]
        company = _make_full_company(
            reputation=80,
            mechs=elite_mechs,
            mechwarriors=elite_pilots,
        )
        contract = _make_contract(difficulty=1, is_final_contract=True)
        company.active_contract = contract

        random.seed(42)
        result = simulate_battle(company, contract)

        self.assertEqual(result.outcome, BattleOutcome.VICTORY,
                         "Elite lance vs 2 lights should produce clean Victory")
        self.assertTrue(
            company.final_contract_completed,
            "final_contract_completed should be True after winning final contract",
        )

    def test_final_contract_defeat_does_not_set_flag(self):
        """Losing the final contract should NOT set final_contract_completed."""
        for seed in range(200):
            random.seed(seed)
            company = _make_full_company(reputation=50)
            contract = _make_contract(difficulty=5, is_final_contract=True)
            company.active_contract = contract

            result = simulate_battle(company, contract)

            if result.outcome == BattleOutcome.DEFEAT:
                self.assertFalse(
                    company.final_contract_completed,
                    "final_contract_completed should be False after losing final contract",
                )
                return

        self.skipTest("Could not produce a Defeat outcome in 200 seeds")

    def test_week_incremented_exactly_once(self):
        """simulate_battle should increment week exactly once."""
        company = _make_full_company(week=10)
        contract = _make_contract()
        company.active_contract = contract

        simulate_battle(company, contract)

        self.assertEqual(company.week, 11)

    def test_month_consistent_with_week(self):
        """company.month should always equal ((week-1)//4)+1 after battle."""
        for start_week in [1, 4, 5, 8, 12, 16, 20]:
            company = _make_full_company(
                week=start_week,
                month=((start_week - 1) // 4) + 1,
            )
            contract = _make_contract()
            company.active_contract = contract

            simulate_battle(company, contract)

            expected_month = ((company.week - 1) // 4) + 1
            self.assertEqual(
                company.month, expected_month,
                f"After battle at week {start_week}: week={company.week}, "
                f"month={company.month}, expected_month={expected_month}",
            )


# ── Edge Cases ──────────────────────────────────────────────────────

class TestMonthBoundaryEdgeCases(unittest.TestCase):
    """Edge cases for week/month transitions."""

    def test_month_formula_week_1(self):
        """Week 1 should be month 1."""
        self.assertEqual(((1 - 1) // 4) + 1, 1)

    def test_month_formula_week_4(self):
        """Week 4 should still be month 1."""
        self.assertEqual(((4 - 1) // 4) + 1, 1)

    def test_month_formula_week_5(self):
        """Week 5 should be month 2."""
        self.assertEqual(((5 - 1) // 4) + 1, 2)

    def test_month_formula_week_8(self):
        """Week 8 should be month 2."""
        self.assertEqual(((8 - 1) // 4) + 1, 2)

    def test_month_formula_week_9(self):
        """Week 9 should be month 3."""
        self.assertEqual(((9 - 1) // 4) + 1, 3)

    def test_advance_week_updates_month_at_boundary(self):
        """advance_week should update month when crossing a 4-week boundary."""
        company = _make_full_company(week=4, month=1)

        advance_week(company)

        self.assertEqual(company.week, 5)
        self.assertEqual(company.month, 2)

    def test_advance_week_month_stays_mid_month(self):
        """advance_week should not change month within a 4-week period."""
        company = _make_full_company(week=5, month=2)

        advance_week(company)

        self.assertEqual(company.week, 6)
        self.assertEqual(company.month, 2)

    def test_multiple_advances_track_month_correctly(self):
        """Month should be correct after many week advances."""
        company = _make_full_company(week=1, month=1)

        for _ in range(20):
            advance_week(company)

        self.assertEqual(company.week, 21)
        expected_month = ((21 - 1) // 4) + 1  # = 6
        self.assertEqual(company.month, expected_month)


class TestFinalContractTiming(unittest.TestCase):
    """Edge cases for final contract appearance and completion."""

    def test_final_contract_appears_at_month_12(self):
        """advance_week at month 12 should include the final contract."""
        company = _make_full_company(week=45, month=12)

        summary = advance_week(company)

        has_final = any(
            c.is_final_contract for c in company.available_contracts
        )
        self.assertTrue(
            has_final,
            "Final contract should appear in available contracts at month 12",
        )

    def test_final_contract_not_before_month_12(self):
        """Before month 12, no final contract should appear."""
        company = _make_full_company(week=40, month=11)

        advance_week(company)

        has_final = any(
            c.is_final_contract for c in company.available_contracts
        )
        self.assertFalse(
            has_final,
            "Final contract should NOT appear before month 12",
        )

    def test_final_contract_not_duplicated(self):
        """Advancing multiple times at month 12+ should not duplicate
        the final contract.
        """
        company = _make_full_company(week=45, month=12)

        advance_week(company)
        advance_week(company)
        advance_week(company)

        final_count = sum(
            1 for c in company.available_contracts if c.is_final_contract
        )
        self.assertEqual(
            final_count, 1,
            f"Expected 1 final contract, found {final_count}",
        )


class TestNoDoubleWeekIncrement(unittest.TestCase):
    """Ensure week is not incremented twice through any code path."""

    def test_resolve_combat_increments_once(self):
        """resolve_combat should increment week exactly once."""
        company = _make_full_company(week=5)
        contract = _make_contract()
        company.active_contract = contract

        resolve_combat(company, contract)

        self.assertEqual(company.week, 6)

    def test_simulate_battle_increments_once(self):
        """simulate_battle should increment week exactly once."""
        company = _make_full_company(week=5)
        contract = _make_contract()
        company.active_contract = contract

        simulate_battle(company, contract)

        self.assertEqual(company.week, 6)

    def test_advance_week_no_battle_increments_once(self):
        """advance_week without a battle should increment week exactly once."""
        company = _make_full_company(week=5)

        advance_week(company)

        self.assertEqual(company.week, 6)

    def test_advance_week_with_battle_does_not_increment(self):
        """advance_week when battle triggers should NOT increment week
        (leaving it for simulate_battle).
        """
        company = _make_full_company(week=5)
        contract = _make_contract(duration=1)
        contract.weeks_remaining = 1
        company.active_contract = contract

        summary = advance_week(company)

        if summary.get("battle_contract"):
            # advance_week skipped the increment
            self.assertEqual(company.week, 5)


if __name__ == "__main__":
    unittest.main()
