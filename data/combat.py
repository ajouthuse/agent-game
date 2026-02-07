"""
data.combat - Auto-resolved combat and mission outcome system for Iron Contract.

Provides:
- calculate_lance_power(): Compute lance power rating from mech stats and pilots.
- resolve_combat(): Simulate a mission outcome (Victory, Pyrrhic Victory, Defeat).
- generate_combat_events(): Produce 4-6 narrative log entries referencing actual
  pilot callsigns and mech names.
- apply_damage(): Apply damage to mechs and injuries to pilots on non-clean victories.
- calculate_rewards(): Award C-Bills and XP based on outcome.
- MissionResult: Dataclass capturing the full combat outcome.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

from data.models import (
    BattleMech,
    Company,
    Contract,
    MechStatus,
    MechWarrior,
    MissionType,
    PilotStatus,
)


# ── Outcome Enumeration ─────────────────────────────────────────────────

class CombatOutcome(Enum):
    """Possible mission outcomes."""
    VICTORY = "Victory"
    PYRRHIC_VICTORY = "Pyrrhic Victory"
    DEFEAT = "Defeat"


# ── Mission Result ───────────────────────────────────────────────────────

@dataclass
class MechDamageReport:
    """Damage dealt to a single mech during combat.

    Attributes:
        mech_name: Name of the damaged mech.
        armor_lost: Total armor points lost.
        structure_lost: Total structure points lost.
        destroyed: Whether the mech was destroyed (structure reached 0).
    """
    mech_name: str
    armor_lost: int = 0
    structure_lost: int = 0
    destroyed: bool = False


@dataclass
class PilotInjuryReport:
    """Injury sustained by a pilot during combat.

    Attributes:
        callsign: The pilot's callsign.
        injuries_sustained: Number of injuries taken this mission.
    """
    callsign: str
    injuries_sustained: int = 0


@dataclass
class MissionResult:
    """Complete outcome of a resolved mission.

    Attributes:
        outcome: Victory, Pyrrhic Victory, or Defeat.
        combat_log: List of narrative combat event strings.
        mech_damage: List of damage reports for each affected mech.
        pilot_injuries: List of injury reports for each affected pilot.
        c_bills_earned: C-Bills payout awarded.
        xp_earned: Experience points awarded to each participating pilot.
        lance_power: Calculated lance power rating for display.
        success_chance: Probability of success used in the roll.
    """
    outcome: CombatOutcome
    combat_log: List[str] = field(default_factory=list)
    mech_damage: List[MechDamageReport] = field(default_factory=list)
    pilot_injuries: List[PilotInjuryReport] = field(default_factory=list)
    c_bills_earned: int = 0
    xp_earned: int = 0
    lance_power: float = 0.0
    success_chance: float = 0.0


# ── Lance Power Calculation ─────────────────────────────────────────────

def calculate_lance_power(company: Company) -> float:
    """Calculate the overall lance power rating from mech stats and pilot skills.

    The lance power is a composite score based on:
    - Mech firepower and armor percentage (weighted heavily)
    - Pilot gunnery and piloting skills (lower is better in BattleTech)
    - Pilot morale (as a percentage bonus)

    Only Ready/Damaged mechs with Active/Injured pilots contribute.

    Args:
        company: The player's company with mechs and pilots.

    Returns:
        A float representing the lance's overall combat power.
    """
    # Build pilot lookup by assigned mech
    pilot_by_mech = {}
    for mw in company.mechwarriors:
        if mw.assigned_mech and mw.status != PilotStatus.KIA:
            pilot_by_mech[mw.assigned_mech] = mw

    total_power = 0.0

    for mech in company.mechs:
        if mech.status == MechStatus.DESTROYED:
            continue

        pilot = pilot_by_mech.get(mech.name)
        if pilot is None:
            continue

        # Mech contribution: firepower is the primary combat stat
        mech_power = mech.firepower * 10.0

        # Armor condition modifier (damaged mechs fight less effectively)
        armor_ratio = mech.armor_current / mech.armor_max if mech.armor_max > 0 else 0.0
        mech_power *= (0.5 + 0.5 * armor_ratio)

        # Speed adds a small evasion bonus
        mech_power += mech.speed * 1.5

        # Pilot skill modifier: gunnery/piloting are 1-6, lower is better
        # A gunnery of 1 gives +50% bonus, gunnery of 6 gives -25% penalty
        skill_modifier = 1.0 + (3.5 - pilot.gunnery) * 0.15
        skill_modifier += (3.5 - pilot.piloting) * 0.10
        mech_power *= max(0.5, skill_modifier)

        # Morale bonus (0-100 scale, centered at 50)
        morale_modifier = 1.0 + (pilot.morale - 50) * 0.003
        mech_power *= max(0.8, morale_modifier)

        # Injured pilots fight less effectively
        if pilot.status == PilotStatus.INJURED or pilot.injuries > 0:
            mech_power *= 0.75

        total_power += mech_power

    return round(total_power, 1)


# ── Mission Difficulty Rating ────────────────────────────────────────────

def _difficulty_rating(difficulty: int) -> float:
    """Convert a 1-5 skull difficulty into a power threshold.

    Args:
        difficulty: Contract difficulty (1-5 skulls).

    Returns:
        A float power threshold the lance must overcome.
    """
    # Each skull roughly corresponds to a lance with moderate gear
    # A fresh starting lance has ~200 power
    # 1 skull = easy patrol, 5 skulls = hardened assault force
    base_ratings = {
        1: 80.0,
        2: 140.0,
        3: 200.0,
        4: 270.0,
        5: 350.0,
    }
    return base_ratings.get(difficulty, 200.0)


# ── Success Probability ─────────────────────────────────────────────────

def calculate_success_chance(lance_power: float, difficulty: int) -> float:
    """Calculate the probability of mission success.

    A strong lance vs. low skulls almost always wins (high chance).
    A weak lance vs. high skulls almost always loses (low chance).
    The probability is clamped between 0.05 and 0.95.

    Args:
        lance_power: Calculated lance power rating.
        difficulty: Contract difficulty (1-5 skulls).

    Returns:
        A float between 0.05 and 0.95 representing success probability.
    """
    diff_rating = _difficulty_rating(difficulty)

    if diff_rating <= 0:
        return 0.95

    # Power ratio determines base success chance
    ratio = lance_power / diff_rating

    # Sigmoid-like scaling centered at ratio=1.0
    # ratio=0.5 => ~20%, ratio=1.0 => ~65%, ratio=1.5 => ~90%, ratio=2.0 => ~95%
    if ratio >= 1.0:
        chance = 0.65 + 0.30 * min(1.0, (ratio - 1.0) / 1.0)
    else:
        chance = 0.65 * ratio

    # Clamp
    return max(0.05, min(0.95, chance))


# ── Combat Resolution ───────────────────────────────────────────────────

def _determine_outcome(success_chance: float) -> CombatOutcome:
    """Roll for mission outcome based on success probability.

    Outcome distribution:
    - Victory: success_chance * 0.65 (clean win, roughly 2/3 of successes)
    - Pyrrhic Victory: success_chance * 0.35 (success but costly)
    - Defeat: 1 - success_chance

    Args:
        success_chance: Probability of success (0.0-1.0).

    Returns:
        A CombatOutcome enum value.
    """
    roll = random.random()

    victory_threshold = success_chance * 0.65
    pyrrhic_threshold = success_chance

    if roll < victory_threshold:
        return CombatOutcome.VICTORY
    elif roll < pyrrhic_threshold:
        return CombatOutcome.PYRRHIC_VICTORY
    else:
        return CombatOutcome.DEFEAT


# ── Narrative Combat Events ─────────────────────────────────────────────

# Event templates use {callsign} and {mech} as placeholders
_VICTORY_EVENTS = [
    "{callsign} lands a devastating alpha strike on an enemy {enemy_mech}!",
    "{callsign}'s {mech} delivers a punishing barrage, crippling the opposition!",
    "Enemy fire bounces harmlessly off {callsign}'s {mech} armor!",
    "{callsign} outflanks the enemy lance with superior positioning!",
    "{callsign}'s precision shots core an enemy mech - it goes down!",
    "The enemy falls back under {callsign}'s relentless assault!",
    "{callsign} leads a coordinated strike that shatters the enemy formation!",
    "{callsign}'s {mech} weaves through enemy fire untouched!",
    "A well-placed shot from {callsign} detonates an enemy ammo rack!",
    "{callsign} pushes forward aggressively, forcing the enemy to retreat!",
]

_PYRRHIC_EVENTS = [
    "{callsign}'s {mech} takes heavy fire to the left torso!",
    "{callsign} scores a hit but takes return fire to the center mass!",
    "An enemy mech lands a solid hit on {callsign}'s {mech} - armor buckling!",
    "{callsign} manages to down an enemy, but not before absorbing serious damage!",
    "Warning alarms blare in {callsign}'s cockpit as armor breaches mount!",
    "{callsign}'s {mech} staggers from a critical hit but keeps fighting!",
    "The enemy focuses fire on {callsign} - multiple armor sections compromised!",
    "{callsign} ejects just in time as {mech} takes a devastating hit!",
    "{callsign} powers through the pain of a cockpit concussion to keep firing!",
    "Shrapnel rakes {callsign}'s {mech} as an enemy mech explodes nearby!",
]

_DEFEAT_EVENTS = [
    "{callsign}'s {mech} is overwhelmed by concentrated enemy fire!",
    "The enemy lance outmaneuvers {callsign} - shots coming from all sides!",
    "{callsign} calls for retreat as {mech}'s armor is shredded!",
    "An enemy assault mech blindsides {callsign}'s {mech} with a devastating blow!",
    "{callsign} struggles to maintain control as {mech} takes critical damage!",
    "Enemy reinforcements arrive - {callsign} is outnumbered and outgunned!",
    "{callsign}'s {mech} goes down hard, smoke pouring from the reactor!",
    "The enemy commander targets {callsign} directly - it's a trap!",
    "{callsign} fights desperately but the enemy has the advantage!",
    "A lucky enemy shot hits {callsign}'s {mech} right in the cockpit!",
]

_NEUTRAL_EVENTS = [
    "The lance closes to engagement range - weapons hot!",
    "Enemy contacts confirmed on radar - {callsign} calls out targets!",
    "The battlefield erupts as both lances open fire simultaneously!",
    "{callsign} maneuvers {mech} into cover behind a rocky outcrop!",
    "Missile trails criss-cross the sky as both sides exchange LRM volleys!",
    "The ground shakes as heavy mechs trade blows at close range!",
]

_ENEMY_MECH_NAMES = [
    "Hunchback", "Wolverine", "Shadow Hawk", "Jenner", "Commando",
    "Centurion", "Thunderbolt", "Catapult", "Atlas", "BattleMaster",
    "Griffin", "Rifleman", "Marauder", "Warhammer", "Panther",
]


def _get_deployed_pairs(company: Company) -> List[Tuple[MechWarrior, BattleMech]]:
    """Get list of (pilot, mech) pairs for all deployable units.

    Only includes non-Destroyed mechs with non-KIA assigned pilots.

    Args:
        company: The player's company.

    Returns:
        List of (MechWarrior, BattleMech) tuples.
    """
    pilot_by_mech = {}
    for mw in company.mechwarriors:
        if mw.assigned_mech and mw.status != PilotStatus.KIA:
            pilot_by_mech[mw.assigned_mech] = mw

    pairs = []
    for mech in company.mechs:
        if mech.status != MechStatus.DESTROYED:
            pilot = pilot_by_mech.get(mech.name)
            if pilot:
                pairs.append((pilot, mech))

    return pairs


def generate_combat_events(
    company: Company,
    outcome: CombatOutcome,
    num_events: int = 0,
) -> List[str]:
    """Generate 4-6 narrative combat log entries for a mission.

    Events reference actual pilot callsigns and mech names from the company
    roster. The tone of events matches the outcome: positive for Victory,
    mixed for Pyrrhic Victory, negative for Defeat.

    Args:
        company: The player's company (for pilot/mech names).
        outcome: The combat outcome determining event tone.
        num_events: Number of events to generate (0 = random 4-6).

    Returns:
        A list of narrative event strings.
    """
    if num_events <= 0:
        num_events = random.randint(4, 6)

    pairs = _get_deployed_pairs(company)
    if not pairs:
        return ["The lance deploys but finds no opposition."]

    events = []

    # Select event pools based on outcome
    if outcome == CombatOutcome.VICTORY:
        # Mostly positive events, one neutral opener
        primary_pool = _VICTORY_EVENTS
        secondary_pool = _NEUTRAL_EVENTS
        primary_ratio = 0.75
    elif outcome == CombatOutcome.PYRRHIC_VICTORY:
        # Mix of positive and damage events
        primary_pool = _PYRRHIC_EVENTS
        secondary_pool = _VICTORY_EVENTS
        primary_ratio = 0.55
    else:  # DEFEAT
        # Mostly negative events
        primary_pool = _DEFEAT_EVENTS
        secondary_pool = _PYRRHIC_EVENTS
        primary_ratio = 0.70

    # Always start with a neutral opening event
    opener_pilot, opener_mech = random.choice(pairs)
    opener = random.choice(_NEUTRAL_EVENTS).format(
        callsign=opener_pilot.callsign,
        mech=opener_mech.name,
        enemy_mech=random.choice(_ENEMY_MECH_NAMES),
    )
    events.append(opener)

    # Generate remaining events
    used_templates = set()
    for i in range(num_events - 1):
        pilot, mech = random.choice(pairs)
        enemy_mech = random.choice(_ENEMY_MECH_NAMES)

        # Choose from primary or secondary pool
        if random.random() < primary_ratio:
            pool = primary_pool
        else:
            pool = secondary_pool

        # Pick a template we haven't used yet (if possible)
        available = [t for t in pool if t not in used_templates]
        if not available:
            available = pool

        template = random.choice(available)
        used_templates.add(template)

        event = template.format(
            callsign=pilot.callsign,
            mech=mech.name,
            enemy_mech=enemy_mech,
        )
        events.append(event)

    # Add a closing event based on outcome
    if outcome == CombatOutcome.VICTORY:
        events.append("All enemy forces neutralized. Mission complete - Victory!")
    elif outcome == CombatOutcome.PYRRHIC_VICTORY:
        events.append(
            "The enemy is defeated, but the cost was high. Pyrrhic Victory."
        )
    else:
        events.append(
            "Command orders a fighting withdrawal. Mission failed - Defeat."
        )

    return events


# ── Damage Application ──────────────────────────────────────────────────

def apply_damage(
    company: Company,
    outcome: CombatOutcome,
    difficulty: int,
) -> Tuple[List[MechDamageReport], List[PilotInjuryReport]]:
    """Apply combat damage to mechs and injuries to pilots.

    On Victory: No damage.
    On Pyrrhic Victory: 1-2 mechs take moderate damage, 0-1 pilot injured.
    On Defeat: 2-3 mechs take heavy damage, 1-2 pilots injured.

    A mech whose structure reaches 0 is marked Destroyed and removed
    from active duty. A destroyed mech's pilot may also be injured.

    Args:
        company: The player's company (mechs/pilots will be modified).
        outcome: The combat outcome determining damage severity.
        difficulty: Contract difficulty (1-5) scaling damage amounts.

    Returns:
        A tuple of (mech_damage_reports, pilot_injury_reports).
    """
    if outcome == CombatOutcome.VICTORY:
        return [], []

    pairs = _get_deployed_pairs(company)
    if not pairs:
        return [], []

    mech_reports = []
    pilot_reports = []

    # Determine how many mechs take damage
    if outcome == CombatOutcome.PYRRHIC_VICTORY:
        max_targets = min(2, len(pairs))
        num_damaged = random.randint(1, max(1, max_targets))
        damage_severity = 0.15 + difficulty * 0.05  # 20-40% of max armor
        injury_chance = 0.25 + difficulty * 0.05
    else:  # DEFEAT
        max_targets = min(3, len(pairs))
        num_damaged = random.randint(min(2, max_targets), max(1, max_targets))
        damage_severity = 0.25 + difficulty * 0.10  # 35-75% of max armor
        injury_chance = 0.40 + difficulty * 0.10

    # Select which mechs take damage
    targets = random.sample(pairs, min(num_damaged, len(pairs)))

    for pilot, mech in targets:
        # Calculate armor damage
        armor_damage = int(mech.armor_max * damage_severity * random.uniform(0.7, 1.3))
        armor_damage = max(1, armor_damage)

        structure_damage = 0
        destroyed = False

        # Apply armor damage
        actual_armor_damage = min(armor_damage, mech.armor_current)
        mech.armor_current -= actual_armor_damage
        remaining_damage = armor_damage - actual_armor_damage

        # If armor is gone, damage bleeds into structure
        if remaining_damage > 0 and mech.armor_current <= 0:
            mech.armor_current = 0
            structure_damage = remaining_damage
            actual_structure_damage = min(structure_damage, mech.structure_current)
            mech.structure_current -= actual_structure_damage
            structure_damage = actual_structure_damage

        # Check for destruction
        if mech.structure_current <= 0:
            mech.structure_current = 0
            mech.status = MechStatus.DESTROYED
            destroyed = True
            # Higher chance of pilot injury when mech is destroyed
            injury_chance = min(0.90, injury_chance + 0.30)
        elif mech.armor_current < mech.armor_max:
            mech.status = MechStatus.DAMAGED

        mech_reports.append(MechDamageReport(
            mech_name=mech.name,
            armor_lost=actual_armor_damage,
            structure_lost=structure_damage,
            destroyed=destroyed,
        ))

        # Roll for pilot injury
        if random.random() < injury_chance:
            injuries = 1
            # On defeat with high difficulty, chance of additional injuries
            if outcome == CombatOutcome.DEFEAT and difficulty >= 4:
                if random.random() < 0.3:
                    injuries = 2

            pilot.injuries += injuries
            pilot.status = PilotStatus.INJURED

            # Morale hit for injured pilots
            pilot.morale = max(0, pilot.morale - random.randint(5, 15))

            pilot_reports.append(PilotInjuryReport(
                callsign=pilot.callsign,
                injuries_sustained=injuries,
            ))

    # All pilots lose some morale on defeat
    if outcome == CombatOutcome.DEFEAT:
        for mw in company.mechwarriors:
            if mw.status != PilotStatus.KIA:
                mw.morale = max(0, mw.morale - random.randint(3, 8))

    return mech_reports, pilot_reports


# ── Rewards Calculation ──────────────────────────────────────────────────

def calculate_rewards(
    company: Company,
    contract: Contract,
    outcome: CombatOutcome,
) -> Tuple[int, int]:
    """Calculate C-Bills and XP rewards based on mission outcome.

    Victory: Full payout + bonus XP for all pilots.
    Pyrrhic Victory: Full payout, reduced XP.
    Defeat: 25% payout (partial compensation), minimal XP.

    Args:
        company: The player's company (pilots will gain XP).
        contract: The completed contract with payout terms.
        outcome: The combat outcome.

    Returns:
        A tuple of (c_bills_earned, xp_per_pilot).
    """
    if outcome == CombatOutcome.VICTORY:
        c_bills = contract.payout
        base_xp = 50 + contract.difficulty * 20  # 70-150 XP
        # Morale boost for victory
        morale_boost = random.randint(3, 8)
    elif outcome == CombatOutcome.PYRRHIC_VICTORY:
        c_bills = contract.payout  # Still get full pay
        base_xp = 30 + contract.difficulty * 10  # 40-80 XP
        morale_boost = random.randint(0, 3)
    else:  # DEFEAT
        c_bills = int(contract.payout * 0.25)  # Partial compensation
        base_xp = 10 + contract.difficulty * 5  # 15-35 XP (learning from failure)
        morale_boost = 0

    # Apply rewards to company
    company.c_bills += c_bills

    # Award XP and morale to all active pilots
    for mw in company.mechwarriors:
        if mw.status != PilotStatus.KIA:
            mw.experience += base_xp
            if morale_boost > 0:
                mw.morale = min(100, mw.morale + morale_boost)

    return c_bills, base_xp


# ── Full Combat Resolution ──────────────────────────────────────────────

def resolve_combat(company: Company, contract: Contract) -> MissionResult:
    """Resolve an entire mission: calculate power, determine outcome,
    generate events, apply damage, and award rewards.

    This is the main entry point for the combat system. It modifies the
    company's mechs, pilots, and C-Bills in place.

    Args:
        company: The player's company (will be modified).
        contract: The accepted contract defining difficulty and payout.

    Returns:
        A MissionResult with the full outcome details.
    """
    # Step 1: Calculate lance power
    lance_power = calculate_lance_power(company)

    # Step 2: Calculate success probability
    success_chance = calculate_success_chance(lance_power, contract.difficulty)

    # Step 3: Roll for outcome
    outcome = _determine_outcome(success_chance)

    # Step 4: Generate narrative events
    combat_log = generate_combat_events(company, outcome)

    # Track pilot KIA count before damage to detect changes
    pilots_kia_before = sum(1 for mw in company.mechwarriors if mw.status == PilotStatus.KIA)

    # Step 5: Apply damage (before rewards, so destroyed mechs are tracked)
    mech_damage, pilot_injuries = apply_damage(
        company, outcome, contract.difficulty
    )

    # Step 6: Calculate and apply rewards
    c_bills_earned, xp_earned = calculate_rewards(company, contract, outcome)

    # Step 7: Update company tracking
    company.contracts_completed += 1
    company.total_earnings += c_bills_earned
    company.week += 1
    company.month = ((company.week - 1) // 4) + 1

    # Count mechs and pilots lost in this battle
    pilots_kia = sum(1 for mw in company.mechwarriors if mw.status == PilotStatus.KIA)
    company.mechs_lost += len([d for d in mech_damage if d.destroyed])
    company.pilots_lost += pilots_kia - pilots_kia_before

    # Check if this was the final contract
    if contract.is_final_contract and outcome == CombatOutcome.VICTORY:
        company.final_contract_completed = True

    # Step 8: Clear the completed contract
    company.active_contract = None

    # Step 9: Update reputation
    if outcome == CombatOutcome.VICTORY:
        company.reputation = min(100, company.reputation + random.randint(2, 5))
    elif outcome == CombatOutcome.PYRRHIC_VICTORY:
        company.reputation = min(100, company.reputation + random.randint(0, 2))
    else:
        company.reputation = max(0, company.reputation - random.randint(1, 3))

    return MissionResult(
        outcome=outcome,
        combat_log=combat_log,
        mech_damage=mech_damage,
        pilot_injuries=pilot_injuries,
        c_bills_earned=c_bills_earned,
        xp_earned=xp_earned,
        lance_power=lance_power,
        success_chance=success_chance,
    )
