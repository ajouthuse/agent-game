"""
game - Game state, scene management, and gameplay logic for Iron Contract.

Submodules:
    scene  - Base Scene class for all game screens.
    scenes - Concrete scene implementations (MainMenu, CompanyName, etc.).
    hq     - HQ dashboard, turn cycle, and related scenes.
    state  - GameState manager with scene stack and main game loop.
"""

from game.scene import Scene
from game.scenes import (
    MainMenuScene,
    CompanyNameScene,
    RosterSummaryScene,
    HQScene,
    RosterScene,
    PilotDetailScene,
    LevelUpScene,
    DeserterScene,
    ContractMarketScene,
    ContractBriefingScene,
    MissionReportScene,
    UpkeepPhaseScene,
    FinancialSummaryScene,
    GameOverScene,
)
from game.hq import (
    WeeklySummaryScene,
    QuitConfirmScene,
    MechBayScene,
    advance_week,
    WEEKLY_PAYROLL_PER_PILOT,
)
from game.roster_screen import RosterManagementScene
from game.mechbay_screen import MechBayManagementScene
from game.state import GameState

__all__ = [
    "Scene",
    "MainMenuScene",
    "CompanyNameScene",
    "RosterSummaryScene",
    "HQScene",
    "WeeklySummaryScene",
    "QuitConfirmScene",
    "MechBayScene",
    "RosterManagementScene",
    "MechBayManagementScene",
    "advance_week",
    "WEEKLY_PAYROLL_PER_PILOT",
    "RosterScene",
    "PilotDetailScene",
    "LevelUpScene",
    "DeserterScene",
    "ContractMarketScene",
    "ContractBriefingScene",
    "MissionReportScene",
    "UpkeepPhaseScene",
    "FinancialSummaryScene",
    "GameOverScene",
    "GameState",
]
