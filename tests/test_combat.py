"""
tests.test_combat - Tests for the auto-resolved combat system.

Covers:
- Lance power calculation from mech stats and pilot skills
- Success probability scaling (strong lance vs weak, easy vs hard)
- Combat outcome determination (Victory, Pyrrhic Victory, Defeat)
- Narrative combat event generation with correct pilot/mech references
- Damage application to mechs and pilot injuries
- Rewards calculation (C-Bills, XP) based on outcome
- Full combat resolution integration
- Mech destruction and status tracking
"""

import random
import unittest

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
from data.combat import (
    CombatOutcome,
    MechDamageReport,
    MissionResult,
    PilotInjuryReport,
    apply_damage,
    calculate_lance_power,
    calculate_rewards,
    calculate_success_chance,
    generate_combat_events,
    resolve_combat,
    _determine_outcome,
    _difficulty_rating,
    _get_deployed_pairs,
)
from data.mechs import create_starting_lance, create_starting_pilots


# ── Test Helpers ──────────────────────────────────────────────────────────

def _make_company(name="Test Company"):
    """Create a standard test company with starting lance and pilots."""
    mechs = create_starting_lance()
    pilots = create_starting_pilots()
    for pilot, mech in zip(pilots, mechs):
        pilot.assigned_mech = mech.name
    return Company(name=name, mechwarriors=pilots, mechs=mechs)


def _make_contract(difficulty=2, payout=200_000, mission_type=MissionType.RAID):
    """Create a standard test contract."""
    return Contract(
        employer="House Davion",
        mission_type=mission_type,
        difficulty=difficulty,
        payout=payout,
        salvage_rights=30,
        bonus_objective="Destroy the target.",
        description="Test mission briefing.",
    )


def _make_mech(name="TestMech", firepower=6, armor_max=120, structure_max=44):
    """Create a simple test mech."""
    return BattleMech(
        name=name,
        weight_class=WeightClass.MEDIUM,
        tonnage=50,
        armor_current=armor_max,
        armor_max=armor_max,
        structure_current=structure_max,
        structure_max=structure_max,
        firepower=firepower,
        speed=5,
    )


def _make_pilot(callsign="TestPilot", gunnery=3, piloting=4, assigned_mech=None):
    """Create a simple test pilot."""
    return MechWarrior(
        name="Test Warrior",
        callsign=callsign,
        gunnery=gunnery,
        piloting=piloting,
        assigned_mech=assigned_mech,
    )


# ── CombatOutcome Tests ──────────────────────────────────────────────────

class TestCombatOutcome(unittest.TestCase):
    """Tests for the CombatOutcome enumeration."""

    def test_victory_value(self):
        self.assertEqual(CombatOutcome.VICTORY.value, "Victory")

    def test_pyrrhic_victory_value(self):
        self.assertEqual(CombatOutcome.PYRRHIC_VICTORY.value, "Pyrrhic Victory")

    def test_defeat_value(self):
        self.assertEqual(CombatOutcome.DEFEAT.value, "Defeat")

    def test_all_outcomes_exist(self):
        outcomes = [o.value for o in CombatOutcome]
        self.assertIn("Victory", outcomes)
        self.assertIn("Pyrrhic Victory", outcomes)
        self.assertIn("Defeat", outcomes)
        self.assertEqual(len(outcomes), 3)


# ── Lance Power Calculation Tests ────────────────────────────────────────

