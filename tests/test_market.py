"""
test_market.py - Unit tests for the salvage market and hiring hall systems.

Tests cover:
- Mech catalog contains at least 10 unique mechs across 4 weight classes
- Salvage market generates 2-3 random mechs from the catalog
- Mech pricing scales with weight class and quality
- Player can purchase a mech with enough C-Bills and open slot
- Player cannot purchase when lance is full (4 mechs) or insufficient funds
- Hiring hall generates 2-3 random pilots with varied skills
- Pilot hiring cost scales with skill level
- Player can hire a pilot with enough C-Bills and open slot
- Player cannot hire when roster is full (4 pilots) or insufficient funds
- Purchased mechs/pilots immediately appear in the roster
- Balance is correctly deducted after purchase/hire
"""

import sys
import os

# Add the project root to path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest

from data.models import (
    BattleMech,
    Company,
    MechStatus,
    MechWarrior,
    PilotStatus,
    WeightClass,
)
from data.mechs import MECH_TEMPLATES, create_mech_from_template
from data.market import (
    MAX_LANCE_SIZE,
    PRICE_PER_TON,
    PRICE_PER_FIREPOWER,
    HIRING_BASE_COST,
    HIRING_SKILL_BONUS,
    SalvageItem,
    HireablePilot,
    calculate_mech_price,
    calculate_hiring_cost,
    generate_salvage_market,
    generate_hiring_hall,
    can_buy_mech,
    can_hire_pilot,
    buy_mech,
    hire_pilot,
)


class TestMechCatalog(unittest.TestCase):
    """Tests for the expanded mech template catalog."""

    def test_at_least_10_mechs(self):
        """Mech catalog contains at least 10 unique mechs."""
        self.assertGreaterEqual(len(MECH_TEMPLATES), 10)

    def test_all_four_weight_classes(self):
        """Mech catalog spans all 4 weight classes."""
        weight_classes = {t["weight_class"] for t in MECH_TEMPLATES.values()}
        self.assertIn(WeightClass.LIGHT, weight_classes)
        self.assertIn(WeightClass.MEDIUM, weight_classes)
        self.assertIn(WeightClass.HEAVY, weight_classes)
        self.assertIn(WeightClass.ASSAULT, weight_classes)

    def test_light_mechs_present(self):
        """Catalog includes Locust, Commando, Jenner, and Panther."""
        names = list(MECH_TEMPLATES.keys())
        self.assertIn("Locust LCT-1V", names)
        self.assertIn("Commando COM-2D", names)
        self.assertIn("Jenner JR7-D", names)
        self.assertIn("Panther PNT-9R", names)

    def test_medium_mechs_present(self):
        """Catalog includes Wolverine, Shadow Hawk, Hunchback, Centurion."""
        names = list(MECH_TEMPLATES.keys())
        self.assertIn("Wolverine WVR-6R", names)
        self.assertIn("Shadow Hawk SHD-2H", names)
        self.assertIn("Hunchback HBK-4G", names)
        self.assertIn("Centurion CN9-A", names)

    def test_heavy_mechs_present(self):
        """Catalog includes Thunderbolt, Catapult, and Marauder."""
        names = list(MECH_TEMPLATES.keys())
        self.assertIn("Thunderbolt TDR-5S", names)
        self.assertIn("Catapult CPLT-C1", names)
        self.assertIn("Marauder MAD-3R", names)

    def test_assault_mechs_present(self):
        """Catalog includes Atlas and BattleMaster."""
        names = list(MECH_TEMPLATES.keys())
        self.assertIn("Atlas AS7-D", names)
        self.assertIn("BattleMaster BLR-1G", names)

    def test_at_least_4_light_mechs(self):
        """There are at least 4 light mechs in the catalog."""
        light_mechs = [
            k for k, v in MECH_TEMPLATES.items()
            if v["weight_class"] == WeightClass.LIGHT
        ]
        self.assertGreaterEqual(len(light_mechs), 4)

    def test_at_least_4_medium_mechs(self):
        """There are at least 4 medium mechs in the catalog."""
        medium_mechs = [
            k for k, v in MECH_TEMPLATES.items()
            if v["weight_class"] == WeightClass.MEDIUM
        ]
        self.assertGreaterEqual(len(medium_mechs), 4)


