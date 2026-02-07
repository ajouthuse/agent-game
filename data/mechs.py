"""
data.mechs - BattleMech template definitions for Iron Contract.

Provides a catalog of mech variants that can be instantiated as BattleMech
objects. Each template is a dictionary of stats that can be passed to
BattleMech's constructor.

Template mechs span Light, Medium, Heavy, and Assault weight classes,
inspired by classic BattleTech designs.
"""

from data.models import BattleMech, MechWarrior, WeightClass


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
        "structure_max": 20,
        "firepower": 2,
        "speed": 10,
    },
    "Commando COM-2D": {
        "name": "Commando COM-2D",
        "weight_class": WeightClass.LIGHT,
        "tonnage": 25,
        "armor_max": 64,
        "structure_max": 25,
        "firepower": 4,
        "speed": 8,
    },
    "Jenner JR7-D": {
        "name": "Jenner JR7-D",
        "weight_class": WeightClass.LIGHT,
        "tonnage": 35,
        "armor_max": 72,
        "structure_max": 30,
        "firepower": 5,
        "speed": 9,
    },
    "Panther PNT-9R": {
        "name": "Panther PNT-9R",
        "weight_class": WeightClass.LIGHT,
        "tonnage": 35,
        "armor_max": 88,
        "structure_max": 30,
        "firepower": 4,
        "speed": 7,
    },

    # Medium Mechs (40-55 tons)
    "Wolverine WVR-6R": {
        "name": "Wolverine WVR-6R",
        "weight_class": WeightClass.MEDIUM,
        "tonnage": 55,
        "armor_max": 136,
        "structure_max": 48,
        "firepower": 6,
        "speed": 6,
    },
    "Shadow Hawk SHD-2H": {
        "name": "Shadow Hawk SHD-2H",
        "weight_class": WeightClass.MEDIUM,
        "tonnage": 55,
        "armor_max": 128,
        "structure_max": 48,
        "firepower": 5,
        "speed": 6,
    },
    "Hunchback HBK-4G": {
        "name": "Hunchback HBK-4G",
        "weight_class": WeightClass.MEDIUM,
        "tonnage": 50,
        "armor_max": 120,
        "structure_max": 44,
        "firepower": 7,
        "speed": 5,
    },
    "Centurion CN9-A": {
        "name": "Centurion CN9-A",
        "weight_class": WeightClass.MEDIUM,
        "tonnage": 50,
        "armor_max": 128,
        "structure_max": 44,
        "firepower": 6,
        "speed": 5,
    },
    "Griffin GRF-1N": {
        "name": "Griffin GRF-1N",
        "weight_class": WeightClass.MEDIUM,
        "tonnage": 55,
        "armor_max": 120,
        "structure_max": 48,
        "firepower": 6,
        "speed": 6,
    },

    # Heavy Mechs (60-75 tons)
    "Thunderbolt TDR-5S": {
        "name": "Thunderbolt TDR-5S",
        "weight_class": WeightClass.HEAVY,
        "tonnage": 65,
        "armor_max": 176,
        "structure_max": 56,
        "firepower": 7,
        "speed": 4,
    },
    "Catapult CPLT-C1": {
        "name": "Catapult CPLT-C1",
        "weight_class": WeightClass.HEAVY,
        "tonnage": 65,
        "armor_max": 152,
        "structure_max": 56,
        "firepower": 8,
        "speed": 4,
    },
    "Marauder MAD-3R": {
        "name": "Marauder MAD-3R",
        "weight_class": WeightClass.HEAVY,
        "tonnage": 75,
        "armor_max": 200,
        "structure_max": 64,
        "firepower": 8,
        "speed": 4,
    },
    "Warhammer WHM-6R": {
        "name": "Warhammer WHM-6R",
        "weight_class": WeightClass.HEAVY,
        "tonnage": 70,
        "armor_max": 192,
        "structure_max": 60,
        "firepower": 8,
        "speed": 4,
    },

    # Assault Mechs (80-100 tons)
    "Atlas AS7-D": {
        "name": "Atlas AS7-D",
        "weight_class": WeightClass.ASSAULT,
        "tonnage": 100,
        "armor_max": 304,
        "structure_max": 80,
        "firepower": 10,
        "speed": 2,
    },
    "BattleMaster BLR-1G": {
        "name": "BattleMaster BLR-1G",
        "weight_class": WeightClass.ASSAULT,
        "tonnage": 85,
        "armor_max": 256,
        "structure_max": 68,
        "firepower": 9,
        "speed": 3,
    },
    "King Crab KGC-0000": {
        "name": "King Crab KGC-0000",
        "weight_class": WeightClass.ASSAULT,
        "tonnage": 100,
        "armor_max": 296,
        "structure_max": 80,
        "firepower": 9,
        "speed": 2,
    },
}


# ── Starting Lance Composition ────────────────────────────────────────────
# The default lance given to the player at company creation.
# 2 medium mechs + 2 light mechs.

STARTING_LANCE_KEYS = [
    "Wolverine WVR-6R",
    "Shadow Hawk SHD-2H",
    "Hunchback HBK-4G",
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
        structure_current=tmpl["structure_max"],
        structure_max=tmpl["structure_max"],
        firepower=tmpl["firepower"],
        speed=tmpl["speed"],
    )


def create_starting_lance() -> list:
    """Create the default starting lance of 4 mechs.

    Returns:
        A list of 4 BattleMech instances (3 medium, 1 light).
    """
    return [create_mech_from_template(key) for key in STARTING_LANCE_KEYS]


# ── Starting Pilot Definitions ──────────────────────────────────────────
# The hardcoded starter pilots assigned to the starting lance.

STARTING_PILOTS = [
    {
        "name": "Marcus Steiner",
        "callsign": "Ace",
        "gunnery": 3,
        "piloting": 4,
    },
    {
        "name": "Nadia Kurita",
        "callsign": "Raven",
        "gunnery": 4,
        "piloting": 3,
    },
    {
        "name": "Gideon Davion",
        "callsign": "Bulldog",
        "gunnery": 3,
        "piloting": 5,
    },
    {
        "name": "Jade Liao",
        "callsign": "Ghost",
        "gunnery": 4,
        "piloting": 3,
    },
]


def create_starting_pilots() -> list:
    """Create the hardcoded starting pilots for the starter lance.

    Returns:
        A list of 4 MechWarrior instances with preset names, callsigns,
        and skills.
    """
    return [
        MechWarrior(
            name=p["name"],
            callsign=p["callsign"],
            gunnery=p["gunnery"],
            piloting=p["piloting"],
        )
        for p in STARTING_PILOTS
    ]
