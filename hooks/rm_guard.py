#!/usr/bin/env python3
"""Block recursive `rm` (-r/-rf/-R/--recursive) on anything outside the project folder."""
import os

from _common import block, commands, read_input

GLOB_CHARS = "*?["


def is_recursive(args):
    for a in args:
        if a == "--":
            break
        if a == "--recursive" or (a.startswith("-") and not a.startswith("--") and ("r" in a or "R" in a)):
            return True
    return False


def targets(args):
    out, opts_done = [], False
    for a in args:
        if a == "--" and not opts_done:
            opts_done = True
        elif opts_done or not a.startswith("-"):
            out.append(a)
    return out


def resolve(path, cwd):
    # Resolve the parent's symlinks but not the last component: `rm -rf link` removes the link only.
    full = os.path.normpath(os.path.join(cwd, path))
    return os.path.join(os.path.realpath(os.path.dirname(full)), os.path.basename(full)).rstrip("/") or "/"


def inside(path, root, allow_root):
    return path.startswith(root + os.sep) or (allow_root and path == root)


def check(target, cwd, root):
    """Return a reason string if deleting `target` is not allowed."""
    expanded = os.path.expandvars(os.path.expanduser(target))
    if "$" in expanded or "`" in expanded:
        return "cannot verify `%s` (unexpanded variable or command substitution)" % target
    glob_at = min([expanded.find(c) for c in GLOB_CHARS if c in expanded] or [-1])
    if glob_at == -1:
        path = resolve(expanded, cwd)
        ok = inside(path, root, allow_root=False)
    else:
        # `dir/*` deletes children of dir; `dir/foo*` deletes siblings in dir. Check that dir.
        prefix = expanded[:glob_at]
        base = prefix if prefix in ("", ".") or prefix.endswith("/") else os.path.dirname(prefix)
        path = resolve(base or ".", cwd)
        ok = inside(path, root, allow_root=True)
    if not ok:
        return "`%s` resolves to %s, which is outside the project folder %s" % (target, path, root)
    return None


def main():
    command, cwd = read_input()
    root = os.path.realpath(os.environ.get("CLAUDE_PROJECT_DIR") or cwd)
    for argv, cur in commands(command, cwd):
        if os.path.basename(argv[0]) != "rm" or not is_recursive(argv[1:]):
            continue
        for t in targets(argv[1:]):
            reason = check(t, cur, root)
            if reason:
                block("blocked recursive rm: %s. Delete it yourself if you really mean it." % reason)


if __name__ == "__main__":
    main()
