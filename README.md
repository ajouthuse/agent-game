# Iron Contract

A terminal-based BattleTech mercenary company management simulator.

## Overview

**Iron Contract** puts you in command of a small mercenary outfit operating in the dangerous Inner Sphere. Hire MechWarriors, choose contracts, manage repairs, and keep your company financially afloat as you build your reputation across the galaxy.

## Features

- Terminal-based UI powered by Python's `curses` library
- Mercenary company management
- Contract negotiation and mission selection
- MechWarrior recruitment and management
- Financial management and repair logistics

## Requirements

- Python 3.8+
- A terminal that supports curses (most Unix terminals, Windows Terminal with appropriate setup)

## Getting Started

```bash
# Clone the repository
git clone https://github.com/ajouthuse/agent-game.git
cd agent-game

# Install dependencies
pip install -r requirements.txt

# Run the game
python main.py
```

## Controls

- **Arrow Keys (Up/Down)**: Navigate menu options
- **Enter**: Select an option
- **Escape**: Go back to previous screen
- **Q**: Quit the game

## Project Structure

```
agent-game/
├── main.py              # Entry point - launches the game
├── game/                # Game logic and scene management
│   ├── __init__.py
│   ├── scene.py         # Base Scene class for all screens
│   ├── scenes.py        # Concrete scenes (MainMenu, CompanyName, HQ, etc.)
│   └── state.py         # GameState manager with scene stack and game loop
├── ui/                  # Terminal UI framework
│   ├── __init__.py
│   ├── colors.py        # Color pair constants and initialization
│   ├── drawing.py       # Core drawing primitives (box, text, menu, bars)
│   └── widgets.py       # Higher-level widgets (text input, roster table)
├── data/                # Data models, templates, and generation
│   ├── __init__.py
│   ├── models.py        # Dataclasses (BattleMech, MechWarrior, Company)
│   ├── mechs.py         # Mech template catalog and starting lance
│   └── names.py         # Random name and callsign generation
├── tests/               # Unit tests
│   ├── __init__.py
│   └── test_models.py   # Tests for data models and generation
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

## Running Tests

```bash
python -m unittest discover -s tests -v
```

## License

This project is open source.
