"""
ui.widgets - Higher-level UI widgets for Iron Contract.

Provides composite drawing functions that combine multiple primitives:
- draw_text_input(): A single-line text input field with cursor.
- draw_table_row(): A fixed-width columnar table row.
- draw_roster_table(): Company roster summary (mech bay + pilot roster).
- draw_title_art(): The IRON CONTRACT ASCII art title.
"""

import curses

from ui.colors import (
    color_text,
    COLOR_ACCENT,
    COLOR_BORDER,
    COLOR_MENU_INACTIVE,
    COLOR_STATUS,
    COLOR_TITLE,
    COLOR_WARNING,
)
from ui.drawing import draw_centered_text


# ── ASCII Art Title ─────────────────────────────────────────────────────────

TITLE_ART = [
    r" _____ _____  ____  _   _    _____ ____  _   _ _______ _____            _____ _______ ",
    r"|_   _|  __ \/ __ \| \ | |  / ____/ __ \| \ | |__   __|  __ \     /\   / ____|__   __|",
    r"  | | | |__) | |  | |  \| | | |   | |  | |  \| |  | |  | |__) |   /  \ | |       | |   ",
    r"  | | |  _  /| |  | | . ` | | |   | |  | | . ` |  | |  |  _  /   / /\ \| |       | |   ",
    r" _| |_| | \ \| |__| | |\  | | |___| |__| | |\  |  | |  | | \ \  / ____ \ |____   | |   ",
    r"|_____|_|  \_\\____/|_| \_|  \_____\____/|_| \_|  |_|  |_|  \_\/_/    \_\_____|  |_|   ",
]


def draw_title_art(win, start_y):
    """Draw the IRON CONTRACT ASCII art title centered on screen.

    Args:
        win: curses window to draw on.
        start_y: Starting row for the top of the title art.
    """
    title_attr = color_text(COLOR_TITLE) | curses.A_BOLD
    for i, line in enumerate(TITLE_ART):
        draw_centered_text(win, start_y + i, line, title_attr)


# ── Text Input ─────────────────────────────────────────────────────────────

def draw_text_input(win, y, x, width, text, active=True):
    """Draw a single-line text input field.

    Renders a bordered input box with the current text value.
    When active, the cursor position is shown.

    Args:
        win: curses window to draw on.
        y: Row position of the input field.
        x: Column position of the input field.
        width: Total width of the input field (including border chars).
        text: Current text content.
        active: Whether the input is focused (shows cursor indicator).
    """
    max_h, max_w = win.getmaxyx()
    if y < 0 or y >= max_h:
        return

    border_attr = color_text(COLOR_BORDER)
    text_attr = color_text(COLOR_TITLE) | curses.A_BOLD if active else color_text(COLOR_MENU_INACTIVE)

    # Draw input border: [ text______ ]
    inner_w = width - 2
    display_text = text[:inner_w]
    padded = display_text.ljust(inner_w)

    try:
        win.addstr(y, x, "[", border_attr)
        win.addstr(y, x + 1, padded, text_attr)
        win.addstr(y, x + width - 1, "]", border_attr)
    except curses.error:
        pass

    # Show cursor as underscore after text
    if active and len(display_text) < inner_w:
        cursor_x = x + 1 + len(display_text)
        try:
            win.addstr(y, cursor_x, "_", color_text(COLOR_ACCENT) | curses.A_BOLD)
        except curses.error:
            pass


# ── Roster / Table Display ─────────────────────────────────────────────────

def draw_table_row(win, y, x, columns, col_widths, attr=0):
    """Draw a single row of a table with fixed-width columns.

    Args:
        win: curses window to draw on.
        y: Row position.
        x: Starting column position.
        columns: List of string values for each column.
        col_widths: List of integer widths for each column.
        attr: curses attribute for text.
    """
    max_h, max_w = win.getmaxyx()
    if y < 0 or y >= max_h:
        return

    offset = x
    for text, w in zip(columns, col_widths):
        truncated = str(text)[:w].ljust(w)
        try:
            win.addstr(y, offset, truncated, attr)
        except curses.error:
            pass
        offset += w + 1  # +1 for column separator space


