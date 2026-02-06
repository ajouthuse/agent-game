"""
ui.colors - Color pair constants and initialization for Iron Contract.

Defines named color pair IDs and provides init_colors() to register
them with curses at startup.
"""

import curses


# ── Color Pair Constants ────────────────────────────────────────────────────

COLOR_NORMAL = 0        # Default terminal colors
COLOR_TITLE = 1          # Game title / headings
COLOR_MENU_ACTIVE = 2    # Currently highlighted menu item
COLOR_MENU_INACTIVE = 3  # Non-highlighted menu items
COLOR_BORDER = 4         # Box borders
COLOR_STATUS = 5         # Status bar text
COLOR_ACCENT = 6         # Accent / highlight text
COLOR_WARNING = 7        # Warning or alert text


def init_colors():
    """Initialize curses color pairs. Must be called after curses.start_color()."""
    curses.start_color()
    curses.use_default_colors()

    curses.init_pair(COLOR_TITLE, curses.COLOR_YELLOW, -1)
    curses.init_pair(COLOR_MENU_ACTIVE, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(COLOR_MENU_INACTIVE, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_BORDER, curses.COLOR_CYAN, -1)
    curses.init_pair(COLOR_STATUS, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(COLOR_ACCENT, curses.COLOR_GREEN, -1)
    curses.init_pair(COLOR_WARNING, curses.COLOR_RED, -1)


def color_text(color_pair_id):
    """Return the curses attribute for a given color pair ID.

    Args:
        color_pair_id: One of the COLOR_* constants defined in this module.

    Returns:
        A curses color pair attribute suitable for use with addstr().
    """
    return curses.color_pair(color_pair_id)
