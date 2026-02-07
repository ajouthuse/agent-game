"""
game.roster_screen - MechWarrior roster management for Iron Contract.

Provides the RosterManagementScene that displays all pilots with their stats,
allows assignment to mechs, hiring new pilots, and dismissing existing ones.
"""

import curses
import random

import ui
from data.models import MechWarrior, PilotStatus, MechStatus
from data.names import generate_mechwarrior
from game.scene import Scene


# ── Constants ────────────────────────────────────────────────────────────

HIRE_COST = 150_000


# ── Roster Management Scene ──────────────────────────────────────────────

class RosterManagementScene(Scene):
    """MechWarrior roster management screen.

    Displays all pilots in a table with their stats and allows:
    - Assigning/unassigning pilots to mechs
    - Hiring new pilots
    - Dismissing pilots
    """

    def __init__(self, game_state):
        super().__init__(game_state)
        self.scroll_offset = 0
        self.selected_row = 0  # Which row is selected (pilot or hire option)
        self.mode = "browse"  # "browse", "assign_mech", "confirm_dismiss"
        self.selected_mech = 0

    def handle_input(self, key):
        """Handle roster management input.

        Args:
            key: The curses key code.
        """
        company = self.game_state.company

        if key == 27 or key in (ord("b"), ord("B")):  # Escape or B
            if self.mode == "browse":
                self.game_state.pop_scene()
            else:
                self.mode = "browse"
        elif self.mode == "browse":
            self._handle_browse_input(key, company)
        elif self.mode == "assign_mech":
            self._handle_assign_mech_input(key, company)
        elif self.mode == "confirm_dismiss":
            self._handle_dismiss_confirm_input(key, company)

    def _handle_browse_input(self, key, company):
        """Handle input in browse mode."""
        pilots = [mw for mw in company.mechwarriors if mw.status != PilotStatus.KIA]
        max_rows = len(pilots) + 1  # +1 for hire option

        if key == curses.KEY_UP:
            self.selected_row = max(0, self.selected_row - 1)
        elif key == curses.KEY_DOWN:
            self.selected_row = min(max_rows - 1, self.selected_row + 1)
        elif key in (curses.KEY_ENTER, 10, 13):
            if self.selected_row < len(pilots):
                # Selected a pilot - show assign menu
                self.mode = "assign_mech"
                self.selected_mech = 0
            else:
                # Selected hire option
                self._hire_pilot(company)
        elif key in (ord("d"), ord("D")):
            # Dismiss pilot
            if self.selected_row < len(pilots):
                self.mode = "confirm_dismiss"

    def _handle_assign_mech_input(self, key, company):
        """Handle input in assign mech mode."""
        pilots = [mw for mw in company.mechwarriors if mw.status != PilotStatus.KIA]
        if self.selected_row >= len(pilots):
            self.mode = "browse"
            return

        pilot = pilots[self.selected_row]

        # Get available mechs (unassigned + current pilot's mech if any)
        assigned_mechs = {
            mw.assigned_mech for mw in company.mechwarriors
            if mw.assigned_mech and mw != pilot
        }
        available_mechs = [
            m for m in company.mechs
            if m.name not in assigned_mechs and m.status != MechStatus.DESTROYED
        ]

        # Add "Unassign" option if pilot has a mech
        options_count = len(available_mechs) + (1 if pilot.assigned_mech else 0) + 1  # +1 for cancel

        if key == curses.KEY_UP:
            self.selected_mech = max(0, self.selected_mech - 1)
        elif key == curses.KEY_DOWN:
            self.selected_mech = min(options_count - 1, self.selected_mech + 1)
        elif key in (curses.KEY_ENTER, 10, 13):
            # Determine what was selected
            option_idx = self.selected_mech

            if pilot.assigned_mech and option_idx == 0:
                # Unassign option
                pilot.assigned_mech = None
                self.mode = "browse"
            elif option_idx < len(available_mechs) + (1 if pilot.assigned_mech else 0):
                # Assign to a mech
                mech_idx = option_idx - (1 if pilot.assigned_mech else 0)
                if 0 <= mech_idx < len(available_mechs):
                    pilot.assigned_mech = available_mechs[mech_idx].name
                self.mode = "browse"
            else:
                # Cancel
                self.mode = "browse"

    def _handle_dismiss_confirm_input(self, key, company):
        """Handle input in dismiss confirmation mode."""
        pilots = [mw for mw in company.mechwarriors if mw.status != PilotStatus.KIA]
        if self.selected_row >= len(pilots):
            self.mode = "browse"
            return

        if key in (ord("y"), ord("Y")):
            # Confirm dismiss
            pilot = pilots[self.selected_row]
            company.mechwarriors.remove(pilot)
            self.selected_row = min(self.selected_row, len(pilots) - 2)
            self.selected_row = max(0, self.selected_row)
            self.mode = "browse"
        elif key in (ord("n"), ord("N"), 27):
            # Cancel
            self.mode = "browse"

    def _hire_pilot(self, company):
        """Hire a new pilot if the company can afford it."""
        if company.c_bills >= HIRE_COST:
            # Generate new pilot with randomized skills (2-5 range as per spec)
            used_callsigns = {mw.callsign for mw in company.mechwarriors}
            new_pilot = generate_mechwarrior(used_callsigns)
            # Adjust skill range to 2-5 as per spec
            new_pilot.gunnery = random.randint(2, 5)
            new_pilot.piloting = random.randint(2, 5)

            company.mechwarriors.append(new_pilot)
            company.c_bills -= HIRE_COST

    def draw(self, win):
        """Render the roster management screen.

        Args:
            win: The curses standard screen window.
        """
        max_h, max_w = win.getmaxyx()
        company = self.game_state.company

        ui.draw_header_bar(win, "IRON CONTRACT - ROSTER MANAGEMENT")

        if self.mode == "assign_mech":
            ui.draw_status_bar(win, "Up/Down: Select | Enter: Assign | Esc: Cancel")
        elif self.mode == "confirm_dismiss":
            ui.draw_status_bar(win, "Y: Confirm Dismiss | N: Cancel")
        else:
            ui.draw_status_bar(
                win,
                "Up/Down: Select | Enter: Assign/Hire | D: Dismiss | Esc/B: Back to HQ"
            )

        row = 2

        # Title
        ui.draw_centered_text(
            win, row,
            "=== MECHWARRIOR ROSTER ===",
            ui.color_text(ui.COLOR_TITLE) | curses.A_BOLD,
        )
        row += 2

        # Company info
        info_text = f"Week {company.week} | C-Bills: {company.c_bills:,}"
        ui.draw_centered_text(
            win, row, info_text,
            ui.color_text(ui.COLOR_MENU_INACTIVE),
        )
        row += 2

        # Draw pilot table
        pilots = [mw for mw in company.mechwarriors if mw.status != PilotStatus.KIA]

        # Table header
        col_widths = [4, 20, 15, 5, 5, 10, 22]
        headers = ["#", "NAME", "CALLSIGN", "GUN", "PLT", "STATUS", "ASSIGNED MECH"]
        table_width = sum(col_widths) + len(col_widths) - 1
        table_x = max(1, (max_w - table_width) // 2)

        ui.draw_table_row(
            win, row, table_x, headers, col_widths,
            ui.color_text(ui.COLOR_STATUS) | curses.A_BOLD,
        )
        row += 1

        # Separator
        try:
            sep = "-" * table_width
            sep_x = max(1, (max_w - len(sep)) // 2)
            win.addstr(row, sep_x, sep, ui.color_text(ui.COLOR_BORDER))
        except curses.error:
            pass
        row += 1

        # Draw pilots
        for i, pilot in enumerate(pilots):
            status_str = pilot.status.value
            mech_name = pilot.assigned_mech if pilot.assigned_mech else "—"

            cols = [
                str(i + 1),
                pilot.name[:19],
                pilot.callsign[:14],
                str(pilot.gunnery),
                str(pilot.piloting),
                status_str[:9],
                mech_name[:21],
            ]

            # Highlighting
            if self.mode == "browse" and i == self.selected_row:
                row_attr = ui.color_text(ui.COLOR_MENU_ACTIVE) | curses.A_BOLD
            elif pilot.status == PilotStatus.INJURED:
                row_attr = ui.color_text(ui.COLOR_WARNING)
            else:
                row_attr = ui.color_text(ui.COLOR_ACCENT)

            ui.draw_table_row(win, row, table_x, cols, col_widths, row_attr)
            row += 1

        # Hire option
        hire_text = f"[HIRE NEW PILOT - {HIRE_COST:,} C-Bills]"
        can_afford = company.c_bills >= HIRE_COST

        if self.mode == "browse" and self.selected_row == len(pilots):
            hire_attr = ui.color_text(ui.COLOR_MENU_ACTIVE) | curses.A_BOLD
        elif can_afford:
            hire_attr = ui.color_text(ui.COLOR_ACCENT)
        else:
            hire_attr = ui.color_text(ui.COLOR_MENU_INACTIVE)

        try:
            hire_x = max(1, (max_w - len(hire_text)) // 2)
            win.addstr(row, hire_x, hire_text, hire_attr)
        except curses.error:
            pass
        row += 2

        # Show assign mech overlay
        if self.mode == "assign_mech":
            self._draw_assign_mech_overlay(win, row, pilots)
        elif self.mode == "confirm_dismiss":
            self._draw_dismiss_confirm_overlay(win, pilots)

    def _draw_assign_mech_overlay(self, win, start_row, pilots):
        """Draw the mech assignment overlay."""
        max_h, max_w = win.getmaxyx()
        company = self.game_state.company

        if self.selected_row >= len(pilots):
            return

        pilot = pilots[self.selected_row]

        # Get available mechs
        assigned_mechs = {
            mw.assigned_mech for mw in company.mechwarriors
            if mw.assigned_mech and mw != pilot
        }
        available_mechs = [
            m for m in company.mechs
            if m.name not in assigned_mechs and m.status != MechStatus.DESTROYED
        ]

        row = start_row
        ui.draw_centered_text(
            win, row,
            f"--- ASSIGN MECH TO {pilot.callsign} ---",
            ui.color_text(ui.COLOR_BORDER) | curses.A_BOLD,
        )
        row += 1

        option_idx = 0

        # Unassign option
        if pilot.assigned_mech:
            if option_idx == self.selected_mech:
                attr = ui.color_text(ui.COLOR_MENU_ACTIVE) | curses.A_BOLD
                label = "  > [Unassign from current mech]"
            else:
                attr = ui.color_text(ui.COLOR_MENU_INACTIVE)
                label = "    [Unassign from current mech]"
            ui.draw_centered_text(win, row, label, attr)
            row += 1
            option_idx += 1

        # Available mechs
        for mech in available_mechs:
            status_note = ""
            if mech.status == MechStatus.DAMAGED:
                status_note = " [DAMAGED]"
            elif pilot.status == PilotStatus.INJURED:
                status_note = " (pilot injured)"

            mech_label = f"{mech.name} ({mech.weight_class.value}, {mech.tonnage}t){status_note}"

            if option_idx == self.selected_mech:
                attr = ui.color_text(ui.COLOR_MENU_ACTIVE) | curses.A_BOLD
                label = f"  > {mech_label}"
            else:
                attr = ui.color_text(ui.COLOR_MENU_INACTIVE)
                label = f"    {mech_label}"

            ui.draw_centered_text(win, row, label, attr)
            row += 1
            option_idx += 1

        # Cancel option
        if option_idx == self.selected_mech:
            attr = ui.color_text(ui.COLOR_MENU_ACTIVE) | curses.A_BOLD
            label = "  > [Cancel]"
        else:
            attr = ui.color_text(ui.COLOR_MENU_INACTIVE)
            label = "    [Cancel]"
        ui.draw_centered_text(win, row, label, attr)

    def _draw_dismiss_confirm_overlay(self, win, pilots):
        """Draw the dismiss confirmation overlay."""
        max_h, max_w = win.getmaxyx()

        if self.selected_row >= len(pilots):
            return

        pilot = pilots[self.selected_row]

        # Draw confirmation box
        box_w = 50
        box_h = 5
        box_x = (max_w - box_w) // 2
        box_y = (max_h - box_h) // 2

        ui.draw_box(win, box_y, box_x, box_h, box_w, title="Confirm Dismiss")

        text = f"Dismiss {pilot.name} ({pilot.callsign})?"
        ui.draw_centered_text(
            win, box_y + 2,
            text,
            ui.color_text(ui.COLOR_WARNING) | curses.A_BOLD,
        )

        ui.draw_centered_text(
            win, box_y + 3,
            "[Y] Yes  [N] No",
            ui.color_text(ui.COLOR_MENU_INACTIVE),
        )