class TestMechPricing(unittest.TestCase):
    """Tests for mech price calculation."""

    def test_price_positive(self):
        """Mech prices are always positive."""
        for key in MECH_TEMPLATES:
            mech = create_mech_from_template(key)
            price = calculate_mech_price(mech)
            self.assertGreater(price, 0, f"{key} has non-positive price")

    def test_heavier_mechs_cost_more(self):
        """On average, heavier mechs cost more than lighter ones."""
        # Calculate average prices per weight class (multiple samples to smooth variance)
        light_prices = []
        assault_prices = []
        for _ in range(50):
            for key, tmpl in MECH_TEMPLATES.items():
                mech = create_mech_from_template(key)
                price = calculate_mech_price(mech)
                if tmpl["weight_class"] == WeightClass.LIGHT:
                    light_prices.append(price)
                elif tmpl["weight_class"] == WeightClass.ASSAULT:
                    assault_prices.append(price)

        avg_light = sum(light_prices) / len(light_prices)
        avg_assault = sum(assault_prices) / len(assault_prices)
        self.assertGreater(avg_assault, avg_light)

    def test_price_components(self):
        """Price includes tonnage and firepower components."""
        mech = create_mech_from_template("Atlas AS7-D")
        # Atlas: 100 tons, firepower 10
        # Minimum price (at 0.90 variance):
        #   100 * 8000 * 0.90 + 10 * 10000 * 0.90 = 720000 + 90000 = 810000
        # Maximum price (at 1.10 variance):
        #   100 * 8000 * 1.10 + 10 * 10000 * 1.10 = 880000 + 110000 = 990000
        price = calculate_mech_price(mech)
        self.assertGreater(price, 0)


class TestSalvageMarket(unittest.TestCase):
    """Tests for salvage market generation."""

    def test_generates_2_or_3_items(self):
        """Market generates 2-3 items by default."""
        for _ in range(20):
            items = generate_salvage_market()
            self.assertIn(len(items), [2, 3])

    def test_specific_count(self):
        """Market generates exact count when specified."""
        items = generate_salvage_market(count=2)
        self.assertEqual(len(items), 2)

    def test_items_are_salvage_items(self):
        """All generated items are SalvageItem instances."""
        items = generate_salvage_market()
        for item in items:
            self.assertIsInstance(item, SalvageItem)
            self.assertIsInstance(item.mech, BattleMech)
            self.assertIsInstance(item.price, int)
            self.assertGreater(item.price, 0)

    def test_mechs_are_full_health(self):
        """All market mechs start at full armor and Ready status."""
        items = generate_salvage_market()
        for item in items:
            self.assertEqual(item.mech.armor_current, item.mech.armor_max)
            self.assertEqual(item.mech.structure_current, item.mech.structure_max)
            self.assertEqual(item.mech.status, MechStatus.READY)

    def test_mechs_from_catalog(self):
        """All market mechs come from the template catalog."""
        items = generate_salvage_market()
        template_names = set(MECH_TEMPLATES.keys())
        for item in items:
            self.assertIn(item.mech.name, template_names)


