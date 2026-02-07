"""
data.market - Salvage market and hiring hall systems for Iron Contract.

Provides:
- MECH_BASE_PRICES: Base purchase prices for each mech template by weight class.
- generate_salvage_market(): Produces 2-3 random mechs available for purchase.
- generate_hiring_hall(): Produces 2-3 random pilots available for hire.
- calculate_mech_price(): Calculate the price of a mech with quality variance.
- calculate_hiring_cost(): Calculate the hiring bonus for a pilot based on skill.
- can_buy_mech(): Check if the player can purchase a mech.
- can_hire_pilot(): Check if the player can hire a pilot.
- buy_mech(): Execute a mech purchase, deducting C-Bills and adding to roster.
- hire_pilot(): Execute a pilot hire, deducting C-Bills and adding to roster.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List

from data.models import BattleMech, Company, MechWarrior, WeightClass
from data.mechs import MECH_TEMPLATES, create_mech_from_template
from data.names import generate_mechwarrior


# ── Constants ─────────────────────────────────────────────────────────────

MAX_LANCE_SIZE = 4

# Base price multiplier by weight class (C-Bills per ton)
PRICE_PER_TON = {
    WeightClass.LIGHT: 4_000,
    WeightClass.MEDIUM: 5_000,
    WeightClass.HEAVY: 6_500,
    WeightClass.ASSAULT: 8_000,
}

# Additional price per firepower point
PRICE_PER_FIREPOWER = 10_000

# Hiring cost constants
HIRING_BASE_COST = 10_000
HIRING_SKILL_BONUS = 5_000  # Per skill point below 6 (lower = better = more expensive)


# ── Market Item Dataclasses ──────────────────────────────────────────────

@dataclass
class SalvageItem:
    """A mech available for purchase in the salvage market.

    Attributes:
        mech: The BattleMech instance available for sale.
        price: Purchase price in C-Bills.
    """
    mech: BattleMech
    price: int


@dataclass
class HireablePilot:
    """A pilot available for hire in the hiring hall.

    Attributes:
        pilot: The MechWarrior instance available for hire.
        hiring_cost: Hiring bonus cost in C-Bills.
    """
    pilot: MechWarrior
    hiring_cost: int


# ── Price Calculation ────────────────────────────────────────────────────

def calculate_mech_price(mech: BattleMech) -> int:
    """Calculate the purchase price of a mech based on tonnage and firepower.

    Price scales with weight class (via per-ton pricing) and firepower rating.
    A random variance of +/-10% is applied for market fluctuation.

    Args:
        mech: The BattleMech to price.

    Returns:
        Price in C-Bills.
    """
    per_ton = PRICE_PER_TON.get(mech.weight_class, 5_000)
    base_price = (mech.tonnage * per_ton) + (mech.firepower * PRICE_PER_FIREPOWER)

    # Apply random market variance (+/- 10%)
    variance = random.uniform(0.90, 1.10)
    return int(base_price * variance)


def calculate_hiring_cost(pilot: MechWarrior) -> int:
    """Calculate the hiring bonus for a pilot based on skill level.

    Better pilots (lower gunnery/piloting) cost more to hire.

    The formula:
        base + skill_bonus * (6 - gunnery) + skill_bonus * (6 - piloting)

    A gunnery 3 / piloting 3 pilot costs: 10000 + 5000*3 + 5000*3 = 40,000
    A gunnery 5 / piloting 5 pilot costs: 10000 + 5000*1 + 5000*1 = 20,000

    Args:
        pilot: The MechWarrior whose hiring cost to calculate.

    Returns:
        Hiring bonus in C-Bills.
    """
    gunnery_bonus = max(0, (6 - pilot.gunnery)) * HIRING_SKILL_BONUS
    piloting_bonus = max(0, (6 - pilot.piloting)) * HIRING_SKILL_BONUS
    return HIRING_BASE_COST + gunnery_bonus + piloting_bonus


# ── Market Generation ────────────────────────────────────────────────────

def generate_salvage_market(count: int = 0) -> List[SalvageItem]:
    """Generate a random selection of mechs available for purchase.

    Picks 2-3 random mechs from the full template catalog (or a specified
    count) and prices them based on weight and firepower.

    Args:
        count: Number of mechs to generate. If 0, randomly picks 2-3.

    Returns:
        A list of SalvageItem instances.
    """
    if count <= 0:
        count = random.randint(2, 3)

    template_keys = list(MECH_TEMPLATES.keys())
    selected_keys = random.sample(template_keys, min(count, len(template_keys)))

    items = []
    for key in selected_keys:
        mech = create_mech_from_template(key)
        price = calculate_mech_price(mech)
        items.append(SalvageItem(mech=mech, price=price))

    return items


def generate_hiring_hall(count: int = 0) -> List[HireablePilot]:
    """Generate a random selection of pilots available for hire.

    Produces 2-3 random pilots (or a specified count) with varied skills
    and calculates their hiring bonus cost.

    Args:
        count: Number of pilots to generate. If 0, randomly picks 2-3.

    Returns:
        A list of HireablePilot instances.
    """
    if count <= 0:
        count = random.randint(2, 3)

    used_callsigns = set()
    pilots = []
    for _ in range(count):
        pilot = generate_mechwarrior(used_callsigns)
        hiring_cost = calculate_hiring_cost(pilot)
        pilots.append(HireablePilot(pilot=pilot, hiring_cost=hiring_cost))

    return pilots


# ── Purchase / Hire Validation ───────────────────────────────────────────

def can_buy_mech(company: Company, price: int) -> tuple:
    """Check if the player can purchase a mech.

    Args:
        company: The player's company.
        price: The purchase price of the mech.

    Returns:
        A tuple of (can_buy: bool, reason: str). If can_buy is False,
        reason describes why.
    """
    if len(company.mechs) >= MAX_LANCE_SIZE:
        return False, "Lance is full (max 4 mechs)."
    if company.c_bills < price:
        return False, f"Not enough C-Bills ({company.c_bills:,} < {price:,})."
    return True, ""


def can_hire_pilot(company: Company, hiring_cost: int) -> tuple:
    """Check if the player can hire a pilot.

    Args:
        company: The player's company.
        hiring_cost: The hiring bonus cost.

    Returns:
        A tuple of (can_hire: bool, reason: str). If can_hire is False,
        reason describes why.
    """
    active_pilots = [
        mw for mw in company.mechwarriors
        if mw.status.value != "KIA"
    ]
    if len(active_pilots) >= MAX_LANCE_SIZE:
        return False, "Roster is full (max 4 pilots)."
    if company.c_bills < hiring_cost:
        return False, f"Not enough C-Bills ({company.c_bills:,} < {hiring_cost:,})."
    return True, ""


# ── Purchase / Hire Execution ────────────────────────────────────────────

def buy_mech(company: Company, salvage_item: SalvageItem) -> bool:
    """Execute a mech purchase, deducting C-Bills and adding to the lance.

    Args:
        company: The player's company (modified in place).
        salvage_item: The SalvageItem to purchase.

    Returns:
        True if the purchase succeeded, False otherwise.
    """
    can, _ = can_buy_mech(company, salvage_item.price)
    if not can:
        return False

    company.c_bills -= salvage_item.price
    company.mechs.append(salvage_item.mech)
    return True


def hire_pilot(company: Company, hireable: HireablePilot) -> bool:
    """Execute a pilot hire, deducting C-Bills and adding to the roster.

    Args:
        company: The player's company (modified in place).
        hireable: The HireablePilot to hire.

    Returns:
        True if the hire succeeded, False otherwise.
    """
    can, _ = can_hire_pilot(company, hireable.hiring_cost)
    if not can:
        return False

    company.c_bills -= hireable.hiring_cost
    company.mechwarriors.append(hireable.pilot)
    return True
