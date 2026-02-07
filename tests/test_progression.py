"""
test_progression.py - Unit tests for Iron Contract pilot progression system.

Tests cover:
- XP and leveling: thresholds, level calculation, level-up mechanics
- Morale system: outcome-based adjustments, combat bonuses/penalties, desertion
- Injury recovery: healing, deployability
- Effective skill calculation with morale modifiers
- Desertion mechanics (pilot + mech removal)
- Integration helpers (pending level-ups, recovery messages)
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
from data.progression import (
    XP_THRESHOLDS,
    MIN_SKILL,
    NEW_PILOT_MORALE,
    MORALE_VICTORY_BOOST,
    MORALE_DEFEAT_PENALTY,
    MORALE_LOW_THRESHOLD,
    MORALE_HIGH_THRESHOLD,
    MORALE_DESERTION_THRESHOLD,
    DeserterReport,
    get_pilot_level,
    get_available_levelups,
    can_level_up,
    apply_level_up,
    get_xp_to_next_level,
    apply_morale_outcome,
    effective_gunnery,
    effective_piloting,
    get_morale_modifier_text,
    check_desertion,
    generate_desertion_message,
    recover_injuries,
    is_pilot_deployable,
    get_pilots_with_pending_levelups,
)


class TestXPAndLeveling(unittest.TestCase):
    """Tests for XP thresholds and leveling mechanics."""

    def _make_pilot(self, **overrides):
        """Helper to create a pilot with sensible defaults."""
        defaults = {
            "name": "Alex Steiner",
            "callsign": "Falcon",
            "gunnery": 4,
            "piloting": 4,
            "morale": 75,
            "injuries": 0,
            "experience": 0,
            "status": PilotStatus.ACTIVE,
        }
        defaults.update(overrides)
        return MechWarrior(**defaults)

    def test_xp_thresholds_defined(self):
        """XP thresholds are correctly defined."""
        self.assertEqual(XP_THRESHOLDS, [100, 300, 600, 1000, 1500])

    def test_level_zero_at_start(self):
        """New pilot with 0 XP is level 0."""
        pilot = self._make_pilot(experience=0)
        self.assertEqual(get_pilot_level(pilot), 0)

    def test_level_one_at_100xp(self):
        """Pilot with 100 XP is level 1."""
        pilot = self._make_pilot(experience=100)
        self.assertEqual(get_pilot_level(pilot), 1)

    def test_level_two_at_300xp(self):
        """Pilot with 300 XP is level 2."""
        pilot = self._make_pilot(experience=300)
        self.assertEqual(get_pilot_level(pilot), 2)

    def test_level_three_at_600xp(self):
        """Pilot with 600 XP is level 3."""
        pilot = self._make_pilot(experience=600)
        self.assertEqual(get_pilot_level(pilot), 3)

    def test_level_four_at_1000xp(self):
        """Pilot with 1000 XP is level 4."""
        pilot = self._make_pilot(experience=1000)
        self.assertEqual(get_pilot_level(pilot), 4)

    def test_level_five_at_1500xp(self):
        """Pilot with 1500 XP is max level 5."""
        pilot = self._make_pilot(experience=1500)
        self.assertEqual(get_pilot_level(pilot), 5)

    def test_level_between_thresholds(self):
        """Pilot with 150 XP (between 100 and 300) is level 1."""
        pilot = self._make_pilot(experience=150)
        self.assertEqual(get_pilot_level(pilot), 1)

    def test_level_just_below_threshold(self):
        """Pilot with 99 XP (just below 100) is level 0."""
        pilot = self._make_pilot(experience=99)
        self.assertEqual(get_pilot_level(pilot), 0)

    def test_level_above_max(self):
        """Pilot with 5000 XP is still max level 5."""
        pilot = self._make_pilot(experience=5000)
        self.assertEqual(get_pilot_level(pilot), 5)

    def test_can_level_up_with_xp(self):
        """Pilot with enough XP and improvable skills can level up."""
        pilot = self._make_pilot(experience=100, gunnery=4, piloting=4)
        self.assertTrue(can_level_up(pilot))

    def test_cannot_level_up_no_xp(self):
        """Pilot with no XP cannot level up."""
        pilot = self._make_pilot(experience=0)
        self.assertFalse(can_level_up(pilot))

    def test_cannot_level_up_kia(self):
        """KIA pilot cannot level up."""
        pilot = self._make_pilot(experience=500, status=PilotStatus.KIA)
        self.assertFalse(can_level_up(pilot))

    def test_cannot_level_up_max_skills(self):
        """Pilot with both skills at minimum cannot level up."""
        pilot = self._make_pilot(experience=500, gunnery=1, piloting=1)
        self.assertFalse(can_level_up(pilot))

    def test_can_level_up_one_skill_maxed(self):
        """Pilot can level up if only one skill is at minimum."""
        pilot = self._make_pilot(experience=100, gunnery=1, piloting=3)
        self.assertTrue(can_level_up(pilot))

    def test_apply_level_up_gunnery(self):
        """Applying level up to gunnery reduces it by 1."""
        pilot = self._make_pilot(gunnery=4)
        result = apply_level_up(pilot, "gunnery")
        self.assertTrue(result)
        self.assertEqual(pilot.gunnery, 3)

    def test_apply_level_up_piloting(self):
        """Applying level up to piloting reduces it by 1."""
        pilot = self._make_pilot(piloting=4)
        result = apply_level_up(pilot, "piloting")
        self.assertTrue(result)
        self.assertEqual(pilot.piloting, 3)

    def test_apply_level_up_gunnery_at_min(self):
        """Cannot apply level up to gunnery already at minimum."""
        pilot = self._make_pilot(gunnery=1)
        result = apply_level_up(pilot, "gunnery")
        self.assertFalse(result)
        self.assertEqual(pilot.gunnery, 1)

    def test_apply_level_up_piloting_at_min(self):
        """Cannot apply level up to piloting already at minimum."""
        pilot = self._make_pilot(piloting=1)
        result = apply_level_up(pilot, "piloting")
        self.assertFalse(result)
        self.assertEqual(pilot.piloting, 1)

    def test_apply_level_up_invalid_skill(self):
        """Invalid skill name returns False."""
        pilot = self._make_pilot()
        result = apply_level_up(pilot, "cooking")
        self.assertFalse(result)

    def test_apply_level_up_increments_levelups_spent(self):
        """Applying a level-up increments the levelups_spent counter."""
        pilot = self._make_pilot(experience=100, gunnery=4, piloting=4)
        self.assertEqual(pilot.levelups_spent, 0)
        apply_level_up(pilot, "gunnery")
        self.assertEqual(pilot.levelups_spent, 1)
        self.assertEqual(pilot.gunnery, 3)

    def test_apply_level_up_failed_does_not_increment(self):
        """Failed level-up does not increment levelups_spent."""
        pilot = self._make_pilot(experience=100, gunnery=1)
        apply_level_up(pilot, "gunnery")
        self.assertEqual(pilot.levelups_spent, 0)

    def test_available_levelups_decreases_after_spend(self):
        """get_available_levelups decreases after spending a level-up."""
        pilot = self._make_pilot(experience=300, gunnery=4, piloting=4)
        self.assertEqual(get_available_levelups(pilot), 2)
        apply_level_up(pilot, "gunnery")
        self.assertEqual(get_available_levelups(pilot), 1)
        apply_level_up(pilot, "piloting")
        self.assertEqual(get_available_levelups(pilot), 0)

    def test_can_level_up_false_after_all_spent(self):
        """can_level_up returns False once all earned level-ups are spent."""
        pilot = self._make_pilot(experience=300, gunnery=4, piloting=4)
        # Level 2 → 2 level-ups available
        self.assertTrue(can_level_up(pilot))
        apply_level_up(pilot, "gunnery")
        self.assertTrue(can_level_up(pilot))
        apply_level_up(pilot, "piloting")
        # Both level-ups spent
        self.assertFalse(can_level_up(pilot))

    def test_reviewer_repro_case(self):
        """Reproduce the exact reviewer bug report scenario.

        Pilot at 300 XP (level 2) should get exactly 2 level-ups, not
        unlimited level-ups.
        """
        pilot = self._make_pilot(experience=300, gunnery=4, piloting=4)
        apply_level_up(pilot, "gunnery")   # First levelup - OK
        apply_level_up(pilot, "piloting")  # Second levelup - OK
        self.assertFalse(can_level_up(pilot))  # Must be False now

    def test_new_xp_threshold_unlocks_more_levelups(self):
        """Gaining XP past a new threshold grants new level-ups."""
        pilot = self._make_pilot(experience=100, gunnery=4, piloting=4)
        # Level 1, spend the one level-up
        apply_level_up(pilot, "gunnery")
        self.assertFalse(can_level_up(pilot))
        # Now gain more XP to reach level 2
        pilot.experience = 300
        self.assertTrue(can_level_up(pilot))
        self.assertEqual(get_available_levelups(pilot), 1)

    def test_levelups_spent_persisted_via_field(self):
        """levelups_spent field defaults to 0 and tracks correctly."""
        pilot = self._make_pilot(experience=600, gunnery=4, piloting=4)
        self.assertEqual(pilot.levelups_spent, 0)
        self.assertEqual(get_available_levelups(pilot), 3)
        apply_level_up(pilot, "gunnery")
        apply_level_up(pilot, "piloting")
        self.assertEqual(pilot.levelups_spent, 2)
        self.assertEqual(get_available_levelups(pilot), 1)

    def test_min_skill_is_one(self):
        """MIN_SKILL constant is 1."""
        self.assertEqual(MIN_SKILL, 1)

    def test_xp_to_next_level_at_zero(self):
        """Pilot at 0 XP needs 100 for next level."""
        pilot = self._make_pilot(experience=0)
        self.assertEqual(get_xp_to_next_level(pilot), 100)

    def test_xp_to_next_level_at_50(self):
        """Pilot at 50 XP needs 50 for next level."""
        pilot = self._make_pilot(experience=50)
        self.assertEqual(get_xp_to_next_level(pilot), 50)

    def test_xp_to_next_level_at_max(self):
        """Pilot at max level returns None."""
        pilot = self._make_pilot(experience=1500)
        self.assertIsNone(get_xp_to_next_level(pilot))


class TestMoraleSystem(unittest.TestCase):
    """Tests for the morale system."""

    def _make_pilot(self, **overrides):
        defaults = {
            "name": "Alex Steiner",
            "callsign": "Falcon",
            "gunnery": 4,
            "piloting": 4,
            "morale": 70,
            "status": PilotStatus.ACTIVE,
        }
        defaults.update(overrides)
        return MechWarrior(**defaults)

    def _make_company(self, pilots=None):
        return Company(
            name="Test Company",
            mechwarriors=pilots or [],
            mechs=[],
        )

    def test_new_pilot_morale(self):
        """NEW_PILOT_MORALE constant is 70."""
        self.assertEqual(NEW_PILOT_MORALE, 70)

    def test_victory_morale_boost(self):
        """Victory boosts morale by 10."""
        pilot = self._make_pilot(morale=50)
        company = self._make_company([pilot])
        apply_morale_outcome(company, "Victory")
        self.assertEqual(pilot.morale, 60)

    def test_defeat_morale_penalty(self):
        """Defeat reduces morale by 15."""
        pilot = self._make_pilot(morale=50)
        company = self._make_company([pilot])
        apply_morale_outcome(company, "Defeat")
        self.assertEqual(pilot.morale, 35)

    def test_pyrrhic_victory_neutral(self):
        """Pyrrhic Victory does not change morale."""
        pilot = self._make_pilot(morale=50)
        company = self._make_company([pilot])
        apply_morale_outcome(company, "Pyrrhic Victory")
        self.assertEqual(pilot.morale, 50)

    def test_morale_capped_at_100(self):
        """Morale cannot exceed 100."""
        pilot = self._make_pilot(morale=95)
        company = self._make_company([pilot])
        apply_morale_outcome(company, "Victory")
        self.assertEqual(pilot.morale, 100)

    def test_morale_capped_at_0(self):
        """Morale cannot go below 0."""
        pilot = self._make_pilot(morale=5)
        company = self._make_company([pilot])
        apply_morale_outcome(company, "Defeat")
        self.assertEqual(pilot.morale, 0)

    def test_kia_pilots_not_affected(self):
        """KIA pilots are not affected by morale changes."""
        pilot = self._make_pilot(morale=50, status=PilotStatus.KIA)
        company = self._make_company([pilot])
        apply_morale_outcome(company, "Victory")
        self.assertEqual(pilot.morale, 50)

    def test_multiple_pilots_affected(self):
        """All active pilots are affected by morale changes."""
        pilot1 = self._make_pilot(callsign="A", morale=50)
        pilot2 = self._make_pilot(callsign="B", morale=60)
        company = self._make_company([pilot1, pilot2])
        apply_morale_outcome(company, "Victory")
        self.assertEqual(pilot1.morale, 60)
        self.assertEqual(pilot2.morale, 70)


class TestEffectiveSkills(unittest.TestCase):
    """Tests for effective skill calculation with morale modifiers."""

    def _make_pilot(self, **overrides):
        defaults = {
            "name": "Alex Steiner",
            "callsign": "Falcon",
            "gunnery": 4,
            "piloting": 4,
            "morale": 50,
            "status": PilotStatus.ACTIVE,
        }
        defaults.update(overrides)
        return MechWarrior(**defaults)

    def test_normal_morale_no_modifier(self):
        """Normal morale (30-80) gives no modifier."""
        pilot = self._make_pilot(morale=50, gunnery=4, piloting=4)
        self.assertEqual(effective_gunnery(pilot), 4)
        self.assertEqual(effective_piloting(pilot), 4)

    def test_low_morale_penalty(self):
        """Low morale (<30) gives +1 penalty (worse skill)."""
        pilot = self._make_pilot(morale=20, gunnery=4, piloting=4)
        self.assertEqual(effective_gunnery(pilot), 5)
        self.assertEqual(effective_piloting(pilot), 5)

    def test_high_morale_bonus(self):
        """High morale (>80) gives -1 bonus (better skill)."""
        pilot = self._make_pilot(morale=90, gunnery=4, piloting=4)
        self.assertEqual(effective_gunnery(pilot), 3)
        self.assertEqual(effective_piloting(pilot), 3)

    def test_low_morale_at_threshold(self):
        """Morale exactly at 30 gives no penalty."""
        pilot = self._make_pilot(morale=30, gunnery=4, piloting=4)
        self.assertEqual(effective_gunnery(pilot), 4)

    def test_high_morale_at_threshold(self):
        """Morale exactly at 80 gives no bonus."""
        pilot = self._make_pilot(morale=80, gunnery=4, piloting=4)
        self.assertEqual(effective_gunnery(pilot), 4)

    def test_low_morale_just_below_threshold(self):
        """Morale at 29 gives penalty."""
        pilot = self._make_pilot(morale=29, gunnery=4, piloting=4)
        self.assertEqual(effective_gunnery(pilot), 5)

    def test_high_morale_just_above_threshold(self):
        """Morale at 81 gives bonus."""
        pilot = self._make_pilot(morale=81, gunnery=4, piloting=4)
        self.assertEqual(effective_gunnery(pilot), 3)

    def test_effective_skill_clamped_min(self):
        """Effective skill cannot go below 1."""
        pilot = self._make_pilot(morale=90, gunnery=1, piloting=1)
        self.assertEqual(effective_gunnery(pilot), 1)
        self.assertEqual(effective_piloting(pilot), 1)

    def test_effective_skill_clamped_max(self):
        """Effective skill cannot exceed 7."""
        pilot = self._make_pilot(morale=10, gunnery=6, piloting=6)
        self.assertEqual(effective_gunnery(pilot), 7)
        self.assertEqual(effective_piloting(pilot), 7)

    def test_morale_modifier_text_low(self):
        """Low morale shows penalty text."""
        pilot = self._make_pilot(morale=20)
        text = get_morale_modifier_text(pilot)
        self.assertIn("LOW MORALE", text)
        self.assertIn("penalty", text)

    def test_morale_modifier_text_high(self):
        """High morale shows bonus text."""
        pilot = self._make_pilot(morale=90)
        text = get_morale_modifier_text(pilot)
        self.assertIn("HIGH MORALE", text)
        self.assertIn("bonus", text)

    def test_morale_modifier_text_normal(self):
        """Normal morale shows empty text."""
        pilot = self._make_pilot(morale=50)
        text = get_morale_modifier_text(pilot)
        self.assertEqual(text, "")


class TestDesertion(unittest.TestCase):
    """Tests for desertion mechanics."""

    def _make_mech(self, name="Wolverine WVR-6R"):
        return BattleMech(
            name=name,
            weight_class=WeightClass.MEDIUM,
            tonnage=55,
            armor_current=136,
            armor_max=136,
            structure_current=48,
            structure_max=48,
            firepower=6,
            speed=6,
        )

    def _make_pilot(self, **overrides):
        defaults = {
            "name": "Alex Steiner",
            "callsign": "Falcon",
            "gunnery": 4,
            "piloting": 4,
            "morale": 50,
            "status": PilotStatus.ACTIVE,
            "assigned_mech": None,
        }
        defaults.update(overrides)
        return MechWarrior(**defaults)

    def test_no_desertion_normal_morale(self):
        """Pilot with normal morale does not desert."""
        pilot = self._make_pilot(morale=50)
        company = Company(name="Test", mechwarriors=[pilot], mechs=[])
        deserters = check_desertion(company)
        self.assertEqual(len(deserters), 0)
        self.assertEqual(len(company.mechwarriors), 1)

    def test_desertion_at_zero_morale(self):
        """Pilot with 0 morale deserts."""
        pilot = self._make_pilot(morale=0, assigned_mech="Wolverine WVR-6R")
        mech = self._make_mech()
        company = Company(name="Test", mechwarriors=[pilot], mechs=[mech])
        deserters = check_desertion(company)
        self.assertEqual(len(deserters), 1)
        self.assertEqual(deserters[0].callsign, "Falcon")
        self.assertEqual(deserters[0].mech_name, "Wolverine WVR-6R")
        # Pilot and mech should be removed
        self.assertEqual(len(company.mechwarriors), 0)
        self.assertEqual(len(company.mechs), 0)

    def test_desertion_removes_mech(self):
        """Deserting pilot takes their assigned mech."""
        pilot = self._make_pilot(morale=0, assigned_mech="Wolverine WVR-6R")
        mech1 = self._make_mech("Wolverine WVR-6R")
        mech2 = self._make_mech("Commando COM-2D")
        company = Company(name="Test", mechwarriors=[pilot], mechs=[mech1, mech2])
        check_desertion(company)
        # Only the stolen mech should be gone
        self.assertEqual(len(company.mechs), 1)
        self.assertEqual(company.mechs[0].name, "Commando COM-2D")

    def test_desertion_kia_ignored(self):
        """KIA pilots do not desert."""
        pilot = self._make_pilot(morale=0, status=PilotStatus.KIA)
        company = Company(name="Test", mechwarriors=[pilot], mechs=[])
        deserters = check_desertion(company)
        self.assertEqual(len(deserters), 0)

    def test_desertion_no_mech(self):
        """Pilot without assigned mech can still desert (no mech stolen)."""
        pilot = self._make_pilot(morale=0, assigned_mech=None)
        company = Company(name="Test", mechwarriors=[pilot], mechs=[])
        deserters = check_desertion(company)
        self.assertEqual(len(deserters), 1)
        self.assertIsNone(deserters[0].mech_name)

    def test_desertion_message_with_mech(self):
        """Desertion message mentions pilot callsign and stolen mech."""
        report = DeserterReport(
            pilot_name="Jade Liao",
            callsign="Ghost",
            mech_name="Commando COM-2D",
        )
        msg = generate_desertion_message(report)
        self.assertIn("Ghost", msg)
        self.assertIn("Commando COM-2D", msg)
        self.assertIn("vanish", msg)

    def test_desertion_message_without_mech(self):
        """Desertion message works when no mech is assigned."""
        report = DeserterReport(
            pilot_name="Jade Liao",
            callsign="Ghost",
            mech_name=None,
        )
        msg = generate_desertion_message(report)
        self.assertIn("Ghost", msg)
        self.assertIn("slip away", msg)

    def test_multiple_desertions(self):
        """Multiple pilots with 0 morale all desert."""
        pilot1 = self._make_pilot(callsign="A", morale=0, assigned_mech="Mech1")
        pilot2 = self._make_pilot(callsign="B", morale=0, assigned_mech="Mech2")
        pilot3 = self._make_pilot(callsign="C", morale=50)
        mech1 = self._make_mech("Mech1")
        mech2 = self._make_mech("Mech2")
        company = Company(
            name="Test",
            mechwarriors=[pilot1, pilot2, pilot3],
            mechs=[mech1, mech2],
        )
        deserters = check_desertion(company)
        self.assertEqual(len(deserters), 2)
        self.assertEqual(len(company.mechwarriors), 1)
        self.assertEqual(company.mechwarriors[0].callsign, "C")
        self.assertEqual(len(company.mechs), 0)


class TestInjuryRecovery(unittest.TestCase):
    """Tests for injury recovery system."""

    def _make_pilot(self, **overrides):
        defaults = {
            "name": "Alex Steiner",
            "callsign": "Falcon",
            "gunnery": 4,
            "piloting": 4,
            "morale": 50,
            "injuries": 0,
            "status": PilotStatus.ACTIVE,
        }
        defaults.update(overrides)
        return MechWarrior(**defaults)

    def test_recover_single_injury(self):
        """Pilot with 1 injury recovers to Active."""
        pilot = self._make_pilot(injuries=1, status=PilotStatus.INJURED)
        company = Company(name="Test", mechwarriors=[pilot], mechs=[])
        messages = recover_injuries(company)
        self.assertEqual(pilot.injuries, 0)
        self.assertEqual(pilot.status, PilotStatus.ACTIVE)
        self.assertEqual(len(messages), 1)
        self.assertIn("recovered", messages[0])

    def test_recover_multiple_injuries(self):
        """Pilot with 2 injuries recovers partially (1 injury remaining)."""
        pilot = self._make_pilot(injuries=2, status=PilotStatus.INJURED)
        company = Company(name="Test", mechwarriors=[pilot], mechs=[])
        messages = recover_injuries(company)
        self.assertEqual(pilot.injuries, 1)
        self.assertEqual(pilot.status, PilotStatus.INJURED)
        self.assertIn("recovering", messages[0])

    def test_active_pilot_not_affected(self):
        """Active pilot with 0 injuries is not affected."""
        pilot = self._make_pilot(injuries=0, status=PilotStatus.ACTIVE)
        company = Company(name="Test", mechwarriors=[pilot], mechs=[])
        messages = recover_injuries(company)
        self.assertEqual(len(messages), 0)
        self.assertEqual(pilot.status, PilotStatus.ACTIVE)

    def test_kia_pilot_not_affected(self):
        """KIA pilot is not affected by recovery."""
        pilot = self._make_pilot(status=PilotStatus.KIA)
        company = Company(name="Test", mechwarriors=[pilot], mechs=[])
        messages = recover_injuries(company)
        self.assertEqual(len(messages), 0)

    def test_is_pilot_deployable_active(self):
        """Active pilot is deployable."""
        pilot = self._make_pilot(status=PilotStatus.ACTIVE)
        self.assertTrue(is_pilot_deployable(pilot))

    def test_is_pilot_deployable_injured(self):
        """Injured pilot is not deployable."""
        pilot = self._make_pilot(status=PilotStatus.INJURED)
        self.assertFalse(is_pilot_deployable(pilot))

    def test_is_pilot_deployable_kia(self):
        """KIA pilot is not deployable."""
        pilot = self._make_pilot(status=PilotStatus.KIA)
        self.assertFalse(is_pilot_deployable(pilot))


class TestPendingLevelUps(unittest.TestCase):
    """Tests for finding pilots with pending level-ups."""

    def _make_pilot(self, **overrides):
        defaults = {
            "name": "Alex Steiner",
            "callsign": "Falcon",
            "gunnery": 4,
            "piloting": 4,
            "morale": 50,
            "experience": 0,
            "status": PilotStatus.ACTIVE,
        }
        defaults.update(overrides)
        return MechWarrior(**defaults)

    def test_no_pending_levelups(self):
        """Company with no eligible pilots returns empty list."""
        pilot = self._make_pilot(experience=0)
        company = Company(name="Test", mechwarriors=[pilot], mechs=[])
        result = get_pilots_with_pending_levelups(company)
        self.assertEqual(len(result), 0)

    def test_one_pending_levelup(self):
        """Pilot with enough XP appears in pending list."""
        pilot = self._make_pilot(experience=100)
        company = Company(name="Test", mechwarriors=[pilot], mechs=[])
        result = get_pilots_with_pending_levelups(company)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].callsign, "Falcon")

    def test_kia_excluded(self):
        """KIA pilots are excluded from pending level-ups."""
        pilot = self._make_pilot(experience=500, status=PilotStatus.KIA)
        company = Company(name="Test", mechwarriors=[pilot], mechs=[])
        result = get_pilots_with_pending_levelups(company)
        self.assertEqual(len(result), 0)

    def test_maxed_skills_excluded(self):
        """Pilots with max skills are excluded."""
        pilot = self._make_pilot(experience=500, gunnery=1, piloting=1)
        company = Company(name="Test", mechwarriors=[pilot], mechs=[])
        result = get_pilots_with_pending_levelups(company)
        self.assertEqual(len(result), 0)

    def test_all_levelups_spent_excluded(self):
        """Pilots who have spent all level-ups are excluded."""
        pilot = self._make_pilot(experience=100, gunnery=4, piloting=4)
        apply_level_up(pilot, "gunnery")  # Spend the 1 level-up
        company = Company(name="Test", mechwarriors=[pilot], mechs=[])
        result = get_pilots_with_pending_levelups(company)
        self.assertEqual(len(result), 0)


class TestDeserterReport(unittest.TestCase):
    """Tests for the DeserterReport dataclass."""

    def test_creation(self):
        """DeserterReport can be created with all fields."""
        report = DeserterReport(
            pilot_name="Jade Liao",
            callsign="Ghost",
            mech_name="Commando COM-2D",
        )
        self.assertEqual(report.pilot_name, "Jade Liao")
        self.assertEqual(report.callsign, "Ghost")
        self.assertEqual(report.mech_name, "Commando COM-2D")

    def test_creation_no_mech(self):
        """DeserterReport can be created without mech."""
        report = DeserterReport(
            pilot_name="Jade Liao",
            callsign="Ghost",
        )
        self.assertIsNone(report.mech_name)


class TestMoraleConstants(unittest.TestCase):
    """Tests for morale constants."""

    def test_victory_boost_value(self):
        """Victory morale boost is 10."""
        self.assertEqual(MORALE_VICTORY_BOOST, 10)

    def test_defeat_penalty_value(self):
        """Defeat morale penalty is 15."""
        self.assertEqual(MORALE_DEFEAT_PENALTY, 15)

    def test_low_threshold(self):
        """Low morale threshold is 30."""
        self.assertEqual(MORALE_LOW_THRESHOLD, 30)

    def test_high_threshold(self):
        """High morale threshold is 80."""
        self.assertEqual(MORALE_HIGH_THRESHOLD, 80)

    def test_desertion_threshold(self):
        """Desertion threshold is 0."""
        self.assertEqual(MORALE_DESERTION_THRESHOLD, 0)

    def test_new_pilot_morale(self):
        """New pilot morale starts at 70."""
        self.assertEqual(NEW_PILOT_MORALE, 70)


if __name__ == "__main__":
    unittest.main()
