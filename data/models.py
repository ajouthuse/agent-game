"""
data.models - Core data models for Iron Contract.

Provides dataclasses for the key game entities:
- BattleMech: A combat mech with stats and status tracking.
- MechWarrior: A pilot with skills and an optional mech assignment.
- Company: The player's mercenary company containing mechs and pilots.
- Contract: A mercenary contract with mission details and payout terms.

All models support serialization to/from dictionaries for save/load.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


# ── Enumerations ──────────────────────────────────────────────────────────

class WeightClass(Enum):
    """BattleMech weight classifications."""
    LIGHT = "Light"
    MEDIUM = "Medium"
    HEAVY = "Heavy"
    ASSAULT = "Assault"


class MechStatus(Enum):
    """Operational status of a BattleMech."""
    READY = "Ready"
    DAMAGED = "Damaged"
    DESTROYED = "Destroyed"


class PilotStatus(Enum):
    """Status of a MechWarrior."""
    ACTIVE = "Active"
    INJURED = "Injured"
    KIA = "KIA"


class MissionType(Enum):
    """Type of contract mission."""
    GARRISON_DUTY = "Garrison Duty"
    RAID = "Raid"
    BASE_ASSAULT = "Base Assault"
    RECON = "Recon"


# ── BattleMech ────────────────────────────────────────────────────────────

@dataclass
class BattleMech:
    """A BattleMech with combat stats and operational status.

    Attributes:
        name: Full name/variant designation (e.g., "Wolverine WVR-6R").
        weight_class: Light, Medium, Heavy, or Assault.
        tonnage: Mech weight in tons.
        armor_current: Current armor hit points.
        armor_max: Maximum armor hit points.
        structure_current: Current internal structure hit points.
        structure_max: Maximum internal structure hit points.
        firepower: Abstract combat strength rating (1-10).
        speed: Abstract speed/mobility rating (1-10).
        status: Operational readiness.
        repair_weeks_remaining: Weeks remaining for repair (0 if not repairing).
    """

    name: str
    weight_class: WeightClass
    tonnage: int
    armor_current: int
    armor_max: int
    structure_current: int
    structure_max: int
    firepower: int
    speed: int
    status: MechStatus = MechStatus.READY
    repair_weeks_remaining: int = 0

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {
            "name": self.name,
            "weight_class": self.weight_class.value,
            "tonnage": self.tonnage,
            "armor_current": self.armor_current,
            "armor_max": self.armor_max,
            "structure_current": self.structure_current,
            "structure_max": self.structure_max,
            "firepower": self.firepower,
            "speed": self.speed,
            "status": self.status.value,
            "repair_weeks_remaining": self.repair_weeks_remaining,
        }

    @classmethod
    def from_dict(cls, d: dict) -> BattleMech:
        """Deserialize from a plain dictionary."""
        return cls(
            name=d["name"],
            weight_class=WeightClass(d["weight_class"]),
            tonnage=d["tonnage"],
            armor_current=d["armor_current"],
            armor_max=d["armor_max"],
            structure_current=d["structure_current"],
            structure_max=d["structure_max"],
            firepower=d["firepower"],
            speed=d["speed"],
            status=MechStatus(d["status"]),
            repair_weeks_remaining=d.get("repair_weeks_remaining", 0),
        )


# ── MechWarrior ───────────────────────────────────────────────────────────

@dataclass
class MechWarrior:
    """A MechWarrior (pilot) with skills and mech assignment.

    Attributes:
        name: Full name of the pilot.
        callsign: Radio callsign / nickname.
        gunnery: Gunnery skill (1-6, lower is better).
        piloting: Piloting skill (1-6, lower is better).
        morale: Pilot morale level (0-100, higher is better).
        injuries: Number of current injuries.
        experience: Accumulated experience points.
        levelups_spent: Number of level-up skill improvements already applied.
        status: Current health/operational status.
        assigned_mech: Name of the assigned BattleMech, or None.
    """

    name: str
    callsign: str
    gunnery: int
    piloting: int
    morale: int = 75
    injuries: int = 0
    experience: int = 0
    levelups_spent: int = 0
    status: PilotStatus = PilotStatus.ACTIVE
    assigned_mech: Optional[str] = None

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {
            "name": self.name,
            "callsign": self.callsign,
            "gunnery": self.gunnery,
            "piloting": self.piloting,
            "morale": self.morale,
            "injuries": self.injuries,
            "experience": self.experience,
            "levelups_spent": self.levelups_spent,
            "status": self.status.value,
            "assigned_mech": self.assigned_mech,
        }

    @classmethod
    def from_dict(cls, d: dict) -> MechWarrior:
        """Deserialize from a plain dictionary."""
        return cls(
            name=d["name"],
            callsign=d["callsign"],
            gunnery=d["gunnery"],
            piloting=d["piloting"],
            morale=d.get("morale", 75),
            injuries=d.get("injuries", 0),
            experience=d.get("experience", 0),
            levelups_spent=d.get("levelups_spent", 0),
            status=PilotStatus(d["status"]),
            assigned_mech=d.get("assigned_mech"),
        )


# ── Company ───────────────────────────────────────────────────────────────

@dataclass
class Company:
    """The player's mercenary company.

    Attributes:
        name: Company name chosen by the player.
        c_bills: Available currency (C-Bills).
        reputation: Reputation score on a 0-100 scale.
        week: Current in-game week number.
        contracts_completed: Total number of contracts completed.
        mechwarriors: Roster of hired MechWarriors.
        mechs: List of owned BattleMechs in the mech bay.
        active_contract: Currently active contract, or None.
        available_contracts: List of available contracts on the market.
    """

    name: str
    c_bills: int = 500_000
    reputation: int = 15
    week: int = 1
    contracts_completed: int = 0
    mechwarriors: List[MechWarrior] = field(default_factory=list)
    mechs: List[BattleMech] = field(default_factory=list)
    active_contract: Optional["Contract"] = None
    available_contracts: List["Contract"] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {
            "name": self.name,
            "c_bills": self.c_bills,
            "reputation": self.reputation,
            "week": self.week,
            "contracts_completed": self.contracts_completed,
            "mechwarriors": [mw.to_dict() for mw in self.mechwarriors],
            "mechs": [m.to_dict() for m in self.mechs],
            "active_contract": self.active_contract.to_dict() if self.active_contract else None,
            "available_contracts": [c.to_dict() for c in self.available_contracts],
        }

    @classmethod
    def from_dict(cls, d: dict) -> Company:
        """Deserialize from a plain dictionary."""
        return cls(
            name=d["name"],
            c_bills=d["c_bills"],
            reputation=d["reputation"],
            week=d.get("week", 1),
            contracts_completed=d.get("contracts_completed", 0),
            mechwarriors=[MechWarrior.from_dict(mw) for mw in d["mechwarriors"]],
            mechs=[BattleMech.from_dict(m) for m in d["mechs"]],
            active_contract=Contract.from_dict(d["active_contract"]) if d.get("active_contract") else None,
            available_contracts=[Contract.from_dict(c) for c in d.get("available_contracts", [])],
        )


# ── Contract ─────────────────────────────────────────────────────────────

@dataclass
class Contract:
    """A mercenary contract available for selection.

    Attributes:
        employer: Name of the hiring faction.
        mission_type: The type of mission (Garrison, Raid, etc.).
        difficulty: Difficulty rating in skulls (1-5).
        payout: Payment in C-Bills upon completion.
        salvage_rights: Percentage of battlefield salvage the company keeps (0-100).
        bonus_objective: Optional bonus objective description.
        description: Flavor text describing the mission briefing.
        duration: Contract duration in weeks (1-3).
        weeks_remaining: Countdown timer for active contracts (initialized from duration).
    """

    employer: str
    mission_type: MissionType
    difficulty: int
    payout: int
    salvage_rights: int
    bonus_objective: str
    description: str
    duration: int = 2
    weeks_remaining: int = 0

    def skulls_display(self) -> str:
        """Return a visual skull rating string like '[***--]'."""
        filled = "*" * self.difficulty
        empty = "-" * (5 - self.difficulty)
        return f"[{filled}{empty}]"

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {
            "employer": self.employer,
            "mission_type": self.mission_type.value,
            "difficulty": self.difficulty,
            "payout": self.payout,
            "salvage_rights": self.salvage_rights,
            "bonus_objective": self.bonus_objective,
            "description": self.description,
            "duration": self.duration,
            "weeks_remaining": self.weeks_remaining,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Contract:
        """Deserialize from a plain dictionary."""
        return cls(
            employer=d["employer"],
            mission_type=MissionType(d["mission_type"]),
            difficulty=d["difficulty"],
            payout=d["payout"],
            salvage_rights=d["salvage_rights"],
            bonus_objective=d["bonus_objective"],
            description=d["description"],
            duration=d.get("duration", 2),
            weeks_remaining=d.get("weeks_remaining", 0),
        )