class TestLancePowerCalculation(unittest.TestCase):
    """Tests for calculate_lance_power()."""

    def test_starting_lance_has_positive_power(self):
        company = _make_company()
        power = calculate_lance_power(company)
        self.assertGreater(power, 0)

    def test_starting_lance_power_in_reasonable_range(self):
        """A fresh starting lance should have power roughly around 200."""
        company = _make_company()
        power = calculate_lance_power(company)
        self.assertGreater(power, 100)
        self.assertLess(power, 400)

    def test_higher_firepower_means_more_power(self):
        """A mech with higher firepower should contribute more power."""
        mech1 = _make_mech("Weak", firepower=3)
        mech2 = _make_mech("Strong", firepower=9)
        pilot1 = _make_pilot("P1", assigned_mech="Weak")
        pilot2 = _make_pilot("P2", assigned_mech="Strong")

        co1 = Company(name="Weak Co", mechwarriors=[pilot1], mechs=[mech1])
        co2 = Company(name="Strong Co", mechwarriors=[pilot2], mechs=[mech2])

        self.assertGreater(calculate_lance_power(co2), calculate_lance_power(co1))

    def test_better_gunnery_means_more_power(self):
        """Lower gunnery (better skill) should give more power."""
        mech1 = _make_mech("M1")
        mech2 = _make_mech("M2")
        pilot_bad = _make_pilot("Bad", gunnery=6, assigned_mech="M1")
        pilot_good = _make_pilot("Good", gunnery=1, assigned_mech="M2")

        co1 = Company(name="Bad", mechwarriors=[pilot_bad], mechs=[mech1])
        co2 = Company(name="Good", mechwarriors=[pilot_good], mechs=[mech2])

        self.assertGreater(calculate_lance_power(co2), calculate_lance_power(co1))

    def test_damaged_armor_reduces_power(self):
        """A mech with reduced armor should contribute less power."""
        mech_full = _make_mech("Full")
        mech_dmg = _make_mech("Damaged")
        mech_dmg.armor_current = mech_dmg.armor_max // 2

        pilot1 = _make_pilot("P1", assigned_mech="Full")
        pilot2 = _make_pilot("P2", assigned_mech="Damaged")

        co1 = Company(name="Full", mechwarriors=[pilot1], mechs=[mech_full])
        co2 = Company(name="Dmg", mechwarriors=[pilot2], mechs=[mech_dmg])

        self.assertGreater(calculate_lance_power(co1), calculate_lance_power(co2))

    def test_destroyed_mechs_not_counted(self):
        """Destroyed mechs should not contribute to lance power."""
        company = _make_company()
        power_before = calculate_lance_power(company)

        company.mechs[0].status = MechStatus.DESTROYED
        power_after = calculate_lance_power(company)

        self.assertLess(power_after, power_before)

    def test_kia_pilots_not_counted(self):
        """KIA pilots should not contribute to lance power."""
        company = _make_company()
        power_before = calculate_lance_power(company)

        company.mechwarriors[0].status = PilotStatus.KIA
        power_after = calculate_lance_power(company)

        self.assertLess(power_after, power_before)

    def test_injured_pilot_reduces_power(self):
        """Injured pilots should fight less effectively."""
        company = _make_company()
        power_healthy = calculate_lance_power(company)

        company.mechwarriors[0].status = PilotStatus.INJURED
        company.mechwarriors[0].injuries = 1
        power_injured = calculate_lance_power(company)

        self.assertLess(power_injured, power_healthy)

    def test_empty_company_has_zero_power(self):
        """A company with no mechs/pilots should have zero power."""
        company = Company(name="Empty")
        self.assertEqual(calculate_lance_power(company), 0.0)

    def test_morale_affects_power(self):
        """Higher morale should give more power."""
        mech1 = _make_mech("M1")
        mech2 = _make_mech("M2")
        pilot_low = _make_pilot("Low", assigned_mech="M1")
        pilot_low.morale = 10
        pilot_high = _make_pilot("High", assigned_mech="M2")
        pilot_high.morale = 100

        co1 = Company(name="Low", mechwarriors=[pilot_low], mechs=[mech1])
        co2 = Company(name="High", mechwarriors=[pilot_high], mechs=[mech2])

        self.assertGreater(calculate_lance_power(co2), calculate_lance_power(co1))


# ── Success Probability Tests ────────────────────────────────────────────

