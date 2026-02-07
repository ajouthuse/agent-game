"""
data.contracts - Contract templates and market generation for Iron Contract.

Provides:
- CONTRACT_TEMPLATES: A catalog of 12+ contract templates with flavor text.
- EMPLOYERS: BattleTech faction names used as contract employers.
- generate_contracts(): Produces 3 random contracts scaled to current month.
"""

import random
from typing import List

from data.models import Contract, MissionType


# ── Employer Factions ────────────────────────────────────────────────────

EMPLOYERS = [
    "House Davion",
    "House Steiner",
    "House Liao",
    "House Marik",
    "House Kurita",
    "ComStar",
]


# ── Contract Templates ───────────────────────────────────────────────────

CONTRACT_TEMPLATES = [
    # ── Garrison Duty (easy, low pay) ──
    {
        "mission_type": MissionType.GARRISON_DUTY,
        "base_difficulty": 1,
        "base_payout": 80_000,
        "salvage_rights": 10,
        "bonus_objective": "No civilian casualties during garrison period.",
        "description": (
            "Border world needs a visible military presence. Expect light "
            "pirate activity and routine patrols. Lodging and resupply "
            "provided on-site."
        ),
    },
    {
        "mission_type": MissionType.GARRISON_DUTY,
        "base_difficulty": 1,
        "base_payout": 90_000,
        "salvage_rights": 15,
        "bonus_objective": "Repel all raids without losing a mech.",
        "description": (
            "A mining colony on the Periphery border requires protection "
            "from bandits. Intelligence suggests only light resistance, "
            "but the locals are nervous."
        ),
    },
    {
        "mission_type": MissionType.GARRISON_DUTY,
        "base_difficulty": 2,
        "base_payout": 120_000,
        "salvage_rights": 15,
        "bonus_objective": "Maintain garrison for the full contract period.",
        "description": (
            "Defend a strategic supply depot along a contested border. "
            "Previous garrison units reported minor skirmishes with "
            "unidentified raiding parties."
        ),
    },
    # ── Raid (medium risk, good pay) ──
    {
        "mission_type": MissionType.RAID,
        "base_difficulty": 2,
        "base_payout": 200_000,
        "salvage_rights": 30,
        "bonus_objective": "Destroy the ammo depot before extraction.",
        "description": (
            "Strike behind enemy lines and hit a forward supply cache. "
            "Speed is essential - get in, cause damage, and withdraw "
            "before reinforcements arrive."
        ),
    },
    {
        "mission_type": MissionType.RAID,
        "base_difficulty": 3,
        "base_payout": 280_000,
        "salvage_rights": 35,
        "bonus_objective": "Capture the enemy commander's mech intact.",
        "description": (
            "Intelligence has located an enemy staging area. Your lance "
            "will conduct a hit-and-run attack on the motor pool. "
            "Expect medium resistance and possible turret defenses."
        ),
    },
    {
        "mission_type": MissionType.RAID,
        "base_difficulty": 3,
        "base_payout": 300_000,
        "salvage_rights": 40,
        "bonus_objective": "Disable the communications array.",
        "description": (
            "A rival house has established a listening post too close "
            "for comfort. Your mission: destroy the sensor equipment "
            "and any defending forces. Watch for minefields."
        ),
    },
    # ── Base Assault (high risk, high pay) ──
    {
        "mission_type": MissionType.BASE_ASSAULT,
        "base_difficulty": 4,
        "base_payout": 500_000,
        "salvage_rights": 45,
        "bonus_objective": "Secure the base with minimal structural damage.",
        "description": (
            "Full-scale assault on an enemy firebase. Intelligence reports "
            "a reinforced lance of heavy mechs defending the perimeter. "
            "Artillery support will soften targets before your advance."
        ),
    },
    {
        "mission_type": MissionType.BASE_ASSAULT,
        "base_difficulty": 4,
        "base_payout": 550_000,
        "salvage_rights": 50,
        "bonus_objective": "Eliminate all defending forces.",
        "description": (
            "An enemy forward operating base threatens supply lines. "
            "We need it taken out. Expect heavy resistance including "
            "assault-class mechs and vehicle support."
        ),
    },
    {
        "mission_type": MissionType.BASE_ASSAULT,
        "base_difficulty": 5,
        "base_payout": 750_000,
        "salvage_rights": 50,
        "bonus_objective": "Capture the base commander alive.",
        "description": (
            "This is the big one, Commander. A fortified command center "
            "deep in enemy territory. Two full lances defend it, with "
            "armor and air support. Glory or death awaits."
        ),
    },
    # ── Recon (low risk, low pay, XP bonus) ──
    {
        "mission_type": MissionType.RECON,
        "base_difficulty": 1,
        "base_payout": 60_000,
        "salvage_rights": 5,
        "bonus_objective": "Map all enemy positions without being detected.",
        "description": (
            "Scout a remote sector and report enemy troop movements. "
            "Stealth is paramount - engage only if discovered. Fast "
            "mechs recommended for this operation."
        ),
    },
    {
        "mission_type": MissionType.RECON,
        "base_difficulty": 2,
        "base_payout": 100_000,
        "salvage_rights": 10,
        "bonus_objective": "Recover the data core from the crashed dropship.",
        "description": (
            "A DropShip went down in contested territory carrying "
            "sensitive intelligence. Retrieve the black box before "
            "the enemy does. Time is critical."
        ),
    },
    {
        "mission_type": MissionType.RECON,
        "base_difficulty": 1,
        "base_payout": 70_000,
        "salvage_rights": 5,
        "bonus_objective": "Identify the enemy lance composition.",
        "description": (
            "Long-range sensors have detected movement in the northern "
            "wastes. We need eyes on the ground to confirm what we're "
            "dealing with. Avoid contact if possible."
        ),
    },
]