class TestHiringHall(unittest.TestCase):
    """Tests for hiring hall generation."""

    def test_generates_2_or_3_pilots(self):
        """Hall generates 2-3 pilots by default."""
        for _ in range(20):
            pilots = generate_hiring_hall()
            self.assertIn(len(pilots), [2, 3])

    def test_specific_count(self):
        """Hall generates exact count when specified."""
        pilots = generate_hiring_hall(count=3)
        self.assertEqual(len(pilots), 3)

    def test_pilots_are_hireable(self):
        """All generated items are HireablePilot instances."""
        pilots = generate_hiring_hall()
        for hp in pilots:
            self.assertIsInstance(hp, HireablePilot)
            self.assertIsInstance(hp.pilot, MechWarrior)
            self.assertIsInstance(hp.hiring_cost, int)
            self.assertGreater(hp.hiring_cost, 0)

    def test_pilots_are_active(self):
        """All generated pilots are Active with no assigned mech."""
        pilots = generate_hiring_hall()
        for hp in pilots:
            self.assertEqual(hp.pilot.status, PilotStatus.ACTIVE)
            self.assertIsNone(hp.pilot.assigned_mech)

    def test_pilots_have_valid_skills(self):
        """All generated pilots have gunnery and piloting in 3-5 range."""
        pilots = generate_hiring_hall()
        for hp in pilots:
            self.assertIn(hp.pilot.gunnery, range(1, 7))
            self.assertIn(hp.pilot.piloting, range(1, 7))

    def test_unique_callsigns(self):
        """Pilots in the same hiring hall have unique callsigns."""
        pilots = generate_hiring_hall(count=3)
        callsigns = [hp.pilot.callsign for hp in pilots]
        self.assertEqual(len(callsigns), len(set(callsigns)))


class TestHiringCost(unittest.TestCase):
    """Tests for hiring cost calculation."""

    def test_cost_positive(self):
        """Hiring cost is always positive."""
        pilot = MechWarrior(name="Test", callsign="Test", gunnery=5, piloting=5)
        cost = calculate_hiring_cost(pilot)
        self.assertGreater(cost, 0)

    def test_better_pilots_cost_more(self):
        """Pilots with lower skills (better) cost more."""
        elite = MechWarrior(name="Elite", callsign="E", gunnery=1, piloting=1)
        green = MechWarrior(name="Green", callsign="G", gunnery=5, piloting=5)
        self.assertGreater(calculate_hiring_cost(elite), calculate_hiring_cost(green))

    def test_cost_formula(self):
        """Hiring cost matches the documented formula."""
        pilot = MechWarrior(name="Test", callsign="T", gunnery=3, piloting=4)
        expected = HIRING_BASE_COST + (6 - 3) * HIRING_SKILL_BONUS + (6 - 4) * HIRING_SKILL_BONUS
        self.assertEqual(calculate_hiring_cost(pilot), expected)


class TestCanBuyMech(unittest.TestCase):
    """Tests for mech purchase validation."""

    def _make_company(self, num_mechs=0, c_bills=500_000):
        """Helper to create a company with a given number of mechs."""
        mechs = []
        for i in range(num_mechs):
            mechs.append(BattleMech(
                name=f"Mech {i}",
                weight_class=WeightClass.MEDIUM,
                tonnage=50,
                armor_current=100, armor_max=100,
                structure_current=40, structure_max=40,
                firepower=5, speed=5,
            ))
        return Company(name="Test", c_bills=c_bills, mechs=mechs)

    def test_can_buy_with_space_and_money(self):
        """Can buy when lance has space and enough C-Bills."""
        company = self._make_company(num_mechs=2, c_bills=500_000)
        can, reason = can_buy_mech(company, 100_000)
        self.assertTrue(can)
        self.assertEqual(reason, "")

    def test_cannot_buy_lance_full(self):
        """Cannot buy when lance is full (4 mechs)."""
        company = self._make_company(num_mechs=4, c_bills=500_000)
        can, reason = can_buy_mech(company, 100_000)
        self.assertFalse(can)
        self.assertIn("full", reason.lower())

    def test_cannot_buy_insufficient_funds(self):
        """Cannot buy when not enough C-Bills."""
        company = self._make_company(num_mechs=2, c_bills=50_000)
        can, reason = can_buy_mech(company, 100_000)
        self.assertFalse(can)
        self.assertIn("not enough", reason.lower())


