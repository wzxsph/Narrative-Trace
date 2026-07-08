from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gamegen.schema_contract import load_default_schema, validate_against_schema
from gamegen.validator import validate_game
from scripts.repair_game import repair_game


FIXTURE_PATH = ROOT / "examples" / "fixtures" / "generation_failures" / "fixture_cases.json"


def load_json(path: Path) -> dict[str, Any]:
  return json.loads(path.read_text(encoding="utf-8"))


def apply_mutations(game: dict[str, Any], mutations: list[dict[str, Any]]) -> dict[str, Any]:
  mutated = copy.deepcopy(game)
  for mutation in mutations:
    apply_mutation(mutated, mutation)
  return mutated


def apply_mutation(target: dict[str, Any], mutation: dict[str, Any]) -> None:
  op = mutation["op"]
  path = mutation["path"]
  if op == "set":
    parent, key = resolve_parent(target, path)
    parent[key] = mutation["value"]
    return
  if op == "delete":
    parent, key = resolve_parent(target, path)
    del parent[key]
    return
  if op == "replace_text":
    parent, key = resolve_parent(target, path)
    parent[key] = str(parent[key]).replace(mutation["old"], mutation["new"])
    return
  raise AssertionError(f"Unknown fixture mutation op: {op}")


def resolve_parent(target: Any, path: list[Any]) -> tuple[Any, Any]:
  current = target
  for part in path[:-1]:
    current = current[part]
  return current, path[-1]


def validator_has_errors(game: dict[str, Any]) -> bool:
  return any(message.level == "error" for message in validate_game(game))


class GenerationFailureFixtureTest(unittest.TestCase):
  @classmethod
  def setUpClass(cls) -> None:
    cls.fixtures = load_json(FIXTURE_PATH)
    cls.base_game = load_json(ROOT / cls.fixtures["base_game"])
    cls.schema = load_default_schema()

  def test_fixture_file_has_unique_case_ids(self) -> None:
    case_ids = [case["id"] for case in self.fixtures["cases"]]
    self.assertEqual(len(case_ids), len(set(case_ids)))

  def test_generation_failure_fixtures_match_gate_expectations(self) -> None:
    for case in self.fixtures["cases"]:
      with self.subTest(case=case["id"]):
        game = apply_mutations(self.base_game, case["mutations"])
        schema_errors = validate_against_schema(game, self.schema)
        validator_errors = validator_has_errors(game)
        repaired, repairs = repair_game(game)
        repaired_validator_errors = validator_has_errors(repaired)

        expect = case["expect"]
        self.assertEqual(bool(schema_errors), expect["schema_errors"], schema_errors)
        self.assertEqual(validator_errors, expect["validator_errors"])
        if expect["repair_clears_validator_errors"]:
          self.assertTrue(repairs)
          self.assertFalse(repaired_validator_errors)
        else:
          self.assertEqual(expect["repair_clears_validator_errors"], validator_errors and not repaired_validator_errors)


if __name__ == "__main__":
  unittest.main()
