"""
test_contracts.py - Unit tests for the Contract data model and market generation.

Tests cover:
- Contract data model creation and serialization
- MissionType enum
- Contract skull display
- Contract template catalog (count, diversity, required fields)
- Contract generation (count, difficulty scaling, employer factions)
- Difficulty scaling rules by month
"""

import sys
import os

# Add the project root to path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest

from data.models import Contract, MissionType
from data.contracts import (
    CONTRACT_TEMPLATES,
    EMPLOYERS,
    generate_contracts,
    _max_difficulty_for_month,
)


class TestMissionType(unittest.TestCase):
    """Tests for the MissionType enum."""

    def test_mission_types_exist(self):
        """All four required mission types are defined."""
        self.assertEqual(MissionType.GARRISON_DUTY.value, "Garrison Duty")
        self.assertEqual(MissionType.RAID.value, "Raid")
        self.assertEqual(MissionType.BASE_ASSAULT.value, "Base Assault")
        self.assertEqual(MissionType.RECON.value, "Recon")

    def test_at_least_four_types(self):
        """There are at least 4 mission types."""
        self.assertGreaterEqual(len(MissionType), 4)


class TestContract(unittest.TestCase):
    """Tests for the Contract dataclass."""

    def _make_contract(self, **overrides):
        """Helper to create a contract with sensible defaults."""
        defaults = {
            "employer": "House Davion",
            "mission_type": MissionType.RAID,
            "difficulty": 3,
            "payout": 250_000,
            "salvage_rights": 30,
            "bonus_objective": "Destroy the ammo depot.",
            "description": "Strike behind enemy lines.",
        }
        defaults.update(overrides)
        return Contract(**defaults)

    def test_creation(self):
        """Contract can be created with all required fields."""
        contract = self._make_contract()
        self.assertEqual(contract.employer, "House Davion")
        self.assertEqual(contract.mission_type, MissionType.RAID)
        self.assertEqual(contract.difficulty, 3)
        self.assertEqual(contract.payout, 250_000)
        self.assertEqual(contract.salvage_rights, 30)
        self.assertEqual(contract.bonus_objective, "Destroy the ammo depot.")
        self.assertEqual(contract.description, "Strike behind enemy lines.")

    def test_skulls_display_1(self):
        """1-skull contract shows [*----]."""
        contract = self._make_contract(difficulty=1)
        self.assertEqual(contract.skulls_display(), "[*----]")

    def test_skulls_display_3(self):
        """3-skull contract shows [***--]."""
        contract = self._make_contract(difficulty=3)
        self.assertEqual(contract.skulls_display(), "[***--]")

    def test_skulls_display_5(self):
        """5-skull contract shows [*****]."""
        contract = self._make_contract(difficulty=5)
        self.assertEqual(contract.skulls_display(), "[*****]")

    def test_to_dict(self):
        """Contract serializes correctly to a dictionary."""
        contract = self._make_contract()
        d = contract.to_dict()
        self.assertEqual(d["employer"], "House Davion")
        self.assertEqual(d["mission_type"], "Raid")
        self.assertEqual(d["difficulty"], 3)
        self.assertEqual(d["payout"], 250_000)
        self.assertEqual(d["salvage_rights"], 30)
        self.assertEqual(d["bonus_objective"], "Destroy the ammo depot.")
        self.assertEqual(d["description"], "Strike behind enemy lines.")

    def test_from_dict(self):
        """Contract can be reconstructed from a dictionary."""
        d = {
            "employer": "House Steiner",
            "mission_type": "Garrison Duty",
            "difficulty": 1,
            "payout": 80_000,
            "salvage_rights": 10,
            "bonus_objective": "No casualties.",
            "description": "Guard the border.",
        }
        contract = Contract.from_dict(d)
        self.assertEqual(contract.employer, "House Steiner")
        self.assertEqual(contract.mission_type, MissionType.GARRISON_DUTY)
        self.assertEqual(contract.difficulty, 1)
        self.assertEqual(contract.payout, 80_000)
        self.assertEqual(contract.salvage_rights, 10)

    def test_round_trip(self):
        """Contract survives a to_dict/from_dict round trip."""
        original = self._make_contract(
            employer="ComStar",
            mission_type=MissionType.BASE_ASSAULT,
            difficulty=5,
            payout=750_000,
            salvage_rights=50,
        )
        restored = Contract.from_dict(original.to_dict())
        self.assertEqual(original, restored)

    def test_all_mission_types_serialize(self):
        """All MissionType values serialize and deserialize correctly."""
        for mt in MissionType:
            contract = self._make_contract(mission_type=mt)
            d = contract.to_dict()
            self.assertEqual(d["mission_type"], mt.value)
            restored = Contract.from_dict(d)
            self.assertEqual(restored.mission_type, mt)


