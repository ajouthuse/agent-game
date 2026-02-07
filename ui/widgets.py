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
- draw_upkeep_phase(): Upkeep phase screen with repair toggle options.
- draw_financial_summary(): Financial summary with itemized income/expenses.
- draw_game_over(): Game over screen for bankruptcy.
- draw_pilot_detail(): Pilot detail screen with full stats and morale bar.
- draw_morale_bar(): Visual morale bar with color coding.
- draw_level_up_choice(): Level-up choice screen for skill improvement.
- draw_desertion_events(): Narrative desertion messages.
"""

import curses

from ui.colors import (
    color_text,
    COLOR_ACCENT,
    COLOR_BORDER,
    COLOR_MENU_ACTIVE,
    COLOR_MENU_INACTIVE,
    COLOR_STATUS,
    COLOR_TITLE,
    COLOR_WARNING,
)
from ui.drawing import draw_centered_text, draw_box
from data.models import PilotStatus
from data.progression import (
    get_pilot_level,
    can_level_up,
    get_xp_to_next_level,
    effective_gunnery,
    effective_piloting,
    get_morale_modifier_text,
    is_pilot_deployable,
    XP_THRESHOLDS,
    MORALE_LOW_THRESHOLD,
    MORALE_HIGH_THRESHOLD,
)


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
    (skull rating), duration, and payout. The selected contract is highlighted.

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

    # Column layout: Type, Employer, Difficulty, Duration, Payout, Salvage
    col_widths = [16, 16, 9, 6, 12, 9]
    headers = ["MISSION", "EMPLOYER", "DIFF", "WEEKS", "PAYOUT", "SALVAGE"]
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
        duration_str = f"{contract.duration}w"
        payout_str = f"{contract.payout:,} CB"
        salvage_str = f"{contract.salvage_rights}%"

        cols = [
            contract.mission_type.value,
            contract.employer,
            skulls,
            duration_str,
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
    # We need: title, blank, type, employer, diff, duration, payout, salvage,
    #          blank, description (wrapped), blank, bonus, blank
    desc_lines = _wrap_text(contract.description, inner_w)
    bonus_lines = _wrap_text(
        f"BONUS: {contract.bonus_objective}", inner_w
    )
    box_h = 11 + len(desc_lines) + len(bonus_lines)

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

    duration_str = f"{contract.duration} week{'s' if contract.duration != 1 else ''}"
    _draw_briefing_line(win, row, inner_x, "Duration:", duration_str, inner_w)
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


# ── Upkeep Phase Display ─────────────────────────────────────────────

def draw_upkeep_phase(win, start_y, report, selected_index, scroll_offset=0):
    """Draw the upkeep phase screen where the player toggles mech repairs.

    Shows a list of damaged mechs with repair costs, allowing the player
    to toggle each repair on or off before finalizing. Also shows a running
    total of expenses and projected balance.

    Args:
        win: curses window to draw on.
        start_y: Starting row for the display.
        report: An UpkeepReport instance from data.finance.
        selected_index: Index of the currently highlighted repair option.
        scroll_offset: Vertical scroll offset.

    Returns:
        The next available row after the display.
    """
    max_h, max_w = win.getmaxyx()
    row = start_y - scroll_offset

    content_w = min(70, max_w - 6)
    content_x = max(2, (max_w - content_w) // 2)

    # Title
    draw_centered_text(
        win, row,
        "MONTHLY UPKEEP - REPAIR DECISIONS",
        color_text(COLOR_TITLE) | curses.A_BOLD,
    )
    row += 2

    # Fixed costs summary
    if 0 <= row < max_h - 1:
        _draw_finance_line(
            win, row, content_x,
            "Pilot Salaries:", f"-{report.total_salaries:,} CB",
            content_w, COLOR_WARNING,
        )
    row += 1

    if 0 <= row < max_h - 1:
        _draw_finance_line(
            win, row, content_x,
            "Mech Maintenance:", f"-{report.total_maintenance:,} CB",
            content_w, COLOR_WARNING,
        )
    row += 2

    # Repair decisions
    if report.repairs:
        draw_centered_text(
            win, row,
            "--- DAMAGED MECHS (Toggle Repairs) ---",
            color_text(COLOR_BORDER) | curses.A_BOLD,
        )
        row += 1

        for i, repair in enumerate(report.repairs):
            if 0 <= row < max_h - 1:
                # Selection indicator
                if i == selected_index:
                    indicator = ">"
                    row_attr = color_text(COLOR_ACCENT) | curses.A_BOLD
                else:
                    indicator = " "
                    row_attr = color_text(COLOR_MENU_INACTIVE)

                # Repair toggle status
                toggle = "[X]" if repair.repaired else "[ ]"
                cost_str = f"{repair.cost:,} CB"
                line = f" {indicator} {toggle} {repair.mech_name:<22} Repair Cost: {cost_str}"

                try:
                    win.addstr(row, content_x, line[:content_w], row_attr)
                except curses.error:
                    pass
            row += 1

        row += 1

        # Instructions
        if 0 <= row < max_h - 1:
            draw_centered_text(
                win, row,
                "Space/Enter: Toggle Repair | Up/Down: Navigate",
                color_text(COLOR_MENU_INACTIVE),
            )
        row += 1
    else:
        if 0 <= row < max_h - 1:
            draw_centered_text(
                win, row,
                "No damaged mechs - no repairs needed!",
                color_text(COLOR_ACCENT),
            )
        row += 1

    row += 1

    # Running totals
    if 0 <= row < max_h - 1:
        try:
            sep = "-" * min(50, content_w)
            sep_x = max(1, (max_w - len(sep)) // 2)
            win.addstr(row, sep_x, sep, color_text(COLOR_BORDER))
        except curses.error:
            pass
    row += 1

    if 0 <= row < max_h - 1:
        _draw_finance_line(
            win, row, content_x,
            "Total Repairs:", f"-{report.total_repairs:,} CB",
            content_w, COLOR_WARNING if report.total_repairs > 0 else COLOR_MENU_INACTIVE,
        )
    row += 1

    if 0 <= row < max_h - 1:
        _draw_finance_line(
            win, row, content_x,
            "Total Expenses:", f"-{report.total_expenses:,} CB",
            content_w, COLOR_WARNING,
        )
    row += 1

    if 0 <= row < max_h - 1:
        _draw_finance_line(
            win, row, content_x,
            "Contract Income:", f"+{report.contract_income:,} CB",
            content_w, COLOR_ACCENT,
        )
    row += 1

    # Net change
    if 0 <= row < max_h - 1:
        net_color = COLOR_ACCENT if report.net_change >= 0 else COLOR_WARNING
        net_prefix = "+" if report.net_change >= 0 else ""
        _draw_finance_line(
            win, row, content_x,
            "Net Change:", f"{net_prefix}{report.net_change:,} CB",
            content_w, net_color,
        )
    row += 1

    if 0 <= row < max_h - 1:
        balance_color = COLOR_ACCENT if report.balance_after >= 0 else COLOR_WARNING
        _draw_finance_line(
            win, row, content_x,
            "Projected Balance:", f"{report.balance_after:,} CB",
            content_w, balance_color,
        )
    row += 1

    # Warning if balance will go negative
    if report.balance_after < 0:
        row += 1
        if 0 <= row < max_h - 1:
            draw_centered_text(
                win, row,
                "!! WARNING: Balance will go negative - BANKRUPTCY !!",
                color_text(COLOR_WARNING) | curses.A_BOLD,
            )
        row += 1

    return row


# ── Financial Summary Display ────────────────────────────────────────

def draw_financial_summary(win, start_y, report, scroll_offset=0):
    """Draw the financial summary screen with itemized income and expenses.

    Shows contract income, pilot salaries, mech maintenance, repair costs,
    and the net total with updated balance.

    Args:
        win: curses window to draw on.
        start_y: Starting row for the display.
        report: An UpkeepReport instance from data.finance.
        scroll_offset: Vertical scroll offset.

    Returns:
        The next available row after the display.
    """
    max_h, max_w = win.getmaxyx()
    row = start_y - scroll_offset

    content_w = min(70, max_w - 6)
    content_x = max(2, (max_w - content_w) // 2)

    # Title
    draw_centered_text(
        win, row,
        "MONTHLY FINANCIAL REPORT",
        color_text(COLOR_TITLE) | curses.A_BOLD,
    )
    row += 2

    # ── Income Section ──
    draw_centered_text(
        win, row,
        "--- INCOME ---",
        color_text(COLOR_BORDER) | curses.A_BOLD,
    )
    row += 1

    if 0 <= row < max_h - 1:
        _draw_finance_line(
            win, row, content_x,
            "Contract Payout:", f"+{report.contract_income:,} CB",
            content_w, COLOR_ACCENT,
        )
    row += 2

    # ── Expenses Section ──
    draw_centered_text(
        win, row,
        "--- EXPENSES ---",
        color_text(COLOR_BORDER) | curses.A_BOLD,
    )
    row += 1

    # Pilot salaries (itemized)
    if 0 <= row < max_h - 1:
        draw_centered_text(
            win, row, "Pilot Salaries:",
            color_text(COLOR_BORDER) | curses.A_BOLD,
        )
    row += 1

    for ps in report.pilot_salaries:
        if 0 <= row < max_h - 1:
            line = f'  "{ps.callsign}" ({ps.name}): -{ps.salary:,} CB'
            try:
                win.addstr(row, content_x, line[:content_w],
                           color_text(COLOR_MENU_INACTIVE))
            except curses.error:
                pass
        row += 1

    if 0 <= row < max_h - 1:
        _draw_finance_line(
            win, row, content_x,
            "  Subtotal Salaries:", f"-{report.total_salaries:,} CB",
            content_w, COLOR_WARNING,
        )
    row += 2

    # Mech maintenance (itemized)
    if 0 <= row < max_h - 1:
        draw_centered_text(
            win, row, "Mech Maintenance:",
            color_text(COLOR_BORDER) | curses.A_BOLD,
        )
    row += 1

    for mm in report.mech_maintenance:
        if 0 <= row < max_h - 1:
            line = f"  {mm.name} ({mm.weight_class}): -{mm.cost:,} CB"
            try:
                win.addstr(row, content_x, line[:content_w],
                           color_text(COLOR_MENU_INACTIVE))
            except curses.error:
                pass
        row += 1

    if 0 <= row < max_h - 1:
        _draw_finance_line(
            win, row, content_x,
            "  Subtotal Maintenance:", f"-{report.total_maintenance:,} CB",
            content_w, COLOR_WARNING,
        )
    row += 2

    # Repairs (itemized)
    if report.repairs:
        if 0 <= row < max_h - 1:
            draw_centered_text(
                win, row, "Mech Repairs:",
                color_text(COLOR_BORDER) | curses.A_BOLD,
            )
        row += 1

        for repair in report.repairs:
            if 0 <= row < max_h - 1:
                status = "REPAIRED" if repair.repaired else "DEFERRED"
                cost_str = f"-{repair.cost:,} CB" if repair.repaired else "0 CB"
                line = f"  {repair.mech_name}: {cost_str} ({status})"
                attr = color_text(COLOR_ACCENT) if repair.repaired else color_text(COLOR_WARNING)
                try:
                    win.addstr(row, content_x, line[:content_w], attr)
                except curses.error:
                    pass
            row += 1

        if 0 <= row < max_h - 1:
            _draw_finance_line(
                win, row, content_x,
                "  Subtotal Repairs:", f"-{report.total_repairs:,} CB",
                content_w, COLOR_WARNING,
            )
        row += 2

    # ── Totals ──
    if 0 <= row < max_h - 1:
        try:
            sep = "=" * min(50, content_w)
            sep_x = max(1, (max_w - len(sep)) // 2)
            win.addstr(row, sep_x, sep, color_text(COLOR_BORDER) | curses.A_BOLD)
        except curses.error:
            pass
    row += 1

    if 0 <= row < max_h - 1:
        _draw_finance_line(
            win, row, content_x,
            "Total Income:", f"+{report.contract_income:,} CB",
            content_w, COLOR_ACCENT,
        )
    row += 1

    if 0 <= row < max_h - 1:
        _draw_finance_line(
            win, row, content_x,
            "Total Expenses:", f"-{report.total_expenses:,} CB",
            content_w, COLOR_WARNING,
        )
    row += 1

    # Net change (bold, color-coded)
    if 0 <= row < max_h - 1:
        net_color = COLOR_ACCENT if report.net_change >= 0 else COLOR_WARNING
        net_prefix = "+" if report.net_change >= 0 else ""
        net_str = f"{net_prefix}{report.net_change:,} CB"
        try:
            label = "NET CHANGE:"
            win.addstr(row, content_x, label,
                       color_text(COLOR_TITLE) | curses.A_BOLD)
            win.addstr(row, content_x + len(label) + 1,
                       net_str[:content_w - len(label) - 1],
                       color_text(net_color) | curses.A_BOLD)
        except curses.error:
            pass
    row += 2

    # Balance before / after
    if 0 <= row < max_h - 1:
        _draw_finance_line(
            win, row, content_x,
            "Balance (Before):", f"{report.balance_before:,} CB",
            content_w, COLOR_MENU_INACTIVE,
        )
    row += 1

    if 0 <= row < max_h - 1:
        balance_color = COLOR_ACCENT if report.balance_after >= 0 else COLOR_WARNING
        _draw_finance_line(
            win, row, content_x,
            "Balance (After):", f"{report.balance_after:,} CB",
            content_w, balance_color,
        )
    row += 1

    return row


# ── Game Over Display ────────────────────────────────────────────────

def draw_game_over(win, start_y, company):
    """Draw the game over screen for bankruptcy.

    Shows final stats: months survived, contracts completed, and a
    message about the company's dissolution.

    Args:
        win: curses window to draw on.
        start_y: Starting row for the display.
        company: The bankrupt Company instance.

    Returns:
        The next available row after the display.
    """
    max_h, max_w = win.getmaxyx()
    row = start_y

    content_w = min(60, max_w - 6)
    content_x = max(2, (max_w - content_w) // 2)

    # Dramatic game over title
    draw_centered_text(
        win, row,
        "===================================",
        color_text(COLOR_WARNING) | curses.A_BOLD,
    )
    row += 1
    draw_centered_text(
        win, row,
        "GAME OVER - BANKRUPTCY",
        color_text(COLOR_WARNING) | curses.A_BOLD,
    )
    row += 1
    draw_centered_text(
        win, row,
        "===================================",
        color_text(COLOR_WARNING) | curses.A_BOLD,
    )
    row += 2

    # Flavor text
    draw_centered_text(
        win, row,
        "Your mercenary company has gone bankrupt.",
        color_text(COLOR_MENU_INACTIVE),
    )
    row += 1
    draw_centered_text(
        win, row,
        "Unable to pay your debts, the company is dissolved.",
        color_text(COLOR_MENU_INACTIVE),
    )
    row += 1
    draw_centered_text(
        win, row,
        "Your pilots scatter to find new employment.",
        color_text(COLOR_MENU_INACTIVE),
    )
    row += 3

    # Final stats
    draw_centered_text(
        win, row,
        "--- FINAL STATISTICS ---",
        color_text(COLOR_BORDER) | curses.A_BOLD,
    )
    row += 2

    if company:
        stats = [
            ("Company:", company.name),
            ("Months Survived:", str(company.month)),
            ("Contracts Completed:", str(company.contracts_completed)),
            ("Final Reputation:", f"{company.reputation}/100"),
            ("Final Balance:", f"{company.c_bills:,} CB"),
            ("Mechs Remaining:", str(len([
                m for m in company.mechs
                if m.status.value != "Destroyed"
            ]))),
            ("Pilots Remaining:", str(len([
                p for p in company.mechwarriors
                if p.status != PilotStatus.KIA
            ]))),
        ]

        for label, value in stats:
            if 0 <= row < max_h - 1:
                _draw_finance_line(
                    win, row, content_x,
                    label, value,
                    content_w, COLOR_TITLE,
                )
            row += 1

    return row


# ── Finance Line Helper ──────────────────────────────────────────────

def _draw_finance_line(win, y, x, label, value, max_width, value_color):
    """Draw a label: value line with the value in the specified color.

    Args:
        win: curses window to draw on.
        y: Row position.
        x: Column position.
        label: The label text.
        value: The value text.
        max_width: Maximum available width.
        value_color: Color constant for the value text.
    """
    max_h, max_w = win.getmaxyx()
    if y < 0 or y >= max_h:
        return

    try:
        win.addstr(y, x, label, color_text(COLOR_BORDER) | curses.A_BOLD)
        value_x = x + len(label) + 1
        win.addstr(y, value_x, value[:max_width - len(label) - 1],
                   color_text(value_color) | curses.A_BOLD)
    except curses.error:
        pass


# ── Morale Bar ────────────────────────────────────────────────────────

def draw_morale_bar(win, y, x, width, morale):
    """Draw a visual morale bar with color coding.

    The bar uses filled and empty blocks to show morale level (0-100).
    Color coding:
    - Red: morale < 30 (low, combat penalty)
    - Yellow: 30 <= morale <= 80 (neutral)
    - Green: morale > 80 (high, combat bonus)

    Args:
        win: curses window to draw on.
        y: Row position.
        x: Column position.
        width: Total width of the bar (including brackets).
        morale: Morale value (0-100).

    Returns:
        The next x position after the bar.
    """
    max_h, max_w = win.getmaxyx()
    if y < 0 or y >= max_h:
        return x + width

    inner_width = width - 2  # Subtract brackets
    filled = int((morale / 100.0) * inner_width)
    filled = max(0, min(inner_width, filled))
    empty = inner_width - filled

    # Determine color based on morale thresholds
    if morale < MORALE_LOW_THRESHOLD:
        bar_color = color_text(COLOR_WARNING) | curses.A_BOLD
    elif morale > MORALE_HIGH_THRESHOLD:
        bar_color = color_text(COLOR_ACCENT) | curses.A_BOLD
    else:
        bar_color = color_text(COLOR_TITLE) | curses.A_BOLD

    bar_str = "#" * filled + "-" * empty

    try:
        win.addstr(y, x, "[", color_text(COLOR_BORDER))
        win.addstr(y, x + 1, bar_str, bar_color)
        win.addstr(y, x + 1 + inner_width, "]", color_text(COLOR_BORDER))
    except curses.error:
        pass

    return x + width


# ── Pilot Detail Display ─────────────────────────────────────────────

def draw_pilot_detail(win, start_y, pilot, assigned_mech=None):
    """Draw a detailed pilot information screen.

    Shows the pilot's full stats, XP progress, morale bar, injury
    status, and assigned mech in a clear, formatted layout.

    Args:
        win: curses window to draw on.
        start_y: Starting row for the display.
        pilot: A MechWarrior instance to display.
        assigned_mech: Optional BattleMech assigned to this pilot.

    Returns:
        The next available row after the display.
    """
    max_h, max_w = win.getmaxyx()

    content_w = min(60, max_w - 6)
    content_x = max(2, (max_w - content_w) // 2)

    row = start_y

    # ── Name and Callsign Header ──
    header_text = f'=== {pilot.name} "{pilot.callsign}" ==='
    draw_centered_text(
        win, row, header_text,
        color_text(COLOR_TITLE) | curses.A_BOLD,
    )
    row += 2

    # ── Status ──
    if pilot.status == PilotStatus.KIA:
        status_attr = color_text(COLOR_WARNING) | curses.A_BOLD
    elif pilot.status == PilotStatus.INJURED:
        status_attr = color_text(COLOR_WARNING)
    else:
        status_attr = color_text(COLOR_ACCENT)

    _draw_detail_line(win, row, content_x, "Status:", pilot.status.value, content_w, status_attr)
    row += 1

    # ── Deployable ──
    deployable = is_pilot_deployable(pilot)
    deploy_text = "Yes" if deployable else "No (Injured)"
    deploy_attr = color_text(COLOR_ACCENT) if deployable else color_text(COLOR_WARNING)
    _draw_detail_line(win, row, content_x, "Deployable:", deploy_text, content_w, deploy_attr)
    row += 1

    # ── Injuries ──
    if pilot.injuries > 0:
        inj_attr = color_text(COLOR_WARNING)
    else:
        inj_attr = color_text(COLOR_ACCENT)
    _draw_detail_line(win, row, content_x, "Injuries:", str(pilot.injuries), content_w, inj_attr)
    row += 2

    # ── Skills ──
    eff_gun = effective_gunnery(pilot)
    eff_plt = effective_piloting(pilot)

    gun_text = str(pilot.gunnery)
    if eff_gun != pilot.gunnery:
        gun_text += f" (eff: {eff_gun})"
    plt_text = str(pilot.piloting)
    if eff_plt != pilot.piloting:
        plt_text += f" (eff: {eff_plt})"

    _draw_detail_line(
        win, row, content_x, "Gunnery:", gun_text, content_w,
        color_text(COLOR_TITLE) | curses.A_BOLD,
    )
    row += 1
    _draw_detail_line(
        win, row, content_x, "Piloting:", plt_text, content_w,
        color_text(COLOR_TITLE) | curses.A_BOLD,
    )
    row += 2

    # ── Morale ──
    _draw_detail_line(
        win, row, content_x, "Morale:", f"{pilot.morale}/100", content_w,
        color_text(COLOR_TITLE),
    )
    row += 1

    # Morale bar
    bar_x = content_x + 2
    bar_width = min(32, content_w - 4)
    draw_morale_bar(win, row, bar_x, bar_width, pilot.morale)

    # Morale percentage after bar
    pct_x = bar_x + bar_width + 1
    try:
        win.addstr(row, pct_x, f"{pilot.morale}%",
                   color_text(COLOR_MENU_INACTIVE))
    except curses.error:
        pass
    row += 1

    # Morale modifier text
    modifier_text = get_morale_modifier_text(pilot)
    if modifier_text:
        if pilot.morale < MORALE_LOW_THRESHOLD:
            mod_attr = color_text(COLOR_WARNING) | curses.A_BOLD
        else:
            mod_attr = color_text(COLOR_ACCENT) | curses.A_BOLD
        try:
            win.addstr(row, content_x + 2, modifier_text, mod_attr)
        except curses.error:
            pass
        row += 1

    row += 1

    # ── Experience / Level ──
    level = get_pilot_level(pilot)
    _draw_detail_line(
        win, row, content_x, "Experience:", f"{pilot.experience} XP", content_w,
        color_text(COLOR_TITLE),
    )
    row += 1
    _draw_detail_line(
        win, row, content_x, "Level:", str(level), content_w,
        color_text(COLOR_TITLE),
    )
    row += 1

    # XP progress to next level
    xp_remaining = get_xp_to_next_level(pilot)
    if xp_remaining is not None:
        next_threshold = XP_THRESHOLDS[level] if level < len(XP_THRESHOLDS) else 0
        xp_text = f"{pilot.experience}/{next_threshold} ({xp_remaining} to next)"
        _draw_detail_line(
            win, row, content_x, "XP Progress:", xp_text, content_w,
            color_text(COLOR_ACCENT),
        )
    else:
        _draw_detail_line(
            win, row, content_x, "XP Progress:", "MAX LEVEL", content_w,
            color_text(COLOR_ACCENT) | curses.A_BOLD,
        )
    row += 1

    # Level-up available indicator
    if can_level_up(pilot):
        row += 1
        draw_centered_text(
            win, row,
            "** LEVEL UP AVAILABLE! **",
            color_text(COLOR_ACCENT) | curses.A_BOLD,
        )
        row += 1

    row += 1

    # ── Assigned Mech ──
    if assigned_mech:
        _draw_detail_line(
            win, row, content_x, "Assigned Mech:", assigned_mech.name, content_w,
            color_text(COLOR_TITLE),
        )
        row += 1
        armor_pct = int((assigned_mech.armor_current / assigned_mech.armor_max) * 100) if assigned_mech.armor_max > 0 else 0
        mech_info = f"{assigned_mech.weight_class.value} {assigned_mech.tonnage}t | Armor: {armor_pct}% | {assigned_mech.status.value}"
        try:
            win.addstr(row, content_x + 2, mech_info[:content_w - 4],
                       color_text(COLOR_MENU_INACTIVE))
        except curses.error:
            pass
        row += 1
    elif pilot.assigned_mech:
        _draw_detail_line(
            win, row, content_x, "Assigned Mech:", pilot.assigned_mech, content_w,
            color_text(COLOR_TITLE),
        )
        row += 1
    else:
        _draw_detail_line(
            win, row, content_x, "Assigned Mech:", "--- (Unassigned)", content_w,
            color_text(COLOR_WARNING),
        )
        row += 1

    return row


def _draw_detail_line(win, y, x, label, value, max_width, value_attr):
    """Draw a label: value line in the pilot detail screen.

    Args:
        win: curses window to draw on.
        y: Row position.
        x: Column position.
        label: The label text.
        value: The value text.
        max_width: Maximum available width.
        value_attr: curses attribute for the value text.
    """
    max_h, max_w = win.getmaxyx()
    if y < 0 or y >= max_h:
        return

    try:
        win.addstr(y, x, label, color_text(COLOR_BORDER) | curses.A_BOLD)
        value_x = x + len(label) + 1
        remaining_w = max_width - len(label) - 1
        if remaining_w > 0:
            win.addstr(y, value_x, value[:remaining_w], value_attr)
    except curses.error:
        pass


# ── Level-Up Choice Display ──────────────────────────────────────────

def draw_level_up_choice(win, start_y, pilot, selected_index):
    """Draw the level-up choice screen for a pilot.

    Shows the pilot's current skills and lets the player choose to
    improve either gunnery or piloting (whichever is above minimum).

    Args:
        win: curses window to draw on.
        start_y: Starting row for the display.
        pilot: A MechWarrior instance eligible for level-up.
        selected_index: Index of the highlighted choice (0=gunnery, 1=piloting).

    Returns:
        The next available row after the display.
    """
    max_h, max_w = win.getmaxyx()
    row = start_y

    # Title
    title_text = f'LEVEL UP - "{pilot.callsign}" ({pilot.name})'
    draw_centered_text(
        win, row, title_text,
        color_text(COLOR_TITLE) | curses.A_BOLD,
    )
    row += 2

    level = get_pilot_level(pilot)
    draw_centered_text(
        win, row,
        f"Level {level} | XP: {pilot.experience}",
        color_text(COLOR_ACCENT),
    )
    row += 2

    draw_centered_text(
        win, row,
        "Choose a skill to improve:",
        color_text(COLOR_MENU_INACTIVE),
    )
    row += 2

    # Options
    content_w = min(50, max_w - 6)
    content_x = max(2, (max_w - content_w) // 2)

    options = []
    if pilot.gunnery > 1:
        options.append(("gunnery", f"Gunnery: {pilot.gunnery} -> {pilot.gunnery - 1}"))
    else:
        options.append(("gunnery_max", f"Gunnery: {pilot.gunnery} (MAX - cannot improve)"))

    if pilot.piloting > 1:
        options.append(("piloting", f"Piloting: {pilot.piloting} -> {pilot.piloting - 1}"))
    else:
        options.append(("piloting_max", f"Piloting: {pilot.piloting} (MAX - cannot improve)"))

    for i, (key, text) in enumerate(options):
        is_maxed = key.endswith("_max")

        if i == selected_index and not is_maxed:
            indicator = ">"
            attr = color_text(COLOR_MENU_ACTIVE) | curses.A_BOLD
        elif i == selected_index and is_maxed:
            indicator = ">"
            attr = color_text(COLOR_WARNING)
        elif is_maxed:
            indicator = " "
            attr = color_text(COLOR_WARNING)
        else:
            indicator = " "
            attr = color_text(COLOR_MENU_INACTIVE)

        line = f" {indicator}  {text}"
        if 0 <= row < max_h - 1:
            try:
                win.addstr(row, content_x, line[:content_w], attr)
            except curses.error:
                pass
        row += 1

    row += 2

    # Hint text
    draw_centered_text(
        win, row,
        "Lower is better! (1 = elite, 6 = green)",
        color_text(COLOR_MENU_INACTIVE),
    )
    row += 1

    return row


# ── Desertion Events Display ─────────────────────────────────────────

def draw_desertion_events(win, start_y, messages):
    """Draw narrative desertion event messages.

    Shows each desertion message in a dramatic format with warning colors.

    Args:
        win: curses window to draw on.
        start_y: Starting row for the display.
        messages: List of desertion message strings.

    Returns:
        The next available row after the display.
    """
    max_h, max_w = win.getmaxyx()
    row = start_y

    if not messages:
        return row

    draw_centered_text(
        win, row,
        "=== DESERTION ===",
        color_text(COLOR_WARNING) | curses.A_BOLD,
    )
    row += 2

    content_w = min(70, max_w - 6)
    content_x = max(2, (max_w - content_w) // 2)

    for msg in messages:
        wrapped = _wrap_text(msg, content_w)
        for line in wrapped:
            if 0 <= row < max_h - 1:
                try:
                    win.addstr(row, content_x, line[:content_w],
                               color_text(COLOR_WARNING))
                except curses.error:
                    pass
            row += 1
        row += 1

    return row


# ── Recovery Messages Display ────────────────────────────────────────

def draw_recovery_messages(win, start_y, messages):
    """Draw pilot recovery messages.

    Shows recovery status messages for injured pilots.

    Args:
        win: curses window to draw on.
        start_y: Starting row for the display.
        messages: List of recovery message strings.

    Returns:
        The next available row after the display.
    """
    max_h, max_w = win.getmaxyx()
    row = start_y

    if not messages:
        return row

    draw_centered_text(
        win, row,
        "--- PILOT RECOVERY ---",
        color_text(COLOR_ACCENT) | curses.A_BOLD,
    )
    row += 1

    content_w = min(70, max_w - 6)
    content_x = max(2, (max_w - content_w) // 2)

    for msg in messages:
        wrapped = _wrap_text(msg, content_w)
        for line in wrapped:
            if 0 <= row < max_h - 1:
                try:
                    win.addstr(row, content_x, line[:content_w],
                               color_text(COLOR_ACCENT))
                except curses.error:
                    pass
            row += 1

    return row