class TestSuccessChance(unittest.TestCase):
    """Tests for calculate_success_chance()."""

    def test_strong_lance_vs_easy_mission_high_chance(self):
        """A strong lance vs 1-skull should have high success chance."""
        chance = calculate_success_chance(300.0, 1)
        self.assertGreater(chance, 0.80)

    def test_weak_lance_vs_hard_mission_low_chance(self):
        """A weak lance vs 5-skull should have low success chance."""
        chance = calculate_success_chance(80.0, 5)
        self.assertLess(chance, 0.25)

    def test_chance_clamped_at_minimum(self):
        """Success chance should never go below 0.05."""
        chance = calculate_success_chance(1.0, 5)
        self.assertGreaterEqual(chance, 0.05)

    def test_chance_clamped_at_maximum(self):
        """Success chance should never exceed 0.95."""
        chance = calculate_success_chance(10000.0, 1)
        self.assertLessEqual(chance, 0.95)

    def test_higher_power_means_higher_chance(self):
        """More lance power should yield higher success chance."""
        chance_low = calculate_success_chance(100.0, 3)
        chance_high = calculate_success_chance(300.0, 3)
        self.assertGreater(chance_high, chance_low)

    def test_higher_difficulty_means_lower_chance(self):
        """Higher difficulty should yield lower success chance."""
        chance_easy = calculate_success_chance(200.0, 1)
        chance_hard = calculate_success_chance(200.0, 5)
        self.assertGreater(chance_easy, chance_hard)

    def test_chance_returns_float(self):
        chance = calculate_success_chance(200.0, 3)
        self.assertIsInstance(chance, float)


# ── Difficulty Rating Tests ──────────────────────────────────────────────

class TestDifficultyRating(unittest.TestCase):
    """Tests for _difficulty_rating()."""

    def test_all_difficulties_have_rating(self):
        for diff in range(1, 6):
            rating = _difficulty_rating(diff)
            self.assertGreater(rating, 0)

    def test_higher_difficulty_higher_rating(self):
        for diff in range(1, 5):
            self.assertLess(_difficulty_rating(diff), _difficulty_rating(diff + 1))

    def test_unknown_difficulty_returns_default(self):
        rating = _difficulty_rating(99)
        self.assertGreater(rating, 0)


# ── Outcome Determination Tests ──────────────────────────────────────────

class TestOutcomeDetermination(unittest.TestCase):
    """Tests for _determine_outcome()."""

    def test_returns_combat_outcome(self):
        result = _determine_outcome(0.5)
        self.assertIsInstance(result, CombatOutcome)

    def test_high_chance_favors_victory(self):
        """With very high success chance, victory should dominate."""
        random.seed(42)
        outcomes = [_determine_outcome(0.95) for _ in range(100)]
        victories = sum(1 for o in outcomes if o == CombatOutcome.VICTORY)
        self.assertGreater(victories, 40)

    def test_low_chance_favors_defeat(self):
        """With very low success chance, defeat should dominate."""
        random.seed(42)
        outcomes = [_determine_outcome(0.10) for _ in range(100)]
        defeats = sum(1 for o in outcomes if o == CombatOutcome.DEFEAT)
        self.assertGreater(defeats, 60)

    def test_all_outcomes_possible(self):
        """All three outcomes should be reachable with moderate chance."""
        random.seed(42)
        outcomes = set()
        for _ in range(200):
            outcomes.add(_determine_outcome(0.5))
        self.assertEqual(len(outcomes), 3)


# ── Combat Event Generation Tests ────────────────────────────────────────