class TestContractTemplates(unittest.TestCase):
    """Tests for the contract template catalog."""

    def test_at_least_12_templates(self):
        """There are at least 12 contract templates."""
        self.assertGreaterEqual(len(CONTRACT_TEMPLATES), 12)

    def test_all_templates_have_required_fields(self):
        """Every template has all required fields."""
        required = {
            "mission_type", "base_difficulty", "base_payout",
            "salvage_rights", "bonus_objective", "description",
        }
        for i, tmpl in enumerate(CONTRACT_TEMPLATES):
            for field in required:
                self.assertIn(
                    field, tmpl,
                    f"Template {i} missing field '{field}'",
                )

    def test_templates_have_valid_difficulty(self):
        """All template base difficulties are 1-5."""
        for i, tmpl in enumerate(CONTRACT_TEMPLATES):
            self.assertGreaterEqual(
                tmpl["base_difficulty"], 1,
                f"Template {i} difficulty too low",
            )
            self.assertLessEqual(
                tmpl["base_difficulty"], 5,
                f"Template {i} difficulty too high",
            )

    def test_templates_have_positive_payout(self):
        """All templates have positive base payout."""
        for i, tmpl in enumerate(CONTRACT_TEMPLATES):
            self.assertGreater(
                tmpl["base_payout"], 0,
                f"Template {i} payout must be positive",
            )

    def test_templates_have_valid_salvage(self):
        """All template salvage rights are 0-100."""
        for i, tmpl in enumerate(CONTRACT_TEMPLATES):
            self.assertGreaterEqual(tmpl["salvage_rights"], 0)
            self.assertLessEqual(tmpl["salvage_rights"], 100)

    def test_templates_cover_all_mission_types(self):
        """Templates include all four mission types."""
        types = {tmpl["mission_type"] for tmpl in CONTRACT_TEMPLATES}
        self.assertIn(MissionType.GARRISON_DUTY, types)
        self.assertIn(MissionType.RAID, types)
        self.assertIn(MissionType.BASE_ASSAULT, types)
        self.assertIn(MissionType.RECON, types)

    def test_templates_have_unique_descriptions(self):
        """All templates have unique flavor text descriptions."""
        descriptions = [tmpl["description"] for tmpl in CONTRACT_TEMPLATES]
        self.assertEqual(len(descriptions), len(set(descriptions)))

    def test_templates_have_nonempty_bonus(self):
        """All templates have a non-empty bonus objective."""
        for i, tmpl in enumerate(CONTRACT_TEMPLATES):
            self.assertTrue(
                len(tmpl["bonus_objective"]) > 0,
                f"Template {i} has empty bonus objective",
            )


class TestEmployers(unittest.TestCase):
    """Tests for the employer factions list."""

    def test_employer_factions_exist(self):
        """Required BattleTech factions are present."""
        employer_names = " ".join(EMPLOYERS).lower()
        self.assertIn("davion", employer_names)
        self.assertIn("steiner", employer_names)
        self.assertIn("liao", employer_names)
        self.assertIn("marik", employer_names)
        self.assertIn("kurita", employer_names)
        self.assertIn("comstar", employer_names)

    def test_at_least_six_employers(self):
        """There are at least 6 employer factions."""
        self.assertGreaterEqual(len(EMPLOYERS), 6)


class TestDifficultyScaling(unittest.TestCase):
    """Tests for the difficulty scaling by month."""

    def test_months_1_to_3_max_2_skulls(self):
        """Months 1-3 allow at most 2-skull missions."""
        for month in range(1, 4):
            self.assertEqual(_max_difficulty_for_month(month), 2)

    def test_months_4_to_6_max_3_skulls(self):
        """Months 4-6 allow at most 3-skull missions."""
        for month in range(4, 7):
            self.assertEqual(_max_difficulty_for_month(month), 3)

    def test_months_7_plus_max_5_skulls(self):
        """Months 7+ allow up to 5-skull missions."""
        for month in [7, 8, 10, 20, 100]:
            self.assertEqual(_max_difficulty_for_month(month), 5)


