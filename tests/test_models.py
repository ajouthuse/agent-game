"""
test_models.py - Unit tests for Iron Contract data models.

Tests cover:
- BattleMech creation and serialization
- MechWarrior creation and serialization
- Company creation and serialization
- Starting lance generation
- MechWarrior name/callsign generation
- Company creation helper round-trip
"""

import sys
import os

# Add the project root to path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest

from models import (
    BattleMech,
    Company,
    MechStatus,
    MechWarrior,
    PilotStatus,
    WeightClass,
)
from data import (
    MECH_TEMPLATES,
    STARTING_LANCE_KEYS,
    create_mech_from_template,
    create_starting_lance,
)
from names import (
    generate_callsign,
    generate_mechwarrior,
    generate_mechwarrior_roster,
    generate_name,
)


class TestBattleMech(unittest.TestCase):
    """Tests for the BattleMech dataclass."""

    def _make_mech(self, **overrides):
        """Helper to create a mech with sensible defaults."""
        defaults = {
            "name": "Wolverine WVR-6R",
            "weight_class": WeightClass.MEDIUM,
            "tonnage": 55,
            "armor_current": 136,
            "armor_max": 136,
            "firepower": 6,
            "status": MechStatus.READY,
        }
        defaults.update(overrides)
        return BattleMech(**defaults)

    def test_creation(self):
        """BattleMech can be created with all required fields."""
        mech = self._make_mech()
        self.assertEqual(mech.name, "Wolverine WVR-6R")
        self.assertEqual(mech.weight_class, WeightClass.MEDIUM)
        self.assertEqual(mech.tonnage, 55)
        self.assertEqual(mech.armor_current, 136)
        self.assertEqual(mech.armor_max, 136)
        self.assertEqual(mech.firepower, 6)
        self.assertEqual(mech.status, MechStatus.READY)

    def test_default_status(self):
        """BattleMech defaults to READY status."""
        mech = BattleMech(
            name="Test",
            weight_class=WeightClass.LIGHT,
            tonnage=20,
            armor_current=48,
            armor_max=48,
            firepower=2,
        )
        self.assertEqual(mech.status, MechStatus.READY)

    def test_to_dict(self):
        """BattleMech serializes correctly to a dictionary."""
        mech = self._make_mech()
        d = mech.to_dict()
        self.assertEqual(d["name"], "Wolverine WVR-6R")
        self.assertEqual(d["weight_class"], "Medium")
        self.assertEqual(d["tonnage"], 55)
        self.assertEqual(d["armor_current"], 136)
        self.assertEqual(d["armor_max"], 136)
        self.assertEqual(d["firepower"], 6)
        self.assertEqual(d["status"], "Ready")

    def test_from_dict(self):
        """BattleMech can be reconstructed from a dictionary."""
        d = {
            "name": "Atlas AS7-D",
            "weight_class": "Assault",
            "tonnage": 100,
            "armor_current": 250,
            "armor_max": 304,
            "firepower": 10,
            "status": "Damaged",
        }
        mech = BattleMech.from_dict(d)
        self.assertEqual(mech.name, "Atlas AS7-D")
        self.assertEqual(mech.weight_class, WeightClass.ASSAULT)
        self.assertEqual(mech.tonnage, 100)
        self.assertEqual(mech.armor_current, 250)
        self.assertEqual(mech.armor_max, 304)
        self.assertEqual(mech.firepower, 10)
        self.assertEqual(mech.status, MechStatus.DAMAGED)

    def test_round_trip(self):
        """BattleMech survives a to_dict/from_dict round trip."""
        original = self._make_mech(status=MechStatus.DAMAGED, armor_current=50)
        restored = BattleMech.from_dict(original.to_dict())
        self.assertEqual(original, restored)

    def test_all_statuses(self):
        """All MechStatus values serialize and deserialize correctly."""
        for status in MechStatus:
            mech = self._make_mech(status=status)
            d = mech.to_dict()
            self.assertEqual(d["status"], status.value)
            restored = BattleMech.from_dict(d)
            self.assertEqual(restored.status, status)

    def test_all_weight_classes(self):
        """All WeightClass values serialize and deserialize correctly."""
        for wc in WeightClass:
            mech = self._make_mech(weight_class=wc)
            d = mech.to_dict()
            self.assertEqual(d["weight_class"], wc.value)
            restored = BattleMech.from_dict(d)
            self.assertEqual(restored.weight_class, wc)