class TestCombatEventGeneration(unittest.TestCase):
    """Tests for generate_combat_events()."""

    def test_generates_events(self):
        company = _make_company()
        events = generate_combat_events(company, CombatOutcome.VICTORY)
        self.assertGreater(len(events), 0)

    def test_generates_4_to_6_events_plus_closing(self):
        """Should generate 4-6 narrative events plus an opening and closing."""
        random.seed(42)
        company = _make_company()
        events = generate_combat_events(company, CombatOutcome.VICTORY)
        # Total = 1 opener + (num_events-1) middle + 1 closing = num_events + 1
        # num_events is 4-6, so total is 5-7
        self.assertGreaterEqual(len(events), 5)
        self.assertLessEqual(len(events), 7)

    def test_events_reference_pilot_callsigns(self):
        """Events should mention actual pilot callsigns from the company."""
        random.seed(42)
        company = _make_company()
        callsigns = {mw.callsign for mw in company.mechwarriors}
        events = generate_combat_events(company, CombatOutcome.VICTORY)

        all_text = " ".join(events)
        found_callsigns = sum(1 for cs in callsigns if cs in all_text)
        self.assertGreater(found_callsigns, 0)

    def test_events_reference_mech_names(self):
        """Events should mention actual mech names from the company."""
        random.seed(42)
        company = _make_company()
        mech_names = {m.name for m in company.mechs}
        events = generate_combat_events(company, CombatOutcome.VICTORY)

        all_text = " ".join(events)
        found_mechs = sum(1 for mn in mech_names if mn in all_text)
        self.assertGreater(found_mechs, 0)

    def test_victory_events_end_with_victory(self):
        company = _make_company()
        events = generate_combat_events(company, CombatOutcome.VICTORY)
        self.assertIn("Victory", events[-1])

    def test_pyrrhic_events_end_with_pyrrhic(self):
        company = _make_company()
        events = generate_combat_events(company, CombatOutcome.PYRRHIC_VICTORY)
        self.assertIn("Pyrrhic Victory", events[-1])

    def test_defeat_events_end_with_defeat(self):
        company = _make_company()
        events = generate_combat_events(company, CombatOutcome.DEFEAT)
        self.assertIn("Defeat", events[-1])

    def test_specific_event_count(self):
        company = _make_company()
        events = generate_combat_events(company, CombatOutcome.VICTORY, num_events=5)
        # 5 events + 1 closing
        self.assertEqual(len(events), 6)

    def test_empty_company_returns_fallback(self):
        company = Company(name="Empty")
        events = generate_combat_events(company, CombatOutcome.VICTORY)
        self.assertGreater(len(events), 0)

    def test_events_are_strings(self):
        company = _make_company()
        events = generate_combat_events(company, CombatOutcome.VICTORY)
        for event in events:
            self.assertIsInstance(event, str)
            self.assertGreater(len(event), 0)


# ── Deployed Pairs Tests ─────────────────────────────────────────────────

class TestDeployedPairs(unittest.TestCase):
    """Tests for _get_deployed_pairs()."""

    def test_starting_lance_has_four_pairs(self):
        company = _make_company()
        pairs = _get_deployed_pairs(company)
        self.assertEqual(len(pairs), 4)

    def test_destroyed_mech_excluded(self):
        company = _make_company()
        company.mechs[0].status = MechStatus.DESTROYED
        pairs = _get_deployed_pairs(company)
        self.assertEqual(len(pairs), 3)

    def test_kia_pilot_excluded(self):
        company = _make_company()
        company.mechwarriors[0].status = PilotStatus.KIA
        pairs = _get_deployed_pairs(company)
        self.assertEqual(len(pairs), 3)

    def test_unassigned_pilot_excluded(self):
        company = _make_company()
        company.mechwarriors[0].assigned_mech = None
        pairs = _get_deployed_pairs(company)
        self.assertEqual(len(pairs), 3)

    def test_empty_company_returns_empty(self):
        company = Company(name="Empty")
        pairs = _get_deployed_pairs(company)
        self.assertEqual(len(pairs), 0)


# ── Damage Application Tests ────────────────────────────────────────────

