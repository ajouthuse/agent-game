"""
data.battle - Auto-battle simulation for Iron Contract.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple

from data.models import (
    BattleMech, Company, Contract, MechStatus,
    MechWarrior, PilotStatus, WeightClass,
)


class BattleOutcome(Enum):
    """Possible battle outcomes."""
    VICTORY = "Victory"
    PYRRHIC_VICTORY = "Pyrrhic Victory"
    DEFEAT = "Defeat"


@dataclass
class EnemyMech:
    """An enemy BattleMech in combat."""
    name: str
    weight_class: WeightClass
    armor: int
    max_armor: int
    firepower: int
    gunnery: int = 4
    destroyed: bool = False


_ENEMY_MECH_TEMPLATES = {
    WeightClass.LIGHT: [
        ("Locust LCT-1V", 20, 5, 3),
        ("Commando COM-2D", 25, 6, 4),
        ("Jenner JR7-D", 35, 7, 5),
        ("Panther PNT-9R", 35, 6, 4),
    ],
    WeightClass.MEDIUM: [
        ("Cicada CDA-2A", 40, 7, 5),
        ("Blackjack BJ-1", 45, 8, 6),
        ("Shadow Hawk SHD-2H", 55, 8, 6),
        ("Wolverine WVR-6R", 55, 9, 7),
    ],
    WeightClass.HEAVY: [
        ("Catapult CPLT-C1", 65, 9, 7),
        ("Thunderbolt TDR-5S", 65, 10, 8),
        ("Warhammer WHM-6R", 70, 10, 8),
        ("Marauder MAD-3R", 75, 11, 9),
    ],
    WeightClass.ASSAULT: [
        ("Zeus ZEU-6S", 80, 11, 9),
        ("Awesome AWS-8Q", 80, 12, 10),
        ("BattleMaster BLR-1G", 85, 12, 9),
        ("Atlas AS7-D", 100, 13, 10),
    ],
}


def generate_enemy_lance(difficulty: int) -> List[EnemyMech]:
    """Generate enemy lance based on contract difficulty."""
    enemies = []

    if difficulty == 1:
        comp = [WeightClass.LIGHT, WeightClass.LIGHT]
    elif difficulty == 2:
        comp = [WeightClass.LIGHT, WeightClass.LIGHT, WeightClass.MEDIUM]
    elif difficulty == 3:
        comp = [WeightClass.MEDIUM, WeightClass.MEDIUM, WeightClass.HEAVY]
    elif difficulty == 4:
        comp = [WeightClass.HEAVY, WeightClass.HEAVY, WeightClass.MEDIUM]
    else:
        comp = [WeightClass.HEAVY, WeightClass.HEAVY, WeightClass.MEDIUM, WeightClass.MEDIUM]

    for weight_class in comp:
        templates = _ENEMY_MECH_TEMPLATES[weight_class]
        name, tonnage, firepower, gunnery = random.choice(templates)
        max_armor = tonnage * 10

        enemies.append(EnemyMech(
            name=name,
            weight_class=weight_class,
            armor=max_armor,
            max_armor=max_armor,
            firepower=firepower,
            gunnery=gunnery,
        ))

    return enemies


@dataclass
class BattleState:
    """Current state of an ongoing battle."""
    player_mechs: List[Tuple[MechWarrior, BattleMech]]
    enemy_mechs: List[EnemyMech]
    round_number: int = 1
    combat_log: List[str] = field(default_factory=list)
    player_losses: int = 0
    enemy_losses: int = 0


def _calculate_hit_chance(gunnery: int) -> float:
    """Calculate hit chance based on pilot gunnery skill."""
    base_chance = 0.60
    skill_modifier = (4 - gunnery) * 0.05
    return max(0.30, min(0.90, base_chance + skill_modifier))


def _apply_damage_to_enemy(enemy: EnemyMech, damage: int) -> Tuple[int, bool]:
    """Apply damage to an enemy mech."""
    actual_damage = min(damage, enemy.armor)
    enemy.armor -= actual_damage
    if enemy.armor <= 0:
        enemy.armor = 0
        enemy.destroyed = True
        return actual_damage, True
    return actual_damage, False


def _apply_damage_to_player(mech: BattleMech, damage: int) -> Tuple[int, int, bool]:
    """Apply damage to a player mech."""
    armor_damage = min(damage, mech.armor_current)
    mech.armor_current -= armor_damage
    remaining_damage = damage - armor_damage
    structure_damage = 0
    destroyed = False
    if remaining_damage > 0 and mech.armor_current <= 0:
        mech.armor_current = 0
        structure_damage = min(remaining_damage, mech.structure_current)
        mech.structure_current -= structure_damage
        if mech.structure_current <= 0:
            mech.structure_current = 0
            destroyed = True
    return armor_damage, structure_damage, destroyed


@dataclass
class BattleResult:
    """Result of a battle simulation."""
    outcome: BattleOutcome
    combat_log: List[str]
    c_bills_earned: int
    salvage_value: int = 0


def simulate_battle(company: Company, contract: Contract) -> BattleResult:
    """Simulate an auto-battle between player and enemy forces.

    Args:
        company: The player's Company.
        contract: The active Contract being completed.

    Returns:
        BattleResult with outcome, combat log, and earnings.
    """
    # Generate enemy lance
    enemy_mechs = generate_enemy_lance(contract.difficulty)

    # Build player units using proper pilot/mech assignment
    pilot_by_mech = {
        mw.assigned_mech: mw for mw in company.mechwarriors
        if mw.assigned_mech and mw.status == PilotStatus.ACTIVE
    }

    player_units = []
    for mech in company.mechs:
        if mech.status == MechStatus.READY:
            pilot = pilot_by_mech.get(mech.name)
            if pilot:
                player_units.append((pilot, mech))

    # Initialize battle state
    state = BattleState(
        player_mechs=player_units,
        enemy_mechs=enemy_mechs,
        combat_log=[],
    )

    state.combat_log.append(f"╔═══ BATTLE START: {contract.mission_type.value.upper()} ═══╗")
    state.combat_log.append(f"Player Lance: {len(player_units)} mechs deployed")
    state.combat_log.append(f"Enemy Force: {len(enemy_mechs)} hostile mechs detected")
    state.combat_log.append("")

    # Combat rounds
    max_rounds = 20
    while state.round_number <= max_rounds:
        # Check victory conditions
        active_player = [p for p in state.player_mechs if p[1].structure_current > 0]
        active_enemy = [e for e in state.enemy_mechs if not e.destroyed]

        if not active_player:
            state.combat_log.append("╚═══ ALL PLAYER MECHS DESTROYED - DEFEAT ═══╝")
            break
        if not active_enemy:
            state.combat_log.append("╚═══ ALL ENEMY MECHS ELIMINATED - VICTORY ═══╝")
            break

        state.combat_log.append(f"─── Round {state.round_number} ───")

        # Player attacks
        for pilot, mech in active_player:
            if mech.structure_current <= 0:
                continue

            target = random.choice(active_enemy)
            hit_chance = _calculate_hit_chance(pilot.gunnery)

            if random.random() < hit_chance:
                damage = mech.firepower
                actual_damage, destroyed = _apply_damage_to_enemy(target, damage)
                state.combat_log.append(
                    f"  {pilot.callsign} ({mech.name}) → {target.name}: {actual_damage} damage"
                )
                if destroyed:
                    state.combat_log.append(f"    >> {target.name} DESTROYED!")
                    state.enemy_losses += 1
            else:
                state.combat_log.append(f"  {pilot.callsign} ({mech.name}) → {target.name}: MISS")

        # Update active enemy list after player attacks
        active_enemy = [e for e in state.enemy_mechs if not e.destroyed]
        if not active_enemy:
            state.combat_log.append("╚═══ ALL ENEMY MECHS ELIMINATED - VICTORY ═══╝")
            break

        # Enemy attacks
        for enemy in active_enemy:
            if not active_player:
                break

            pilot, mech = random.choice(active_player)
            hit_chance = _calculate_hit_chance(enemy.gunnery)

            if random.random() < hit_chance:
                damage = enemy.firepower
                armor_dmg, struct_dmg, destroyed = _apply_damage_to_player(mech, damage)
                total_dmg = armor_dmg + struct_dmg
                state.combat_log.append(
                    f"  {enemy.name} → {pilot.callsign} ({mech.name}): {total_dmg} damage"
                )
                if destroyed:
                    state.combat_log.append(f"    >> {mech.name} DESTROYED!")
                    state.player_losses += 1

                    # Pilot ejection and survival check
                    if random.random() < 0.3:  # 30% KIA rate
                        pilot.status = PilotStatus.KIA
                        state.combat_log.append(f"    >> {pilot.callsign} KIA!")
                    else:
                        pilot.status = PilotStatus.INJURED
                        state.combat_log.append(f"    >> {pilot.callsign} ejected safely (INJURED)")

                    # Update mech status
                    mech.status = MechStatus.DESTROYED
            else:
                state.combat_log.append(f"  {enemy.name} → {pilot.callsign} ({mech.name}): MISS")

        # Update active player list after enemy attacks
        active_player = [p for p in state.player_mechs if p[1].structure_current > 0]

        state.combat_log.append("")
        state.round_number += 1

    # Determine outcome
    active_player_final = [p for p in state.player_mechs if p[1].structure_current > 0]
    active_enemy_final = [e for e in state.enemy_mechs if not e.destroyed]

    if not active_player_final:
        outcome = BattleOutcome.DEFEAT
        payment_multiplier = 0.3
    elif not active_enemy_final:
        if state.player_losses >= len(state.player_mechs) / 2:
            outcome = BattleOutcome.PYRRHIC_VICTORY
            payment_multiplier = 0.7
        else:
            outcome = BattleOutcome.VICTORY
            payment_multiplier = 1.0
    else:
        # Timeout - partial victory/defeat
        if state.enemy_losses > state.player_losses:
            outcome = BattleOutcome.PYRRHIC_VICTORY
            payment_multiplier = 0.7
        else:
            outcome = BattleOutcome.DEFEAT
            payment_multiplier = 0.3

    # Calculate payment
    c_bills_earned = int(contract.payout * payment_multiplier)
    company.c_bills += c_bills_earned

    # Calculate salvage (optional bonus)
    salvage_value = state.enemy_losses * 10_000
    company.c_bills += salvage_value

    # Update damaged mechs
    for pilot, mech in state.player_mechs:
        if mech.status != MechStatus.DESTROYED:
            if mech.armor_current < mech.armor_max or mech.structure_current < mech.structure_max:
                mech.status = MechStatus.DAMAGED

    # Advance company week
    company.week += 1

    # Clear active contract
    company.active_contract = None

    state.combat_log.append("")
    state.combat_log.append(f"Battle Complete: {outcome.value}")
    state.combat_log.append(f"Payment: {c_bills_earned:,} C-Bills")
    if salvage_value > 0:
        state.combat_log.append(f"Salvage: {salvage_value:,} C-Bills")

    return BattleResult(
        outcome=outcome,
        combat_log=state.combat_log,
        c_bills_earned=c_bills_earned,
        salvage_value=salvage_value,
    )
