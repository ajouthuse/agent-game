#!/usr/bin/env python3
"""
main.py - Entry point for Iron Contract.

Iron Contract is a terminal-based BattleTech mercenary company management
simulator. This module initializes the curses environment and starts the
main game loop.

Usage:
    python main.py
"""

import curses
import sys

from game.state import GameState


def main():
    """Launch the Iron Contract game."""
    game_state = GameState()

    try:
        curses.wrapper(game_state.run)
    except KeyboardInterrupt:
        pass  # Clean exit on Ctrl+C
    except curses.error as e:
        print(f"Terminal error: {e}", file=sys.stderr)
        print("Make sure your terminal window is large enough (at least 80x24).",
              file=sys.stderr)
        sys.exit(1)

    print("Thanks for playing Iron Contract!")


if __name__ == "__main__":
    main()
