import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLIENTS = ROOT / "templates" / "clients.yml"

EXPECTED = ["claude", "agy", "copilot", "gemini", "opencode", "cursor", "kiro"]


def client_ids(text: str) -> list[str]:
    """Top-level keys nested one level under `clients:` (2-space indent)."""
    ids, inside = [], False
    for raw in text.splitlines():
        if raw.startswith("clients:"):
            inside = True
            continue
        if inside:
            if raw and not raw.startswith(" "):
                break
            if raw.startswith("  ") and not raw.startswith("    ") and raw.rstrip().endswith(":"):
                ids.append(raw.strip().rstrip(":"))
    return ids


class ClientTableTests(unittest.TestCase):
    def setUp(self):
        self.text = CLIENTS.read_text(encoding="utf-8")

    def test_file_exists(self):
        self.assertTrue(CLIENTS.is_file())

    def test_all_seven_clients_present(self):
        self.assertEqual(sorted(client_ids(self.text)), sorted(EXPECTED))

    def test_claude_code_is_an_alias_not_a_duplicate_entry(self):
        self.assertNotIn("claude-code", client_ids(self.text))
        self.assertIn("claude-code", self.text)

    def test_every_client_declares_a_format(self):
        self.assertEqual(self.text.count("format:"), len(EXPECTED))

    def test_no_web_fallback_remains(self):
        for banned in ("agentskills.io/clients", "instructionsUrl", "web search"):
            self.assertNotIn(banned, self.text)


if __name__ == "__main__":
    unittest.main()
