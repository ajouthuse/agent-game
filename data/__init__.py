"""
data - Game data models, templates, and generation for Iron Contract.

Submodules:
    models    - Core dataclasses (BattleMech, MechWarrior, Company, Contract).
    mechs     - BattleMech template catalog and starting lance generation.
    names     - Random MechWarrior name and callsign generation.
    contracts - Contract templates and market generation.
"""

from data.models import (
    WeightClass,
    MechStatus,
    PilotStatus,
    MissionType,
    BattleMech,
    MechWarrior,
    Company,
    Contract,
)
from data.mechs import (
    MECH_TEMPLATES,
    STARTING_LANCE_KEYS,
    STARTING_PILOTS,
    create_mech_from_template,
    create_starting_lance,
    create_starting_pilots,
)
from data.names import (
    generate_name,
    generate_callsign,
    generate_mechwarrior,
    generate_mechwarrior_roster,
)
from data.contracts import (
    CONTRACT_TEMPLATES,
    EMPLOYERS,
    generate_contracts,
)

__all__ = [
    # Models
    "WeightClass",
    "MechStatus",
    "PilotStatus",
    "MissionType",
    "BattleMech",
    "MechWarrior",
    "Company",
    "Contract",
    # Mechs
    "MECH_TEMPLATES",
    "STARTING_LANCE_KEYS",
    "STARTING_PILOTS",
    "create_mech_from_template",
    "create_starting_lance",
    "create_starting_pilots",
    # Names
    "generate_name",
    "generate_callsign",
    "generate_mechwarrior",
    "generate_mechwarrior_roster",
    # Contracts
    "CONTRACT_TEMPLATES",
    "EMPLOYERS",
    "generate_contracts",
]
