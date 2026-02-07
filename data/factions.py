"""
data.factions - Faction definitions for Iron Contract.

Provides faction data including color themes, preferred contract types,
and flavor descriptions for the BattleTech Great Houses and mercenary employers.
"""

from data.models import MissionType


# ── Faction Definitions ──────────────────────────────────────────────────

FACTIONS = {
    "House Davion": {
        "name": "House Davion",
        "color": "blue",
        "preferred_contracts": [MissionType.GARRISON_DUTY, MissionType.RECON],
        "description": (
            "The Federated Suns - honorable and strategic, they prefer "
            "defensive contracts and intelligence gathering missions."
        ),
    },
    "House Steiner": {
        "name": "House Steiner",
        "color": "cyan",
        "preferred_contracts": [MissionType.GARRISON_DUTY, MissionType.BASE_ASSAULT],
        "description": (
            "The Lyran Commonwealth - wealthy and industrial, they favor "
            "garrison duty and overwhelming force in major assaults."
        ),
    },
    "House Liao": {
        "name": "House Liao",
        "color": "green",
        "preferred_contracts": [MissionType.RAID, MissionType.RECON],
        "description": (
            "The Capellan Confederation - cunning and secretive, they "
            "specialize in raids and covert operations."
        ),
    },
    "House Marik": {
        "name": "House Marik",
        "color": "magenta",
        "preferred_contracts": [MissionType.RAID, MissionType.GARRISON_DUTY],
        "description": (
            "The Free Worlds League - pragmatic merchants who need both "
            "aggressive raids and defensive garrison contracts."
        ),
    },
    "House Kurita": {
        "name": "House Kurita",
        "color": "red",
        "preferred_contracts": [MissionType.RAID, MissionType.BASE_ASSAULT],
        "description": (
            "The Draconis Combine - aggressive and honor-bound, they favor "
            "bold raids and direct assaults on enemy positions."
        ),
    },
    "ComStar": {
        "name": "ComStar",
        "color": "white",
        "preferred_contracts": [MissionType.GARRISON_DUTY, MissionType.RECON],
        "description": (
            "The interstellar communications network - neutral mediators "
            "who primarily need garrison forces and reconnaissance."
        ),
    },
    "Mercenary Guild": {
        "name": "Mercenary Guild",
        "color": "yellow",
        "preferred_contracts": [MissionType.RAID, MissionType.BASE_ASSAULT, MissionType.GARRISON_DUTY, MissionType.RECON],
        "description": (
            "Independent mercenary contracts from various sources. "
            "Mission types vary widely based on client needs."
        ),
    },
}


def get_faction(name: str) -> dict:
    """Retrieve faction data by name.

    Args:
        name: The faction name (e.g., "House Davion").

    Returns:
        A dictionary containing faction data, or None if not found.
    """
    return FACTIONS.get(name)


def get_faction_color(name: str) -> str:
    """Get the color theme for a faction.

    Args:
        name: The faction name.

    Returns:
        Color name as a string (e.g., "blue"), or "white" if not found.
    """
    faction = FACTIONS.get(name)
    return faction["color"] if faction else "white"


def get_faction_description(name: str) -> str:
    """Get the flavor description for a faction.

    Args:
        name: The faction name.

    Returns:
        Description string, or empty string if not found.
    """
    faction = FACTIONS.get(name)
    return faction["description"] if faction else ""


def get_preferred_contracts(name: str) -> list:
    """Get the preferred contract types for a faction.

    Args:
        name: The faction name.

    Returns:
        A list of MissionType enums, or empty list if not found.
    """
    faction = FACTIONS.get(name)
    return faction["preferred_contracts"] if faction else []