def draw_roster_table(win, start_y, company):
    """Draw the company roster summary showing mechs and pilots.

    Displays two tables: one for the mech bay and one for the pilot roster.

    Args:
        win: curses window to draw on.
        start_y: Starting row for the roster display.
        company: A Company instance with mechs and mechwarriors.

    Returns:
        The next available row after the roster display.
    """
    max_h, max_w = win.getmaxyx()

    # ── Company Header ──
    row = start_y
    draw_centered_text(
        win, row,
        f"== {company.name} ==",
        color_text(COLOR_TITLE) | curses.A_BOLD,
    )
    row += 2

    # Company stats line
    stats_text = (
        f"C-Bills: {company.c_bills:,}  |  "
        f"Reputation: {company.reputation}/100"
    )
    draw_centered_text(win, row, stats_text, color_text(COLOR_ACCENT))
    row += 2

    # ── Mech Bay Table ──
    mech_col_widths = [24, 8, 6, 10, 5, 8]
    mech_headers = ["MECH", "CLASS", "TONS", "ARMOR", "FP", "STATUS"]
    table_width = sum(mech_col_widths) + len(mech_col_widths) - 1
    table_x = max(1, (max_w - table_width) // 2)

    draw_centered_text(
        win, row, "--- MECH BAY ---",
        color_text(COLOR_BORDER) | curses.A_BOLD,
    )
    row += 1

    draw_table_row(
        win, row, table_x, mech_headers, mech_col_widths,
        color_text(COLOR_STATUS) | curses.A_BOLD,
    )
    row += 1

    # Separator
    try:
        sep = "-" * table_width
        sep_x = max(1, (max_w - len(sep)) // 2)
        win.addstr(row, sep_x, sep, color_text(COLOR_BORDER))
    except curses.error:
        pass
    row += 1

    for mech in company.mechs:
        armor_str = f"{mech.armor_current}/{mech.armor_max}"
        cols = [
            mech.name,
            mech.weight_class.value,
            str(mech.tonnage),
            armor_str,
            str(mech.firepower),
            mech.status.value,
        ]
        status_attr = color_text(COLOR_ACCENT) if mech.status.value == "Ready" else color_text(COLOR_WARNING)
        draw_table_row(win, row, table_x, cols, mech_col_widths, status_attr)
        row += 1

    row += 1

    # ── Pilot Roster Table ──
    pilot_col_widths = [20, 12, 4, 4, 8, 24]
    pilot_headers = ["NAME", "CALLSIGN", "GUN", "PLT", "STATUS", "ASSIGNED MECH"]
    pilot_table_width = sum(pilot_col_widths) + len(pilot_col_widths) - 1
    pilot_table_x = max(1, (max_w - pilot_table_width) // 2)

    draw_centered_text(
        win, row, "--- PILOT ROSTER ---",
        color_text(COLOR_BORDER) | curses.A_BOLD,
    )
    row += 1

    draw_table_row(
        win, row, pilot_table_x, pilot_headers, pilot_col_widths,
        color_text(COLOR_STATUS) | curses.A_BOLD,
    )
    row += 1

    try:
        sep = "-" * pilot_table_width
        sep_x = max(1, (max_w - len(sep)) // 2)
        win.addstr(row, sep_x, sep, color_text(COLOR_BORDER))
    except curses.error:
        pass
    row += 1

    for mw in company.mechwarriors:
        assigned = mw.assigned_mech if mw.assigned_mech else "---"
        cols = [
            mw.name,
            mw.callsign,
            str(mw.gunnery),
            str(mw.piloting),
            mw.status.value,
            assigned,
        ]
        draw_table_row(win, row, pilot_table_x, cols, pilot_col_widths, color_text(COLOR_MENU_INACTIVE))
        row += 1

    return row
