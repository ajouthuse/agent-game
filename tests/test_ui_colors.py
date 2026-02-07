"""
test_ui_colors.py - Verify all ui.COLOR_* references resolve to defined constants.

Catches bugs where scenes or other modules reference color constants
(e.g. COLOR_SUCCESS, COLOR_DANGER) that were never defined in ui.colors.
"""

import ast
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ui
from ui.colors import (
    COLOR_NORMAL,
    COLOR_TITLE,
    COLOR_MENU_ACTIVE,
    COLOR_MENU_INACTIVE,
    COLOR_BORDER,
    COLOR_STATUS,
    COLOR_ACCENT,
    COLOR_WARNING,
)

# All valid COLOR_* names exported from ui
DEFINED_COLORS = {name for name in dir(ui) if name.startswith("COLOR_")}


def _find_color_refs(filepath):
    """Parse a Python file and return all `ui.COLOR_*` attribute names used."""
    with open(filepath, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=filepath)

    refs = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "ui"
            and node.attr.startswith("COLOR_")
        ):
            refs.add(node.attr)
    return refs


class TestColorConstants(unittest.TestCase):
    """Ensure every ui.COLOR_* reference in game/ and ui/ resolves."""

    def _collect_source_files(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        source_files = []
        for dirpath, _, filenames in os.walk(root):
            if "tests" in dirpath or "__pycache__" in dirpath:
                continue
            for fn in filenames:
                if fn.endswith(".py"):
                    source_files.append(os.path.join(dirpath, fn))
        return source_files

    def test_all_color_references_are_defined(self):
        """Every ui.COLOR_* used in source files must exist in the ui module."""
        undefined = {}
        for filepath in self._collect_source_files():
            refs = _find_color_refs(filepath)
            missing = refs - DEFINED_COLORS
            if missing:
                rel = os.path.relpath(filepath)
                undefined[rel] = sorted(missing)

        self.assertEqual(
            undefined,
            {},
            f"Undefined ui color constants found: {undefined}",
        )


if __name__ == "__main__":
    unittest.main()
