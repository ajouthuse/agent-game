"""
data.models - Core data models for Iron Contract.

Provides dataclasses for the key game entities:
- BattleMech: A combat mech with stats and status tracking.
- MechWarrior: A pilot with skills and an optional mech assignment.
- Company: The player's mercenary company containing mechs and pilots.

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
        firepower: Abstract combat strength rating (1-10).
        status: Operational readiness.
    """

    name: str
    weight_class: WeightClass
    tonnage: int
    armor_current: int
    armor_max: int
    firepower: int
    status: MechStatus = MechStatus.READY

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {
            "name": self.name,
            "weight_class": self.weight_class.value,
            "tonnage": self.tonnage,
            "armor_current": self.armor_current,
            "armor_max": self.armor_max,
            "firepower": self.firepower,
            "status": self.status.value,
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
            firepower=d["firepower"],
            status=MechStatus(d["status"]),
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
        status: Current health/operational status.
        assigned_mech: Name of the assigned BattleMech, or None.
    """

    name: str
    callsign: str
    gunnery: int
    piloting: int
    status: PilotStatus = PilotStatus.ACTIVE
    assigned_mech: Optional[str] = None

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {
            "name": self.name,
            "callsign": self.callsign,
            "gunnery": self.gunnery,
            "piloting": self.piloting,
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
    """

    name: str
    c_bills: int = 2_000_000
    reputation: int = 15
    week: int = 1
    contracts_completed: int = 0
    mechwarriors: List[MechWarrior] = field(default_factory=list)
    mechs: List[BattleMech] = field(default_factory=list)

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
        )
