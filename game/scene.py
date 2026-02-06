"""
game.scene - Base Scene class for Iron Contract.

All game screens (menus, gameplay views, etc.) inherit from Scene and
override handle_input() and draw() to provide their behavior.
"""


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

    def on_resize(self, max_h, max_w):
        """Called when the terminal is resized.

        Subclasses can override to recalculate layout. The default
        implementation does nothing; the next draw() call will
        automatically use the new dimensions.

        Args:
            max_h: New terminal height in rows.
            max_w: New terminal width in columns.
        """
        pass