class TestDamageApplication(unittest.TestCase):
    """Tests for apply_damage()."""

    def test_no_damage_on_victory(self):
        company = _make_company()
        mech_dmg, pilot_inj = apply_damage(company, CombatOutcome.VICTORY, 3)
        self.assertEqual(len(mech_dmg), 0)
        self.assertEqual(len(pilot_inj), 0)

    def test_damage_on_pyrrhic_victory(self):
        """Pyrrhic victory should damage 1-2 mechs."""
        random.seed(42)
        company = _make_company()
        mech_dmg, _ = apply_damage(company, CombatOutcome.PYRRHIC_VICTORY, 3)
        self.assertGreaterEqual(len(mech_dmg), 1)
        self.assertLessEqual(len(mech_dmg), 2)

    def test_damage_on_defeat(self):
        """Defeat should damage 2-3 mechs."""
        random.seed(42)
        company = _make_company()
        mech_dmg, _ = apply_damage(company, CombatOutcome.DEFEAT, 3)
        self.assertGreaterEqual(len(mech_dmg), 2)
        self.assertLessEqual(len(mech_dmg), 3)

    def test_armor_reduced_on_damage(self):
        """Damaged mechs should have reduced armor."""
        random.seed(42)
        company = _make_company()
        original_armor = [m.armor_current for m in company.mechs]

        apply_damage(company, CombatOutcome.PYRRHIC_VICTORY, 3)

        # At least one mech should have reduced armor
        reduced = any(
            m.armor_current < orig
            for m, orig in zip(company.mechs, original_armor)
        )
        self.assertTrue(reduced)

    def test_damaged_mech_gets_damaged_status(self):
        """A mech that takes damage should be marked DAMAGED."""
        random.seed(42)
        company = _make_company()
        apply_damage(company, CombatOutcome.DEFEAT, 3)

        damaged_count = sum(
            1 for m in company.mechs
            if m.status in (MechStatus.DAMAGED, MechStatus.DESTROYED)
        )
        self.assertGreater(damaged_count, 0)

    def test_mech_destruction_sets_structure_zero(self):
        """A destroyed mech should have structure at 0."""
        # Create a very weak mech that will be destroyed
        mech = _make_mech("Fragile", armor_max=10, structure_max=5)
        mech.armor_current = 0  # No armor left
        mech.armor_max = 10
        pilot = _make_pilot("Doomed", assigned_mech="Fragile")

        company = Company(name="Weak", mechwarriors=[pilot], mechs=[mech])

        # Apply heavy damage with high difficulty
        random.seed(42)
        apply_damage(company, CombatOutcome.DEFEAT, 5)

        # Mech should be destroyed
        if mech.status == MechStatus.DESTROYED:
            self.assertEqual(mech.structure_current, 0)

    def test_damage_reports_contain_mech_names(self):
        random.seed(42)
        company = _make_company()
        mech_dmg, _ = apply_damage(company, CombatOutcome.DEFEAT, 3)

        mech_names = {m.name for m in company.mechs}
        for report in mech_dmg:
            self.assertIn(report.mech_name, mech_names)

    def test_pilot_injury_increases_injury_count(self):
        """Injured pilots should have their injury count increased."""
        random.seed(42)
        company = _make_company()
        _, pilot_inj = apply_damage(company, CombatOutcome.DEFEAT, 5)

        if pilot_inj:
            injured_callsigns = {inj.callsign for inj in pilot_inj}
            for mw in company.mechwarriors:
                if mw.callsign in injured_callsigns:
                    self.assertGreater(mw.injuries, 0)
                    self.assertEqual(mw.status, PilotStatus.INJURED)

    def test_morale_decreases_on_defeat(self):
        """All pilots should lose morale on defeat."""
        company = _make_company()
        original_morale = [mw.morale for mw in company.mechwarriors]

        apply_damage(company, CombatOutcome.DEFEAT, 3)

        for mw, orig in zip(company.mechwarriors, original_morale):
            if mw.status != PilotStatus.KIA:
                self.assertLessEqual(mw.morale, orig)

    def test_damage_report_types(self):
        random.seed(42)
        company = _make_company()
        mech_dmg, pilot_inj = apply_damage(company, CombatOutcome.DEFEAT, 3)

        for report in mech_dmg:
            self.assertIsInstance(report, MechDamageReport)
            self.assertGreaterEqual(report.armor_lost, 0)
            self.assertGreaterEqual(report.structure_lost, 0)
            self.assertIsInstance(report.destroyed, bool)

        for report in pilot_inj:
            self.assertIsInstance(report, PilotInjuryReport)
            self.assertGreater(report.injuries_sustained, 0)

    def test_higher_difficulty_more_damage(self):
        """Higher difficulty should generally cause more damage."""
        random.seed(42)
        company1 = _make_company()
        mech_dmg1, _ = apply_damage(company1, CombatOutcome.DEFEAT, 1)
        total_dmg1 = sum(r.armor_lost + r.structure_lost for r in mech_dmg1)

        random.seed(42)
        company2 = _make_company()
        mech_dmg2, _ = apply_damage(company2, CombatOutcome.DEFEAT, 5)
        total_dmg2 = sum(r.armor_lost + r.structure_lost for r in mech_dmg2)

        self.assertGreater(total_dmg2, total_dmg1)


