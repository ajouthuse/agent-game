"""
data.finance - Financial management and monthly upkeep system for Iron Contract.

Provides:
- calculate_pilot_salary(): Compute monthly salary for a pilot based on skill.
- calculate_mech_maintenance(): Compute monthly maintenance cost for a mech.
- calculate_repair_cost(): Estimate the C-Bill cost to fully repair a damaged mech.
- repair_mech(): Apply repairs to a mech, restoring armor and structure to max.
- calculate_monthly_upkeep(): Compute full monthly upkeep breakdown.
- apply_upkeep(): Deduct upkeep costs from company balance.
- UpkeepReport: Dataclass capturing the full monthly financial summary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from data.models import (
    BattleMech,
    Company,
    MechStatus,
    MechWarrior,
    PilotStatus,
    WeightClass,
)


# ── Cost Constants ─────────────────────────────────────────────────────

# Base pilot salary per month (C-Bills)
PILOT_BASE_SALARY = 5_000

# Salary multiplier per skill point below 6 (lower skill = better = more expensive)
# Gunnery and piloting are 1-6, lower is better.
# A gunnery 1 pilot costs much more than a gunnery 6 pilot.
PILOT_SKILL_BONUS = 2_500

# Base mech maintenance per month by weight class
MECH_MAINTENANCE_BASE = {
    WeightClass.LIGHT: 5_000,
    WeightClass.MEDIUM: 10_000,
    WeightClass.HEAVY: 20_000,
    WeightClass.ASSAULT: 35_000,
}

# Repair cost per point of armor restored
REPAIR_COST_PER_ARMOR = 100

# Repair cost per point of structure restored
REPAIR_COST_PER_STRUCTURE = 500


# ── Cost Calculation Functions ─────────────────────────────────────────

def calculate_pilot_salary(pilot: MechWarrior) -> int:
    """Calculate monthly salary for a pilot based on skill level.

    Better pilots (lower gunnery/piloting scores) command higher salaries.
    KIA pilots cost nothing.

    The formula:
        base_salary + skill_bonus * (6 - gunnery) + skill_bonus * (6 - piloting)

    A gunnery 1 / piloting 1 pilot costs: 5000 + 2500*5 + 2500*5 = 30,000
    A gunnery 4 / piloting 4 pilot costs: 5000 + 2500*2 + 2500*2 = 15,000
    A gunnery 6 / piloting 6 pilot costs: 5000 + 0 + 0 = 5,000

    Args:
        pilot: The MechWarrior whose salary to calculate.

    Returns:
        Monthly salary in C-Bills.
    """
    if pilot.status == PilotStatus.KIA:
        return 0

    gunnery_bonus = (6 - pilot.gunnery) * PILOT_SKILL_BONUS
    piloting_bonus = (6 - pilot.piloting) * PILOT_SKILL_BONUS
    return PILOT_BASE_SALARY + gunnery_bonus + piloting_bonus


def calculate_mech_maintenance(mech: BattleMech) -> int:
    """Calculate monthly maintenance cost for a mech based on weight class.

    Destroyed mechs still cost a reduced maintenance fee (50%) to keep
    in the bay. Heavier mechs cost more to maintain.

    Args:
        mech: The BattleMech to calculate maintenance for.

    Returns:
        Monthly maintenance cost in C-Bills.
    """
    base_cost = MECH_MAINTENANCE_BASE.get(mech.weight_class, 10_000)

    if mech.status == MechStatus.DESTROYED:
        # Reduced maintenance for storing a wreck
        return base_cost // 2

    return base_cost


def calculate_repair_cost(mech: BattleMech) -> int:
    """Calculate the cost to fully repair a damaged mech.

    Restoring armor costs REPAIR_COST_PER_ARMOR per point missing.
    Restoring structure costs REPAIR_COST_PER_STRUCTURE per point missing.
    Ready mechs and destroyed mechs have zero repair cost.
    (Destroyed mechs cannot be repaired through normal maintenance.)

    Args:
        mech: The BattleMech to estimate repair cost for.

    Returns:
        Total repair cost in C-Bills, or 0 if no repairs needed.
    """
    if mech.status == MechStatus.DESTROYED:
        return 0  # Destroyed mechs cannot be field-repaired
    if mech.status == MechStatus.READY:
        return 0  # No damage to repair

    armor_missing = mech.armor_max - mech.armor_current
    structure_missing = mech.structure_max - mech.structure_current

    armor_cost = armor_missing * REPAIR_COST_PER_ARMOR
    structure_cost = structure_missing * REPAIR_COST_PER_STRUCTURE

    return armor_cost + structure_cost


def repair_mech(mech: BattleMech) -> int:
    """Repair a damaged mech, restoring armor and structure to maximum.

    Args:
        mech: The BattleMech to repair (modified in place).

    Returns:
        The cost of the repair in C-Bills.
    """
    cost = calculate_repair_cost(mech)
    if cost > 0:
        mech.armor_current = mech.armor_max
        mech.structure_current = mech.structure_max
        mech.status = MechStatus.READY
    return cost


# ── Upkeep Report ──────────────────────────────────────────────────────

@dataclass
class PilotSalaryLine:
    """A single pilot salary line item.

    Attributes:
        name: Pilot's name.
        callsign: Pilot's callsign.
        salary: Monthly salary in C-Bills.
    """
    name: str
    callsign: str
    salary: int


@dataclass
class MechMaintenanceLine:
    """A single mech maintenance line item.

    Attributes:
        name: Mech's name.
        weight_class: Mech's weight class string.
        cost: Monthly maintenance cost in C-Bills.
    """
    name: str
    weight_class: str
    cost: int


@dataclass
class RepairLine:
    """A single mech repair line item.

    Attributes:
        mech_name: Name of the mech needing repair.
        cost: Repair cost in C-Bills.
        repaired: Whether the player chose to repair this mech.
    """
    mech_name: str
    cost: int
    repaired: bool = False


@dataclass
class UpkeepReport:
    """Full monthly financial report.

    Attributes:
        contract_income: Income from the completed contract.
        pilot_salaries: List of individual pilot salary line items.
        mech_maintenance: List of individual mech maintenance line items.
        repairs: List of repair decisions for damaged mechs.
        total_salaries: Sum of all pilot salaries.
        total_maintenance: Sum of all mech maintenance costs.
        total_repairs: Sum of all repair costs (only for repaired mechs).
        total_expenses: Total outgoing C-Bills.
        net_change: Net profit or loss (income - expenses).
        balance_before: C-Bills balance before upkeep.
        balance_after: C-Bills balance after upkeep.
    """
    contract_income: int = 0
    pilot_salaries: List[PilotSalaryLine] = field(default_factory=list)
    mech_maintenance: List[MechMaintenanceLine] = field(default_factory=list)
    repairs: List[RepairLine] = field(default_factory=list)
    total_salaries: int = 0
    total_maintenance: int = 0
    total_repairs: int = 0
    total_expenses: int = 0
    net_change: int = 0
    balance_before: int = 0
    balance_after: int = 0


# ── Upkeep Calculation ─────────────────────────────────────────────────

def calculate_monthly_upkeep(company: Company, contract_income: int) -> UpkeepReport:
    """Calculate the full monthly upkeep breakdown.

    Computes pilot salaries, mech maintenance, and repair cost estimates
    for all damaged mechs. Does NOT apply any costs yet — the player must
    first choose which repairs to approve.

    Args:
        company: The player's company.
        contract_income: C-Bills earned from the completed contract.

    Returns:
        An UpkeepReport with all line items and totals.
    """
    report = UpkeepReport()
    report.contract_income = contract_income
    report.balance_before = company.c_bills

    # Pilot salaries
    for mw in company.mechwarriors:
        salary = calculate_pilot_salary(mw)
        if salary > 0:
            report.pilot_salaries.append(PilotSalaryLine(
                name=mw.name,
                callsign=mw.callsign,
                salary=salary,
            ))
    report.total_salaries = sum(ps.salary for ps in report.pilot_salaries)

    # Mech maintenance
    for mech in company.mechs:
        maint = calculate_mech_maintenance(mech)
        report.mech_maintenance.append(MechMaintenanceLine(
            name=mech.name,
            weight_class=mech.weight_class.value,
            cost=maint,
        ))
    report.total_maintenance = sum(mm.cost for mm in report.mech_maintenance)

    # Repair estimates for damaged mechs
    for mech in company.mechs:
        cost = calculate_repair_cost(mech)
        if cost > 0:
            report.repairs.append(RepairLine(
                mech_name=mech.name,
                cost=cost,
                repaired=True,  # Default to repair; player can toggle off
            ))

    # Calculate totals (repairs default to all repaired)
    _recalculate_totals(report)

    return report


def _recalculate_totals(report: UpkeepReport):
    """Recalculate expense totals based on current repair decisions.

    Args:
        report: The UpkeepReport to update (modified in place).
    """
    report.total_repairs = sum(
        r.cost for r in report.repairs if r.repaired
    )
    report.total_expenses = (
        report.total_salaries
        + report.total_maintenance
        + report.total_repairs
    )
    report.net_change = report.contract_income - report.total_expenses
    report.balance_after = report.balance_before + report.net_change


def apply_upkeep(company: Company, report: UpkeepReport) -> None:
    """Apply the finalized upkeep costs to the company.

    Deducts expenses from C-Bills and repairs mechs that were approved.
    The company's C-Bills balance is updated to balance_after.

    Args:
        company: The player's company (modified in place).
        report: The finalized UpkeepReport with repair decisions.
    """
    # Build mech lookup by name
    mech_by_name = {m.name: m for m in company.mechs}

    # Apply repairs for approved mechs
    for repair in report.repairs:
        if repair.repaired:
            mech = mech_by_name.get(repair.mech_name)
            if mech:
                repair_mech(mech)

    # Update company balance
    company.c_bills = report.balance_after


def is_bankrupt(company: Company) -> bool:
    """Check if the company has gone bankrupt.

    Args:
        company: The player's company.

    Returns:
        True if C-Bills balance is below 0.
    """
    return company.c_bills < 0
