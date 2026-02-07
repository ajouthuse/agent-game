"""
game.hq - HQ dashboard and turn cycle system for Iron Contract.

Provides:
- HQScene: The main headquarters dashboard with letter-key navigation.
- WeeklySummaryScene: Displays the results of advancing one week.
- QuitConfirmScene: Confirmation prompt before quitting the game.
- MechBayScene: Placeholder screen for the mech bay (future issue).
- ContractsPlaceholderScene: Placeholder for contracts when market exists.

The HQ is the central hub of the game. Each turn represents one week.
When the player advances a week, overhead costs are deducted, repair
and contract timers progress, and the week counter increments.
"""

import curses

import ui
from data.models import MechStatus, PilotStatus
from data.finance import (
    PILOT_BASE_SALARY,
    calculate_pilot_salary,
    is_bankrupt,
)
from game.scene import Scene


# ── Constants ────────────────────────────────────────────────────────────

# Weekly payroll cost per active MechWarrior (as specified in issue #3)
WEEKLY_PAYROLL_PER_PILOT = 5_000


# ── Turn Cycle Logic ─────────────────────────────────────────────────────

def advance_week(company):
    """Advance the game by one week, applying all turn cycle effects.

    Steps:
    1. Deduct weekly overhead costs (payroll: 5,000 C-Bills per active MW)
    2. Progress any active repair timers by 1 week
    3. Progress any active contract timers by 1 week
    4. Regenerate available contracts each week
    5. Update week counter

    Args:
        company: The player's Company instance (modified in place).

    Returns:
        A dict containing the weekly summary data:
        - week_before: Week number before advancing.
        - week_after: Week number after advancing.
        - active_pilots: Number of active (non-KIA) MechWarriors.
        - payroll_cost: Total payroll deducted.
        - balance_before: C-Bills before deduction.
        - balance_after: C-Bills after deduction.
        - repairs_progressed: List of mech names with repair progress.
        - status_changes: List of string descriptions of status changes.
    """
    from data.contracts import generate_contracts

    summary = {
        "week_before": company.week,
        "active_pilots": 0,
        "payroll_cost": 0,
        "balance_before": company.c_bills,
        "repairs_progressed": [],
        "status_changes": [],
    }

    # 1. Deduct weekly overhead (payroll for active MechWarriors)
    active_pilots = [
        mw for mw in company.mechwarriors
        if mw.status != PilotStatus.KIA
    ]
    summary["active_pilots"] = len(active_pilots)

    payroll = len(active_pilots) * WEEKLY_PAYROLL_PER_PILOT
    summary["payroll_cost"] = payroll
    company.c_bills -= payroll

    # 2. Progress repair timers (damaged mechs get a note)
    for mech in company.mechs:
        if mech.status == MechStatus.DAMAGED:
            # Progress repair if one is active
            if hasattr(mech, 'repair_weeks_remaining') and mech.repair_weeks_remaining > 0:
                mech.repair_weeks_remaining -= 1
                if mech.repair_weeks_remaining <= 0:
                    # Repair complete
                    mech.armor_current = mech.armor_max
                    mech.status = MechStatus.READY
                    summary["repairs_progressed"].append(mech.name)
                    summary["status_changes"].append(
                        f"{mech.name}: Repair complete - ready for deployment!"
                    )
                else:
                    summary["repairs_progressed"].append(mech.name)
                    summary["status_changes"].append(
                        f"{mech.name}: Repair in progress ({mech.repair_weeks_remaining}w remaining)"
                    )
            else:
                # Damaged but not being repaired
                summary["status_changes"].append(
                    f"{mech.name}: Damaged - awaiting repair orders"
                )

    # 3. Progress active contract timer and check for battle
    battle_contract = None
    if company.active_contract:
        company.active_contract.weeks_remaining -= 1
        if company.active_contract.weeks_remaining <= 0:
            # Contract duration elapsed - battle time!
            battle_contract = company.active_contract
            summary["status_changes"].append(
                f"Contract with {company.active_contract.employer} ready for deployment!"
            )
            # Don't clear active_contract here - battle will do that

    # 4. Regenerate available contracts each week
    company.available_contracts = generate_contracts(company.week)

    # 5. Update week counter (only if no battle - battle will do this)
    if not battle_contract:
        company.week += 1
    summary["week_after"] = company.week
    summary["balance_after"] = company.c_bills
    summary["battle_contract"] = battle_contract

    return summary


