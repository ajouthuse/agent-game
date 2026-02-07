"""
game.scenes - Concrete scene implementations for Iron Contract.

Provides:
- MainMenuScene: The main menu with New Game / Quit options.
- CompanyNameScene: Text input screen for naming the mercenary company.
- RosterSummaryScene: Displays the newly created company roster.
- HQScene: Re-exported from game.hq (headquarters dashboard with turn cycle).
- RosterScene: Full company roster view with pilot selection.
- PilotDetailScene: Detailed view of a single pilot's stats and progression.
- LevelUpScene: Skill improvement choice screen for leveling up.
- ContractMarketScene: Contract market with selectable contracts.
- ContractBriefingScene: Detailed briefing for a selected contract.
- MissionReportScene: Post-mission combat log and results summary.
- UpkeepPhaseScene: Monthly upkeep screen for repair decisions.
- FinancialSummaryScene: End-of-month financial report.
- DeserterScene: Narrative screen for pilot desertions.
- GameOverScene: Bankruptcy game over screen.
"""

import curses

import ui
from data import Company, create_starting_lance, create_starting_pilots
from data.models import PilotStatus, MechStatus
from data.contracts import generate_contracts
from data.combat import resolve_combat, CombatOutcome
from data.finance import (
    calculate_monthly_upkeep,
    apply_upkeep,
    is_bankrupt,
    _recalculate_totals,
)
from data.progression import (
    apply_morale_outcome,
    check_desertion,
    generate_desertion_message,
    recover_injuries,
    get_pilots_with_pending_levelups,
    can_level_up,
    apply_level_up,
    is_pilot_deployable,
)
from data.save_system import (
    autosave_exists,
    load_game,
    list_save_files,
)
from game.scene import Scene


# ── Main Menu Scene ─────────────────────────────────────────────────────────

