"""
data - Game data models, templates, and generation for Iron Contract.

Submodules:
    models    - Core dataclasses (BattleMech, MechWarrior, Company, Contract).
    mechs     - BattleMech template catalog and starting lance generation.
    names     - Random MechWarrior name and callsign generation.
    contracts - Contract templates and market generation.
    combat    - Auto-resolved combat and mission outcome system.
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
from data.combat import (
    CombatOutcome,
    MechDamageReport,
    PilotInjuryReport,
    MissionResult,
    calculate_lance_power,
    calculate_success_chance,
    generate_combat_events,
    apply_damage,
    calculate_rewards,
    resolve_combat,
)
from data.finance import (
    PILOT_BASE_SALARY,
    PILOT_SKILL_BONUS,
    MECH_MAINTENANCE_BASE,
    REPAIR_COST_PER_ARMOR,
    REPAIR_COST_PER_STRUCTURE,
    PilotSalaryLine,
    MechMaintenanceLine,
    RepairLine,
    UpkeepReport,
    calculate_pilot_salary,
    calculate_mech_maintenance,
    calculate_repair_cost,
    repair_mech,
    calculate_monthly_upkeep,
    apply_upkeep,
    is_bankrupt,
)
from data.progression import (
    XP_THRESHOLDS,
    MIN_SKILL,
    NEW_PILOT_MORALE,
    MORALE_VICTORY_BOOST,
    MORALE_DEFEAT_PENALTY,
    MORALE_LOW_THRESHOLD,
    MORALE_HIGH_THRESHOLD,
    MORALE_DESERTION_THRESHOLD,
    DeserterReport,
    get_pilot_level,
    get_available_levelups,
    can_level_up,
    apply_level_up,
    get_xp_to_next_level,
    apply_morale_outcome,
    effective_gunnery,
    effective_piloting,
    get_morale_modifier_text,
    check_desertion,
    generate_desertion_message,
    recover_injuries,
    is_pilot_deployable,
    get_pilots_with_pending_levelups,
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
    # Combat
    "CombatOutcome",
    "MechDamageReport",
    "PilotInjuryReport",
    "MissionResult",
    "calculate_lance_power",
    "calculate_success_chance",
    "generate_combat_events",
    "apply_damage",
    "calculate_rewards",
    "resolve_combat",
    # Finance
    "PILOT_BASE_SALARY",
    "PILOT_SKILL_BONUS",
    "MECH_MAINTENANCE_BASE",
    "REPAIR_COST_PER_ARMOR",
    "REPAIR_COST_PER_STRUCTURE",
    "PilotSalaryLine",
    "MechMaintenanceLine",
    "RepairLine",
    "UpkeepReport",
    "calculate_pilot_salary",
    "calculate_mech_maintenance",
    "calculate_repair_cost",
    "repair_mech",
    "calculate_monthly_upkeep",
    "apply_upkeep",
    "is_bankrupt",
    # Progression
    "XP_THRESHOLDS",
    "MIN_SKILL",
    "NEW_PILOT_MORALE",
    "MORALE_VICTORY_BOOST",
    "MORALE_DEFEAT_PENALTY",
    "MORALE_LOW_THRESHOLD",
    "MORALE_HIGH_THRESHOLD",
    "MORALE_DESERTION_THRESHOLD",
    "DeserterReport",
    "get_pilot_level",
    "get_available_levelups",
    "can_level_up",
    "apply_level_up",
    "get_xp_to_next_level",
    "apply_morale_outcome",
    "effective_gunnery",
    "effective_piloting",
    "get_morale_modifier_text",
    "check_desertion",
    "generate_desertion_message",
    "recover_injuries",
    "is_pilot_deployable",
    "get_pilots_with_pending_levelups",
]