# ── Rewards Calculation Tests ────────────────────────────────────────────

class TestRewardsCalculation(unittest.TestCase):
    """Tests for calculate_rewards()."""

    def test_victory_gives_full_payout(self):
        company = _make_company()
        contract = _make_contract(payout=200_000)
        initial_bills = company.c_bills

        c_bills, xp = calculate_rewards(company, contract, CombatOutcome.VICTORY)

        self.assertEqual(c_bills, 200_000)
        self.assertEqual(company.c_bills, initial_bills + 200_000)

    def test_pyrrhic_victory_gives_full_payout(self):
        company = _make_company()
        contract = _make_contract(payout=200_000)
        initial_bills = company.c_bills

        c_bills, xp = calculate_rewards(company, contract, CombatOutcome.PYRRHIC_VICTORY)

        self.assertEqual(c_bills, 200_000)

    def test_defeat_gives_partial_payout(self):
        company = _make_company()
        contract = _make_contract(payout=200_000)

        c_bills, xp = calculate_rewards(company, contract, CombatOutcome.DEFEAT)

        self.assertEqual(c_bills, 50_000)  # 25% of 200k

    def test_victory_gives_most_xp(self):
        company1 = _make_company()
        company2 = _make_company()
        company3 = _make_company()
        contract = _make_contract(difficulty=3)

        _, xp_victory = calculate_rewards(company1, contract, CombatOutcome.VICTORY)
        _, xp_pyrrhic = calculate_rewards(company2, contract, CombatOutcome.PYRRHIC_VICTORY)
        _, xp_defeat = calculate_rewards(company3, contract, CombatOutcome.DEFEAT)

        self.assertGreater(xp_victory, xp_pyrrhic)
        self.assertGreater(xp_pyrrhic, xp_defeat)

    def test_xp_scales_with_difficulty(self):
        company1 = _make_company()
        company2 = _make_company()
        contract_easy = _make_contract(difficulty=1)
        contract_hard = _make_contract(difficulty=5)

        _, xp_easy = calculate_rewards(company1, contract_easy, CombatOutcome.VICTORY)
        _, xp_hard = calculate_rewards(company2, contract_hard, CombatOutcome.VICTORY)

        self.assertGreater(xp_hard, xp_easy)

    def test_pilots_gain_xp(self):
        company = _make_company()
        contract = _make_contract(difficulty=3)
        initial_xp = [mw.experience for mw in company.mechwarriors]

        calculate_rewards(company, contract, CombatOutcome.VICTORY)

        for mw, orig in zip(company.mechwarriors, initial_xp):
            self.assertGreater(mw.experience, orig)

    def test_victory_boosts_morale(self):
        company = _make_company()
        # Set morale to a moderate value
        for mw in company.mechwarriors:
            mw.morale = 50
        contract = _make_contract()

        calculate_rewards(company, contract, CombatOutcome.VICTORY)

        for mw in company.mechwarriors:
            self.assertGreater(mw.morale, 50)

    def test_defeat_no_morale_boost(self):
        company = _make_company()
        for mw in company.mechwarriors:
            mw.morale = 50
        contract = _make_contract()

        calculate_rewards(company, contract, CombatOutcome.DEFEAT)

        # Defeat gives 0 morale boost
        for mw in company.mechwarriors:
            self.assertEqual(mw.morale, 50)

    def test_kia_pilots_excluded_from_rewards(self):
        company = _make_company()
        company.mechwarriors[0].status = PilotStatus.KIA
        initial_xp = company.mechwarriors[0].experience
        contract = _make_contract()

        calculate_rewards(company, contract, CombatOutcome.VICTORY)

        # KIA pilot should not gain XP
        self.assertEqual(company.mechwarriors[0].experience, initial_xp)


