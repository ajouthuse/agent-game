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
- **Q**: Quit the game

## Project Structure

```
agent-game/
├── main.py          # Entry point - launches the game
├── game.py          # GameState class with scene management
├── ui.py            # Reusable terminal UI helpers
├── requirements.txt # Python dependencies
└── README.md        # This file
```

## License

This project is open source.
