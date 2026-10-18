import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = os.path.join(ROOT, "hooks")


def run_hook(hook, command, cwd, project_dir=None):
    """Feed a PreToolUse payload to a hook; return (exit_code, stderr)."""
    env = dict(os.environ)
    env.pop("CLAUDE_PROJECT_DIR", None)
    if project_dir:
        env["CLAUDE_PROJECT_DIR"] = project_dir
    payload = {"hook_event_name": "PreToolUse", "tool_name": "Bash",
               "tool_input": {"command": command}, "cwd": cwd}
    r = subprocess.run([sys.executable, os.path.join(HOOKS, hook)], input=json.dumps(payload),
                       capture_output=True, text=True, cwd=cwd, env=env)
    return r.returncode, r.stderr


def git_repo():
    """A fresh temp git repo with one commit on `main`."""
    d = os.path.realpath(tempfile.mkdtemp())
    for args in (["init", "-q", "-b", "main"], ["config", "user.email", "t@t"], ["config", "user.name", "t"],
                 ["commit", "-q", "--allow-empty", "-m", "init"]):
        subprocess.run(["git", *args], cwd=d, check=True)
    return d


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)
