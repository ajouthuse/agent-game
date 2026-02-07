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
from data.save_system import save_game


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
    5. Check for random events (30% chance)
    6. Update week counter

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
        - random_event: RandomEvent instance if one occurred, None otherwise.
    """
    from data.contracts import generate_contracts
    from data.events import get_random_event

    summary = {
        "week_before": company.week,
        "active_pilots": 0,
        "payroll_cost": 0,
        "balance_before": company.c_bills,
        "repairs_progressed": [],
        "status_changes": [],
        "random_event": None,
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

    # 4. Update month tracker (each month = 4 weeks)
    old_month = company.month
    if not battle_contract:
        company.week += 1
        company.month = ((company.week - 1) // 4) + 1

    # Check if we entered a new month and if final contract should appear
    new_month = company.month
    month_changed = new_month > old_month
    summary["month_changed"] = month_changed
    summary["old_month"] = old_month
    summary["new_month"] = new_month

    # 5. Regenerate available contracts each week
    # After month 12, check if final contract should be added
    if company.month >= 12 and not company.final_contract_completed:
        from data.contracts import generate_final_contract
        # Check if final contract is already in available contracts
        has_final = any(c.is_final_contract for c in company.available_contracts)
        if not has_final:
            # Add final contract to the market
            company.available_contracts = generate_contracts(company.week)
            final_contract = generate_final_contract()
            company.available_contracts.append(final_contract)
        else:
            company.available_contracts = generate_contracts(company.week)
    else:
        company.available_contracts = generate_contracts(company.week)

    # 6. Check for random events (30% chance)
    random_event = get_random_event()
    summary["random_event"] = random_event

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
        S - Stats (view campaign statistics)
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
        elif key in (ord("s"), ord("S")):
            self._go_campaign_stats()
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

    def _go_campaign_stats(self):
        """Navigate to the campaign statistics screen."""
        self.game_state.push_scene(CampaignStatsScene(self.game_state))

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
            # Check if random event occurred
            elif summary.get("random_event"):
                # Show event first, then summary
                self.game_state.push_scene(
                    RandomEventScene(self.game_state, summary["random_event"], summary)
                )
            else:
                # Normal week summary
                self.game_state.push_scene(
                    WeeklySummaryScene(self.game_state, summary)
                )

            # Auto-save after week advances
            save_game(company)

            # Check victory condition (reputation >= 75 AND c_bills >= 10,000,000)
            if company.reputation >= 75 and company.c_bills >= 10_000_000:
                from game.scenes import VictoryScene
                self.game_state.push_scene(VictoryScene(self.game_state))

    def _confirm_quit(self):
        """Save the game and return to main menu."""
        company = self.game_state.company
        if company:
            save_game(company)
        # Pop back to main menu (clear all scenes)
        while self.game_state.current_scene:
            self.game_state.pop_scene()

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

        # Company name and month
        title_line = f"IRON CONTRACT - {company.name}"
        month_str = f"Month {company.month}"
        # Draw title on left, month on right within box
        title_attr = ui.color_text(ui.COLOR_TITLE) | curses.A_BOLD
        try:
            # Truncate if necessary
            avail = inner_w - len(month_str) - 2
            display_title = title_line[:avail] if len(title_line) > avail else title_line
            win.addstr(row, inner_x, display_title, title_attr)
            month_x = box_x + box_w - len(month_str) - 3
            win.addstr(row, month_x, month_str, title_attr)
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
        row += 1

        # Company stats (lance size, contracts completed)
        lance_size = len([mw for mw in company.mechwarriors if mw.status != PilotStatus.KIA])
        stats2_line = f"Lance: {lance_size} pilots | Contracts: {company.contracts_completed}"
        try:
            win.addstr(
                row, inner_x, stats2_line[:inner_w],
                ui.color_text(ui.COLOR_ACCENT),
            )
        except curses.error:
            pass
        row += 1

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
            ("S", "Stats", "View campaign statistics"),
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


# ── Random Event Scene ───────────────────────────────────────────────────

class RandomEventScene(Scene):
    """Displays a random inter-week event.

    Shows event title, description, and applies the event's effect.
    If the event requires a choice, shows Y/N options.
    """

    def __init__(self, game_state, event, summary):
        """Initialize with the event and weekly summary data.

        Args:
            game_state: The GameState instance.
            event: The RandomEvent instance.
            summary: Dict from advance_week() with summary data.
        """
        super().__init__(game_state)
        self.event = event
        self.summary = summary
        self.selected = 1  # Default to "No" for choice events
        self.event_applied = False
        self.result_text = ""

    def handle_input(self, key):
        """Handle event screen input.

        For non-choice events: Enter to continue
        For choice events: Y/N or arrow keys + Enter

        Args:
            key: The curses key code.
        """
        if not self.event.requires_choice:
            # Simple event - just press Enter to continue
            if key in (curses.KEY_ENTER, 10, 13):
                if not self.event_applied:
                    self._apply_event(True)
                else:
                    self._proceed()
        else:
            # Choice event - Y/N or arrow keys
            if key in (ord("y"), ord("Y")):
                self._apply_event(True)
            elif key in (ord("n"), ord("N")):
                self._apply_event(False)
            elif key == curses.KEY_UP or key == curses.KEY_LEFT:
                self.selected = (self.selected - 1) % 2
            elif key == curses.KEY_DOWN or key == curses.KEY_RIGHT:
                self.selected = (self.selected + 1) % 2
            elif key in (curses.KEY_ENTER, 10, 13):
                # 0 = Yes, 1 = No
                self._apply_event(self.selected == 0)

    def _apply_event(self, accepted):
        """Apply the event's effect and store the result."""
        if not self.event_applied:
            from data.events import apply_event
            self.result_text = apply_event(self.event, self.game_state.company, accepted)
            self.event_applied = True
            # Record event in history
            if self.game_state.company:
                event_entry = f"Week {self.game_state.company.week}: {self.event.title}"
                self.game_state.company.event_history.append(event_entry)
        # After applying, proceed to summary
        self._proceed()

    def _proceed(self):
        """Continue to weekly summary."""
        self.game_state.pop_scene()  # Pop event scene
        # Push weekly summary
        self.game_state.push_scene(
            WeeklySummaryScene(self.game_state, self.summary)
        )

    def draw(self, win):
        """Render the random event screen.

        Args:
            win: The curses standard screen window.
        """
        max_h, max_w = win.getmaxyx()

        ui.draw_header_bar(win, "IRON CONTRACT - RANDOM EVENT")

        if self.event.requires_choice and not self.event_applied:
            ui.draw_status_bar(win, "Y: Accept | N: Decline | Arrow Keys: Navigate | Enter: Select")
        else:
            ui.draw_status_bar(win, "Press ENTER to continue")

        # Event box
        box_w = min(70, max_w - 6)
        box_h = 15
        box_x = (max_w - box_w) // 2
        box_y = max(2, (max_h - box_h) // 2)

        ui.draw_box(win, box_y, box_x, box_h, box_w, title="Event")

        inner_x = box_x + 2
        inner_w = box_w - 4
        row = box_y + 2

        # Event title
        try:
            win.addstr(
                row, inner_x,
                self.event.title.upper()[:inner_w],
                ui.color_text(ui.COLOR_TITLE) | curses.A_BOLD,
            )
        except curses.error:
            pass
        row += 2

        # Event description (word wrap)
        description_lines = self._wrap_text(self.event.description, inner_w)
        for line in description_lines[:5]:  # Limit to 5 lines
            try:
                win.addstr(
                    row, inner_x,
                    line,
                    ui.color_text(ui.COLOR_MENU_INACTIVE),
                )
            except curses.error:
                pass
            row += 1
        row += 1

        # Show result if event was applied
        if self.event_applied and self.result_text:
            try:
                win.addstr(
                    row, inner_x,
                    f"Result: {self.result_text[:inner_w]}",
                    ui.color_text(ui.COLOR_ACCENT) | curses.A_BOLD,
                )
            except curses.error:
                pass
            row += 2

        # Show choice options if needed
        if self.event.requires_choice and not self.event_applied:
            row += 1
            try:
                win.addstr(
                    row, inner_x,
                    self.event.choice_prompt[:inner_w],
                    ui.color_text(ui.COLOR_TITLE),
                )
            except curses.error:
                pass
            row += 1

            # Yes / No options
            options = ["Accept", "Decline"]
            option_y = row
            ui.draw_menu(win, option_y, options, self.selected)

    def _wrap_text(self, text, width):
        """Wrap text to fit within a given width.

        Args:
            text: The text to wrap.
            width: Maximum width in characters.

        Returns:
            A list of wrapped lines.
        """
        words = text.split()
        lines = []
        current_line = []
        current_length = 0

        for word in words:
            word_len = len(word)
            # +1 for space between words
            if current_length + word_len + len(current_line) > width:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
                current_length = word_len
            else:
                current_line.append(word)
                current_length += word_len

        if current_line:
            lines.append(" ".join(current_line))

        return lines


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


# ── Campaign Stats Scene ──────────────────────────────────────────────────

class CampaignStatsScene(Scene):
    """Displays comprehensive campaign statistics.

    Shows the player's performance across the entire campaign run including
    months survived, contracts completed, earnings, losses, and more.
    """

    def __init__(self, game_state):
        super().__init__(game_state)

    def handle_input(self, key):
        """Press Escape or Enter to return to HQ.

        Args:
            key: The curses key code.
        """
        if key in (27, curses.KEY_ENTER, 10, 13):  # Escape or Enter
            self.game_state.pop_scene()

    def draw(self, win):
        """Render the campaign statistics screen.

        Args:
            win: The curses standard screen window.
        """
        max_h, max_w = win.getmaxyx()
        company = self.game_state.company

        ui.draw_header_bar(win, "IRON CONTRACT - CAMPAIGN STATISTICS")
        ui.draw_status_bar(win, "Press ENTER or ESC to return to HQ")

        if not company:
            return

        # Stats box
        box_w = min(60, max_w - 6)
        box_h = 20
        box_x = (max_w - box_w) // 2
        box_y = max(2, (max_h - box_h) // 2)

        ui.draw_box(win, box_y, box_x, box_h, box_w, title="Campaign Statistics")

        inner_x = box_x + 2
        inner_w = box_w - 4
        row = box_y + 2

        # Company name
        try:
            win.addstr(
                row, inner_x,
                company.name.upper()[:inner_w],
                ui.color_text(ui.COLOR_TITLE) | curses.A_BOLD,
            )
        except curses.error:
            pass
        row += 2

        # Campaign progress
        stats = [
            ("Campaign Progress", ""),
            (f"  Month:", f"{company.month}"),
            (f"  Week:", f"{company.week}"),
            ("", ""),
            ("Performance", ""),
            (f"  Contracts Completed:", f"{company.contracts_completed}"),
            (f"  Total Earnings:", f"{company.total_earnings:,} C-Bills"),
            (f"  Current Balance:", f"{company.c_bills:,} C-Bills"),
            (f"  Reputation:", f"{company.reputation}/100"),
            ("", ""),
            ("Losses", ""),
            (f"  Mechs Lost:", f"{company.mechs_lost}"),
            (f"  Pilots Lost:", f"{company.pilots_lost}"),
            ("", ""),
            ("Current Forces", ""),
            (f"  Active Mechs:", f"{len([m for m in company.mechs if m.status == MechStatus.READY])}"),
            (f"  Total Mechs:", f"{len(company.mechs)}"),
            (f"  Active Pilots:", f"{len([mw for mw in company.mechwarriors if mw.status != PilotStatus.KIA])}"),
        ]

        for label, value in stats:
            if row >= box_y + box_h - 1:
                break

            if label and not value:
                # Section header
                try:
                    win.addstr(
                        row, inner_x,
                        label[:inner_w],
                        ui.color_text(ui.COLOR_ACCENT) | curses.A_BOLD,
                    )
                except curses.error:
                    pass
            elif label:
                # Stat line
                try:
                    win.addstr(
                        row, inner_x,
                        label[:inner_w - 20],
                        ui.color_text(ui.COLOR_MENU_INACTIVE),
                    )
                    value_x = box_x + box_w - len(value) - 3
                    win.addstr(
                        row, value_x,
                        value[:20],
                        ui.color_text(ui.COLOR_TITLE),
                    )
                except curses.error:
                    pass
            row += 1


# ── Victory Scene ─────────────────────────────────────────────────────────

class VictoryScene(Scene):
    """Displays the campaign victory screen.

    Shows when the player completes the final contract successfully.
    Displays comprehensive campaign statistics and congratulations.
    """

    def __init__(self, game_state):
        super().__init__(game_state)

    def handle_input(self, key):
        """Press Enter to return to main menu.

        Args:
            key: The curses key code.
        """
        if key in (curses.KEY_ENTER, 10, 13):
            # Return to main menu
            while self.game_state.current_scene:
                self.game_state.pop_scene()

    def draw(self, win):
        """Render the victory screen.

        Args:
            win: The curses standard screen window.
        """
        max_h, max_w = win.getmaxyx()
        company = self.game_state.company

        ui.draw_header_bar(win, "IRON CONTRACT - VICTORY!")
        ui.draw_status_bar(win, "Press ENTER to return to main menu")

        if not company:
            return

        row = 3

        # Victory banner
        ui.draw_centered_text(
            win, row,
            "╔═══════════════════════════════════════╗",
            ui.color_text(ui.COLOR_TITLE) | curses.A_BOLD,
        )
        row += 1
        ui.draw_centered_text(
            win, row,
            "║       CAMPAIGN VICTORY ACHIEVED!      ║",
            ui.color_text(ui.COLOR_TITLE) | curses.A_BOLD,
        )
        row += 1
        ui.draw_centered_text(
            win, row,
            "╚═══════════════════════════════════════╝",
            ui.color_text(ui.COLOR_TITLE) | curses.A_BOLD,
        )
        row += 3

        # Victory message
        victory_lines = [
            f"Congratulations, Commander!",
            "",
            f"{company.name} has completed the legendary final contract",
            "and secured the Star League cache. Your company's reputation",
            "now echoes across the Inner Sphere as one of the greatest",
            "mercenary units of the era.",
            "",
            "Your name will be remembered in the annals of history.",
        ]

        for line in victory_lines:
            ui.draw_centered_text(
                win, row,
                line,
                ui.color_text(ui.COLOR_ACCENT),
            )
            row += 1

        row += 2

        # Campaign stats
        ui.draw_centered_text(
            win, row,
            "═══ FINAL CAMPAIGN STATISTICS ═══",
            ui.color_text(ui.COLOR_BORDER) | curses.A_BOLD,
        )
        row += 2

        stats_lines = [
            f"Campaign Duration: {company.month} months ({company.week} weeks)",
            f"Contracts Completed: {company.contracts_completed}",
            f"Total Earnings: {company.total_earnings:,} C-Bills",
            f"Final Balance: {company.c_bills:,} C-Bills",
            f"Final Reputation: {company.reputation}/100",
            f"Mechs Lost: {company.mechs_lost}",
            f"Pilots Lost: {company.pilots_lost}",
        ]

        for line in stats_lines:
            ui.draw_centered_text(
                win, row,
                line,
                ui.color_text(ui.COLOR_TITLE),
            )
            row += 1

        row += 2

        ui.draw_centered_text(
            win, row,
            "[ Press ENTER to return to main menu ]",
            ui.color_text(ui.COLOR_MENU_ACTIVE) | curses.A_BOLD,
        )