# ── Difficulty Scaling ───────────────────────────────────────────────────

def _max_difficulty_for_month(month: int) -> int:
    """Return the maximum contract difficulty allowed for a given month.

    Difficulty scales gradually:
    - Months 1-3: max 2 skulls
    - Months 4-6: max 3 skulls
    - Months 7+:  max 5 skulls

    Args:
        month: The current in-game month (1-based).

    Returns:
        Maximum difficulty rating (1-5).
    """
    if month <= 3:
        return 2
    elif month <= 6:
        return 3
    else:
        return 5


def _scale_contract(template: dict, month: int) -> dict:
    """Scale a contract template's difficulty and payout for the current month.

    Difficulty may be increased by +0 or +1 based on the month, capped at 5.
    Payout scales with difficulty increases.

    Args:
        template: A contract template dictionary.
        month: The current in-game month (1-based).

    Returns:
        A new dictionary with scaled difficulty and payout.
    """
    scaled = dict(template)

    # Add a difficulty bump based on month progression
    bonus_difficulty = 0
    if month >= 4:
        bonus_difficulty = random.randint(0, 1)
    if month >= 7:
        bonus_difficulty = random.randint(0, 2)

    scaled["difficulty"] = min(5, scaled["base_difficulty"] + bonus_difficulty)

    # Scale payout proportionally to difficulty increase
    difficulty_increase = scaled["difficulty"] - scaled["base_difficulty"]
    payout_multiplier = 1.0 + (difficulty_increase * 0.3)
    # Add some randomness to payout (±15%)
    variance = random.uniform(0.85, 1.15)
    scaled["payout"] = int(scaled["base_payout"] * payout_multiplier * variance)

    return scaled


# ── Contract Generation ──────────────────────────────────────────────────

def generate_contracts(month: int, count: int = 3) -> List[Contract]:
    """Generate a set of contracts for the contract market.

    Produces the specified number of contracts from the template pool,
    scaled for the current month. Ensures variety in mission types.

    Args:
        month: The current in-game month (1-based).
        count: Number of contracts to generate (default: 3).

    Returns:
        A list of Contract instances.
    """
    max_diff = _max_difficulty_for_month(month)

    # Filter templates to those whose base difficulty fits the current month
    eligible = [
        t for t in CONTRACT_TEMPLATES
        if t["base_difficulty"] <= max_diff
    ]

    # Try to ensure variety in mission types
    selected_templates = []
    used_types = set()

    # Shuffle for randomness
    shuffled = list(eligible)
    random.shuffle(shuffled)

    # First pass: pick one of each mission type (up to count)
    for tmpl in shuffled:
        if len(selected_templates) >= count:
            break
        if tmpl["mission_type"] not in used_types:
            selected_templates.append(tmpl)
            used_types.add(tmpl["mission_type"])

    # Fill remaining slots with any eligible template
    for tmpl in shuffled:
        if len(selected_templates) >= count:
            break
        if tmpl not in selected_templates:
            selected_templates.append(tmpl)

    # If still not enough (unlikely), allow duplicates
    while len(selected_templates) < count:
        selected_templates.append(random.choice(eligible))

    # Build Contract instances
    contracts = []
    used_employers = []
    for tmpl in selected_templates:
        # Pick a unique employer if possible
        available_employers = [e for e in EMPLOYERS if e not in used_employers]
        if not available_employers:
            available_employers = EMPLOYERS
        employer = random.choice(available_employers)
        used_employers.append(employer)

        # Scale the contract
        scaled = _scale_contract(tmpl, month)

        # Generate duration (1-3 weeks)
        duration = random.randint(1, 3)

        contract = Contract(
            employer=employer,
            mission_type=scaled["mission_type"],
            difficulty=scaled["difficulty"],
            payout=scaled["payout"],
            salvage_rights=scaled["salvage_rights"],
            bonus_objective=scaled["bonus_objective"],
            description=scaled["description"],
            duration=duration,
            weeks_remaining=0,
        )
        contracts.append(contract)

    return contracts