# ── Status Bar Helper ────────────────────────────────────────────────────

def get_status_text(company):
    """Generate contextual status text for the HQ status bar.

    Shows active contract status, damaged mechs, injured pilots, etc.

    Args:
        company: The player's Company instance.

    Returns:
        A string describing the current company status.
    """
    parts = []

    # Active contract status (most important, show first)
    if company.active_contract:
        contract = company.active_contract
        parts.append(
            f"Active: {contract.mission_type.value} for {contract.employer} "
            f"({contract.weeks_remaining}w remaining)"
        )
    else:
        parts.append("No active contract")

    # Check for damaged mechs
    damaged_mechs = [
        m for m in company.mechs if m.status == MechStatus.DAMAGED
    ]
    destroyed_mechs = [
        m for m in company.mechs if m.status == MechStatus.DESTROYED
    ]
    ready_mechs = [
        m for m in company.mechs if m.status == MechStatus.READY
    ]

    if destroyed_mechs:
        parts.append(f"{len(destroyed_mechs)} mech(s) destroyed")
    if damaged_mechs:
        parts.append(f"{len(damaged_mechs)} mech(s) damaged")
    elif not destroyed_mechs:
        parts.append("All mechs operational")

    # Check for injured pilots
    injured_pilots = [
        mw for mw in company.mechwarriors
        if mw.status == PilotStatus.INJURED
    ]
    kia_pilots = [
        mw for mw in company.mechwarriors
        if mw.status == PilotStatus.KIA
    ]

    if kia_pilots:
        parts.append(f"{len(kia_pilots)} pilot(s) KIA")
    if injured_pilots:
        parts.append(f"{len(injured_pilots)} pilot(s) injured")

    return "STATUS: " + ". ".join(parts) + "."


# ── HQ Scene ─────────────────────────────────────────────────────────────

