import json
import os
import subprocess
import tempfile
import unittest

from _util import ROOT, write

EXISTING = {
    "model": "opus",
    "permissions": {"allow": ["Bash(npm test)"]},
    "hooks": {
        "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "my-own-hook.sh"}]}],
        "Stop": [{"hooks": [{"type": "command", "command": "say done"}]}],
    },
}


class InstallTest(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.settings = os.path.join(self.home, "settings.json")

    def install(self):
        env = dict(os.environ, CLAUDE_CONFIG_DIR=self.home)
        return subprocess.run(["bash", os.path.join(ROOT, "install.sh")], env=env, capture_output=True, text=True)

    def load(self):
        with open(self.settings) as f:
            return json.load(f)

    def ours(self, settings):
        return [h["command"] for e in settings["hooks"]["PreToolUse"] for h in e["hooks"] if "cc-guardrails" in h["command"]]

    def test_merges_without_overwriting_and_is_idempotent(self):
        write(self.settings, json.dumps(EXISTING))
        self.assertEqual(self.install().returncode, 0)
        self.assertEqual(self.install().returncode, 0)  # second run must not duplicate

        s = self.load()
        self.assertEqual(s["model"], "opus")
        self.assertEqual(s["permissions"], EXISTING["permissions"])
        self.assertEqual(s["hooks"]["Stop"], EXISTING["hooks"]["Stop"])
        self.assertEqual(s["hooks"]["PreToolUse"][0], EXISTING["hooks"]["PreToolUse"][0])
        self.assertEqual(len(self.ours(s)), 3)
        self.assertTrue(os.path.exists(self.settings + ".bak"))
        for name in ("rm_guard.py", "secret_guard.py", "force_push_guard.py", "_common.py"):
            self.assertTrue(os.path.exists(os.path.join(self.home, "hooks", "cc-guardrails", name)))

    def test_creates_settings_when_missing(self):
        self.assertEqual(self.install().returncode, 0)
        self.assertEqual(len(self.ours(self.load())), 3)

    def test_refuses_invalid_json(self):
        write(self.settings, "{ not json")
        r = self.install()
        self.assertNotEqual(r.returncode, 0)
        with open(self.settings) as f:
            self.assertEqual(f.read(), "{ not json")


if __name__ == "__main__":
    unittest.main()
