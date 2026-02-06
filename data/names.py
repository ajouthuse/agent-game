"""
data.names - Random MechWarrior name and callsign generation for Iron Contract.

Provides curated lists of first names, last names, and callsigns used to
generate randomized MechWarrior identities during company creation and
recruitment.
"""

import random

from data.models import MechWarrior


# ── Name Lists ────────────────────────────────────────────────────────────

FIRST_NAMES = [
    "Alex", "Brynn", "Carlos", "Diana", "Erik",
    "Fatima", "Gideon", "Hana", "Ivan", "Jade",
    "Kai", "Lena", "Marcus", "Nadia", "Oscar",
    "Petra", "Quinn", "Riku", "Sasha", "Tomas",
    "Uma", "Victor", "Wren", "Xander", "Yara",
    "Zane", "Asha", "Declan", "Elena", "Felix",
    "Greta", "Hugo", "Ingrid", "Jasper", "Kira",
    "Leif", "Mira", "Nolan", "Opal", "Piotr",
]

LAST_NAMES = [
    "Steiner", "Kurita", "Davion", "Liao", "Marik",
    "Kerensky", "Hazen", "Pryde", "Ward", "Sortek",
    "Allard", "Kell", "Redburn", "Ardan", "Hasek",
    "Sung", "Tanaga", "Ngo", "Rivera", "Czerny",
    "Volkov", "Brandt", "Okada", "Frost", "Mercer",
    "Calloway", "Vasquez", "Ironside", "Drake", "Ashworth",
    "Takeda", "Lindholm", "Petrov", "Mbeki", "Okonkwo",
    "Chen", "Gallagher", "Torres", "Nakamura", "Johanssen",
]

CALLSIGNS = [
    "Anvil", "Blaze", "Cobra", "Dagger", "Echo",
    "Falcon", "Ghost", "Hammer", "Iceman", "Joker",
    "Knight", "Lightning", "Maverick", "Nomad", "Oracle",
    "Phoenix", "Raptor", "Spectre", "Thunder", "Viper",
    "Wolf", "Ace", "Bishop", "Cinder", "Deadbolt",
    "Ember", "Flint", "Grizzly", "Havoc", "Iron",
    "Jaguar", "Kraken", "Longbow", "Mustang", "Nitro",
    "Onyx", "Pyro", "Razor", "Sabre", "Talon",
]


# ── Generation Functions ──────────────────────────────────────────────────

def generate_name() -> str:
    """Generate a random full name from the curated lists.

    Returns:
        A string in 'First Last' format.
    """
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    return f"{first} {last}"


def generate_callsign(used: set = None) -> str:
    """Pick a random callsign, avoiding duplicates if a used set is given.

    Args:
        used: Optional set of already-used callsigns to avoid.

    Returns:
        A callsign string.
    """
    if used is None:
        used = set()
    available = [cs for cs in CALLSIGNS if cs not in used]
    if not available:
        # Fallback: append a number to a random callsign
        base = random.choice(CALLSIGNS)
        return f"{base}-{random.randint(2, 99)}"
    return random.choice(available)


def generate_mechwarrior(used_callsigns: set = None) -> MechWarrior:
    """Generate a random MechWarrior with randomized stats.

    Gunnery and piloting skills range from 3-5 (competent but not elite).
    Starting pilots are Active with no assigned mech.

    Args:
        used_callsigns: Optional set of callsigns already in use.

    Returns:
        A new MechWarrior instance.
    """
    if used_callsigns is None:
        used_callsigns = set()

    callsign = generate_callsign(used_callsigns)
    used_callsigns.add(callsign)

    return MechWarrior(
        name=generate_name(),
        callsign=callsign,
        gunnery=random.randint(3, 5),
        piloting=random.randint(3, 5),
        morale=random.randint(60, 85),
    )


def generate_mechwarrior_roster(count: int) -> list:
    """Generate a roster of unique MechWarriors.

    Ensures no duplicate callsigns within the roster.

    Args:
        count: Number of MechWarriors to generate.

    Returns:
        A list of MechWarrior instances.
    """
    used_callsigns = set()
    return [generate_mechwarrior(used_callsigns) for _ in range(count)]
