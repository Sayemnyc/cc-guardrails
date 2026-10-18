"""Shared helpers for cc-guardrails PreToolUse hooks (Python 3 stdlib only)."""
import json
import os
import shlex
import subprocess
import sys

WRAPPERS = {"sudo", "env", "command", "exec", "nohup", "time", "nice"}


def read_input():
    """Return (command, cwd) for a Bash tool call, or exit 0 (allow) for anything else."""
    try:
        data = json.load(sys.stdin)
    except ValueError:
        sys.exit(0)
    if data.get("tool_name") != "Bash":
        sys.exit(0)
    command = (data.get("tool_input") or {}).get("command") or ""
    return command, data.get("cwd") or os.getcwd()


def block(reason):
    """Exit code 2 = deny the tool call; stderr is shown to Claude."""
    print("cc-guardrails: " + reason, file=sys.stderr)
    sys.exit(2)


def _is_separator(tok):
    return tok and all(c in ";&|()" for c in tok)


def _is_redirect(tok):
    return tok and all(c in "<>&" for c in tok) and ("<" in tok or ">" in tok)


def commands(command, cwd):
    """Yield (argv, cwd) per simple command, following `cd` so later commands get the right cwd.

    ponytail: a tokenizer, not a shell. `bash -c`, `eval`, `xargs`, `find -delete` and
    scripts are not looked into. These hooks catch slips; they are not a sandbox.
    """
    lex = shlex.shlex(command.replace("\n", " ; "), posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    try:
        tokens = list(lex)
    except ValueError:  # unbalanced quotes: bash would reject it too
        return

    argv, skip_next = [], False
    for tok in tokens + [";"]:
        if skip_next:
            skip_next = False
        elif _is_redirect(tok):
            skip_next = True  # drop the redirect target, e.g. `> /dev/null`
        elif _is_separator(tok):
            argv = _strip_wrappers(argv)
            if argv:
                if argv[0] in ("cd", "pushd"):
                    target = argv[1] if len(argv) > 1 else "~"
                    cwd = os.path.normpath(os.path.join(cwd, os.path.expanduser(target)))
                else:
                    yield argv, cwd
            argv = []
        else:
            argv.append(tok)


def _strip_wrappers(argv):
    while argv and (os.path.basename(argv[0]) in WRAPPERS or ("=" in argv[0] and not argv[0].startswith("-"))):
        argv = argv[1:]
        while argv and argv[0].startswith("-"):  # wrapper flags like `sudo -E`
            argv = argv[1:]
    return argv


def git_call(argv, cwd):
    """For `git [global opts] <sub> args...` return (sub, args, cwd); otherwise None."""
    if not argv or os.path.basename(argv[0]) != "git":
        return None
    i = 1
    while i < len(argv) and argv[i].startswith("-"):
        if argv[i] in ("-C", "-c", "--git-dir", "--work-tree", "--namespace") and i + 1 < len(argv):
            if argv[i] == "-C":
                cwd = os.path.join(cwd, os.path.expanduser(argv[i + 1]))
            i += 2
        else:
            i += 1
    if i >= len(argv):
        return None
    return argv[i], argv[i + 1:], cwd


def git(cwd, *args, raw=False):
    """Run git and return stdout ('' / b'' on failure)."""
    try:
        r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        r = None
    out = r.stdout if r is not None and r.returncode == 0 else b""
    return out if raw else out.decode("utf-8", "replace")
