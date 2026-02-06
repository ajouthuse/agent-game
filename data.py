"""
data.py - BattleMech template definitions for Iron Contract.

Provides a catalog of mech variants that can be instantiated as BattleMech
objects. Each template is a dictionary of stats that can be passed to
BattleMech's constructor.

Template mechs span Light, Medium, Heavy, and Assault weight classes,
inspired by classic BattleTech designs.
"""

from models import BattleMech, WeightClass


# ── Mech Templates ────────────────────────────────────────────────────────
# Each template defines stats for a mech variant.
# Firepower is an abstract 1-10 combat strength rating.

MECH_TEMPLATES = {
    # Light Mechs (20-35 tons)
    "Locust LCT-1V": {
        "name": "Locust LCT-1V",
        "weight_class": WeightClass.LIGHT,
        "tonnage": 20,
        "armor_max": 48,
        "firepower": 2,
    },
    "Commando COM-2D": {
        "name": "Commando COM-2D",
        "weight_class": WeightClass.LIGHT,
        "tonnage": 25,
        "armor_max": 64,
        "firepower": 4,
    },
    "Jenner JR7-D": {
        "name": "Jenner JR7-D",
        "weight_class": WeightClass.LIGHT,
        "tonnage": 35,
        "armor_max": 72,
        "firepower": 5,
    },

    # Medium Mechs (40-55 tons)
    "Wolverine WVR-6R": {
        "name": "Wolverine WVR-6R",
        "weight_class": WeightClass.MEDIUM,
        "tonnage": 55,
        "armor_max": 136,
        "firepower": 6,
    },
    "Shadow Hawk SHD-2H": {
        "name": "Shadow Hawk SHD-2H",
        "weight_class": WeightClass.MEDIUM,
        "tonnage": 55,
        "armor_max": 128,
        "firepower": 5,
    },
    "Hunchback HBK-4G": {
        "name": "Hunchback HBK-4G",
        "weight_class": WeightClass.MEDIUM,
        "tonnage": 50,
        "armor_max": 120,
        "firepower": 7,
    },
    "Centurion CN9-A": {
        "name": "Centurion CN9-A",
        "weight_class": WeightClass.MEDIUM,
        "tonnage": 50,
        "armor_max": 128,
        "firepower": 6,
    },

    # Heavy Mechs (60-75 tons)
    "Thunderbolt TDR-5S": {
        "name": "Thunderbolt TDR-5S",
        "weight_class": WeightClass.HEAVY,
        "tonnage": 65,
        "armor_max": 176,
        "firepower": 7,
    },
    "Catapult CPLT-C1": {
        "name": "Catapult CPLT-C1",
        "weight_class": WeightClass.HEAVY,
        "tonnage": 65,
        "armor_max": 152,
        "firepower": 8,
    },

    # Assault Mechs (80-100 tons)
    "Atlas AS7-D": {
        "name": "Atlas AS7-D",
        "weight_class": WeightClass.ASSAULT,
        "tonnage": 100,
        "armor_max": 304,
        "firepower": 10,
    },
    "BattleMaster BLR-1G": {
        "name": "BattleMaster BLR-1G",
        "weight_class": WeightClass.ASSAULT,
        "tonnage": 85,
        "armor_max": 256,
        "firepower": 9,
    },
}


# ── Starting Lance Composition ────────────────────────────────────────────
# The default lance given to the player at company creation.
# 2 medium mechs + 2 light mechs.

STARTING_LANCE_KEYS = [
    "Wolverine WVR-6R",
    "Shadow Hawk SHD-2H",
    "Jenner JR7-D",
    "Commando COM-2D",
]


def create_mech_from_template(template_key: str) -> BattleMech:
    """Create a fresh BattleMech instance from a named template.

    The mech starts at full armor and Ready status.

    Args:
        template_key: Key into MECH_TEMPLATES (e.g., "Wolverine WVR-6R").

    Returns:
        A new BattleMech instance.

    Raises:
        KeyError: If template_key is not found in MECH_TEMPLATES.
    """
    tmpl = MECH_TEMPLATES[template_key]
    return BattleMech(
        name=tmpl["name"],
        weight_class=tmpl["weight_class"],
        tonnage=tmpl["tonnage"],
        armor_current=tmpl["armor_max"],
        armor_max=tmpl["armor_max"],
        firepower=tmpl["firepower"],
    )


def create_starting_lance() -> list:
    """Create the default starting lance of 4 mechs.

    Returns:
        A list of 4 BattleMech instances (2 medium, 2 light).
    """
    return [create_mech_from_template(key) for key in STARTING_LANCE_KEYS]
