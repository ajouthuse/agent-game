"""
game - Game state, scene management, and gameplay logic for Iron Contract.

Submodules:
    scene  - Base Scene class for all game screens.
    scenes - Concrete scene implementations (MainMenu, CompanyName, etc.).
    state  - GameState manager with scene stack and main game loop.
"""

from game.scene import Scene
from game.scenes import (
    MainMenuScene,
    CompanyNameScene,
    RosterSummaryScene,
    HQScene,
)
from game.state import GameState

__all__ = [
    "Scene",
    "MainMenuScene",
    "CompanyNameScene",
    "RosterSummaryScene",
    "HQScene",
    "GameState",
]