class TestMechWarrior(unittest.TestCase):
    """Tests for the MechWarrior dataclass."""

    def _make_pilot(self, **overrides):
        """Helper to create a pilot with sensible defaults."""
        defaults = {
            "name": "Alex Steiner",
            "callsign": "Falcon",
            "gunnery": 4,
            "piloting": 4,
            "status": PilotStatus.ACTIVE,
            "assigned_mech": None,
        }
        defaults.update(overrides)
        return MechWarrior(**defaults)

    def test_creation(self):
        """MechWarrior can be created with all required fields."""
        pilot = self._make_pilot()
        self.assertEqual(pilot.name, "Alex Steiner")
        self.assertEqual(pilot.callsign, "Falcon")
        self.assertEqual(pilot.gunnery, 4)
        self.assertEqual(pilot.piloting, 4)
        self.assertEqual(pilot.status, PilotStatus.ACTIVE)
        self.assertIsNone(pilot.assigned_mech)

    def test_default_status(self):
        """MechWarrior defaults to ACTIVE status."""
        pilot = MechWarrior(name="Test", callsign="Test", gunnery=3, piloting=3)
        self.assertEqual(pilot.status, PilotStatus.ACTIVE)

    def test_assigned_mech(self):
        """MechWarrior can be assigned to a mech."""
        pilot = self._make_pilot(assigned_mech="Wolverine WVR-6R")
        self.assertEqual(pilot.assigned_mech, "Wolverine WVR-6R")

    def test_to_dict(self):
        """MechWarrior serializes correctly to a dictionary."""
        pilot = self._make_pilot(assigned_mech="Atlas AS7-D")
        d = pilot.to_dict()
        self.assertEqual(d["name"], "Alex Steiner")
        self.assertEqual(d["callsign"], "Falcon")
        self.assertEqual(d["gunnery"], 4)
        self.assertEqual(d["piloting"], 4)
        self.assertEqual(d["status"], "Active")
        self.assertEqual(d["assigned_mech"], "Atlas AS7-D")

    def test_to_dict_no_mech(self):
        """MechWarrior with no assigned mech serializes assigned_mech as None."""
        pilot = self._make_pilot()
        d = pilot.to_dict()
        self.assertIsNone(d["assigned_mech"])

    def test_from_dict(self):
        """MechWarrior can be reconstructed from a dictionary."""
        d = {
            "name": "Brynn Kurita",
            "callsign": "Blaze",
            "gunnery": 3,
            "piloting": 5,
            "status": "Injured",
            "assigned_mech": "Jenner JR7-D",
        }
        pilot = MechWarrior.from_dict(d)
        self.assertEqual(pilot.name, "Brynn Kurita")
        self.assertEqual(pilot.callsign, "Blaze")
        self.assertEqual(pilot.gunnery, 3)
        self.assertEqual(pilot.piloting, 5)
        self.assertEqual(pilot.status, PilotStatus.INJURED)
        self.assertEqual(pilot.assigned_mech, "Jenner JR7-D")

    def test_round_trip(self):
        """MechWarrior survives a to_dict/from_dict round trip."""
        original = self._make_pilot(
            status=PilotStatus.INJURED,
            assigned_mech="Catapult CPLT-C1",
        )
        restored = MechWarrior.from_dict(original.to_dict())
        self.assertEqual(original, restored)

    def test_round_trip_no_mech(self):
        """MechWarrior with no mech survives round trip."""
        original = self._make_pilot()
        restored = MechWarrior.from_dict(original.to_dict())
        self.assertEqual(original, restored)

    def test_all_statuses(self):
        """All PilotStatus values serialize and deserialize correctly."""
        for status in PilotStatus:
            pilot = self._make_pilot(status=status)
            d = pilot.to_dict()
            self.assertEqual(d["status"], status.value)
            restored = MechWarrior.from_dict(d)
            self.assertEqual(restored.status, status)