class TestContractGeneration(unittest.TestCase):
    """Tests for the contract market generation."""

    def test_generates_exactly_3_contracts(self):
        """generate_contracts produces exactly 3 contracts by default."""
        contracts = generate_contracts(month=1)
        self.assertEqual(len(contracts), 3)

    def test_generates_custom_count(self):
        """generate_contracts can produce a custom number of contracts."""
        contracts = generate_contracts(month=1, count=5)
        self.assertEqual(len(contracts), 5)

    def test_all_contracts_are_contract_instances(self):
        """All generated contracts are Contract instances."""
        contracts = generate_contracts(month=3)
        for contract in contracts:
            self.assertIsInstance(contract, Contract)

    def test_contracts_have_valid_difficulty(self):
        """All generated contracts have difficulty between 1 and 5."""
        for month in [1, 3, 5, 7, 10]:
            contracts = generate_contracts(month=month)
            for contract in contracts:
                self.assertGreaterEqual(contract.difficulty, 1)
                self.assertLessEqual(contract.difficulty, 5)

    def test_contracts_have_positive_payout(self):
        """All generated contracts have positive payout."""
        for month in [1, 5, 10]:
            contracts = generate_contracts(month=month)
            for contract in contracts:
                self.assertGreater(contract.payout, 0)

    def test_early_months_no_high_difficulty(self):
        """Months 1-3 should not produce contracts above 2 base difficulty."""
        # Run multiple times for statistical significance since there's randomness
        for _ in range(20):
            contracts = generate_contracts(month=1)
            for contract in contracts:
                self.assertLessEqual(
                    contract.difficulty, 2,
                    f"Month 1 produced {contract.difficulty}-skull mission",
                )

    def test_mid_months_no_extreme_difficulty(self):
        """Months 4-6 should not produce contracts above 4 difficulty."""
        for _ in range(20):
            contracts = generate_contracts(month=5)
            for contract in contracts:
                self.assertLessEqual(
                    contract.difficulty, 4,
                    f"Month 5 produced {contract.difficulty}-skull mission",
                )

    def test_employers_from_factions(self):
        """All generated contract employers are from the factions list."""
        for month in [1, 5, 10]:
            contracts = generate_contracts(month=month)
            for contract in contracts:
                self.assertIn(contract.employer, EMPLOYERS)

    def test_contracts_have_valid_salvage(self):
        """All generated contracts have salvage rights between 0 and 100."""
        contracts = generate_contracts(month=5)
        for contract in contracts:
            self.assertGreaterEqual(contract.salvage_rights, 0)
            self.assertLessEqual(contract.salvage_rights, 100)

    def test_contracts_have_nonempty_description(self):
        """All generated contracts have non-empty descriptions."""
        contracts = generate_contracts(month=3)
        for contract in contracts:
            self.assertTrue(len(contract.description) > 0)

    def test_contracts_have_nonempty_bonus(self):
        """All generated contracts have non-empty bonus objectives."""
        contracts = generate_contracts(month=3)
        for contract in contracts:
            self.assertTrue(len(contract.bonus_objective) > 0)

    def test_contracts_have_valid_mission_type(self):
        """All generated contracts have a valid MissionType."""
        contracts = generate_contracts(month=5)
        for contract in contracts:
            self.assertIsInstance(contract.mission_type, MissionType)

    def test_varied_mission_types(self):
        """Generated contracts tend to have varied mission types.

        Over multiple generations, at least 2 different types should appear.
        """
        all_types = set()
        for _ in range(10):
            contracts = generate_contracts(month=5)
            for c in contracts:
                all_types.add(c.mission_type)
        self.assertGreaterEqual(len(all_types), 2)

    def test_skulls_display_format(self):
        """Generated contracts produce valid skull display strings."""
        contracts = generate_contracts(month=5)
        for contract in contracts:
            display = contract.skulls_display()
            self.assertTrue(display.startswith("["))
            self.assertTrue(display.endswith("]"))
            # Inner content should be exactly 5 chars of * and -
            inner = display[1:-1]
            self.assertEqual(len(inner), 5)
            self.assertTrue(all(c in ("*", "-") for c in inner))


if __name__ == "__main__":
    unittest.main()
