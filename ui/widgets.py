"""
ui.widgets - Higher-level UI widgets for Iron Contract.

Provides composite drawing functions that combine multiple primitives:
- draw_text_input(): A single-line text input field with cursor.
- draw_table_row(): A fixed-width columnar table row.
- draw_roster_table(): Company roster summary (mech bay + pilot roster).
- draw_title_art(): The IRON CONTRACT ASCII art title.
- draw_contract_list(): Selectable list of contracts for the market screen.
- draw_contract_briefing(): Detailed contract briefing panel.
- draw_mission_report(): Mission report with combat log and summary.
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
from ui.drawing import draw_centered_text, draw_box


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

    Displays a combined lance roster table with mech info and assigned
    pilot info side by side, followed by armor percentage and damage
    indicators.

    Damaged mechs show a [!] warning indicator and are colored red.
    Destroyed mechs show a [X] indicator.

    Args:
        win: curses window to draw on.
        start_y: Starting row for the roster display.
        company: A Company instance with mechs and mechwarriors.

    Returns:
        The next available row after the roster display.
    """
    max_h, max_w = win.getmaxyx()

    # Build a lookup of pilot callsigns by assigned mech name
    pilot_by_mech = {}
    for mw in company.mechwarriors:
        if mw.assigned_mech:
            pilot_by_mech[mw.assigned_mech] = mw

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

    # ── Lance Roster Table (combined mech + pilot view) ──
    lance_col_widths = [22, 6, 8, 10, 4, 5, 8]
    lance_headers = ["MECH", "TONS", "PILOT", "ARMOR %", "GUN", "PLT", "STATUS"]
    table_width = sum(lance_col_widths) + len(lance_col_widths) - 1
    table_x = max(1, (max_w - table_width) // 2)

    draw_centered_text(
        win, row, "--- LANCE ROSTER ---",
        color_text(COLOR_BORDER) | curses.A_BOLD,
    )
    row += 1

    draw_table_row(
        win, row, table_x, lance_headers, lance_col_widths,
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
        pilot = pilot_by_mech.get(mech.name)
        pilot_callsign = pilot.callsign if pilot else "---"
        pilot_gun = str(pilot.gunnery) if pilot else "-"
        pilot_plt = str(pilot.piloting) if pilot else "-"

        # Calculate armor percentage
        armor_pct = int((mech.armor_current / mech.armor_max) * 100) if mech.armor_max > 0 else 0
        armor_str = f"{armor_pct}%"

        # Status with damage indicator
        if mech.status.value == "Destroyed":
            status_str = "[X] DEST"
        elif mech.status.value == "Damaged":
            status_str = "[!] DMG"
        else:
            status_str = "Ready"

        cols = [
            mech.name,
            str(mech.tonnage),
            pilot_callsign,
            armor_str,
            pilot_gun,
            pilot_plt,
            status_str,
        ]

        # Color based on mech status
        if mech.status.value == "Destroyed":
            row_attr = color_text(COLOR_WARNING) | curses.A_BOLD
        elif mech.status.value == "Damaged":
            row_attr = color_text(COLOR_WARNING)
        else:
            row_attr = color_text(COLOR_ACCENT)

        draw_table_row(win, row, table_x, cols, lance_col_widths, row_attr)
        row += 1

    row += 1

    # ── Mech Bay Detail Table ──
    mech_col_widths = [22, 8, 6, 10, 10, 4, 4, 8]
    mech_headers = ["MECH", "CLASS", "TONS", "ARMOR", "STRUCT", "FP", "SPD", "STATUS"]
    mech_table_width = sum(mech_col_widths) + len(mech_col_widths) - 1
    mech_table_x = max(1, (max_w - mech_table_width) // 2)

    draw_centered_text(
        win, row, "--- MECH BAY ---",
        color_text(COLOR_BORDER) | curses.A_BOLD,
    )
    row += 1

    draw_table_row(
        win, row, mech_table_x, mech_headers, mech_col_widths,
        color_text(COLOR_STATUS) | curses.A_BOLD,
    )
    row += 1

    try:
        sep = "-" * mech_table_width
        sep_x = max(1, (max_w - len(sep)) // 2)
        win.addstr(row, sep_x, sep, color_text(COLOR_BORDER))
    except curses.error:
        pass
    row += 1

    for mech in company.mechs:
        armor_str = f"{mech.armor_current}/{mech.armor_max}"
        struct_str = f"{mech.structure_current}/{mech.structure_max}"

        # Status with damage indicator
        if mech.status.value == "Destroyed":
            status_str = "[X] DEST"
        elif mech.status.value == "Damaged":
            status_str = "[!] DMG"
        else:
            status_str = "Ready"

        cols = [
            mech.name,
            mech.weight_class.value,
            str(mech.tonnage),
            armor_str,
            struct_str,
            str(mech.firepower),
            str(mech.speed),
            status_str,
        ]

        if mech.status.value == "Destroyed":
            row_attr = color_text(COLOR_WARNING) | curses.A_BOLD
        elif mech.status.value == "Damaged":
            row_attr = color_text(COLOR_WARNING)
        else:
            row_attr = color_text(COLOR_ACCENT)

        draw_table_row(win, row, mech_table_x, cols, mech_col_widths, row_attr)
        row += 1

    row += 1

    # ── Pilot Roster Table ──
    pilot_col_widths = [18, 10, 4, 4, 8, 22]
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
        # Color injured/KIA pilots with warning color
        if mw.status.value == "KIA":
            pilot_attr = color_text(COLOR_WARNING) | curses.A_BOLD
        elif mw.status.value == "Injured":
            pilot_attr = color_text(COLOR_WARNING)
        else:
            pilot_attr = color_text(COLOR_MENU_INACTIVE)
        draw_table_row(win, row, pilot_table_x, cols, pilot_col_widths, pilot_attr)
        row += 1

    return row


# ── Contract Market Display ───────────────────────────────────────────────

def draw_contract_list(win, start_y, contracts, selected_index):
    """Draw a list of available contracts in the contract market.

    Shows each contract as a row with mission type, employer, difficulty
    (skull rating), and payout. The selected contract is highlighted.

    Args:
        win: curses window to draw on.
        start_y: Starting row for the list.
        contracts: List of Contract instances to display.
        selected_index: Index of the currently highlighted contract.

    Returns:
        The next available row after the contract list.
    """
    max_h, max_w = win.getmaxyx()
    row = start_y

    # Column layout: Type, Employer, Difficulty, Payout, Salvage
    col_widths = [16, 16, 9, 12, 9]
    headers = ["MISSION", "EMPLOYER", "DIFF", "PAYOUT", "SALVAGE"]
    table_width = sum(col_widths) + len(col_widths) - 1
    table_x = max(1, (max_w - table_width) // 2)

    # Header row
    draw_table_row(
        win, row, table_x, headers, col_widths,
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

    for i, contract in enumerate(contracts):
        skulls = contract.skulls_display()
        payout_str = f"{contract.payout:,} CB"
        salvage_str = f"{contract.salvage_rights}%"

        cols = [
            contract.mission_type.value,
            contract.employer,
            skulls,
            payout_str,
            salvage_str,
        ]

        if i == selected_index:
            row_attr = color_text(COLOR_ACCENT) | curses.A_BOLD
            # Draw selection indicator
            indicator_x = table_x - 2
            if indicator_x >= 0:
                try:
                    win.addstr(row, indicator_x, ">", row_attr)
                except curses.error:
                    pass
        else:
            row_attr = color_text(COLOR_MENU_INACTIVE)

        draw_table_row(win, row, table_x, cols, col_widths, row_attr)
        row += 1

    return row


def draw_contract_briefing(win, start_y, contract):
    """Draw a detailed contract briefing panel.

    Shows full contract details including mission type, employer,
    difficulty, payout, salvage rights, bonus objective, and
    the flavor text description.

    Args:
        win: curses window to draw on.
        start_y: Starting row for the briefing panel.
        contract: A Contract instance to display.

    Returns:
        The next available row after the briefing panel.
    """
    max_h, max_w = win.getmaxyx()

    # Briefing box
    box_w = min(66, max_w - 4)
    box_x = max(1, (max_w - box_w) // 2)
    inner_x = box_x + 2
    inner_w = box_w - 4

    # Calculate box height based on content
    # We need: title, blank, type, employer, diff, payout, salvage,
    #          blank, description (wrapped), blank, bonus, blank
    desc_lines = _wrap_text(contract.description, inner_w)
    bonus_lines = _wrap_text(
        f"BONUS: {contract.bonus_objective}", inner_w
    )
    box_h = 10 + len(desc_lines) + len(bonus_lines)

    if start_y + box_h >= max_h:
        box_h = max_h - start_y - 1

    draw_box(win, start_y, box_x, box_h, box_w, title="Mission Briefing")

    row = start_y + 1

    # Mission type and employer
    title_text = f"{contract.mission_type.value} - {contract.employer}"
    draw_centered_text(
        win, row, title_text,
        color_text(COLOR_TITLE) | curses.A_BOLD,
    )
    row += 2

    # Stats
    skulls = contract.skulls_display()
    _draw_briefing_line(win, row, inner_x, "Difficulty:", skulls, inner_w)
    row += 1

    payout_str = f"{contract.payout:,} C-Bills"
    _draw_briefing_line(win, row, inner_x, "Payout:", payout_str, inner_w)
    row += 1

    salvage_str = f"{contract.salvage_rights}%"
    _draw_briefing_line(win, row, inner_x, "Salvage Rights:", salvage_str, inner_w)
    row += 2

    # Description
    for line in desc_lines:
        if 0 <= row < max_h:
            try:
                win.addstr(row, inner_x, line[:inner_w], color_text(COLOR_MENU_INACTIVE))
            except curses.error:
                pass
        row += 1

    row += 1

    # Bonus objective
    for line in bonus_lines:
        if 0 <= row < max_h:
            try:
                win.addstr(row, inner_x, line[:inner_w], color_text(COLOR_ACCENT))
            except curses.error:
                pass
        row += 1

    return row + 1


def _draw_briefing_line(win, y, x, label, value, max_width):
    """Draw a label: value line in the briefing panel.

    Args:
        win: curses window to draw on.
        y: Row position.
        x: Column position.
        label: The label text (e.g., "Payout:").
        value: The value text (e.g., "500,000 C-Bills").
        max_width: Maximum available width.
    """
    max_h, max_w = win.getmaxyx()
    if y < 0 or y >= max_h:
        return

    try:
        win.addstr(y, x, label, color_text(COLOR_BORDER) | curses.A_BOLD)
        value_x = x + len(label) + 1
        win.addstr(y, value_x, value[:max_width - len(label) - 1],
                   color_text(COLOR_TITLE))
    except curses.error:
        pass


def _wrap_text(text, width):
    """Wrap text to fit within the given width.

    Args:
        text: The text to wrap.
        width: Maximum line width.

    Returns:
        A list of strings, each no longer than width.
    """
    if width <= 0:
        return [text]

    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        if current_line:
            test_line = current_line + " " + word
        else:
            test_line = word

        if len(test_line) <= width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word[:width]

    if current_line:
        lines.append(current_line)

    return lines if lines else [""]


# ── Mission Report Display ───────────────────────────────────────────────

def draw_mission_report(win, start_y, result, visible_events, scroll_offset=0):
    """Draw the mission report screen with combat log and summary.

    Shows combat log entries up to visible_events count (for dramatic
    press-any-key pacing), followed by a summary panel showing outcome,
    damage, injuries, and rewards once all events are revealed.

    Args:
        win: curses window to draw on.
        start_y: Starting row for the report.
        result: A MissionResult instance from data.combat.
        visible_events: Number of combat log entries currently visible.
        scroll_offset: Vertical scroll offset for long reports.

    Returns:
        The next available row after the report display.
    """
    max_h, max_w = win.getmaxyx()
    row = start_y - scroll_offset

    # ── Outcome Banner ──
    outcome_text = f"=== MISSION OUTCOME: {result.outcome.value.upper()} ==="
    if result.outcome.value == "Victory":
        outcome_attr = color_text(COLOR_ACCENT) | curses.A_BOLD
    elif result.outcome.value == "Pyrrhic Victory":
        outcome_attr = color_text(COLOR_TITLE) | curses.A_BOLD
    else:
        outcome_attr = color_text(COLOR_WARNING) | curses.A_BOLD
    draw_centered_text(win, row, outcome_text, outcome_attr)
    row += 1

    # Lance power and success chance info
    info_text = (
        f"Lance Power: {result.lance_power:.0f} | "
        f"Success Chance: {result.success_chance * 100:.0f}%"
    )
    draw_centered_text(win, row, info_text, color_text(COLOR_MENU_INACTIVE))
    row += 2

    # ── Combat Log ──
    draw_centered_text(
        win, row, "--- COMBAT LOG ---",
        color_text(COLOR_BORDER) | curses.A_BOLD,
    )
    row += 1

    log_width = min(70, max_w - 6)
    log_x = max(2, (max_w - log_width) // 2)

    for i, event in enumerate(result.combat_log):
        if i >= visible_events:
            break

        # Wrap long event text
        wrapped = _wrap_text(event, log_width)
        for line in wrapped:
            if 0 <= row < max_h - 1:
                # Color events based on content tone
                if i == len(result.combat_log) - 1:
                    # Final event (outcome summary) gets outcome color
                    event_attr = outcome_attr
                else:
                    event_attr = color_text(COLOR_MENU_INACTIVE)
                try:
                    prefix = f"  [{i + 1}] " if line == wrapped[0] else "      "
                    win.addstr(row, log_x, prefix, color_text(COLOR_BORDER))
                    win.addstr(row, log_x + len(prefix), line[:log_width - len(prefix)],
                               event_attr)
                except curses.error:
                    pass
            row += 1
        row += 1  # Blank line between events

    # Show "press any key" prompt if not all events visible
    all_events_visible = visible_events >= len(result.combat_log)

    if not all_events_visible:
        if 0 <= row < max_h - 1:
            draw_centered_text(
                win, row,
                "[ Press any key to continue... ]",
                color_text(COLOR_TITLE) | curses.A_BOLD,
            )
        row += 2
        return row

    # ── Summary Panel (shown after all events are revealed) ──
    row += 1
    draw_centered_text(
        win, row, "--- MISSION SUMMARY ---",
        color_text(COLOR_BORDER) | curses.A_BOLD,
    )
    row += 2

    summary_w = min(60, max_w - 6)
    summary_x = max(2, (max_w - summary_w) // 2)

    # Rewards
    if 0 <= row < max_h - 1:
        _draw_summary_line(win, row, summary_x, "C-Bills Earned:",
                           f"{result.c_bills_earned:,}", summary_w)
    row += 1

    if 0 <= row < max_h - 1:
        _draw_summary_line(win, row, summary_x, "XP Earned:",
                           f"{result.xp_earned} per pilot", summary_w)
    row += 2

    # Mech Damage
    if result.mech_damage:
        if 0 <= row < max_h - 1:
            draw_centered_text(
                win, row, "DAMAGE REPORT",
                color_text(COLOR_WARNING) | curses.A_BOLD,
            )
        row += 1

        for dmg in result.mech_damage:
            if 0 <= row < max_h - 1:
                if dmg.destroyed:
                    dmg_text = f"  {dmg.mech_name}: DESTROYED (Armor -{dmg.armor_lost}, Structure -{dmg.structure_lost})"
                    dmg_attr = color_text(COLOR_WARNING) | curses.A_BOLD
                else:
                    dmg_text = f"  {dmg.mech_name}: Armor -{dmg.armor_lost}"
                    if dmg.structure_lost > 0:
                        dmg_text += f", Structure -{dmg.structure_lost}"
                    dmg_attr = color_text(COLOR_WARNING)
                try:
                    win.addstr(row, summary_x, dmg_text[:summary_w], dmg_attr)
                except curses.error:
                    pass
            row += 1
        row += 1
    else:
        if 0 <= row < max_h - 1:
            draw_centered_text(
                win, row, "No damage sustained!",
                color_text(COLOR_ACCENT),
            )
        row += 2

    # Pilot Injuries
    if result.pilot_injuries:
        if 0 <= row < max_h - 1:
            draw_centered_text(
                win, row, "PILOT INJURIES",
                color_text(COLOR_WARNING) | curses.A_BOLD,
            )
        row += 1

        for inj in result.pilot_injuries:
            if 0 <= row < max_h - 1:
                inj_text = f'  "{inj.callsign}": {inj.injuries_sustained} injury(s) sustained'
                try:
                    win.addstr(row, summary_x, inj_text[:summary_w],
                               color_text(COLOR_WARNING))
                except curses.error:
                    pass
            row += 1
        row += 1
    else:
        if 0 <= row < max_h - 1:
            draw_centered_text(
                win, row, "No pilot injuries!",
                color_text(COLOR_ACCENT),
            )
        row += 2

    return row


def _draw_summary_line(win, y, x, label, value, max_width):
    """Draw a label: value line in the mission summary.

    Args:
        win: curses window to draw on.
        y: Row position.
        x: Column position.
        label: The label text.
        value: The value text.
        max_width: Maximum available width.
    """
    max_h, max_w = win.getmaxyx()
    if y < 0 or y >= max_h:
        return

    try:
        win.addstr(y, x, label, color_text(COLOR_BORDER) | curses.A_BOLD)
        value_x = x + len(label) + 1
        win.addstr(y, value_x, value[:max_width - len(label) - 1],
                   color_text(COLOR_ACCENT) | curses.A_BOLD)
    except curses.error:
        pass
