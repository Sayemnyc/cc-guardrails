#!/usr/bin/env python3
"""Block `git add` / `git commit` of .env files or files that contain API keys."""
import os
import re

from _common import block, commands, git, git_call, read_input

ENV_FILE = re.compile(r"^\.env(\..+)?$")
ENV_OK = re.compile(r"\.(example|sample|template|dist)$")
MAX_BYTES = 1024 * 1024

SECRETS = [
    ("AWS access key", r"AKIA[0-9A-Z]{16}"),
    ("Anthropic API key", r"sk-ant-[A-Za-z0-9_\-]{20,}"),
    ("OpenAI API key", r"sk-(proj-)?[A-Za-z0-9]{32,}"),
    ("GitHub token", r"(gh[pousr]_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{22,})"),
    ("Slack token", r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    ("Google API key", r"AIza[0-9A-Za-z_\-]{35}"),
    ("Stripe live key", r"[sr]k_live_[0-9A-Za-z]{20,}"),
    ("private key", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ("hardcoded secret", r"(?i)(api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret)"
                         r"['\"]?\s*[:=]\s*['\"][A-Za-z0-9_\-/+=]{20,}['\"]"),
]
SECRETS = [(name, re.compile(rx)) for name, rx in SECRETS]


def find_secret(data):
    if b"\0" in data[:8000]:  # binary
        return None
    text = data.decode("utf-8", "replace")
    for name, rx in SECRETS:
        if rx.search(text):
            return name
    return None


def files_for_add(args, cwd):
    """Paths (repo-relative) that `git add args` would stage, straight from git's own dry run."""
    args = [a for a in args if a not in ("-p", "--patch", "-i", "--interactive", "-e", "--edit")]
    out = git(cwd, "-c", "core.quotePath=false", "add", "--dry-run", *args)
    return [line[5:-1] for line in out.splitlines() if line.startswith("add '")]


def files_for_commit(args, cwd):
    staged = git(cwd, "diff", "--cached", "--name-only", "--diff-filter=ACMR").splitlines()
    commit_all = any(a == "--all" or (a.startswith("-") and not a.startswith("--") and "a" in a) for a in args)
    if commit_all:
        staged += git(cwd, "diff", "--name-only", "--diff-filter=ACMR").splitlines()
    return staged, commit_all


def read_file(top, path, from_index):
    if from_index:
        return git(top, "show", ":" + path, raw=True)[:MAX_BYTES]
    try:
        with open(os.path.join(top, path), "rb") as f:
            return f.read(MAX_BYTES)
    except OSError:
        return b""


def main():
    command, cwd = read_input()
    problems = []
    for argv, cur in commands(command, cwd):
        call = git_call(argv, cur)
        if not call or call[0] not in ("add", "commit"):
            continue
        sub, args, gcwd = call
        top = git(gcwd, "rev-parse", "--show-toplevel").strip()
        if not top:
            continue
        if sub == "add":
            paths, from_index = files_for_add(args, gcwd), False
        else:
            paths, commit_all = files_for_commit(args, gcwd)
            from_index = not commit_all
        for p in dict.fromkeys(paths):
            name = os.path.basename(p)
            if ENV_FILE.match(name) and not ENV_OK.search(name):
                problems.append("%s (env file)" % p)
                continue
            found = find_secret(read_file(top, p, from_index))
            if found:
                problems.append("%s (looks like it contains a %s)" % (p, found))
    if problems:
        block("refusing to git add/commit secrets:\n  " + "\n  ".join(problems)
              + "\nAdd these to .gitignore or move the secret to an untracked .env file. "
              "Unstage with `git restore --staged <file>`.")


if __name__ == "__main__":
    main()
