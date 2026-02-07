"""
data.save_system - Save/Load system for Iron Contract.

Provides functionality to serialize and deserialize the entire game state
to JSON files stored in ~/.ironcontract/saves/ directory.

Functions:
    save_game: Serialize Company state to a JSON save file
    load_game: Deserialize a save file into a Company instance
    list_save_files: Get a list of available save files
    get_autosave_path: Get the path to the auto-save file
    ensure_save_directory: Create the save directory if it doesn't exist
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple

from data.models import Company


def get_save_directory() -> Path:
    """Get the save directory path (~/.ironcontract/saves/).

    Returns:
        Path object pointing to the save directory.
    """
    home = Path.home()
    save_dir = home / ".ironcontract" / "saves"
    return save_dir


def ensure_save_directory() -> Path:
    """Create the save directory if it doesn't exist.

    Returns:
        Path object pointing to the save directory.
    """
    save_dir = get_save_directory()
    save_dir.mkdir(parents=True, exist_ok=True)
    return save_dir


def get_autosave_path() -> Path:
    """Get the path to the auto-save file.

    Returns:
        Path object pointing to autosave.json
    """
    return get_save_directory() / "autosave.json"


def save_game(company: Company, filename: Optional[str] = None) -> Tuple[bool, str]:
    """Save the game state to a JSON file.

    Args:
        company: The Company instance to save.
        filename: Optional filename (without path). If None, uses autosave.json

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        save_dir = ensure_save_directory()

        if filename is None:
            save_path = get_autosave_path()
        else:
            # Ensure filename has .json extension
            if not filename.endswith('.json'):
                filename += '.json'
            save_path = save_dir / filename

        # Serialize company to dict
        save_data = {
            "version": "1.0",
            "saved_at": datetime.now().isoformat(),
            "company": company.to_dict(),
        }

        # Write to file with pretty formatting
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)

        return True, f"Game saved to {save_path.name}"

    except Exception as e:
        return False, f"Failed to save game: {str(e)}"


def load_game(filename: Optional[str] = None) -> Tuple[Optional[Company], str]:
    """Load a game state from a JSON file.

    Args:
        filename: Optional filename (without path). If None, loads autosave.json

    Returns:
        Tuple of (company: Optional[Company], message: str)
        Company is None if loading failed.
    """
    try:
        save_dir = get_save_directory()

        if filename is None:
            save_path = get_autosave_path()
        else:
            # Ensure filename has .json extension
            if not filename.endswith('.json'):
                filename += '.json'
            save_path = save_dir / filename

        # Check if file exists
        if not save_path.exists():
            return None, f"Save file not found: {save_path.name}"

        # Read and parse JSON
        with open(save_path, 'r', encoding='utf-8') as f:
            save_data = json.load(f)

        # Validate save file structure
        if "company" not in save_data:
            return None, "Corrupted save file: missing company data"

        # Deserialize company
        company = Company.from_dict(save_data["company"])

        return company, f"Game loaded from {save_path.name}"

    except json.JSONDecodeError:
        return None, f"Corrupted save file: invalid JSON format"
    except Exception as e:
        return None, f"Failed to load game: {str(e)}"


def list_save_files() -> List[Tuple[str, str, datetime]]:
    """List all available save files.

    Returns:
        List of tuples (filename, company_name, saved_at).
        Returns empty list if no saves exist or directory doesn't exist.
    """
    save_dir = get_save_directory()

    if not save_dir.exists():
        return []

    saves = []

    for save_file in save_dir.glob("*.json"):
        try:
            with open(save_file, 'r', encoding='utf-8') as f:
                save_data = json.load(f)

            company_data = save_data.get("company", {})
            company_name = company_data.get("name", "Unknown")
            saved_at_str = save_data.get("saved_at", "")

            # Parse datetime
            if saved_at_str:
                saved_at = datetime.fromisoformat(saved_at_str)
            else:
                # Fall back to file modification time
                saved_at = datetime.fromtimestamp(save_file.stat().st_mtime)

            saves.append((save_file.name, company_name, saved_at))

        except Exception:
            # Skip corrupted files
            continue

    # Sort by saved_at (most recent first)
    saves.sort(key=lambda x: x[2], reverse=True)

    return saves


def autosave_exists() -> bool:
    """Check if an autosave file exists.

    Returns:
        True if autosave.json exists, False otherwise.
    """
    return get_autosave_path().exists()


def get_save_metadata(filename: Optional[str] = None) -> Optional[dict]:
    """Get metadata about a save file without fully loading it.

    Args:
        filename: Optional filename. If None, checks autosave.json

    Returns:
        Dictionary with save metadata, or None if file doesn't exist/is corrupted.
    """
    try:
        save_dir = get_save_directory()

        if filename is None:
            save_path = get_autosave_path()
        else:
            if not filename.endswith('.json'):
                filename += '.json'
            save_path = save_dir / filename

        if not save_path.exists():
            return None

        with open(save_path, 'r', encoding='utf-8') as f:
            save_data = json.load(f)

        company_data = save_data.get("company", {})

        return {
            "company_name": company_data.get("name", "Unknown"),
            "week": company_data.get("week", 1),
            "c_bills": company_data.get("c_bills", 0),
            "reputation": company_data.get("reputation", 0),
            "saved_at": save_data.get("saved_at", ""),
        }

    except Exception:
        return None
