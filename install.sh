#!/usr/bin/env bash
# Install cc-guardrails: copy hooks into ~/.claude/hooks/cc-guardrails and merge them into
# ~/.claude/settings.json. Existing settings and hooks are kept; re-running is safe.
set -euo pipefail

CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
HOOK_DIR="$CLAUDE_DIR/hooks/cc-guardrails"
SETTINGS="$CLAUDE_DIR/settings.json"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/hooks"

command -v python3 >/dev/null || { echo "cc-guardrails needs python3 on PATH" >&2; exit 1; }

mkdir -p "$HOOK_DIR"
cp "$SRC"/*.py "$HOOK_DIR"/

if [ -f "$SETTINGS" ]; then
  cp "$SETTINGS" "$SETTINGS.bak"
fi

python3 - "$SETTINGS" "$HOOK_DIR" <<'PY'
import json, os, sys

settings_path, hook_dir = os.path.realpath(sys.argv[1]), sys.argv[2]  # realpath: keep dotfile symlinks intact
settings = {}
if os.path.exists(settings_path):
    with open(settings_path) as f:
        text = f.read().strip()
    try:
        settings = json.loads(text) if text else {}
    except ValueError as e:
        sys.exit("cc-guardrails: %s is not valid JSON (%s); not touching it." % (settings_path, e))

pre = settings.setdefault("hooks", {}).setdefault("PreToolUse", [])

# Drop any previous cc-guardrails entries so re-installs update instead of duplicating.
ours = lambda h: "/hooks/cc-guardrails/" in h.get("command", "")
for entry in pre:
    if any(ours(h) for h in entry.get("hooks", [])):
        entry["hooks"] = [h for h in entry["hooks"] if not ours(h)]
        entry["_cc_guardrails_emptied"] = not entry["hooks"]
pre[:] = [e for e in pre if not e.pop("_cc_guardrails_emptied", False)]

pre.append({
    "matcher": "Bash",
    "hooks": [
        {"type": "command", "command": 'python3 "%s/%s"' % (hook_dir, name)}
        for name in ("rm_guard.py", "secret_guard.py", "force_push_guard.py")
    ],
})

tmp = settings_path + ".tmp"
with open(tmp, "w") as f:
    json.dump(settings, f, indent=2)
    f.write("\n")
os.replace(tmp, settings_path)
PY

echo "cc-guardrails installed:"
echo "  hooks    -> $HOOK_DIR"
echo "  settings -> $SETTINGS (previous version saved as settings.json.bak)"
echo "Restart Claude Code (or run /hooks) to pick them up."