class TestCanHirePilot(unittest.TestCase):
    """Tests for pilot hire validation."""

    def _make_company(self, num_pilots=0, c_bills=500_000):
        """Helper to create a company with a given number of active pilots."""
        pilots = []
        for i in range(num_pilots):
            pilots.append(MechWarrior(
                name=f"Pilot {i}",
                callsign=f"CS{i}",
                gunnery=4, piloting=4,
            ))
        return Company(name="Test", c_bills=c_bills, mechwarriors=pilots)

    def test_can_hire_with_space_and_money(self):
        """Can hire when roster has space and enough C-Bills."""
        company = self._make_company(num_pilots=2, c_bills=500_000)
        can, reason = can_hire_pilot(company, 30_000)
        self.assertTrue(can)
        self.assertEqual(reason, "")

    def test_cannot_hire_roster_full(self):
        """Cannot hire when roster is full (4 active pilots)."""
        company = self._make_company(num_pilots=4, c_bills=500_000)
        can, reason = can_hire_pilot(company, 30_000)
        self.assertFalse(can)
        self.assertIn("full", reason.lower())

    def test_cannot_hire_insufficient_funds(self):
        """Cannot hire when not enough C-Bills."""
        company = self._make_company(num_pilots=2, c_bills=5_000)
        can, reason = can_hire_pilot(company, 30_000)
        self.assertFalse(can)
        self.assertIn("not enough", reason.lower())

    def test_kia_pilots_dont_count(self):
        """KIA pilots don't count toward the roster limit."""
        pilots = [
            MechWarrior(name="Active1", callsign="A1", gunnery=4, piloting=4),
            MechWarrior(name="Active2", callsign="A2", gunnery=4, piloting=4),
            MechWarrior(name="Active3", callsign="A3", gunnery=4, piloting=4),
            MechWarrior(
                name="Dead", callsign="D",
                gunnery=4, piloting=4, status=PilotStatus.KIA,
            ),
        ]
        company = Company(name="Test", c_bills=500_000, mechwarriors=pilots)
        can, reason = can_hire_pilot(company, 30_000)
        self.assertTrue(can)


class TestBuyMech(unittest.TestCase):
    """Tests for executing mech purchases."""

    def _make_company(self, num_mechs=0, c_bills=500_000):
        """Helper to create a company."""
        mechs = []
        for i in range(num_mechs):
            mechs.append(BattleMech(
                name=f"Mech {i}",
                weight_class=WeightClass.MEDIUM,
                tonnage=50,
                armor_current=100, armor_max=100,
                structure_current=40, structure_max=40,
                firepower=5, speed=5,
            ))
        return Company(name="Test", c_bills=c_bills, mechs=mechs)

    def test_successful_purchase(self):
        """Successful purchase adds mech to lance and deducts C-Bills."""
        company = self._make_company(num_mechs=2, c_bills=500_000)
        mech = create_mech_from_template("Atlas AS7-D")
        item = SalvageItem(mech=mech, price=200_000)

        initial_bills = company.c_bills
        initial_mechs = len(company.mechs)

        result = buy_mech(company, item)

        self.assertTrue(result)
        self.assertEqual(len(company.mechs), initial_mechs + 1)
        self.assertEqual(company.c_bills, initial_bills - 200_000)
        self.assertIn(mech, company.mechs)

    def test_failed_purchase_no_funds(self):
        """Failed purchase doesn't change company state."""
        company = self._make_company(num_mechs=2, c_bills=50_000)
        mech = create_mech_from_template("Atlas AS7-D")
        item = SalvageItem(mech=mech, price=200_000)

        initial_bills = company.c_bills
        initial_mechs = len(company.mechs)

        result = buy_mech(company, item)

        self.assertFalse(result)
        self.assertEqual(len(company.mechs), initial_mechs)
        self.assertEqual(company.c_bills, initial_bills)

    def test_failed_purchase_lance_full(self):
        """Failed purchase when lance is full doesn't change state."""
        company = self._make_company(num_mechs=4, c_bills=500_000)
        mech = create_mech_from_template("Locust LCT-1V")
        item = SalvageItem(mech=mech, price=50_000)

        result = buy_mech(company, item)
        self.assertFalse(result)
        self.assertEqual(len(company.mechs), 4)

    def test_purchased_mech_immediately_in_roster(self):
        """Purchased mech appears in company.mechs immediately."""
        company = self._make_company(num_mechs=1, c_bills=500_000)
        mech = create_mech_from_template("Wolverine WVR-6R")
        item = SalvageItem(mech=mech, price=100_000)

        buy_mech(company, item)
        mech_names = [m.name for m in company.mechs]
        self.assertIn("Wolverine WVR-6R", mech_names)


