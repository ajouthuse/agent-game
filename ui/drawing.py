"""
ui.drawing - Core drawing primitives for Iron Contract.

Provides low-level drawing functions for the curses terminal interface:
- draw_box(): Draw a bordered box on screen.
- draw_centered_text(): Render text centered horizontally.
- draw_menu(): Render a selectable menu with highlight.
- draw_header_bar(): Render the top header bar.
- draw_status_bar(): Render the bottom status bar with key hints.
"""

import curses

from ui.colors import color_text, COLOR_BORDER, COLOR_MENU_ACTIVE, COLOR_MENU_INACTIVE, COLOR_STATUS


def draw_box(win, y, x, height, width, title=None):
    """Draw a bordered box on the given curses window.

    Args:
        win: curses window to draw on.
        y: Top-left row position.
        x: Top-left column position.
        height: Total height of the box (including borders).
        width: Total width of the box (including borders).
        title: Optional title string to display on the top border.
    """
    max_h, max_w = win.getmaxyx()
    border_attr = color_text(COLOR_BORDER)

    # Clamp dimensions to screen
    if y + height > max_h:
        height = max_h - y
    if x + width > max_w:
        width = max_w - x
    if height < 2 or width < 2:
        return

    # Top border
    try:
        win.addch(y, x, curses.ACS_ULCORNER, border_attr)
        win.addstr(y, x + 1, "─" * (width - 2), border_attr)
        win.addch(y, x + width - 1, curses.ACS_URCORNER, border_attr)
    except curses.error:
        pass

    # Side borders
    for row in range(1, height - 1):
        try:
            win.addch(y + row, x, curses.ACS_VLINE, border_attr)
            win.addch(y + row, x + width - 1, curses.ACS_VLINE, border_attr)
        except curses.error:
            pass

    # Bottom border
    try:
        win.addch(y + height - 1, x, curses.ACS_LLCORNER, border_attr)
        win.addstr(y + height - 1, x + 1, "─" * (width - 2), border_attr)
        win.addch(y + height - 1, x + width - 1, curses.ACS_LRCORNER, border_attr)
    except curses.error:
        pass

    # Optional title
    if title:
        title_str = f" {title} "
        if len(title_str) < width - 2:
            title_x = x + (width - len(title_str)) // 2
            try:
                win.addstr(y, title_x, title_str, border_attr | curses.A_BOLD)
            except curses.error:
                pass


def draw_centered_text(win, y, text, attr=0):
    """Draw text centered horizontally on the given row.

    Args:
        win: curses window to draw on.
        y: Row position.
        text: String to display.
        attr: curses attribute (color, bold, etc.).
    """
    max_h, max_w = win.getmaxyx()
    if y < 0 or y >= max_h:
        return
    x = max(0, (max_w - len(text)) // 2)
    truncated = text[:max_w - x]
    try:
        win.addstr(y, x, truncated, attr)
    except curses.error:
        pass


def draw_menu(win, y, options, selected_index):
    """Draw a vertical list of selectable menu options.

    The currently selected option is highlighted. Options are centered
    horizontally on the screen.

    Args:
        win: curses window to draw on.
        y: Starting row for the first option.
        options: List of option label strings.
        selected_index: Index of the currently highlighted option.
    """
    for i, option in enumerate(options):
        if i == selected_index:
            attr = color_text(COLOR_MENU_ACTIVE) | curses.A_BOLD
            label = f"  > {option} <  "
        else:
            attr = color_text(COLOR_MENU_INACTIVE)
            label = f"    {option}    "
        draw_centered_text(win, y + i, label, attr)


def draw_header_bar(win, title="IRON CONTRACT"):
    """Draw the header bar across the top of the screen.

    Args:
        win: curses window to draw on.
        title: Title text to display in the header.
    """
    max_h, max_w = win.getmaxyx()
    header_attr = color_text(COLOR_STATUS) | curses.A_BOLD
    try:
        win.addstr(0, 0, " " * max_w, header_attr)
        centered_x = max(0, (max_w - len(title)) // 2)
        win.addstr(0, centered_x, title, header_attr)
    except curses.error:
        pass


def draw_status_bar(win, text="Arrow Keys: Navigate | Enter: Select | Q: Quit"):
    """Draw the status bar across the bottom of the screen.

    Args:
        win: curses window to draw on.
        text: Help text to display in the status bar.
    """
    max_h, max_w = win.getmaxyx()
    status_attr = color_text(COLOR_STATUS)
    try:
        win.addstr(max_h - 1, 0, " " * (max_w - 1), status_attr)
        win.addstr(max_h - 1, 1, text[:max_w - 2], status_attr)
    except curses.error:
        pass
