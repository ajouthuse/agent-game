"""
data.events - Random event system for Iron Contract.

Provides random inter-week events that create narrative moments and
tough decisions. Events have a 30% chance of triggering after advancing
a week.
"""

import random
from typing import Optional, Callable
from data.models import PilotStatus, MechStatus


# ── Event Definitions ────────────────────────────────────────────────────

class RandomEvent:
    """Represents a random inter-week event.

    Attributes:
        title: Short event title.
        description: Flavor text describing the event.
        effect_callback: Function that applies the event's mechanical effect.
        requires_choice: Whether the event requires player acceptance/decline.
        choice_prompt: Text shown for the choice (if requires_choice is True).
    """

    def __init__(self, title: str, description: str, effect_callback: Callable,
                 requires_choice: bool = False, choice_prompt: str = ""):
        self.title = title
        self.description = description
        self.effect_callback = effect_callback
        self.requires_choice = requires_choice
        self.choice_prompt = choice_prompt


# ── Event Effect Functions ───────────────────────────────────────────────

def _windfall_effect(company) -> str:
    """Award bonus C-Bills."""
    amount = 50_000
    company.c_bills += amount
    return f"Received {amount:,} C-Bills."


def _desertion_effect(company) -> str:
    """Remove the pilot with the lowest morale."""
    active_pilots = [
        mw for mw in company.mechwarriors
        if mw.status == PilotStatus.ACTIVE
    ]

    if not active_pilots:
        return "No active pilots to desert."

    # Find lowest morale pilot
    deserter = min(active_pilots, key=lambda p: p.morale)
    company.mechwarriors.remove(deserter)

    return f"{deserter.name} ({deserter.callsign}) has gone AWOL and left the company."


def _reputation_boost_effect(company) -> str:
    """Increase reputation."""
    amount = 5
    company.reputation += amount
    return f"Reputation increased by {amount}."


def _mechanics_discovery_effect(company) -> str:
    """Partially repair a damaged mech for free."""
    damaged_mechs = [
        m for m in company.mechs
        if m.status == MechStatus.DAMAGED
    ]

    if not damaged_mechs:
        return "No damaged mechs to repair."

    # Pick a random damaged mech and partially repair it
    mech = random.choice(damaged_mechs)
    repair_amount = mech.armor_max // 4  # 25% armor restoration
    mech.armor_current = min(mech.armor_max, mech.armor_current + repair_amount)

    return f"Repaired {mech.name} armor by {repair_amount} points."


def _supply_shortage_effect(company) -> str:
    """Mark that next repair will cost 2x (handled in repair logic)."""
    # This would need to be stored in company state
    # For now, just return the warning message
    return "WARNING: Spare parts prices have doubled. Next repair will cost 2x normal."


def _black_market_effect(company) -> str:
    """Offer to buy a mech at 50% discount (requires implementation)."""
    # This event requires player choice and mech purchase logic
    return "A shady dealer approaches with a mech offer..."


def _ambush_effect(company) -> str:
    """Trigger a mini-battle (requires battle system integration)."""
    # This would trigger a battle scene
    return "Pirates are attacking the DropShip! Prepare for combat!"


def _hiring_fair_effect(company) -> str:
    """Offer to hire a veteran pilot at 50% discount."""
    # This would need to integrate with hiring logic
    return "A veteran MechWarrior is available for hire at a discount."


# ── Event Pool ───────────────────────────────────────────────────────────

EVENT_POOL = [
    RandomEvent(
        title="Windfall",
        description=(
            "A grateful merchant whose convoy you once protected has sent "
            "a gift of spare parts and supplies to your company."
        ),
        effect_callback=_windfall_effect,
    ),
    RandomEvent(
        title="Desertion",
        description=(
            "One of your MechWarriors has gone AWOL. Security footage shows "
            "them leaving the DropShip in the middle of the night with a "
            "packed duffel bag."
        ),
        effect_callback=_desertion_effect,
    ),
    RandomEvent(
        title="Reputation Boost",
        description=(
            "Your last mission made the news feeds across several systems. "
            "Combat footage has gone viral, and your company's reputation "
            "has improved significantly."
        ),
        effect_callback=_reputation_boost_effect,
    ),
    RandomEvent(
        title="Mechanic's Discovery",
        description=(
            "Your chief tech has found salvageable parts in the storage bay "
            "that were written off as scrap. One of your damaged mechs has "
            "been partially repaired at no cost."
        ),
        effect_callback=_mechanics_discovery_effect,
    ),
    RandomEvent(
        title="Supply Shortage",
        description=(
            "A regional supply shortage has driven up the price of spare "
            "parts and repair materials. Your next repair will cost "
            "significantly more than usual."
        ),
        effect_callback=_supply_shortage_effect,
    ),
    RandomEvent(
        title="Black Market Deal",
        description=(
            "A shady dealer has contacted you with an offer: a 'slightly used' "
            "mech at a steep discount. No questions asked about its origin."
        ),
        effect_callback=_black_market_effect,
        requires_choice=True,
        choice_prompt="Accept the black market deal?",
    ),
    RandomEvent(
        title="Pirate Ambush",
        description=(
            "Your DropShip has been ambushed by pirates during a routine jump! "
            "Scanners detect two light mechs closing in. Your pilots are "
            "scrambling to launch a defense."
        ),
        effect_callback=_ambush_effect,
    ),
    RandomEvent(
        title="Hiring Fair",
        description=(
            "A veteran MechWarrior who lost their last company is looking for "
            "work. They're willing to sign on for half the usual hiring bonus "
            "if you can offer them a mech to pilot."
        ),
        effect_callback=_hiring_fair_effect,
        requires_choice=True,
        choice_prompt="Hire the veteran pilot?",
    ),
]


# ── Event Trigger Logic ──────────────────────────────────────────────────

EVENT_CHANCE = 0.30  # 30% chance of event per week


def should_trigger_event() -> bool:
    """Roll for whether a random event should occur.

    Returns:
        True if an event should trigger (30% chance), False otherwise.
    """
    return random.random() < EVENT_CHANCE


def get_random_event() -> Optional[RandomEvent]:
    """Select a random event from the pool.

    Returns:
        A RandomEvent instance, or None if no event should occur.
    """
    if not should_trigger_event():
        return None

    return random.choice(EVENT_POOL)


def apply_event(event: RandomEvent, company, accepted: bool = True) -> str:
    """Apply an event's effect to the company.

    Args:
        event: The RandomEvent to apply.
        company: The player's Company instance.
        accepted: Whether the player accepted the event (for choice events).

    Returns:
        A string describing the effect that was applied.
    """
    if event.requires_choice and not accepted:
        return "Declined."

    return event.effect_callback(company)