class TestCompany(unittest.TestCase):
    """Tests for the Company dataclass."""

    def _make_company(self, **overrides):
        """Helper to create a company with sensible defaults."""
        defaults = {
            "name": "Wolf's Dragoons",
            "c_bills": 2_000_000,
            "reputation": 15,
            "mechwarriors": [],
            "mechs": [],
        }
        defaults.update(overrides)
        return Company(**defaults)

    def test_creation(self):
        """Company can be created with all required fields."""
        company = self._make_company()
        self.assertEqual(company.name, "Wolf's Dragoons")
        self.assertEqual(company.c_bills, 2_000_000)
        self.assertEqual(company.reputation, 15)
        self.assertEqual(company.mechwarriors, [])
        self.assertEqual(company.mechs, [])

    def test_default_values(self):
        """Company defaults to correct starting values."""
        company = Company(name="Test Company")
        self.assertEqual(company.c_bills, 2_000_000)
        self.assertEqual(company.reputation, 15)
        self.assertEqual(company.mechwarriors, [])
        self.assertEqual(company.mechs, [])

    def test_to_dict_empty(self):
        """Empty company serializes correctly."""
        company = self._make_company()
        d = company.to_dict()
        self.assertEqual(d["name"], "Wolf's Dragoons")
        self.assertEqual(d["c_bills"], 2_000_000)
        self.assertEqual(d["reputation"], 15)
        self.assertEqual(d["mechwarriors"], [])
        self.assertEqual(d["mechs"], [])

    def test_to_dict_with_roster(self):
        """Company with mechs and pilots serializes nested objects."""
        mech = BattleMech(
            name="Wolverine WVR-6R",
            weight_class=WeightClass.MEDIUM,
            tonnage=55,
            armor_current=136,
            armor_max=136,
            firepower=6,
        )
        pilot = MechWarrior(
            name="Alex Steiner",
            callsign="Falcon",
            gunnery=4,
            piloting=4,
            assigned_mech="Wolverine WVR-6R",
        )
        company = self._make_company(mechs=[mech], mechwarriors=[pilot])
        d = company.to_dict()
        self.assertEqual(len(d["mechs"]), 1)
        self.assertEqual(len(d["mechwarriors"]), 1)
        self.assertEqual(d["mechs"][0]["name"], "Wolverine WVR-6R")
        self.assertEqual(d["mechwarriors"][0]["callsign"], "Falcon")

    def test_from_dict(self):
        """Company can be reconstructed from a dictionary."""
        d = {
            "name": "Kell Hounds",
            "c_bills": 5_000_000,
            "reputation": 60,
            "mechwarriors": [
                {
                    "name": "Test Pilot",
                    "callsign": "Ghost",
                    "gunnery": 3,
                    "piloting": 3,
                    "status": "Active",
                    "assigned_mech": None,
                }
            ],
            "mechs": [
                {
                    "name": "Atlas AS7-D",
                    "weight_class": "Assault",
                    "tonnage": 100,
                    "armor_current": 304,
                    "armor_max": 304,
                    "firepower": 10,
                    "status": "Ready",
                }
            ],
        }
        company = Company.from_dict(d)
        self.assertEqual(company.name, "Kell Hounds")
        self.assertEqual(company.c_bills, 5_000_000)
        self.assertEqual(company.reputation, 60)
        self.assertEqual(len(company.mechwarriors), 1)
        self.assertEqual(len(company.mechs), 1)
        self.assertIsInstance(company.mechwarriors[0], MechWarrior)
        self.assertIsInstance(company.mechs[0], BattleMech)

    def test_round_trip(self):
        """Company with full roster survives a to_dict/from_dict round trip."""
        mech = BattleMech(
            name="Hunchback HBK-4G",
            weight_class=WeightClass.MEDIUM,
            tonnage=50,
            armor_current=100,
            armor_max=120,
            firepower=7,
            status=MechStatus.DAMAGED,
        )
        pilot = MechWarrior(
            name="Brynn Kurita",
            callsign="Blaze",
            gunnery=3,
            piloting=5,
            status=PilotStatus.INJURED,
            assigned_mech="Hunchback HBK-4G",
        )
        original = self._make_company(
            name="Iron Fists",
            c_bills=1_500_000,
            reputation=42,
            mechs=[mech],
            mechwarriors=[pilot],
        )
        restored = Company.from_dict(original.to_dict())
        self.assertEqual(original, restored)