class MainMenuScene(Scene):
    """The main menu screen with dynamic options based on save files.

    Menu options adapt based on save file availability:
    - Continue: appears if autosave exists, loads it automatically
    - New Game: always available
    - Load Game: appears if any saves exist, allows file selection
    - Quit: always available
    """

    def __init__(self, game_state):
        super().__init__(game_state)
        self.selected = 0
        self._build_menu_options()

    def _build_menu_options(self):
        """Build menu options based on save file availability."""
        self.menu_options = []

        # Add "Continue" if autosave exists
        if autosave_exists():
            self.menu_options.append("Continue")

        # Always add "New Game"
        self.menu_options.append("New Game")

        # Add "Load Game" if any saves exist
        if list_save_files():
            self.menu_options.append("Load Game")

        # Always add "Quit"
        self.menu_options.append("Quit")

    def handle_input(self, key):
        """Navigate menu with arrow keys, select with Enter.

        Args:
            key: The curses key code.
        """
        if key == curses.KEY_UP:
            self.selected = (self.selected - 1) % len(self.menu_options)
        elif key == curses.KEY_DOWN:
            self.selected = (self.selected + 1) % len(self.menu_options)
        elif key in (curses.KEY_ENTER, 10, 13):
            self._select_option()
        elif key in (ord("q"), ord("Q")):
            self.game_state.running = False

    def _select_option(self):
        """Execute the currently highlighted menu option."""
        choice = self.menu_options[self.selected]
        if choice == "Continue":
            self._load_autosave()
        elif choice == "New Game":
            self.game_state.push_scene(CompanyNameScene(self.game_state))
        elif choice == "Load Game":
            self.game_state.push_scene(LoadGameScene(self.game_state))
        elif choice == "Quit":
            self.game_state.running = False

    def _load_autosave(self):
        """Load the autosave file and proceed to HQ."""
        company, message = load_game()
        if company:
            self.game_state.company = company
            self.game_state.push_scene(HQScene(self.game_state))
        else:
            # Failed to load - show error message
            # For now, just rebuild menu (autosave might be corrupted)
            self._build_menu_options()
            self.selected = 0

    def draw(self, win):
        """Render the main menu with title art and selectable options.

        Args:
            win: The curses standard screen window.
        """
        max_h, max_w = win.getmaxyx()

        # Draw layout
        ui.draw_header_bar(win)
        ui.draw_status_bar(win)

        # Draw title art centered vertically in the upper portion
        title_start_y = max(2, (max_h // 2) - len(ui.TITLE_ART) - 3)
        ui.draw_title_art(win, title_start_y)

        # Subtitle
        subtitle_y = title_start_y + len(ui.TITLE_ART) + 1
        ui.draw_centered_text(
            win,
            subtitle_y,
            "Mercenary Company Management Simulator",
            ui.color_text(ui.COLOR_ACCENT),
        )

        # Menu options
        menu_y = subtitle_y + 3
        ui.draw_menu(win, menu_y, self.menu_options, self.selected)


# ── Load Game Scene ──────────────────────────────────────────────────────

class LoadGameScene(Scene):
    """Save file selection screen for loading saved games.

    Displays all available save files with metadata (company name, week, etc.)
    and allows the player to select one to load.
    """

    def __init__(self, game_state):
        super().__init__(game_state)
        self.save_files = list_save_files()
        self.selected = 0

    def handle_input(self, key):
        """Navigate save file list with arrow keys, select with Enter.

        Args:
            key: The curses key code.
        """
        if key == 27:  # Escape - go back to main menu
            self.game_state.pop_scene()
        elif key == curses.KEY_UP:
            if self.save_files:
                self.selected = (self.selected - 1) % len(self.save_files)
        elif key == curses.KEY_DOWN:
            if self.save_files:
                self.selected = (self.selected + 1) % len(self.save_files)
        elif key in (curses.KEY_ENTER, 10, 13):
            self._load_selected_save()
        elif key in (ord("q"), ord("Q")):
            self.game_state.running = False

    def _load_selected_save(self):
        """Load the currently selected save file."""
        if not self.save_files:
            return

        filename, company_name, saved_at = self.save_files[self.selected]
        company, message = load_game(filename)

        if company:
            self.game_state.company = company
            # Pop load game scene, then push HQ
            self.game_state.pop_scene()
            self.game_state.push_scene(HQScene(self.game_state))
        else:
            # Failed to load - refresh the list
            self.save_files = list_save_files()
            self.selected = 0

    def draw(self, win):
        """Render the load game screen with save file list.

        Args:
            win: The curses standard screen window.
        """
        max_h, max_w = win.getmaxyx()

        ui.draw_header_bar(win, "IRON CONTRACT - LOAD GAME")
        ui.draw_status_bar(win, "Up/Down: Select | Enter: Load | Esc: Back | Q: Quit")

        row = 3

        ui.draw_centered_text(
            win, row,
            "SELECT SAVE FILE",
            ui.color_text(ui.COLOR_TITLE) | curses.A_BOLD,
        )
        row += 2

        if not self.save_files:
            ui.draw_centered_text(
                win, row,
                "No save files found.",
                ui.color_text(ui.COLOR_MENU_INACTIVE),
            )
            return

        # Draw save file list
        for i, (filename, company_name, saved_at) in enumerate(self.save_files):
            if row >= max_h - 3:
                break

            # Format the save file info
            date_str = saved_at.strftime("%Y-%m-%d %H:%M")
            label = f"{company_name} - {filename} ({date_str})"

            if i == self.selected:
                attr = ui.color_text(ui.COLOR_MENU_ACTIVE) | curses.A_BOLD
                label = f"  > {label}"
            else:
                attr = ui.color_text(ui.COLOR_MENU_INACTIVE)
                label = f"    {label}"

            try:
                # Center the text
                text_x = max(1, (max_w - len(label)) // 2)
                win.addstr(row, text_x, label[:max_w - 2], attr)
            except curses.error:
                pass

            row += 1


# ── Company Name Input Scene ───────────────────────────────────────────────

class CompanyNameScene(Scene):
    """Text input scene where the player names their mercenary company.

    After entering a valid name and pressing Enter, the company is created
    with a starting lance and roster, and the player proceeds to the
    roster summary screen.
    """

    MAX_NAME_LENGTH = 30

    def __init__(self, game_state):
        super().__init__(game_state)
        self.company_name = ""
        self.error_message = ""

    def handle_input(self, key):
        """Handle text input for the company name.

        Supports typing, backspace, Enter to confirm, and Escape to cancel.

        Args:
            key: The curses key code.
        """
        if key == 27:  # Escape
            self.game_state.pop_scene()
        elif key in (curses.KEY_ENTER, 10, 13):
            self._confirm_name()
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            if self.company_name:
                self.company_name = self.company_name[:-1]
                self.error_message = ""
        elif 32 <= key <= 126:  # Printable ASCII
            if len(self.company_name) < self.MAX_NAME_LENGTH:
                self.company_name += chr(key)
                self.error_message = ""

    def _confirm_name(self):
        """Validate the company name and create the company."""
        name = self.company_name.strip()
        if not name:
            self.error_message = "Company name cannot be empty!"
            return

        # Create company with starting lance and pilots
        company = _create_new_company(name)
        self.game_state.company = company

        # Pop this scene and push the roster summary
        self.game_state.pop_scene()
        self.game_state.push_scene(RosterSummaryScene(self.game_state))

    def draw(self, win):
        """Render the company name input screen.

        Args:
            win: The curses standard screen window.
        """
        max_h, max_w = win.getmaxyx()

        ui.draw_header_bar(win, "IRON CONTRACT - NEW CAMPAIGN")
        ui.draw_status_bar(win, "Type your company name | Enter: Confirm | Esc: Back")

        center_y = max_h // 2

        # Box around the input area
        box_w = 50
        box_h = 9
        box_x = (max_w - box_w) // 2
        box_y = center_y - 5
        ui.draw_box(win, box_y, box_x, box_h, box_w, title="Company Creation")

        # Prompt text
        ui.draw_centered_text(
            win,
            center_y - 3,
            "Name your mercenary company:",
            ui.color_text(ui.COLOR_TITLE) | curses.A_BOLD,
        )

        # Text input field
        input_w = 34
        input_x = (max_w - input_w) // 2
        ui.draw_text_input(win, center_y - 1, input_x, input_w, self.company_name)

        # Error message (if any)
        if self.error_message:
            ui.draw_centered_text(
                win,
                center_y + 1,
                self.error_message,
                ui.color_text(ui.COLOR_WARNING) | curses.A_BOLD,
            )

        # Hint
        ui.draw_centered_text(
            win,
            center_y + 5,
            "Choose a name worthy of the battlefield.",
            ui.color_text(ui.COLOR_MENU_INACTIVE),
        )


# ── Roster Summary Scene ──────────────────────────────────────────────────

class RosterSummaryScene(Scene):
    """Displays the newly created company roster before proceeding to HQ.

    Shows the full mech bay and pilot roster in table format.
    """

    def __init__(self, game_state):
        super().__init__(game_state)
        self.scroll_offset = 0

    def handle_input(self, key):
        """Press Enter to proceed to HQ, or Escape to go back.

        Args:
            key: The curses key code.
        """
        if key in (curses.KEY_ENTER, 10, 13):
            # Replace the scene stack: pop summary, push HQ
            self.game_state.pop_scene()
            self.game_state.push_scene(HQScene(self.game_state))
        elif key == 27:  # Escape - go back to main menu
            self.game_state.company = None
            self.game_state.pop_scene()
        elif key == curses.KEY_UP:
            self.scroll_offset = max(0, self.scroll_offset - 1)
        elif key == curses.KEY_DOWN:
            self.scroll_offset += 1
        elif key in (ord("q"), ord("Q")):
            self.game_state.running = False

    def draw(self, win):
        """Render the company roster summary.

        Args:
            win: The curses standard screen window.
        """
        max_h, max_w = win.getmaxyx()
        company = self.game_state.company

        ui.draw_header_bar(win, "IRON CONTRACT - COMPANY ROSTER")
        ui.draw_status_bar(win, "Enter: Proceed to HQ | Esc: Cancel | Q: Quit")

        # Title
        start_y = 2 - self.scroll_offset

        ui.draw_centered_text(
            win,
            start_y,
            "COMPANY CREATED SUCCESSFULLY",
            ui.color_text(ui.COLOR_ACCENT) | curses.A_BOLD,
        )
        start_y += 1

        # Draw the roster tables
        ui.draw_roster_table(win, start_y + 1, company)

        # "Press Enter to continue" prompt at bottom
        ui.draw_centered_text(
            win,
            max_h - 3,
            "[ Press ENTER to proceed to Headquarters ]",
            ui.color_text(ui.COLOR_TITLE) | curses.A_BOLD,
        )


# ── HQ Scene (Hub / Dashboard) ───────────────────────────────────────────
# The HQ dashboard and turn cycle system are implemented in game.hq.
# HQScene is imported from there for backwards compatibility. It provides
# letter-key navigation (C, R, M, A, Q), weekly advance with payroll,
# and contextual status bar. See game/hq.py for full implementation.

from game.hq import HQScene  # noqa: F811 — re-exported intentionally


# ── Roster Scene (Accessible from HQ) ───────────────────────────────────

class RosterScene(Scene):
    """Full roster screen accessible from HQ.

    Displays the company's mech bay and pilot roster in a combined
    table view. Shows armor percentage, pilot assignments, and
    damage indicators for non-Ready mechs and non-Active pilots.
    Players can select a pilot to view their detailed stats.
    """

    def __init__(self, game_state):
        super().__init__(game_state)
        self.scroll_offset = 0
        self.selected_pilot = 0
        self.mode = "roster"  # "roster" = viewing table, "pilot_select" = pilot list

    def handle_input(self, key):
        """Navigate roster and select pilots for detail view.

        Args:
            key: The curses key code.
        """
        company = self.game_state.company
        pilots = [mw for mw in company.mechwarriors if mw.status != PilotStatus.KIA]

        if key == 27:  # Escape - return to HQ
            if self.mode == "pilot_select":
                self.mode = "roster"
            else:
                self.game_state.pop_scene()
        elif key in (ord("p"), ord("P")):
            # Toggle pilot selection mode
            if pilots:
                self.mode = "pilot_select"
                self.selected_pilot = 0
        elif self.mode == "pilot_select":
            if key == curses.KEY_UP:
                self.selected_pilot = (self.selected_pilot - 1) % len(pilots)
            elif key == curses.KEY_DOWN:
                self.selected_pilot = (self.selected_pilot + 1) % len(pilots)
            elif key in (curses.KEY_ENTER, 10, 13):
                if pilots:
                    pilot = pilots[self.selected_pilot]
                    self.game_state.push_scene(
                        PilotDetailScene(self.game_state, pilot)
                    )
        else:
            if key == curses.KEY_UP:
                self.scroll_offset = max(0, self.scroll_offset - 1)
            elif key == curses.KEY_DOWN:
                self.scroll_offset += 1
            elif key in (ord("q"), ord("Q")):
                self.game_state.running = False

    def draw(self, win):
        """Render the full roster screen.

        Args:
            win: The curses standard screen window.
        """
        max_h, max_w = win.getmaxyx()
        company = self.game_state.company

        ui.draw_header_bar(win, "IRON CONTRACT - COMPANY ROSTER")

        if self.mode == "pilot_select":
            ui.draw_status_bar(
                win,
                "Up/Down: Select Pilot | Enter: View Detail | Esc: Back"
            )
        else:
            ui.draw_status_bar(
                win,
                "P: Select Pilot | Esc: Back to HQ | Q: Quit | Up/Down: Scroll"
            )

        start_y = 2 - self.scroll_offset

        # Draw the roster tables
        end_row = ui.draw_roster_table(win, start_y + 1, company)

        # If in pilot selection mode, show selection overlay
        if self.mode == "pilot_select":
            pilots = [mw for mw in company.mechwarriors if mw.status != PilotStatus.KIA]
            sel_y = max(end_row + 1, 2) if end_row else 2
            ui.draw_centered_text(
                win, sel_y,
                "--- SELECT PILOT ---",
                ui.color_text(ui.COLOR_BORDER) | curses.A_BOLD,
            )
            sel_y += 1
            for i, mw in enumerate(pilots):
                if sel_y >= max_h - 2:
                    break
                if i == self.selected_pilot:
                    attr = ui.color_text(ui.COLOR_MENU_ACTIVE) | curses.A_BOLD
                    label = f'  > {mw.callsign} ({mw.name}) - {mw.status.value}'
                else:
                    attr = ui.color_text(ui.COLOR_MENU_INACTIVE)
                    label = f'    {mw.callsign} ({mw.name}) - {mw.status.value}'
                ui.draw_centered_text(win, sel_y, label, attr)
                sel_y += 1


# ── Contract Market Scene ─────────────────────────────────────────────────

class ContractMarketScene(Scene):
    """Contract market screen showing available contracts.

    Displays the 3 available contracts from the company's contract market.
    The player can select a contract to view its detailed briefing.
    """

    def __init__(self, game_state):
        super().__init__(game_state)
        self.selected = 0
        company = game_state.company

        # Generate contracts if none exist (first time visiting)
        if company and not company.available_contracts:
            company.available_contracts = generate_contracts(company.week)

        self.contracts = company.available_contracts if company else []

    def handle_input(self, key):
        """Navigate the contract list and select contracts.

        Args:
            key: The curses key code.
        """
        if key == curses.KEY_UP:
            self.selected = (self.selected - 1) % len(self.contracts)
        elif key == curses.KEY_DOWN:
            self.selected = (self.selected + 1) % len(self.contracts)
        elif key in (curses.KEY_ENTER, 10, 13):
            # Open briefing for the selected contract
            contract = self.contracts[self.selected]
            self.game_state.push_scene(
                ContractBriefingScene(self.game_state, contract)
            )
        elif key == 27:  # Escape - return to HQ
            self.game_state.pop_scene()
        elif key in (ord("q"), ord("Q")):
            self.game_state.running = False

    def draw(self, win):
        """Render the contract market screen.

        Args:
            win: The curses standard screen window.
        """
        max_h, max_w = win.getmaxyx()
        company = self.game_state.company

        ui.draw_header_bar(win, "IRON CONTRACT - CONTRACT MARKET")
        ui.draw_status_bar(
            win,
            "Up/Down: Browse | Enter: View Briefing | Esc: Back to HQ"
        )

        row = 2

        # Title
        ui.draw_centered_text(
            win, row,
            "AVAILABLE CONTRACTS",
            ui.color_text(ui.COLOR_TITLE) | curses.A_BOLD,
        )
        row += 1

        if company:
            month_str = f"Month {company.week} | C-Bills: {company.c_bills:,}"
            ui.draw_centered_text(
                win, row, month_str,
                ui.color_text(ui.COLOR_MENU_INACTIVE),
            )
        row += 2

        # Draw the contract list
        row = ui.draw_contract_list(win, row, self.contracts, self.selected)

        row += 2

        # Hint
        ui.draw_centered_text(
            win, row,
            "Select a contract to view the mission briefing.",
            ui.color_text(ui.COLOR_MENU_INACTIVE),
        )


# ── Contract Briefing Scene ──────────────────────────────────────────────

class ContractBriefingScene(Scene):
    """Detailed contract briefing screen.

    Shows full contract details including flavor text and payout terms.
    The player can confirm acceptance or go back to the contract market.
    If a contract is already active, acceptance is disabled.
    """

    def __init__(self, game_state, contract):
        super().__init__(game_state)
        self.contract = contract
        self.selected = 0
        self.can_accept = not (game_state.company and game_state.company.active_contract)

        # Set menu options based on whether we can accept
        if self.can_accept:
            self.MENU_OPTIONS = ["Accept Contract", "Go Back"]
        else:
            self.MENU_OPTIONS = ["Go Back"]

    def handle_input(self, key):
        """Navigate briefing options. Accept or go back.

        Args:
            key: The curses key code.
        """
        if key == curses.KEY_UP:
            self.selected = (self.selected - 1) % len(self.MENU_OPTIONS)
        elif key == curses.KEY_DOWN:
            self.selected = (self.selected + 1) % len(self.MENU_OPTIONS)
        elif key in (curses.KEY_ENTER, 10, 13):
            self._select_option()
        elif key == 27:  # Escape - go back
            self.game_state.pop_scene()
        elif key in (ord("q"), ord("Q")):
            self.game_state.running = False

    def _select_option(self):
        """Execute the currently highlighted option."""
        choice = self.MENU_OPTIONS[self.selected]
        if choice == "Accept Contract" and self.can_accept:
            self._accept_contract()
        elif choice == "Go Back":
            self.game_state.pop_scene()

    def _accept_contract(self):
        """Accept the contract and set it as active.

        If a contract is already active, shows an error message.
        Otherwise, sets the contract as active and initializes its duration countdown.
        Then resolves combat and displays the mission report.
        """
        company = self.game_state.company
        if not company:
            return

        # Check if a contract is already active
        if company.active_contract:
            # Cannot accept - show error (for now, just ignore)
            # In a real implementation, we'd show a message to the user
            return

        # Set this contract as active
        self.contract.weeks_remaining = self.contract.duration
        company.active_contract = self.contract

        # Resolve combat (modifies company in place)
        result = resolve_combat(company, self.contract)

        # Pop briefing and market scenes
        self.game_state.pop_scene()  # Pop briefing
        self.game_state.pop_scene()  # Pop market

        # Push mission report scene
        self.game_state.push_scene(
            MissionReportScene(self.game_state, result, self.contract)
        )

    def draw(self, win):
        """Render the contract briefing screen.

        Args:
            win: The curses standard screen window.
        """
        max_h, max_w = win.getmaxyx()

        ui.draw_header_bar(win, "IRON CONTRACT - MISSION BRIEFING")
        ui.draw_status_bar(
            win,
            "Up/Down: Navigate | Enter: Select | Esc: Back"
        )

        # Draw the contract briefing
        row = 2
        row = ui.draw_contract_briefing(win, row, self.contract)

        # Show warning if contract already active
        if not self.can_accept:
            row += 1
            ui.draw_centered_text(
                win, row,
                "!! CANNOT ACCEPT: A contract is already active !!",
                ui.color_text(ui.COLOR_WARNING) | curses.A_BOLD,
            )
            row += 1

        # Draw the accept/go back menu
        menu_y = min(row + 1, max_h - 5)
        ui.draw_menu(win, menu_y, self.MENU_OPTIONS, self.selected)


# ── Mission Report Scene ─────────────────────────────────────────────────

class MissionReportScene(Scene):
    """Post-mission report screen showing combat log and results.

    Displays combat log entries one at a time with press-any-key pacing
    for dramatic effect. Once all events are revealed, shows a summary
    panel with outcome, damage, injuries, and rewards. Press Enter to
    return to HQ.
    """

    def __init__(self, game_state, result, contract):
        super().__init__(game_state)
        self.result = result
        self.contract = contract
        self.visible_events = 1  # Start with first event visible
        self.all_revealed = False
        self.scroll_offset = 0

    def handle_input(self, key):
        """Advance combat log or proceed to upkeep phase.

        Any key press reveals the next combat log entry. Once all
        entries are visible, the summary is shown. Press Enter or
        Escape to proceed to the monthly upkeep phase.

        Args:
            key: The curses key code.
        """
        if key == -1:
            return

        if not self.all_revealed:
            # Reveal next event
            self.visible_events += 1
            if self.visible_events >= len(self.result.combat_log):
                self.all_revealed = True
        else:
            # Summary is visible - navigate or dismiss
            if key in (curses.KEY_ENTER, 10, 13, 27):
                self._proceed_to_upkeep()
            elif key == curses.KEY_UP:
                self.scroll_offset = max(0, self.scroll_offset - 1)
            elif key == curses.KEY_DOWN:
                self.scroll_offset += 1
            elif key in (ord("q"), ord("Q")):
                self.game_state.running = False

    def _proceed_to_upkeep(self):
        """Transition from mission report through progression to upkeep.

        Applies morale adjustments based on outcome, checks for desertions,
        recovers injuries, then proceeds to level-up prompts if any pilots
        are eligible, and finally to the upkeep phase.
        """
        company = self.game_state.company
        if company:
            # Check if this was the final contract and it was won
            if self.contract.is_final_contract and company.final_contract_completed:
                # Victory! Show victory screen
                self.game_state.pop_scene()  # Pop mission report
                from game.hq import VictoryScene
                self.game_state.push_scene(VictoryScene(self.game_state))
                return

            # Apply standardized morale outcome (in addition to combat system adjustments)
            apply_morale_outcome(company, self.result.outcome.value)

            # Check for desertions (pilots with 0 morale)
            deserters = check_desertion(company)
            desertion_messages = [
                generate_desertion_message(d) for d in deserters
            ]

            # Recover injuries from previously injured pilots
            recovery_messages = recover_injuries(company)

            # Calculate upkeep
            report = calculate_monthly_upkeep(company, self.result.c_bills_earned)

            self.game_state.pop_scene()  # Pop mission report

            # If there are desertions, show desertion scene first
            if desertion_messages:
                self.game_state.push_scene(
                    DeserterScene(
                        self.game_state, desertion_messages,
                        recovery_messages, report,
                    )
                )
            # Otherwise check for level-ups
            elif get_pilots_with_pending_levelups(company):
                pilots_to_level = get_pilots_with_pending_levelups(company)
                self.game_state.push_scene(
                    LevelUpScene(
                        self.game_state, pilots_to_level,
                        recovery_messages, report,
                    )
                )
            else:
                # Proceed directly to upkeep
                self.game_state.push_scene(
                    UpkeepPhaseScene(self.game_state, report, recovery_messages)
                )

    def draw(self, win):
        """Render the mission report screen.

        Args:
            win: The curses standard screen window.
        """
        max_h, max_w = win.getmaxyx()

        # Header
        outcome_title = f"IRON CONTRACT - MISSION REPORT"
        ui.draw_header_bar(win, outcome_title)

        if self.all_revealed:
            ui.draw_status_bar(
                win,
                "Enter: Proceed to Monthly Upkeep | Up/Down: Scroll | Q: Quit"
            )
        else:
            ui.draw_status_bar(
                win,
                "Press any key to continue..."
            )

        # Contract info line
        row = 2
        contract_info = (
            f"{self.contract.mission_type.value} for {self.contract.employer} "
            f"| Difficulty: {self.contract.skulls_display()}"
        )
        ui.draw_centered_text(
            win, row, contract_info,
            ui.color_text(ui.COLOR_MENU_INACTIVE),
        )
        row += 2

        # Draw the mission report (combat log + summary)
        ui.draw_mission_report(
            win, row, self.result,
            self.visible_events,
            self.scroll_offset,
        )

        # Show "Proceed to Upkeep" prompt when summary is visible
        if self.all_revealed:
            ui.draw_centered_text(
                win,
                max_h - 3,
                "[ Press ENTER to proceed to Monthly Upkeep ]",
                ui.color_text(ui.COLOR_TITLE) | curses.A_BOLD,
            )


# ── Upkeep Phase Scene ───────────────────────────────────────────────────

class UpkeepPhaseScene(Scene):
    """Monthly upkeep screen where the player decides on mech repairs.

    Displays fixed costs (pilot salaries, mech maintenance) and lets the
    player toggle repair decisions for each damaged mech. When confirmed,
    transitions to the financial summary screen. Also shows recovery
    messages for injured pilots.
    """

    def __init__(self, game_state, report, recovery_messages=None):
        super().__init__(game_state)
        self.report = report
        self.recovery_messages = recovery_messages or []
        self.selected = 0
        self.scroll_offset = 0

    def handle_input(self, key):
        """Navigate repair options and confirm upkeep.

        Up/Down: Navigate repair list.
        Space: Toggle repair on/off.
        F (Finalize): Confirm and proceed to financial summary.

        Args:
            key: The curses key code.
        """
        if self.report.repairs:
            if key == curses.KEY_UP:
                self.selected = (self.selected - 1) % len(self.report.repairs)
            elif key == curses.KEY_DOWN:
                self.selected = (self.selected + 1) % len(self.report.repairs)
            elif key == ord(" "):
                # Toggle the selected repair
                self.report.repairs[self.selected].repaired = (
                    not self.report.repairs[self.selected].repaired
                )
                _recalculate_totals(self.report)
            elif key in (ord("f"), ord("F"), curses.KEY_ENTER, 10, 13):
                self._finalize()
            elif key in (ord("q"), ord("Q")):
                self.game_state.running = False
        else:
            # No repairs needed - any confirm key to continue
            if key in (curses.KEY_ENTER, 10, 13, ord("f"), ord("F")):
                self._finalize()
            elif key in (ord("q"), ord("Q")):
                self.game_state.running = False

    def _finalize(self):
        """Apply upkeep costs and proceed to financial summary."""
        company = self.game_state.company
        if company:
            apply_upkeep(company, self.report)
            self.game_state.pop_scene()  # Pop upkeep phase
            self.game_state.push_scene(
                FinancialSummaryScene(self.game_state, self.report)
            )

    def draw(self, win):
        """Render the upkeep phase screen.

        Args:
            win: The curses standard screen window.
        """
        max_h, max_w = win.getmaxyx()

        ui.draw_header_bar(win, "IRON CONTRACT - MONTHLY UPKEEP")
        if self.report.repairs:
            ui.draw_status_bar(
                win,
                "Up/Down: Navigate | Space: Toggle Repair | F/Enter: Finalize Month"
            )
        else:
            ui.draw_status_bar(
                win,
                "Enter/F: Finalize Month | Q: Quit"
            )

        row = 2

        # Show recovery messages if any
        if self.recovery_messages:
            row = ui.draw_recovery_messages(win, row, self.recovery_messages)
            row += 1

        ui.draw_upkeep_phase(
            win, row, self.report,
            self.selected, self.scroll_offset,
        )

        # Finalize prompt at bottom
        ui.draw_centered_text(
            win,
            max_h - 3,
            "[ Press F or ENTER to finalize the month ]",
            ui.color_text(ui.COLOR_TITLE) | curses.A_BOLD,
        )


# ── Financial Summary Scene ──────────────────────────────────────────────

class FinancialSummaryScene(Scene):
    """End-of-month financial report showing itemized income and expenses.

    Displays the full breakdown of income from the contract vs. expenses
    (salaries, maintenance, repairs) with net profit/loss and updated balance.
    If the company is bankrupt, transitions to the GameOverScene.
    """

    def __init__(self, game_state, report):
        super().__init__(game_state)
        self.report = report
        self.scroll_offset = 0

    def handle_input(self, key):
        """Press Enter to return to HQ (or game over if bankrupt).

        Args:
            key: The curses key code.
        """
        if key in (curses.KEY_ENTER, 10, 13, 27):
            self._proceed()
        elif key == curses.KEY_UP:
            self.scroll_offset = max(0, self.scroll_offset - 1)
        elif key == curses.KEY_DOWN:
            self.scroll_offset += 1
        elif key in (ord("q"), ord("Q")):
            self.game_state.running = False

    def _proceed(self):
        """Check for bankruptcy and proceed accordingly."""
        company = self.game_state.company
        self.game_state.pop_scene()  # Pop financial summary

        if company and is_bankrupt(company):
            self.game_state.push_scene(
                GameOverScene(self.game_state)
            )
        # Otherwise, we return to HQ (already on the stack)

    def draw(self, win):
        """Render the financial summary screen.

        Args:
            win: The curses standard screen window.
        """
        max_h, max_w = win.getmaxyx()

        ui.draw_header_bar(win, "IRON CONTRACT - FINANCIAL SUMMARY")
        ui.draw_status_bar(
            win,
            "Enter: Continue | Up/Down: Scroll | Q: Quit"
        )

        row = 2
        ui.draw_financial_summary(
            win, row, self.report, self.scroll_offset,
        )

        # Continue prompt
        ui.draw_centered_text(
            win,
            max_h - 3,
            "[ Press ENTER to continue ]",
            ui.color_text(ui.COLOR_TITLE) | curses.A_BOLD,
        )


# ── Pilot Detail Scene ──────────────────────────────────────────────────

class PilotDetailScene(Scene):
    """Detailed view of a single pilot's stats and progression.

    Shows the pilot's full stats, XP progress, morale bar, injury
    status, and assigned mech. If the pilot can level up, allows
    the player to initiate a level-up.
    """

    def __init__(self, game_state, pilot):
        super().__init__(game_state)
        self.pilot = pilot
        self.scroll_offset = 0

    def handle_input(self, key):
        """Navigate pilot detail and optionally level up.

        Args:
            key: The curses key code.
        """
        if key == 27:  # Escape - go back
            self.game_state.pop_scene()
        elif key in (ord("l"), ord("L")):
            # Level up if available
            if can_level_up(self.pilot):
                self.game_state.push_scene(
                    LevelUpScene(
                        self.game_state,
                        [self.pilot],
                        callback_scene="detail",
                    )
                )
        elif key == curses.KEY_UP:
            self.scroll_offset = max(0, self.scroll_offset - 1)
        elif key == curses.KEY_DOWN:
            self.scroll_offset += 1
        elif key in (ord("q"), ord("Q")):
            self.game_state.running = False

    def draw(self, win):
        """Render the pilot detail screen.

        Args:
            win: The curses standard screen window.
        """
        max_h, max_w = win.getmaxyx()

        ui.draw_header_bar(win, "IRON CONTRACT - PILOT DETAIL")

        hints = "Esc: Back | Up/Down: Scroll"
        if can_level_up(self.pilot):
            hints += " | L: Level Up"
        ui.draw_status_bar(win, hints)

        # Find assigned mech
        assigned_mech = None
        if self.pilot.assigned_mech and self.game_state.company:
            for m in self.game_state.company.mechs:
                if m.name == self.pilot.assigned_mech:
                    assigned_mech = m
                    break

        start_y = 2 - self.scroll_offset
        ui.draw_pilot_detail(win, start_y, self.pilot, assigned_mech)


# ── Level-Up Scene ──────────────────────────────────────────────────────

class LevelUpScene(Scene):
    """Skill improvement choice screen for pilots with pending level-ups.

    Shows each eligible pilot one at a time, letting the player choose
    to improve gunnery or piloting. Can be triggered from the mission
    flow (between missions) or from the pilot detail screen.
    """

    def __init__(self, game_state, pilots, recovery_messages=None,
                 report=None, callback_scene=None):
        """Initialize the level-up scene.

        Args:
            game_state: The GameState instance.
            pilots: List of MechWarrior instances eligible for level-up.
            recovery_messages: Optional recovery messages to pass to upkeep.
            report: Optional UpkeepReport to pass to upkeep after level-ups.
            callback_scene: If "detail", pop back to pilot detail when done.
        """
        super().__init__(game_state)
        self.pilots = list(pilots)
        self.recovery_messages = recovery_messages or []
        self.report = report
        self.callback_scene = callback_scene
        self.current_pilot_index = 0
        self.selected = 0  # 0 = gunnery, 1 = piloting

    def handle_input(self, key):
        """Navigate level-up choices.

        Args:
            key: The curses key code.
        """
        pilot = self.pilots[self.current_pilot_index]

        if key == curses.KEY_UP:
            self.selected = (self.selected - 1) % 2
        elif key == curses.KEY_DOWN:
            self.selected = (self.selected + 1) % 2
        elif key in (curses.KEY_ENTER, 10, 13):
            self._apply_choice(pilot)
        elif key == 27:  # Escape - skip this level-up
            self._next_pilot()
        elif key in (ord("q"), ord("Q")):
            self.game_state.running = False

    def _apply_choice(self, pilot):
        """Apply the selected skill improvement.

        Args:
            pilot: The MechWarrior to level up.
        """
        if self.selected == 0:
            skill = "gunnery"
        else:
            skill = "piloting"

        success = apply_level_up(pilot, skill)
        if not success:
            # Skill already at minimum, try the other one
            return

        self._next_pilot()

    def _next_pilot(self):
        """Move to the next pilot or finish level-ups."""
        self.current_pilot_index += 1
        self.selected = 0

        if self.current_pilot_index >= len(self.pilots):
            self._finish()

    def _finish(self):
        """Complete the level-up phase and proceed."""
        self.game_state.pop_scene()  # Pop level-up scene

        if self.callback_scene == "detail":
            # We were called from pilot detail, just go back
            return

        # We were called from mission flow - proceed to upkeep
        if self.report:
            self.game_state.push_scene(
                UpkeepPhaseScene(
                    self.game_state, self.report, self.recovery_messages
                )
            )

    def draw(self, win):
        """Render the level-up choice screen.

        Args:
            win: The curses standard screen window.
        """
        max_h, max_w = win.getmaxyx()

        ui.draw_header_bar(win, "IRON CONTRACT - LEVEL UP")
        ui.draw_status_bar(
            win,
            "Up/Down: Choose Skill | Enter: Confirm | Esc: Skip"
        )

        if self.current_pilot_index < len(self.pilots):
            pilot = self.pilots[self.current_pilot_index]

            # Progress indicator
            progress = f"Pilot {self.current_pilot_index + 1} of {len(self.pilots)}"
            ui.draw_centered_text(
                win, 2, progress,
                ui.color_text(ui.COLOR_MENU_INACTIVE),
            )

            ui.draw_level_up_choice(win, 4, pilot, self.selected)


# ── Deserter Scene ──────────────────────────────────────────────────────

class DeserterScene(Scene):
    """Narrative screen showing pilot desertions.

    Displays dramatic desertion messages when pilots with 0 morale
    abandon the company, taking their mech with them. After viewing,
    proceeds to level-ups (if any) or the upkeep phase.
    """

    def __init__(self, game_state, desertion_messages, recovery_messages=None,
                 report=None):
        super().__init__(game_state)
        self.desertion_messages = desertion_messages
        self.recovery_messages = recovery_messages or []
        self.report = report

    def handle_input(self, key):
        """Press Enter to proceed.

        Args:
            key: The curses key code.
        """
        if key in (curses.KEY_ENTER, 10, 13, 27):
            self._proceed()
        elif key in (ord("q"), ord("Q")):
            self.game_state.running = False

    def _proceed(self):
        """Proceed to level-ups or upkeep after viewing desertions."""
        company = self.game_state.company
        self.game_state.pop_scene()  # Pop deserter scene

        # Check for level-ups
        if company and get_pilots_with_pending_levelups(company):
            pilots_to_level = get_pilots_with_pending_levelups(company)
            self.game_state.push_scene(
                LevelUpScene(
                    self.game_state, pilots_to_level,
                    self.recovery_messages, self.report,
                )
            )
        elif self.report:
            self.game_state.push_scene(
                UpkeepPhaseScene(
                    self.game_state, self.report, self.recovery_messages
                )
            )

    def draw(self, win):
        """Render the desertion scene.

        Args:
            win: The curses standard screen window.
        """
        max_h, max_w = win.getmaxyx()

        ui.draw_header_bar(win, "IRON CONTRACT - DESERTION")
        ui.draw_status_bar(win, "Press ENTER to continue")

        row = 3
        row = ui.draw_desertion_events(win, row, self.desertion_messages)

        # Continue prompt
        ui.draw_centered_text(
            win,
            max_h - 3,
            "[ Press ENTER to continue ]",
            ui.color_text(ui.COLOR_TITLE) | curses.A_BOLD,
        )


# ── Game Over Scene ──────────────────────────────────────────────────────

class GameOverScene(Scene):
    """Game over screen displayed when the company goes bankrupt.

    Shows final stats (months survived, contracts completed) and offers
    to return to the main menu.
    """

    MENU_OPTIONS = ["Return to Main Menu", "Quit"]

    def __init__(self, game_state):
        super().__init__(game_state)
        self.selected = 0

    def handle_input(self, key):
        """Navigate game over menu options.

        Args:
            key: The curses key code.
        """
        if key == curses.KEY_UP:
            self.selected = (self.selected - 1) % len(self.MENU_OPTIONS)
        elif key == curses.KEY_DOWN:
            self.selected = (self.selected + 1) % len(self.MENU_OPTIONS)
        elif key in (curses.KEY_ENTER, 10, 13):
            self._select_option()
        elif key in (ord("q"), ord("Q")):
            self.game_state.running = False

    def _select_option(self):
        """Execute the currently highlighted menu option."""
        choice = self.MENU_OPTIONS[self.selected]
        if choice == "Return to Main Menu":
            self._return_to_menu()
        elif choice == "Quit":
            self.game_state.running = False

    def _return_to_menu(self):
        """Clear game state and return to the main menu.

        Pops all scenes and pushes the main menu fresh.
        """
        # Pop all scenes
        while self.game_state.current_scene:
            self.game_state.pop_scene()
        # Reset company
        self.game_state.company = None
        # Push main menu
        self.game_state.push_scene(MainMenuScene(self.game_state))

    def draw(self, win):
        """Render the game over screen.

        Args:
            win: The curses standard screen window.
        """
        max_h, max_w = win.getmaxyx()

        ui.draw_header_bar(win, "IRON CONTRACT - GAME OVER")
        ui.draw_status_bar(win, "Up/Down: Navigate | Enter: Select")

        row = 3
        row = ui.draw_game_over(win, row, self.game_state.company)

        # Menu
        menu_y = min(row + 2, max_h - 5)
        ui.draw_menu(win, menu_y, self.MENU_OPTIONS, self.selected)


# ── Company Creation Helper ──────────────────────────────────────────────

def _create_new_company(name):
    """Create a new mercenary company with a starting lance and pilots.

    Creates 4 mechs (3 medium, 1 light) and the hardcoded starter pilots
    (Ace, Raven, Bulldog, Ghost), then auto-assigns each pilot to a mech.
    Starting C-Bills: 500,000.

    Args:
        name: The player-chosen company name.

    Returns:
        A fully initialized Company instance.
    """
    mechs = create_starting_lance()
    pilots = create_starting_pilots()

    # Auto-assign pilots to mechs
    for pilot, mech in zip(pilots, mechs):
        pilot.assigned_mech = mech.name

    return Company(
        name=name,
        c_bills=500_000,
        mechwarriors=pilots,
        mechs=mechs,
    )


# ── Battle Deployment Scene ─────────────────────────────────────────────

class BattleDeploymentScene(Scene):
    """Pre-battle deployment screen showing lance lineup vs enemy force."""

    def __init__(self, game_state, contract, enemy_mechs):
        super().__init__(game_state)
        self.contract = contract
        self.enemy_mechs = enemy_mechs

    def handle_input(self, key):
        if key in (curses.KEY_ENTER, 10, 13):
            self._begin_battle()
        elif key in (ord("q"), ord("Q")):
            self.game_state.running = False

    def _begin_battle(self):
        from data.battle import simulate_battle
        result = simulate_battle(self.game_state.company, self.contract)
        self.game_state.pop_scene()
        self.game_state.push_scene(
            BattleSimulationScene(self.game_state, result, self.contract)
        )

    def draw(self, win):
        max_h, max_w = win.getmaxyx()
        company = self.game_state.company

        ui.draw_header_bar(win, "IRON CONTRACT - DEPLOYMENT")
        ui.draw_status_bar(win, "Enter: Begin Mission | Q: Quit")

        row = 2
        ui.draw_centered_text(
            win, row,
            f"═══ {self.contract.mission_type.value.upper()} ═══",
            ui.color_text(ui.COLOR_TITLE) | curses.A_BOLD,
        )
        row += 1
        ui.draw_centered_text(
            win, row,
            f"Employer: {self.contract.employer} | Difficulty: {self.contract.skulls_display()}",
            ui.color_text(ui.COLOR_MENU_INACTIVE),
        )
        row += 2

        ui.draw_centered_text(
            win, row, "YOUR LANCE",
            ui.color_text(ui.COLOR_SUCCESS) | curses.A_BOLD,
        )
        row += 1

        pilot_by_mech = {
            mw.assigned_mech: mw for mw in company.mechwarriors
            if mw.assigned_mech and mw.status != PilotStatus.KIA
        }

        deployed_count = 0
        for mech in company.mechs:
            if mech.status != MechStatus.DESTROYED:
                pilot = pilot_by_mech.get(mech.name)
                if pilot:
                    deployed_count += 1
                    armor_pct = int(100 * mech.armor_current / mech.armor_max) if mech.armor_max > 0 else 0
                    line = f'  [{deployed_count}] {mech.name} | Pilot: "{pilot.callsign}" | Armor: {armor_pct}%'
                    ui.draw_centered_text(win, row, line, ui.color_text(ui.COLOR_TEXT))
                    row += 1

        row += 1
        ui.draw_centered_text(
            win, row, "ENEMY FORCE (ESTIMATED)",
            ui.color_text(ui.COLOR_DANGER) | curses.A_BOLD,
        )
        row += 1

        for i, enemy in enumerate(self.enemy_mechs, 1):
            line = f"  [{i}] {enemy.name} | {enemy.weight_class.value} | Threat Level: {enemy.firepower}"
            ui.draw_centered_text(win, row, line, ui.color_text(ui.COLOR_TEXT))
            row += 1

        row += 2
        ui.draw_centered_text(
            win, row, "[ Press ENTER to engage ]",
            ui.color_text(ui.COLOR_TITLE) | curses.A_BOLD,
        )


# ── Battle Simulation Scene ──────────────────────────────────────────────

class BattleSimulationScene(Scene):
    """Auto-battle simulation with scrolling combat log."""

    def __init__(self, game_state, battle_result, contract):
        super().__init__(game_state)
        self.result = battle_result
        self.contract = contract
        self.visible_events = 1
        self.all_revealed = False
        self.scroll_offset = 0

    def handle_input(self, key):
        if key == -1:
            return

        if not self.all_revealed:
            self.visible_events += 1
            if self.visible_events >= len(self.result.combat_log):
                self.all_revealed = True
        else:
            if key in (curses.KEY_ENTER, 10, 13, 27):
                self._proceed_to_report()
            elif key == curses.KEY_UP:
                self.scroll_offset = max(0, self.scroll_offset - 1)
            elif key == curses.KEY_DOWN:
                self.scroll_offset += 1
            elif key in (ord("q"), ord("Q")):
                self.game_state.running = False

    def _proceed_to_report(self):
        from data.progression import (
            apply_morale_outcome, check_desertion, generate_desertion_message,
            recover_injuries, get_pilots_with_pending_levelups,
        )
        from data.finance import calculate_monthly_upkeep

        company = self.game_state.company
        company.active_contract = None

        apply_morale_outcome(company, self.result.outcome.value)
        deserters = check_desertion(company)
        desertion_messages = [generate_desertion_message(d) for d in deserters]
        recovery_messages = recover_injuries(company)
        report = calculate_monthly_upkeep(company, self.result.c_bills_earned)

        self.game_state.pop_scene()

        if desertion_messages:
            self.game_state.push_scene(
                DeserterScene(self.game_state, desertion_messages, recovery_messages, report)
            )
        elif get_pilots_with_pending_levelups(company):
            pilots_to_level = get_pilots_with_pending_levelups(company)
            self.game_state.push_scene(
                LevelUpScene(self.game_state, pilots_to_level, recovery_messages, report)
            )
        else:
            self.game_state.push_scene(
                UpkeepPhaseScene(self.game_state, report, recovery_messages)
            )

    def draw(self, win):
        max_h, max_w = win.getmaxyx()

        ui.draw_header_bar(win, f"IRON CONTRACT - {self.result.outcome.value.upper()}")

        if self.all_revealed:
            ui.draw_status_bar(win, "Enter: Continue | Up/Down: Scroll | Q: Quit")
        else:
            ui.draw_status_bar(win, "Press any key to continue...")

        row = 2
        log_area_height = max_h - 8
        visible_log = self.result.combat_log[:self.visible_events]
        start_idx = max(0, min(self.scroll_offset, len(visible_log) - log_area_height))
        display_log = visible_log[start_idx:start_idx + log_area_height]

        for line in display_log:
            if row >= max_h - 4:
                break

            color = ui.color_text(ui.COLOR_TEXT)
            if "DESTROYED" in line or "KIA" in line:
                color = ui.color_text(ui.COLOR_DANGER) | curses.A_BOLD
            elif "VICTORY" in line:
                color = ui.color_text(ui.COLOR_SUCCESS) | curses.A_BOLD
            elif "DEFEAT" in line:
                color = ui.color_text(ui.COLOR_DANGER) | curses.A_BOLD
            elif line.startswith("---") or line.startswith("═"):
                color = ui.color_text(ui.COLOR_MENU_INACTIVE) | curses.A_BOLD

            try:
                win.addstr(row, 2, line[:max_w - 4], color)
            except curses.error:
                pass
            row += 1

        if not self.all_revealed:
            progress = f"[{self.visible_events}/{len(self.result.combat_log)}]"
            try:
                win.addstr(max_h - 3, max_w - len(progress) - 2, progress, ui.color_text(ui.COLOR_MENU_INACTIVE))
            except curses.error:
                pass

        if self.all_revealed:
            ui.draw_centered_text(
                win, max_h - 3, "[ Press ENTER to continue ]",
                ui.color_text(ui.COLOR_TITLE) | curses.A_BOLD,
            )


# ── Victory Scene ──────────────────────────────────────────────────────────

class VictoryScene(Scene):
    """Victory screen displayed when the player wins the campaign.
    
    Victory conditions: Reputation >= 75 AND C-Bills >= 10,000,000
    
    Shows campaign statistics:
    - Weeks played
    - Contracts completed
    - Mechs lost (destroyed)
    - MechWarriors KIA
    - Peak C-Bills (current amount)
    - Final reputation
    
    Options: Continue playing or Return to main menu
    """

    MENU_OPTIONS = ["Continue Playing", "Return to Main Menu"]

    def __init__(self, game_state):
        super().__init__(game_state)
        self.selected = 0

    def handle_input(self, key):
        """Navigate menu with arrow keys, select with Enter.

        Args:
            key: The curses key code.
        """
        if key == curses.KEY_UP:
            self.selected = (self.selected - 1) % len(self.MENU_OPTIONS)
        elif key == curses.KEY_DOWN:
            self.selected = (self.selected + 1) % len(self.MENU_OPTIONS)
        elif key in (curses.KEY_ENTER, 10, 13):
            self._select_option()

    def _select_option(self):
        """Execute the currently highlighted menu option."""
        choice = self.MENU_OPTIONS[self.selected]
        if choice == "Continue Playing":
            # Just pop this scene to return to HQ
            self.game_state.pop_scene()
        elif choice == "Return to Main Menu":
            # Pop all scenes to return to main menu
            while self.game_state.current_scene:
                self.game_state.pop_scene()

    def draw(self, win):
        """Render the victory screen with campaign statistics.

        Args:
            win: The curses standard screen window.
        """
        max_h, max_w = win.getmaxyx()
        company = self.game_state.company

        # Draw layout
        ui.draw_header_bar(win, "IRON CONTRACT - VICTORY!")
        ui.draw_status_bar(win, "Congratulations, Commander!")

        if not company:
            return

        # Calculate statistics
        mechs_lost = sum(1 for m in company.mechs if m.status == MechStatus.DESTROYED)
        pilots_kia = sum(1 for mw in company.mechwarriors if mw.status == PilotStatus.KIA)

        # Victory box
        box_w = min(70, max_w - 4)
        box_h = 22
        box_x = (max_w - box_w) // 2
        box_y = max(2, (max_h - box_h) // 2 - 2)

        ui.draw_box(win, box_y, box_x, box_h, box_w, title="Campaign Victory")

        inner_x = box_x + 2
        inner_w = box_w - 4
        row = box_y + 2

        # Victory message
        title_attr = ui.color_text(ui.COLOR_TITLE) | curses.A_BOLD
        success_attr = ui.color_text(ui.COLOR_SUCCESS) | curses.A_BOLD
        
        victory_msg = "MISSION ACCOMPLISHED!"
        try:
            msg_x = inner_x + (inner_w - len(victory_msg)) // 2
            win.addstr(row, msg_x, victory_msg, success_attr)
        except curses.error:
            pass
        row += 2

        # Congratulatory text
        congrats_lines = [
            f"Commander, {company.name} has achieved legendary status!",
            "",
            "With a reputation of 75+ and over 10 million C-Bills in the bank,",
            "you have established yourself as one of the most successful",
            "mercenary units in the Inner Sphere. Your company is now wealthy",
            "enough to establish a permanent base of operations.",
        ]

        for line in congrats_lines:
            try:
                if line:
                    win.addstr(row, inner_x, line[:inner_w], ui.color_text(ui.COLOR_TEXT))
                row += 1
            except curses.error:
                pass

        row += 1

        # Campaign Statistics
        try:
            stats_title = "CAMPAIGN STATISTICS"
            title_x = inner_x + (inner_w - len(stats_title)) // 2
            win.addstr(row, title_x, stats_title, title_attr)
        except curses.error:
            pass
        row += 2

        stats = [
            f"Weeks Played:        {company.week}",
            f"Contracts Completed: {company.contracts_completed}",
            f"Mechs Lost:          {mechs_lost}",
            f"MechWarriors KIA:    {pilots_kia}",
            f"Peak C-Bills:        {company.c_bills:,}",
            f"Final Reputation:    {company.reputation}",
        ]

        for stat in stats:
            try:
                win.addstr(row, inner_x + 4, stat, ui.color_text(ui.COLOR_ACCENT))
                row += 1
            except curses.error:
                pass

        row += 2

        # Menu options
        try:
            menu_y = row
            ui.draw_menu(win, menu_y, self.MENU_OPTIONS, self.selected, center_x=inner_x + inner_w // 2)
        except curses.error:
            pass
