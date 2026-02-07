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
