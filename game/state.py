"""
game.state - GameState manager for Iron Contract.

Provides the GameState class that manages the scene stack and drives
the main game loop, including input handling, screen refresh, and
graceful terminal resize handling.
"""

import curses

import ui
from ui.drawing import draw_centered_text
from ui.colors import color_text, COLOR_WARNING


class GameState:
    """Manages the game loop and a stack of scenes.

    The scene stack allows pushing new scenes on top (e.g., submenus,
    gameplay screens) and popping back to previous ones.

    Attributes:
        running: Whether the game loop should continue.
        company: The player's Company instance (None until created).
    """

    MIN_WIDTH = 80
    MIN_HEIGHT = 24

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

    def _handle_resize(self, stdscr):
        """Handle terminal resize events gracefully.

        Updates curses internal state and notifies the current scene.

        Args:
            stdscr: The curses standard screen window.
        """
        curses.update_lines_cols()
        max_h, max_w = stdscr.getmaxyx()
        stdscr.clear()

        scene = self.current_scene
        if scene:
            scene.on_resize(max_h, max_w)

    def _draw_size_warning(self, stdscr):
        """Draw a warning message when the terminal is too small.

        Args:
            stdscr: The curses standard screen window.

        Returns:
            True if terminal is too small (warning was drawn), False otherwise.
        """
        max_h, max_w = stdscr.getmaxyx()
        if max_w < self.MIN_WIDTH or max_h < self.MIN_HEIGHT:
            warning_attr = color_text(COLOR_WARNING) | curses.A_BOLD
            msg = f"Terminal too small ({max_w}x{max_h})"
            hint = f"Minimum: {self.MIN_WIDTH}x{self.MIN_HEIGHT}"
            center_y = max_h // 2
            try:
                draw_centered_text(stdscr, center_y - 1, msg, warning_attr)
                draw_centered_text(stdscr, center_y + 1, hint, warning_attr)
            except curses.error:
                pass
            return True
        return False

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
        from game.scenes import MainMenuScene
        self.push_scene(MainMenuScene(self))

        while self.running:
            stdscr.erase()

            # Check minimum terminal size
            if self._draw_size_warning(stdscr):
                stdscr.refresh()
                try:
                    key = stdscr.getch()
                except curses.error:
                    continue
                if key == curses.KEY_RESIZE:
                    self._handle_resize(stdscr)
                elif key in (ord("q"), ord("Q")):
                    self.running = False
                continue

            # Draw current scene before waiting for input
            scene = self.current_scene
            if scene is None:
                break
            scene.draw(stdscr)
            stdscr.refresh()

            # Now wait for input
            try:
                key = stdscr.getch()
            except curses.error:
                continue

            if key == curses.KEY_RESIZE:
                self._handle_resize(stdscr)
                continue

            if key == -1:
                continue  # Timeout, no key pressed

            scene.handle_input(key)

            # If all scenes popped, exit
            if not self._scene_stack:
                self.running = False