# ── Full Combat Resolution Tests ────────────────────────────────────────

class TestResolveCombat(unittest.TestCase):
    """Tests for the full resolve_combat() function."""

    def test_returns_mission_result(self):
        company = _make_company()
        contract = _make_contract()
        result = resolve_combat(company, contract)
        self.assertIsInstance(result, MissionResult)

    def test_result_has_valid_outcome(self):
        company = _make_company()
        contract = _make_contract()
        result = resolve_combat(company, contract)
        self.assertIn(result.outcome, list(CombatOutcome))

    def test_result_has_combat_log(self):
        company = _make_company()
        contract = _make_contract()
        result = resolve_combat(company, contract)
        self.assertGreater(len(result.combat_log), 0)

    def test_result_has_lance_power(self):
        company = _make_company()
        contract = _make_contract()
        result = resolve_combat(company, contract)
        self.assertGreater(result.lance_power, 0)

    def test_result_has_success_chance(self):
        company = _make_company()
        contract = _make_contract()
        result = resolve_combat(company, contract)
        self.assertGreater(result.success_chance, 0)
        self.assertLessEqual(result.success_chance, 1.0)

    def test_result_has_c_bills_earned(self):
        company = _make_company()
        contract = _make_contract(payout=200_000)
        result = resolve_combat(company, contract)
        self.assertGreater(result.c_bills_earned, 0)

    def test_result_has_xp_earned(self):
        company = _make_company()
        contract = _make_contract()
        result = resolve_combat(company, contract)
        self.assertGreater(result.xp_earned, 0)

    def test_company_week_incremented(self):
        company = _make_company()
        initial_week = company.week
        contract = _make_contract()
        resolve_combat(company, contract)
        self.assertEqual(company.week, initial_week + 1)

    def test_company_contracts_completed_incremented(self):
        company = _make_company()
        initial_completed = company.contracts_completed
        contract = _make_contract()
        resolve_combat(company, contract)
        self.assertEqual(company.contracts_completed, initial_completed + 1)

    def test_c_bills_added_to_company(self):
        company = _make_company()
        initial_bills = company.c_bills
        contract = _make_contract(payout=200_000)
        result = resolve_combat(company, contract)
        self.assertEqual(company.c_bills, initial_bills + result.c_bills_earned)

    def test_reputation_changes(self):
        """Reputation should change based on outcome."""
        random.seed(42)
        company = _make_company()
        initial_rep = company.reputation
        contract = _make_contract()
        result = resolve_combat(company, contract)

        # Reputation should change (up on victory/pyrrhic, down on defeat)
        if result.outcome == CombatOutcome.VICTORY:
            self.assertGreater(company.reputation, initial_rep)
        elif result.outcome == CombatOutcome.DEFEAT:
            self.assertLess(company.reputation, initial_rep)

    def test_combat_log_events_are_strings(self):
        company = _make_company()
        contract = _make_contract()
        result = resolve_combat(company, contract)
        for event in result.combat_log:
            self.assertIsInstance(event, str)
            self.assertGreater(len(event), 0)

    def test_mech_damage_reports_valid(self):
        """Damage reports should reference actual company mechs."""
        random.seed(42)
        company = _make_company()
        contract = _make_contract(difficulty=5)
        result = resolve_combat(company, contract)

        mech_names = {m.name for m in company.mechs}
        for dmg in result.mech_damage:
            self.assertIn(dmg.mech_name, mech_names)

    def test_pilot_injury_reports_valid(self):
        """Injury reports should reference actual company pilots."""
        random.seed(42)
        company = _make_company()
        contract = _make_contract(difficulty=5)
        result = resolve_combat(company, contract)

        callsigns = {mw.callsign for mw in company.mechwarriors}
        for inj in result.pilot_injuries:
            self.assertIn(inj.callsign, callsigns)


