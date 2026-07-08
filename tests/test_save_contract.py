from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gamegen.save_contract import DEFAULT_SAVE_CONTRACT, load_save_contract, validate_save_contract


class SaveContractTest(unittest.TestCase):
  def test_current_save_contract_fixtures_are_valid(self) -> None:
    self.assertEqual(validate_save_contract(DEFAULT_SAVE_CONTRACT), [])

  def test_save_contract_rejects_bad_scene_reference(self) -> None:
    contract = load_save_contract(DEFAULT_SAVE_CONTRACT)
    mutated = copy.deepcopy(contract)
    mutated["cases"][0]["payload"]["sceneId"] = "missing_scene"

    errors = validate_mutated_contract(mutated)

    self.assertTrue(any("sceneId does not exist" in error for error in errors))

  def test_save_contract_rejects_duplicate_case_id(self) -> None:
    contract = load_save_contract(DEFAULT_SAVE_CONTRACT)
    mutated = copy.deepcopy(contract)
    mutated["cases"][1]["id"] = mutated["cases"][0]["id"]

    errors = validate_mutated_contract(mutated)

    self.assertTrue(any("duplicate id" in error for error in errors))

  def test_save_contract_rejects_missing_fallback_notice(self) -> None:
    contract = load_save_contract(DEFAULT_SAVE_CONTRACT)
    mutated = copy.deepcopy(contract)
    del mutated["cases"][2]["expect"]["recovery_notice_contains"]

    errors = validate_mutated_contract(mutated)

    self.assertTrue(any("fallback case must declare recovery_notice_contains" in error for error in errors))


def validate_mutated_contract(contract: dict) -> list[str]:
  with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "save_cases.json"
    path.write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")
    return validate_save_contract(path)


if __name__ == "__main__":
  unittest.main()
