from __future__ import annotations

import unittest
from unittest import mock

from gamegen.llm_client import LLMConfig, parse_json_response


class LLMClientTest(unittest.TestCase):
  def test_from_env_strips_api_key_whitespace_and_disables_minimax_m3_thinking(self) -> None:
    with mock.patch.dict(
      "os.environ",
      {
        "LLM_BASE_URL": "https://api.minimaxi.com/v1",
        "LLM_API_KEY": " sk-test\n-token ",
        "LLM_MODEL": "Minimax-M3",
      },
      clear=False,
    ):
      config = LLMConfig.from_env()

    self.assertIsNotNone(config)
    assert config is not None
    self.assertEqual(config.api_key, "sk-test-token")
    self.assertEqual(config.thinking_type, "disabled")

  def test_parse_json_response_accepts_thinking_prefix(self) -> None:
    text = '<think>The model is reasoning.</think>\n\n{"ok":"game_writer_llm_smoke_ok"}'

    self.assertEqual(parse_json_response(text), {"ok": "game_writer_llm_smoke_ok"})

  def test_parse_json_response_skips_invalid_brace_fragments(self) -> None:
    text = 'reasoning with {not json yet\nfinal answer:\n{"text":"ok"}'

    self.assertEqual(parse_json_response(text), {"text": "ok"})

  def test_parse_json_response_accepts_markdown_json_block(self) -> None:
    text = '```json\n{"ok":"yes"}\n```'

    self.assertEqual(parse_json_response(text), {"ok": "yes"})


if __name__ == "__main__":
  unittest.main()