# ── Mission Result Dataclass Tests ───────────────────────────────────────

class TestMissionResult(unittest.TestCase):
    """Tests for the MissionResult dataclass."""

    def test_default_values(self):
        result = MissionResult(outcome=CombatOutcome.VICTORY)
        self.assertEqual(result.combat_log, [])
        self.assertEqual(result.mech_damage, [])
        self.assertEqual(result.pilot_injuries, [])
        self.assertEqual(result.c_bills_earned, 0)
        self.assertEqual(result.xp_earned, 0)
        self.assertEqual(result.lance_power, 0.0)
        self.assertEqual(result.success_chance, 0.0)

    def test_custom_values(self):
        result = MissionResult(
            outcome=CombatOutcome.DEFEAT,
            combat_log=["Event 1", "Event 2"],
            c_bills_earned=100_000,
            xp_earned=50,
            lance_power=200.0,
            success_chance=0.65,
        )
        self.assertEqual(result.outcome, CombatOutcome.DEFEAT)
        self.assertEqual(len(result.combat_log), 2)
        self.assertEqual(result.c_bills_earned, 100_000)


class TestMechDamageReport(unittest.TestCase):
    """Tests for MechDamageReport dataclass."""

    def test_default_values(self):
        report = MechDamageReport(mech_name="Test")
        self.assertEqual(report.armor_lost, 0)
        self.assertEqual(report.structure_lost, 0)
        self.assertFalse(report.destroyed)

    def test_destroyed_report(self):
        report = MechDamageReport(
            mech_name="Test", armor_lost=100, structure_lost=40, destroyed=True
        )
        self.assertTrue(report.destroyed)


class TestPilotInjuryReport(unittest.TestCase):
    """Tests for PilotInjuryReport dataclass."""

    def test_default_values(self):
        report = PilotInjuryReport(callsign="Test")
        self.assertEqual(report.injuries_sustained, 0)

    def test_injury_report(self):
        report = PilotInjuryReport(callsign="Ace", injuries_sustained=2)
        self.assertEqual(report.injuries_sustained, 2)


# ── Destroyed Mech Removal Tests ────────────────────────────────────────

class TestDestroyedMechHandling(unittest.TestCase):
    """Tests for destroyed mech status tracking."""

    def test_destroyed_mech_marked_destroyed(self):
        """A mech whose structure reaches 0 should be marked Destroyed."""
        mech = _make_mech("Fragile", armor_max=1, structure_max=1)
        mech.armor_current = 0
        pilot = _make_pilot("Doomed", assigned_mech="Fragile")
        company = Company(name="Weak", mechwarriors=[pilot], mechs=[mech])

        # Force heavy damage
        random.seed(42)
        apply_damage(company, CombatOutcome.DEFEAT, 5)

        if mech.structure_current <= 0:
            self.assertEqual(mech.status, MechStatus.DESTROYED)

    def test_destroyed_mech_excluded_from_future_power(self):
        """A destroyed mech should not contribute to lance power."""
        company = _make_company()
        company.mechs[0].status = MechStatus.DESTROYED

        pairs = _get_deployed_pairs(company)
        mech_names = {mech.name for _, mech in pairs}
        self.assertNotIn(company.mechs[0].name, mech_names)


if __name__ == "__main__":
    unittest.main()
