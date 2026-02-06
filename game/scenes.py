"""
game.scenes - Concrete scene implementations for Iron Contract.

Provides:
- MainMenuScene: The main menu with New Game / Quit options.
- CompanyNameScene: Text input screen for naming the mercenary company.
- RosterSummaryScene: Displays the newly created company roster.
- HQScene: Headquarters hub with contract market and roster access.
- RosterScene: Full company roster view.
- ContractMarketScene: Contract market with selectable contracts.
- ContractBriefingScene: Detailed briefing for a selected contract.
- MissionReportScene: Post-mission combat log and results summary.
"""

import curses

import ui
from data import Company, create_starting_lance, create_starting_pilots
from data.contracts import generate_contracts
from data.combat import resolve_combat
from game.scene import Scene


# ── Main Menu Scene ─────────────────────────────────────────────────────────

class MainMenuScene(Scene):
    """The main menu screen with New Game and Quit options."""

    MENU_OPTIONS = ["New Game", "Quit"]

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
        elif key in (ord("q"), ord("Q")):
            self.game_state.running = False

    def _select_option(self):
        """Execute the currently highlighted menu option."""
        choice = self.MENU_OPTIONS[self.selected]
        if choice == "New Game":
            self.game_state.push_scene(CompanyNameScene(self.game_state))
        elif choice == "Quit":
            self.game_state.running = False

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
        ui.draw_menu(win, menu_y, self.MENU_OPTIONS, self.selected)


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

class HQScene(Scene):
    """Headquarters hub screen shown after company creation.

    Serves as the main gameplay dashboard with menu options including
    viewing the company roster and accessing the contract market.
    """

    MENU_OPTIONS = ["Contract Market", "View Roster", "Quit"]

    def __init__(self, game_state):
        super().__init__(game_state)
        self.selected = 0

    def handle_input(self, key):
        """Handle input at HQ with selectable menu.

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
        if choice == "Contract Market":
            self.game_state.push_scene(ContractMarketScene(self.game_state))
        elif choice == "View Roster":
            self.game_state.push_scene(RosterScene(self.game_state))
        elif choice == "Quit":
            self.game_state.running = False

    def draw(self, win):
        """Render the HQ dashboard screen with menu.

        Args:
            win: The curses standard screen window.
        """
        max_h, max_w = win.getmaxyx()
        company = self.game_state.company

        company_title = f"IRON CONTRACT - {company.name.upper()}" if company else "IRON CONTRACT - HQ"
        ui.draw_header_bar(win, company_title)
        ui.draw_status_bar(win, "Arrow Keys: Navigate | Enter: Select | Q: Quit")

        center_y = max_h // 2 - 2

        # Box
        box_w = 50
        box_h = 15
        box_x = (max_w - box_w) // 2
        box_y = center_y - 4
        ui.draw_box(win, box_y, box_x, box_h, box_w, title="Headquarters")

        ui.draw_centered_text(
            win,
            center_y - 2,
            "Welcome, Commander.",
            ui.color_text(ui.COLOR_TITLE) | curses.A_BOLD,
        )

        if company:
            ui.draw_centered_text(
                win,
                center_y,
                f"{company.name} is ready for action.",
                ui.color_text(ui.COLOR_ACCENT),
            )
            stats = (
                f"Mechs: {len(company.mechs)} | "
                f"Pilots: {len(company.mechwarriors)} | "
                f"C-Bills: {company.c_bills:,}"
            )
            ui.draw_centered_text(
                win,
                center_y + 1,
                stats,
                ui.color_text(ui.COLOR_MENU_INACTIVE),
            )
            month_str = f"Month: {company.week}"
            ui.draw_centered_text(
                win,
                center_y + 2,
                month_str,
                ui.color_text(ui.COLOR_MENU_INACTIVE),
            )

        # Menu options
        menu_y = center_y + 5
        ui.draw_menu(win, menu_y, self.MENU_OPTIONS, self.selected)


# ── Roster Scene (Accessible from HQ) ───────────────────────────────────

class RosterScene(Scene):
    """Full roster screen accessible from HQ.

    Displays the company's mech bay and pilot roster in a combined
    table view. Shows armor percentage, pilot assignments, and
    damage indicators for non-Ready mechs and non-Active pilots.
    """

    def __init__(self, game_state):
        super().__init__(game_state)
        self.scroll_offset = 0

    def handle_input(self, key):
        """Press Escape to return to HQ.

        Args:
            key: The curses key code.
        """
        if key == 27:  # Escape - return to HQ
            self.game_state.pop_scene()
        elif key == curses.KEY_UP:
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
        ui.draw_status_bar(win, "Esc: Back to HQ | Q: Quit | Up/Down: Scroll")

        start_y = 2 - self.scroll_offset

        # Draw the roster tables
        ui.draw_roster_table(win, start_y + 1, company)


# ── Contract Market Scene ─────────────────────────────────────────────────

class ContractMarketScene(Scene):
    """Contract market screen showing available contracts.

    Generates 3 random contracts scaled to the current month and displays
    them in a navigable list. The player can select a contract to view
    its detailed briefing.
    """

    def __init__(self, game_state):
        super().__init__(game_state)
        self.selected = 0
        month = game_state.company.week if game_state.company else 1
        self.contracts = generate_contracts(month)

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
    """

    MENU_OPTIONS = ["Accept Contract", "Go Back"]

    def __init__(self, game_state, contract):
        super().__init__(game_state)
        self.contract = contract
        self.selected = 0

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
        if choice == "Accept Contract":
            self._accept_contract()
        elif choice == "Go Back":
            self.game_state.pop_scene()

    def _accept_contract(self):
        """Accept the contract and launch the mission.

        Resolves combat using the auto-resolved combat system, then
        pushes the MissionReportScene to display the results.
        The briefing and market scenes are popped so that when the
        report is dismissed, the player returns to HQ.
        """
        company = self.game_state.company
        if company:
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
        """Advance combat log or return to HQ.

        Any key press reveals the next combat log entry. Once all
        entries are visible, the summary is shown. Press Enter or
        Escape to return to HQ.

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
                self.game_state.pop_scene()  # Return to HQ
            elif key == curses.KEY_UP:
                self.scroll_offset = max(0, self.scroll_offset - 1)
            elif key == curses.KEY_DOWN:
                self.scroll_offset += 1
            elif key in (ord("q"), ord("Q")):
                self.game_state.running = False

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
                "Enter: Return to HQ | Up/Down: Scroll | Q: Quit"
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

        # Show "Return to HQ" prompt when summary is visible
        if self.all_revealed:
            ui.draw_centered_text(
                win,
                max_h - 3,
                "[ Press ENTER to return to Headquarters ]",
                ui.color_text(ui.COLOR_TITLE) | curses.A_BOLD,
            )


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
