"""
ui - Terminal UI framework for Iron Contract.

Provides drawing primitives and reusable widgets for the curses-based
terminal interface.

Submodules:
    colors  - Color pair constants and initialization.
    drawing - Core drawing primitives (box, text, menu, header/status bar).
    widgets - Higher-level widgets (text input, roster table, title art).
"""

from ui.colors import (
    COLOR_NORMAL,
    COLOR_TITLE,
    COLOR_MENU_ACTIVE,
    COLOR_MENU_INACTIVE,
    COLOR_BORDER,
    COLOR_STATUS,
    COLOR_ACCENT,
    COLOR_WARNING,
    init_colors,
    color_text,
)
from ui.drawing import (
    draw_box,
    draw_centered_text,
    draw_menu,
    draw_header_bar,
    draw_status_bar,
)
from ui.widgets import (
    draw_text_input,
    draw_table_row,
    draw_roster_table,
    draw_title_art,
    draw_contract_list,
    draw_contract_briefing,
    TITLE_ART,
)

__all__ = [
    # Colors
    "COLOR_NORMAL",
    "COLOR_TITLE",
    "COLOR_MENU_ACTIVE",
    "COLOR_MENU_INACTIVE",
    "COLOR_BORDER",
    "COLOR_STATUS",
    "COLOR_ACCENT",
    "COLOR_WARNING",
    "init_colors",
    "color_text",
    # Drawing
    "draw_box",
    "draw_centered_text",
    "draw_menu",
    "draw_header_bar",
    "draw_status_bar",
    # Widgets
    "draw_text_input",
    "draw_table_row",
    "draw_roster_table",
    "draw_title_art",
    "draw_contract_list",
    "draw_contract_briefing",
    "TITLE_ART",
]
