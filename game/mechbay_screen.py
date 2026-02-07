"""
game.mechbay_screen - Mech bay management for Iron Contract.

Provides the MechBayManagementScene that displays all mechs with their stats,
allows viewing details, and initiating repairs for damaged mechs.
"""

import curses
import math

import ui
from data.models import MechStatus, PilotStatus
from game.scene import Scene


# ── Constants ────────────────────────────────────────────────────────────

REPAIR_COST_PER_ARMOR = 2_000  # C-Bills per armor point


# ── Helper Functions ──────────────────────────────────────────────────────

def calculate_repair_cost(mech):
    """Calculate the repair cost for a damaged mech.

    Args:
        mech: BattleMech instance.

    Returns:
        Repair cost in C-Bills.
    """
    if mech.status != MechStatus.DAMAGED:
        return 0
    damage = mech.armor_max - mech.armor_current
    return damage * REPAIR_COST_PER_ARMOR


def calculate_repair_weeks(mech):
    """Calculate the repair time for a damaged mech.

    Args:
        mech: BattleMech instance.

    Returns:
        Repair time in weeks.
    """
    if mech.status != MechStatus.DAMAGED:
        return 0
    damage = mech.armor_max - mech.armor_current
    return max(1, math.ceil(damage / 30))


# ── Mech Bay Management Scene ────────────────────────────────────────────