class TestMechTemplates(unittest.TestCase):
    """Tests for the data.py mech template catalog."""

    def test_template_count(self):
        """There are at least 6 mech templates."""
        self.assertGreaterEqual(len(MECH_TEMPLATES), 6)

    def test_weight_class_diversity(self):
        """Templates span at least 3 weight classes."""
        weight_classes = {t["weight_class"] for t in MECH_TEMPLATES.values()}
        self.assertGreaterEqual(len(weight_classes), 3)

    def test_all_weight_classes_covered(self):
        """All four weight classes are represented in templates."""
        weight_classes = {t["weight_class"] for t in MECH_TEMPLATES.values()}
        self.assertIn(WeightClass.LIGHT, weight_classes)
        self.assertIn(WeightClass.MEDIUM, weight_classes)
        self.assertIn(WeightClass.HEAVY, weight_classes)
        self.assertIn(WeightClass.ASSAULT, weight_classes)

    def test_create_mech_from_template(self):
        """create_mech_from_template returns a valid BattleMech."""
        mech = create_mech_from_template("Wolverine WVR-6R")
        self.assertIsInstance(mech, BattleMech)
        self.assertEqual(mech.name, "Wolverine WVR-6R")
        self.assertEqual(mech.weight_class, WeightClass.MEDIUM)
        self.assertEqual(mech.armor_current, mech.armor_max)
        self.assertEqual(mech.status, MechStatus.READY)

    def test_create_mech_invalid_key(self):
        """create_mech_from_template raises KeyError for unknown key."""
        with self.assertRaises(KeyError):
            create_mech_from_template("Nonexistent Mech")

    def test_starting_lance_composition(self):
        """Starting lance has 4 mechs: 2 medium and 2 light."""
        lance = create_starting_lance()
        self.assertEqual(len(lance), 4)
        weight_classes = [m.weight_class for m in lance]
        self.assertEqual(weight_classes.count(WeightClass.MEDIUM), 2)
        self.assertEqual(weight_classes.count(WeightClass.LIGHT), 2)

    def test_starting_lance_all_ready(self):
        """All starting lance mechs are at full armor and Ready status."""
        lance = create_starting_lance()
        for mech in lance:
            self.assertEqual(mech.status, MechStatus.READY)
            self.assertEqual(mech.armor_current, mech.armor_max)

    def test_template_firepower_range(self):
        """All template firepower ratings are between 1 and 10."""
        for key, tmpl in MECH_TEMPLATES.items():
            self.assertGreaterEqual(tmpl["firepower"], 1, f"{key} firepower too low")
            self.assertLessEqual(tmpl["firepower"], 10, f"{key} firepower too high")


class TestNameGeneration(unittest.TestCase):
    """Tests for the names.py random name/callsign generation."""

    def test_generate_name_format(self):
        """Generated names are in 'First Last' format."""
        name = generate_name()
        parts = name.split(" ")
        self.assertEqual(len(parts), 2)
        self.assertTrue(all(part.strip() for part in parts))

    def test_generate_callsign(self):
        """Generated callsign is a non-empty string."""
        callsign = generate_callsign()
        self.assertIsInstance(callsign, str)
        self.assertTrue(len(callsign) > 0)

    def test_generate_callsign_avoids_used(self):
        """Callsign generation avoids already-used callsigns."""
        used = {"Falcon", "Blaze", "Ghost"}
        for _ in range(20):
            callsign = generate_callsign(used)
            self.assertNotIn(callsign, used)

    def test_generate_mechwarrior(self):
        """Generated MechWarrior has valid fields."""
        pilot = generate_mechwarrior()
        self.assertIsInstance(pilot, MechWarrior)
        self.assertTrue(len(pilot.name) > 0)
        self.assertTrue(len(pilot.callsign) > 0)
        self.assertIn(pilot.gunnery, range(1, 7))
        self.assertIn(pilot.piloting, range(1, 7))
        self.assertEqual(pilot.status, PilotStatus.ACTIVE)
        self.assertIsNone(pilot.assigned_mech)

    def test_generate_roster_count(self):
        """Roster generation creates the requested number of pilots."""
        roster = generate_mechwarrior_roster(4)
        self.assertEqual(len(roster), 4)

    def test_generate_roster_unique_callsigns(self):
        """Roster callsigns are unique within the roster."""
        roster = generate_mechwarrior_roster(10)
        callsigns = [mw.callsign for mw in roster]
        self.assertEqual(len(callsigns), len(set(callsigns)))

    def test_generate_roster_all_active(self):
        """All generated roster pilots start as Active."""
        roster = generate_mechwarrior_roster(4)
        for mw in roster:
            self.assertEqual(mw.status, PilotStatus.ACTIVE)


if __name__ == "__main__":
    unittest.main()
