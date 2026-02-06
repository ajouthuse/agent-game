"""
game.py - Game state and scene management for Iron Contract.

Provides:
- Scene: Base class for all game scenes (menus, gameplay screens, etc.)
- GameState: Manages a stack of scenes and drives the main game loop.
- MainMenuScene: The main menu with New Game / Quit options.
- CompanyNameScene: Text input screen for naming the mercenary company.
- RosterSummaryScene: Displays the newly created company roster.
- HQScene: Placeholder headquarters screen (post-company-creation).
"""

import curses

import ui
from data import create_starting_lance
from models import Company
from names import generate_mechwarrior_roster


# ── Scene Base Class ────────────────────────────────────────────────────────

class Scene:
    """Base class for a game scene.

    Subclasses must override handle_input() and draw() at minimum.
    """

    def __init__(self, game_state):
        """Initialize the scene with a reference to the parent GameState.

        Args:
            game_state: The GameState instance managing this scene.
        """
        self.game_state = game_state

    def on_enter(self):
        """Called when this scene becomes the active scene."""
        pass

    def on_exit(self):
        """Called when this scene is removed from the stack."""
        pass

    def handle_input(self, key):
        """Process a single key press.

        Args:
            key: The curses key code or character ordinal.
        """
        pass

    def draw(self, win):
        """Render the scene to the given curses window.

        Args:
            win: The curses standard screen window.
        """
        pass


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


# ── HQ Scene (Placeholder) ───────────────────────────────────────────────

class HQScene(Scene):
    """Placeholder headquarters screen shown after company creation.

    This will be expanded in future issues to become the main gameplay hub.
    """

    def handle_input(self, key):
        """Handle input at HQ.

        Args:
            key: The curses key code.
        """
        if key in (ord("q"), ord("Q")):
            self.game_state.running = False

    def draw(self, win):
        """Render the HQ placeholder screen.

        Args:
            win: The curses standard screen window.
        """
        max_h, max_w = win.getmaxyx()
        company = self.game_state.company

        company_title = f"IRON CONTRACT - {company.name.upper()}" if company else "IRON CONTRACT - HQ"
        ui.draw_header_bar(win, company_title)
        ui.draw_status_bar(win, "Q: Quit")

        center_y = max_h // 2

        # Box
        box_w = 50
        box_h = 9
        box_x = (max_w - box_w) // 2
        box_y = center_y - 5
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

        ui.draw_centered_text(
            win,
            center_y + 5,
            "(More features coming soon.)",
            ui.color_text(ui.COLOR_MENU_INACTIVE),
        )


# ── Company Creation Helper ──────────────────────────────────────────────

def _create_new_company(name):
    """Create a new mercenary company with a starting lance and pilots.

    Generates 4 mechs (2 medium, 2 light) and 4 randomized MechWarriors,
    then auto-assigns each pilot to a mech.

    Args:
        name: The player-chosen company name.

    Returns:
        A fully initialized Company instance.
    """
    mechs = create_starting_lance()
    pilots = generate_mechwarrior_roster(4)

    # Auto-assign pilots to mechs
    for pilot, mech in zip(pilots, mechs):
        pilot.assigned_mech = mech.name

    return Company(
        name=name,
        mechwarriors=pilots,
        mechs=mechs,
    )


# ── Game State Manager ──────────────────────────────────────────────────────

class GameState:
    """Manages the game loop and a stack of scenes.

    The scene stack allows pushing new scenes on top (e.g., submenus,
    gameplay screens) and popping back to previous ones.

    Attributes:
        running: Whether the game loop should continue.
        company: The player's Company instance (None until created).
    """

    def __init__(self):
        self.running = True
        self.company = None
        self._scene_stack = []

    @property
    def current_scene(self):
        """Return the scene on top of the stack, or None if empty."""
        return self._scene_stack[-1] if self._scene_stack else None

    def push_scene(self, scene):
        """Push a new scene onto the stack and activate it.

        Args:
            scene: A Scene instance to make active.
        """
        self._scene_stack.append(scene)
        scene.on_enter()

    def pop_scene(self):
        """Remove the top scene from the stack.

        Returns:
            The removed Scene instance, or None if the stack was empty.
        """
        if self._scene_stack:
            scene = self._scene_stack.pop()
            scene.on_exit()
            if self.current_scene:
                self.current_scene.on_enter()
            return scene
        return None

    def run(self, stdscr):
        """Main game loop. Called from within curses.wrapper().

        Args:
            stdscr: The curses standard screen window.
        """
        # Terminal setup
        curses.curs_set(0)          # Hide cursor
        stdscr.nodelay(False)       # Blocking input (wait for key)
        stdscr.timeout(100)         # Refresh every 100ms for responsiveness
        ui.init_colors()

        # Start with the main menu
        self.push_scene(MainMenuScene(self))

        while self.running:
            # Draw current scene
            stdscr.erase()
            scene = self.current_scene
            if scene is None:
                break
            scene.draw(stdscr)
            stdscr.refresh()

            # Handle input
            try:
                key = stdscr.getch()
            except curses.error:
                continue

            if key == -1:
                continue  # Timeout, no key pressed

            scene.handle_input(key)

            # If all scenes popped, exit
            if not self._scene_stack:
                self.running = False