class HQScene(Scene):
    """Headquarters dashboard — the central hub of Iron Contract.

    Displays company name, week number, C-Bills, reputation, and a menu
    navigable via highlighted letter keys (C, R, M, A, Q). Also shows
    a contextual status bar at the bottom.
    """

    def __init__(self, game_state):
        super().__init__(game_state)

    def handle_input(self, key):
        """Handle letter-key navigation at HQ.

        C - Contracts (find new work)
        R - Roster (manage MechWarriors)
        M - Mech Bay (view and repair mechs)
        A - Advance (end week)
        Q - Quit (save and exit)

        Args:
            key: The curses key code.
        """
        if key in (ord("c"), ord("C")):
            self._go_contracts()
        elif key in (ord("r"), ord("R")):
            self._go_roster()
        elif key in (ord("m"), ord("M")):
            self._go_mech_bay()
        elif key in (ord("a"), ord("A")):
            self._advance_week()
        elif key in (ord("q"), ord("Q")):
            self._confirm_quit()

    def _go_contracts(self):
        """Navigate to the contract market."""
        from game.scenes import ContractMarketScene
        self.game_state.push_scene(ContractMarketScene(self.game_state))

    def _go_roster(self):
        """Navigate to the roster management screen."""
        from game.roster_screen import RosterManagementScene
        self.game_state.push_scene(RosterManagementScene(self.game_state))

    def _go_mech_bay(self):
        """Navigate to the mech bay management screen."""
        from game.mechbay_screen import MechBayManagementScene
        self.game_state.push_scene(MechBayManagementScene(self.game_state))

    def _advance_week(self):
        """Advance the game by one week and show the summary."""
        company = self.game_state.company
        if company:
            summary = advance_week(company)
            
            # Check if battle should trigger
            if summary.get("battle_contract"):
                from game.scenes import BattleDeploymentScene
                from data.battle import generate_enemy_lance
                
                contract = summary["battle_contract"]
                enemies = generate_enemy_lance(contract.difficulty)
                self.game_state.push_scene(
                    BattleDeploymentScene(self.game_state, contract, enemies)
                )
            else:
                # Normal week summary
                self.game_state.push_scene(
                    WeeklySummaryScene(self.game_state, summary)
                )
    def _confirm_quit(self):
        """Show a quit confirmation prompt."""
        self.game_state.push_scene(QuitConfirmScene(self.game_state))

    def draw(self, win):
        """Render the HQ dashboard matching the issue's layout spec.

        Args:
            win: The curses standard screen window.
        """
        max_h, max_w = win.getmaxyx()
        company = self.game_state.company

        # Header
        company_title = (
            f"IRON CONTRACT - {company.name.upper()}" if company
            else "IRON CONTRACT - HQ"
        )
        ui.draw_header_bar(win, company_title)

        # Status bar (bottom)
        if company:
            status_text = get_status_text(company)
        else:
            status_text = "STATUS: No company loaded."
        ui.draw_status_bar(win, status_text)

        if not company:
            return

        # Dashboard box
        box_w = min(56, max_w - 4)
        box_h = 17
        box_x = (max_w - box_w) // 2
        box_y = max(2, (max_h - box_h) // 2 - 1)

        ui.draw_box(win, box_y, box_x, box_h, box_w, title="Headquarters")

        inner_x = box_x + 2
        inner_w = box_w - 4
        row = box_y + 1

        # Company name and week
        title_line = f"IRON CONTRACT - {company.name}"
        week_str = f"Week {company.week}"
        # Draw title on left, week on right within box
        title_attr = ui.color_text(ui.COLOR_TITLE) | curses.A_BOLD
        try:
            # Truncate if necessary
            avail = inner_w - len(week_str) - 2
            display_title = title_line[:avail] if len(title_line) > avail else title_line
            win.addstr(row, inner_x, display_title, title_attr)
            week_x = box_x + box_w - len(week_str) - 3
            win.addstr(row, week_x, week_str, title_attr)
        except curses.error:
            pass
        row += 1

        # C-Bills and Reputation
        stats_line = f"C-Bills: {company.c_bills:,}    Reputation: {company.reputation}"
        try:
            win.addstr(
                row, inner_x, stats_line[:inner_w],
                ui.color_text(ui.COLOR_ACCENT),
            )
        except curses.error:
            pass
        row += 2

        # Separator line
        try:
            sep = "─" * (box_w - 2)
            win.addstr(row, box_x + 1, sep, ui.color_text(ui.COLOR_BORDER))
        except curses.error:
            pass
        row += 1

        # Menu options with letter-key highlighting
        menu_items = [
            ("C", "Contracts", "Find new work"),
            ("R", "Roster", "Manage MechWarriors"),
            ("M", "Mech Bay", "View and repair mechs"),
            ("A", "Advance", "End week"),
            ("Q", "Quit", "Save and exit"),
        ]

        row += 1
        for key_char, label, description in menu_items:
            if row >= box_y + box_h - 1:
                break
            _draw_menu_item(win, row, inner_x, key_char, label, description, inner_w)
            row += 1

        row += 1

        # Lower separator
        if row < box_y + box_h - 1:
            try:
                sep = "─" * (box_w - 2)
                win.addstr(row, box_x + 1, sep, ui.color_text(ui.COLOR_BORDER))
            except curses.error:
                pass
            row += 1

        # Status line inside box
        if row < box_y + box_h - 1 and company:
            status = get_status_text(company)
            try:
                win.addstr(
                    row, inner_x,
                    status[:inner_w],
                    ui.color_text(ui.COLOR_MENU_INACTIVE),
                )
            except curses.error:
                pass


def _draw_menu_item(win, y, x, key_char, label, description, max_width):
    """Draw a single HQ menu item with highlighted letter key.

    Format: [C] Contracts - Find new work

    Args:
        win: curses window to draw on.
        y: Row position.
        x: Column position.
        key_char: The letter key (e.g., "C").
        label: The menu item label (e.g., "Contracts").
        description: A short description (e.g., "Find new work").
        max_width: Maximum available width.
    """
    max_h, max_w = win.getmaxyx()
    if y < 0 or y >= max_h:
        return

    key_attr = ui.color_text(ui.COLOR_MENU_ACTIVE) | curses.A_BOLD
    label_attr = ui.color_text(ui.COLOR_TITLE) | curses.A_BOLD
    desc_attr = ui.color_text(ui.COLOR_MENU_INACTIVE)

    line = f"  [{key_char}] {label} - {description}"
    try:
        # Draw the bracket and key in highlight color
        win.addstr(y, x, "  [", desc_attr)
        win.addstr(y, x + 3, key_char, key_attr)
        win.addstr(y, x + 4, "] ", desc_attr)
        # Draw label in bold
        win.addstr(y, x + 6, label, label_attr)
        # Draw separator and description
        rest = f" - {description}"
        win.addstr(y, x + 6 + len(label), rest[:max_width - 6 - len(label)], desc_attr)
    except curses.error:
        pass


# ── Weekly Summary Scene ─────────────────────────────────────────────────

class WeeklySummaryScene(Scene):
    """Displays the results of advancing one week.

    Shows costs paid, status changes, and any notable events.
    After viewing, returns to HQ or transitions to game over.
    """

    def __init__(self, game_state, summary):
        """Initialize with the weekly summary data.

        Args:
            game_state: The GameState instance.
            summary: Dict from advance_week() with summary data.
        """
        super().__init__(game_state)
        self.summary = summary

    def handle_input(self, key):
        """Press Enter to continue (back to HQ or game over).

        Args:
            key: The curses key code.
        """
        if key in (curses.KEY_ENTER, 10, 13, 27):
            self._proceed()

    def _proceed(self):
        """Return to HQ or trigger game over if bankrupt."""
        company = self.game_state.company
        self.game_state.pop_scene()  # Pop weekly summary

        if company and is_bankrupt(company):
            from game.scenes import GameOverScene
            self.game_state.push_scene(GameOverScene(self.game_state))

    def draw(self, win):
        """Render the weekly summary screen.

        Args:
            win: The curses standard screen window.
        """
        max_h, max_w = win.getmaxyx()
        s = self.summary

        ui.draw_header_bar(win, "IRON CONTRACT - WEEK SUMMARY")
        ui.draw_status_bar(win, "Press ENTER to continue")

        content_w = min(60, max_w - 6)
        content_x = max(2, (max_w - content_w) // 2)
        row = 3

        # Title
        ui.draw_centered_text(
            win, row,
            f"=== WEEK {s['week_before']} COMPLETE ===",
            ui.color_text(ui.COLOR_TITLE) | curses.A_BOLD,
        )
        row += 2

        # Week advancement
        ui.draw_centered_text(
            win, row,
            f"Advancing to Week {s['week_after']}",
            ui.color_text(ui.COLOR_ACCENT),
        )
        row += 2

        # Payroll
        ui.draw_centered_text(
            win, row,
            "--- WEEKLY OVERHEAD ---",
            ui.color_text(ui.COLOR_BORDER) | curses.A_BOLD,
        )
        row += 1

        payroll_text = (
            f"Payroll ({s['active_pilots']} active pilots "
            f"x {WEEKLY_PAYROLL_PER_PILOT:,} CB): -{s['payroll_cost']:,} CB"
        )
        try:
            win.addstr(
                row, content_x,
                payroll_text[:content_w],
                ui.color_text(ui.COLOR_WARNING),
            )
        except curses.error:
            pass
        row += 2

        # Balance
        balance_color = (
            ui.COLOR_ACCENT if s["balance_after"] >= 0
            else ui.COLOR_WARNING
        )
        balance_before_text = f"Balance Before: {s['balance_before']:,} CB"
        balance_after_text = f"Balance After:  {s['balance_after']:,} CB"

        try:
            win.addstr(
                row, content_x,
                balance_before_text[:content_w],
                ui.color_text(ui.COLOR_MENU_INACTIVE),
            )
        except curses.error:
            pass
        row += 1

        try:
            win.addstr(
                row, content_x,
                balance_after_text[:content_w],
                ui.color_text(balance_color) | curses.A_BOLD,
            )
        except curses.error:
            pass
        row += 2

        # Status changes
        if s["status_changes"]:
            ui.draw_centered_text(
                win, row,
                "--- STATUS CHANGES ---",
                ui.color_text(ui.COLOR_BORDER) | curses.A_BOLD,
            )
            row += 1

            for change in s["status_changes"]:
                if 0 <= row < max_h - 2:
                    try:
                        win.addstr(
                            row, content_x,
                            f"  {change}"[:content_w],
                            ui.color_text(ui.COLOR_MENU_INACTIVE),
                        )
                    except curses.error:
                        pass
                row += 1
            row += 1
        else:
            ui.draw_centered_text(
                win, row,
                "No status changes this week.",
                ui.color_text(ui.COLOR_MENU_INACTIVE),
            )
            row += 2

        # Bankruptcy warning
        if s["balance_after"] < 0:
            ui.draw_centered_text(
                win, row,
                "!! WARNING: BANKRUPTCY - GAME OVER !!",
                ui.color_text(ui.COLOR_WARNING) | curses.A_BOLD,
            )
            row += 1

        # Continue prompt
        ui.draw_centered_text(
            win, max_h - 3,
            "[ Press ENTER to continue ]",
            ui.color_text(ui.COLOR_TITLE) | curses.A_BOLD,
        )


# ── Quit Confirmation Scene ──────────────────────────────────────────────

class QuitConfirmScene(Scene):
    """Confirmation prompt before quitting the game.

    Shows a yes/no prompt. Y confirms quit, N/Escape returns to HQ.
    """

    def __init__(self, game_state):
        super().__init__(game_state)
        self.selected = 1  # Default to "No" (safe option)

    def handle_input(self, key):
        """Handle quit confirmation input.

        Y - Quit the game
        N / Escape - Return to HQ
        Arrow keys / Enter - Navigate and select

        Args:
            key: The curses key code.
        """
        if key in (ord("y"), ord("Y")):
            self.game_state.running = False
        elif key in (ord("n"), ord("N"), 27):  # N or Escape
            self.game_state.pop_scene()
        elif key == curses.KEY_UP or key == curses.KEY_LEFT:
            self.selected = (self.selected - 1) % 2
        elif key == curses.KEY_DOWN or key == curses.KEY_RIGHT:
            self.selected = (self.selected + 1) % 2
        elif key in (curses.KEY_ENTER, 10, 13):
            if self.selected == 0:
                self.game_state.running = False
            else:
                self.game_state.pop_scene()

    def draw(self, win):
        """Render the quit confirmation dialog.

        Args:
            win: The curses standard screen window.
        """
        max_h, max_w = win.getmaxyx()

        ui.draw_header_bar(win, "IRON CONTRACT - QUIT?")
        ui.draw_status_bar(win, "Y: Quit | N: Cancel | Arrow Keys: Navigate | Enter: Select")

        center_y = max_h // 2

        # Confirmation box
        box_w = 40
        box_h = 7
        box_x = (max_w - box_w) // 2
        box_y = center_y - 4

        ui.draw_box(win, box_y, box_x, box_h, box_w, title="Confirm Quit")

        ui.draw_centered_text(
            win, box_y + 2,
            "Are you sure you want to quit?",
            ui.color_text(ui.COLOR_TITLE) | curses.A_BOLD,
        )

        # Yes / No options
        options = ["Yes", "No"]
        option_y = box_y + 4
        ui.draw_menu(win, option_y, options, self.selected)


# ── Mech Bay Placeholder Scene ───────────────────────────────────────────

class MechBayScene(Scene):
    """Placeholder screen for the mech bay.

    Displays the current mech roster with armor/status info.
    Full repair and customization features to be added in later issues.
    """

    def __init__(self, game_state):
        super().__init__(game_state)
        self.scroll_offset = 0

    def handle_input(self, key):
        """Navigate the mech bay. Escape returns to HQ.

        Args:
            key: The curses key code.
        """
        if key == 27:  # Escape
            self.game_state.pop_scene()
        elif key == curses.KEY_UP:
            self.scroll_offset = max(0, self.scroll_offset - 1)
        elif key == curses.KEY_DOWN:
            self.scroll_offset += 1

    def draw(self, win):
        """Render the mech bay screen.

        Args:
            win: The curses standard screen window.
        """
        max_h, max_w = win.getmaxyx()
        company = self.game_state.company

        ui.draw_header_bar(win, "IRON CONTRACT - MECH BAY")
        ui.draw_status_bar(win, "Esc: Back to HQ | Up/Down: Scroll")

        row = 2 - self.scroll_offset

        ui.draw_centered_text(
            win, row,
            "=== MECH BAY ===",
            ui.color_text(ui.COLOR_TITLE) | curses.A_BOLD,
        )
        row += 2

        if not company or not company.mechs:
            ui.draw_centered_text(
                win, row,
                "No mechs in the bay.",
                ui.color_text(ui.COLOR_MENU_INACTIVE),
            )
            return

        # Mech table
        col_widths = [22, 8, 6, 10, 10, 4, 4, 8]
        headers = ["MECH", "CLASS", "TONS", "ARMOR", "STRUCT", "FP", "SPD", "STATUS"]
        table_width = sum(col_widths) + len(col_widths) - 1
        table_x = max(1, (max_w - table_width) // 2)

        ui.draw_table_row(
            win, row, table_x, headers, col_widths,
            ui.color_text(ui.COLOR_STATUS) | curses.A_BOLD,
        )
        row += 1

        try:
            sep = "-" * table_width
            sep_x = max(1, (max_w - len(sep)) // 2)
            win.addstr(row, sep_x, sep, ui.color_text(ui.COLOR_BORDER))
        except curses.error:
            pass
        row += 1

        for mech in company.mechs:
            armor_str = f"{mech.armor_current}/{mech.armor_max}"
            struct_str = f"{mech.structure_current}/{mech.structure_max}"

            if mech.status == MechStatus.DESTROYED:
                status_str = "[X] DEST"
            elif mech.status == MechStatus.DAMAGED:
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

            if mech.status == MechStatus.DESTROYED:
                row_attr = ui.color_text(ui.COLOR_WARNING) | curses.A_BOLD
            elif mech.status == MechStatus.DAMAGED:
                row_attr = ui.color_text(ui.COLOR_WARNING)
            else:
                row_attr = ui.color_text(ui.COLOR_ACCENT)

            ui.draw_table_row(win, row, table_x, cols, col_widths, row_attr)
            row += 1

        row += 2

        ui.draw_centered_text(
            win, row,
            "(Full repair and customization coming in a future update)",
            ui.color_text(ui.COLOR_MENU_INACTIVE),
        )
