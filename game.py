"""
game.py - Game state and scene management for Iron Contract.

Provides:
- Scene: Base class for all game scenes (menus, gameplay screens, etc.)
- GameState: Manages a stack of scenes and drives the main game loop.
- MainMenuScene: The main menu with New Game / Quit options.
- PlaceholderScene: A temporary "Game starting..." screen.
"""

import curses

import ui


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
            self.game_state.push_scene(PlaceholderScene(self.game_state))
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


# ── Placeholder Scene ───────────────────────────────────────────────────────

class PlaceholderScene(Scene):
    """Temporary placeholder scene shown when starting a new game."""

    def handle_input(self, key):
        """Press any key to return to the main menu.

        Args:
            key: The curses key code.
        """
        if key in (ord("q"), ord("Q")):
            self.game_state.running = False
        elif key in (curses.KEY_ENTER, 10, 13, 27):  # Enter or Escape
            self.game_state.pop_scene()

    def draw(self, win):
        """Render the placeholder new-game screen.

        Args:
            win: The curses standard screen window.
        """
        max_h, max_w = win.getmaxyx()

        ui.draw_header_bar(win, "IRON CONTRACT - NEW GAME")
        ui.draw_status_bar(win, "Press Enter or Esc to return to menu | Q: Quit")

        # Centered content
        center_y = max_h // 2
        ui.draw_centered_text(
            win,
            center_y - 2,
            "Game starting...",
            ui.color_text(ui.COLOR_TITLE) | curses.A_BOLD,
        )

        # Decorative box around the message
        box_w = 40
        box_h = 7
        box_x = (max_w - box_w) // 2
        box_y = center_y - 4
        ui.draw_box(win, box_y, box_x, box_h, box_w, title="New Campaign")

        ui.draw_centered_text(
            win,
            center_y + 1,
            "Your mercenary company awaits.",
            ui.color_text(ui.COLOR_ACCENT),
        )

        ui.draw_centered_text(
            win,
            center_y + 4,
            "(This screen will be replaced in a future update.)",
            ui.color_text(ui.COLOR_MENU_INACTIVE),
        )


# ── Game State Manager ──────────────────────────────────────────────────────

class GameState:
    """Manages the game loop and a stack of scenes.

    The scene stack allows pushing new scenes on top (e.g., submenus,
    gameplay screens) and popping back to previous ones.
    """

    def __init__(self):
        self.running = True
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