class MechBayManagementScene(Scene):
    """Mech bay management screen.

    Displays all mechs in a table with their stats and allows:
    - Viewing mech details
    - Initiating repairs on damaged mechs
    """

    def __init__(self, game_state):
        super().__init__(game_state)
        self.scroll_offset = 0
        self.selected_mech = 0
        self.mode = "browse"  # "browse", "confirm_repair", "view_details"

    def handle_input(self, key):
        """Handle mech bay management input.

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
        elif self.mode == "confirm_repair":
            self._handle_repair_confirm_input(key, company)
        elif self.mode == "view_details":
            self._handle_details_input(key)

    def _handle_browse_input(self, key, company):
        """Handle input in browse mode."""
        mechs = company.mechs

        if key == curses.KEY_UP:
            self.selected_mech = max(0, self.selected_mech - 1)
        elif key == curses.KEY_DOWN:
            self.selected_mech = min(len(mechs) - 1, self.selected_mech + 1)
        elif key in (curses.KEY_ENTER, 10, 13):
            # View details
            self.mode = "view_details"
        elif key in (ord("r"), ord("R")):
            # Initiate repair
            if self.selected_mech < len(mechs):
                mech = mechs[self.selected_mech]
                if mech.status == MechStatus.DAMAGED:
                    self.mode = "confirm_repair"

    def _handle_repair_confirm_input(self, key, company):
        """Handle input in repair confirmation mode."""
        mechs = company.mechs
        if self.selected_mech >= len(mechs):
            self.mode = "browse"
            return

        mech = mechs[self.selected_mech]
        repair_cost = calculate_repair_cost(mech)

        if key in (ord("y"), ord("Y")):
            # Confirm repair
            if company.c_bills >= repair_cost:
                # Deduct cost and set repair timer
                company.c_bills -= repair_cost
                repair_weeks = calculate_repair_weeks(mech)
                if not hasattr(mech, 'repair_weeks_remaining'):
                    # Add the attribute dynamically if not present
                    mech.repair_weeks_remaining = repair_weeks
                else:
                    mech.repair_weeks_remaining = repair_weeks
            self.mode = "browse"
        elif key in (ord("n"), ord("N"), 27):
            # Cancel
            self.mode = "browse"

    def _handle_details_input(self, key):
        """Handle input in details view mode."""
        if key in (27, curses.KEY_ENTER, 10, 13):  # Escape or Enter
            self.mode = "browse"

    def draw(self, win):
        """Render the mech bay management screen.

        Args:
            win: The curses standard screen window.
        """
        max_h, max_w = win.getmaxyx()
        company = self.game_state.company

        ui.draw_header_bar(win, "IRON CONTRACT - MECH BAY")

        if self.mode == "confirm_repair":
            ui.draw_status_bar(win, "Y: Confirm Repair | N: Cancel")
        elif self.mode == "view_details":
            ui.draw_status_bar(win, "Enter/Esc: Back")
        else:
            ui.draw_status_bar(
                win,
                "Up/Down: Select | Enter: Details | R: Repair | Esc/B: Back to HQ"
            )

        row = 2

        # Title
        ui.draw_centered_text(
            win, row,
            "=== MECH BAY ===",
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

        if not company.mechs:
            ui.draw_centered_text(
                win, row,
                "No mechs in the bay.",
                ui.color_text(ui.COLOR_MENU_INACTIVE),
            )
            return

        # Draw mech table
        if self.mode == "view_details":
            self._draw_mech_details(win, row, company)
        else:
            self._draw_mech_table(win, row, company)

            # Show repair confirmation overlay
            if self.mode == "confirm_repair":
                self._draw_repair_confirm_overlay(win, company)

    def _draw_mech_table(self, win, start_row, company):
        """Draw the mech table."""
        max_h, max_w = win.getmaxyx()
        mechs = company.mechs
        row = start_row

        # Table header
        col_widths = [4, 22, 8, 6, 4, 12, 10]
        headers = ["#", "MECH", "CLASS", "TONS", "FP", "ARMOR", "STATUS"]
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

        # Draw mechs
        for i, mech in enumerate(mechs):
            armor_str = f"{mech.armor_current}/{mech.armor_max}"

            if mech.status == MechStatus.DESTROYED:
                status_str = "Destroyed"
            elif mech.status == MechStatus.DAMAGED:
                # Check if repair is in progress
                if hasattr(mech, 'repair_weeks_remaining') and mech.repair_weeks_remaining > 0:
                    status_str = f"Repairing ({mech.repair_weeks_remaining}w)"
                else:
                    status_str = "Damaged"
            else:
                status_str = "Ready"

            cols = [
                str(i + 1),
                mech.name[:21],
                mech.weight_class.value[:7],
                str(mech.tonnage),
                str(mech.firepower),
                armor_str[:11],
                status_str[:9],
            ]

            # Highlighting
            if self.mode == "browse" and i == self.selected_mech:
                row_attr = ui.color_text(ui.COLOR_MENU_ACTIVE) | curses.A_BOLD
            elif mech.status == MechStatus.DESTROYED:
                row_attr = ui.color_text(ui.COLOR_WARNING) | curses.A_BOLD
            elif mech.status == MechStatus.DAMAGED:
                row_attr = ui.color_text(ui.COLOR_WARNING)
            else:
                row_attr = ui.color_text(ui.COLOR_ACCENT)

            ui.draw_table_row(win, row, table_x, cols, col_widths, row_attr)
            row += 1

            # Show repair info for damaged mechs
            if mech.status == MechStatus.DAMAGED and i == self.selected_mech:
                repair_cost = calculate_repair_cost(mech)
                repair_weeks = calculate_repair_weeks(mech)

                # Only show if not already repairing
                if not (hasattr(mech, 'repair_weeks_remaining') and mech.repair_weeks_remaining > 0):
                    repair_info = f"   [REPAIR: {repair_weeks} week{'s' if repair_weeks > 1 else ''}, {repair_cost:,} C-Bills]"
                    try:
                        repair_x = table_x
                        win.addstr(row, repair_x, repair_info, ui.color_text(ui.COLOR_ACCENT))
                    except curses.error:
                        pass
                    row += 1

    def _draw_mech_details(self, win, start_row, company):
        """Draw detailed mech information."""
        max_h, max_w = win.getmaxyx()
        mechs = company.mechs
        if self.selected_mech >= len(mechs):
            return

        mech = mechs[self.selected_mech]
        row = start_row

        # Mech name
        ui.draw_centered_text(
            win, row,
            mech.name,
            ui.color_text(ui.COLOR_TITLE) | curses.A_BOLD,
        )
        row += 2

        # Find assigned pilot
        assigned_pilot = None
        for mw in company.mechwarriors:
            if mw.assigned_mech == mech.name and mw.status != PilotStatus.KIA:
                assigned_pilot = mw
                break

        # Details
        details = [
            f"Class: {mech.weight_class.value}",
            f"Tonnage: {mech.tonnage} tons",
            f"Firepower: {mech.firepower}",
            f"Speed: {mech.speed}",
            f"Armor: {mech.armor_current}/{mech.armor_max}",
            f"Structure: {mech.structure_current}/{mech.structure_max}",
            f"Status: {mech.status.value}",
            f"Assigned Pilot: {assigned_pilot.callsign if assigned_pilot else 'None'}",
        ]

        content_x = max(2, (max_w - 40) // 2)
        for detail in details:
            try:
                win.addstr(row, content_x, detail, ui.color_text(ui.COLOR_MENU_INACTIVE))
            except curses.error:
                pass
            row += 1

        row += 1

        # Repair info if damaged
        if mech.status == MechStatus.DAMAGED:
            repair_cost = calculate_repair_cost(mech)
            repair_weeks = calculate_repair_weeks(mech)

            if hasattr(mech, 'repair_weeks_remaining') and mech.repair_weeks_remaining > 0:
                repair_info = f"Repair in progress: {mech.repair_weeks_remaining} week(s) remaining"
                ui.draw_centered_text(
                    win, row,
                    repair_info,
                    ui.color_text(ui.COLOR_WARNING),
                )
            else:
                repair_info = f"Repair Cost: {repair_cost:,} C-Bills ({repair_weeks} week{'s' if repair_weeks > 1 else ''})"
                ui.draw_centered_text(
                    win, row,
                    repair_info,
                    ui.color_text(ui.COLOR_ACCENT),
                )

    def _draw_repair_confirm_overlay(self, win, company):
        """Draw the repair confirmation overlay."""
        max_h, max_w = win.getmaxyx()
        mechs = company.mechs

        if self.selected_mech >= len(mechs):
            return

        mech = mechs[self.selected_mech]
        repair_cost = calculate_repair_cost(mech)
        repair_weeks = calculate_repair_weeks(mech)

        # Draw confirmation box
        box_w = 55
        box_h = 7
        box_x = (max_w - box_w) // 2
        box_y = (max_h - box_h) // 2

        ui.draw_box(win, box_y, box_x, box_h, box_w, title="Confirm Repair")

        mech_text = f"Repair {mech.name}?"
        ui.draw_centered_text(
            win, box_y + 2,
            mech_text,
            ui.color_text(ui.COLOR_TITLE) | curses.A_BOLD,
        )

        cost_text = f"Cost: {repair_cost:,} C-Bills | Time: {repair_weeks} week{'s' if repair_weeks > 1 else ''}"
        ui.draw_centered_text(
            win, box_y + 3,
            cost_text,
            ui.color_text(ui.COLOR_MENU_INACTIVE),
        )

        # Check if can afford
        can_afford = company.c_bills >= repair_cost
        if can_afford:
            ui.draw_centered_text(
                win, box_y + 5,
                "[Y] Yes  [N] No",
                ui.color_text(ui.COLOR_MENU_INACTIVE),
            )
        else:
            ui.draw_centered_text(
                win, box_y + 5,
                "INSUFFICIENT FUNDS",
                ui.color_text(ui.COLOR_WARNING) | curses.A_BOLD,
            )