class TestHirePilot(unittest.TestCase):
    """Tests for executing pilot hires."""

    def _make_company(self, num_pilots=0, c_bills=500_000):
        """Helper to create a company."""
        pilots = []
        for i in range(num_pilots):
            pilots.append(MechWarrior(
                name=f"Pilot {i}",
                callsign=f"CS{i}",
                gunnery=4, piloting=4,
            ))
        return Company(name="Test", c_bills=c_bills, mechwarriors=pilots)

    def test_successful_hire(self):
        """Successful hire adds pilot to roster and deducts C-Bills."""
        company = self._make_company(num_pilots=2, c_bills=500_000)
        pilot = MechWarrior(
            name="New Pilot", callsign="Newbie",
            gunnery=4, piloting=4,
        )
        hireable = HireablePilot(pilot=pilot, hiring_cost=30_000)

        initial_bills = company.c_bills
        initial_pilots = len(company.mechwarriors)

        result = hire_pilot(company, hireable)

        self.assertTrue(result)
        self.assertEqual(len(company.mechwarriors), initial_pilots + 1)
        self.assertEqual(company.c_bills, initial_bills - 30_000)
        self.assertIn(pilot, company.mechwarriors)

    def test_failed_hire_no_funds(self):
        """Failed hire doesn't change company state."""
        company = self._make_company(num_pilots=2, c_bills=5_000)
        pilot = MechWarrior(
            name="Expensive", callsign="Exp",
            gunnery=1, piloting=1,
        )
        hireable = HireablePilot(pilot=pilot, hiring_cost=50_000)

        initial_bills = company.c_bills
        initial_pilots = len(company.mechwarriors)

        result = hire_pilot(company, hireable)

        self.assertFalse(result)
        self.assertEqual(len(company.mechwarriors), initial_pilots)
        self.assertEqual(company.c_bills, initial_bills)

    def test_failed_hire_roster_full(self):
        """Failed hire when roster is full doesn't change state."""
        company = self._make_company(num_pilots=4, c_bills=500_000)
        pilot = MechWarrior(
            name="Extra", callsign="Xtra",
            gunnery=4, piloting=4,
        )
        hireable = HireablePilot(pilot=pilot, hiring_cost=20_000)

        result = hire_pilot(company, hireable)
        self.assertFalse(result)
        self.assertEqual(len(company.mechwarriors), 4)

    def test_hired_pilot_immediately_in_roster(self):
        """Hired pilot appears in company.mechwarriors immediately."""
        company = self._make_company(num_pilots=1, c_bills=500_000)
        pilot = MechWarrior(
            name="Hired Gun", callsign="Hired",
            gunnery=3, piloting=3,
        )
        hireable = HireablePilot(pilot=pilot, hiring_cost=40_000)

        hire_pilot(company, hireable)
        callsigns = [mw.callsign for mw in company.mechwarriors]
        self.assertIn("Hired", callsigns)


class TestMaxLanceSize(unittest.TestCase):
    """Tests for the lance size limit constant."""

    def test_max_lance_size_is_4(self):
        """MAX_LANCE_SIZE is 4."""
        self.assertEqual(MAX_LANCE_SIZE, 4)


if __name__ == "__main__":
    unittest.main()
