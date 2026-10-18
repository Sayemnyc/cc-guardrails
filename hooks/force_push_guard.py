#!/usr/bin/env python3
"""Block force pushes (--force, -f, --force-with-lease, +refspec) to main/master."""
from _common import block, commands, git, git_call, read_input

PROTECTED = {"main", "master"}
TAKES_VALUE = {"-o", "--push-option", "--repo", "--receive-pack", "--exec"}


def check(args, cwd):
    """Return a reason string if this `git push` force-pushes a protected branch."""
    force = every_ref = False
    positional = []
    i = 0
    while i < len(args):
        a = args[i]
        if a in TAKES_VALUE:
            i += 1
        elif a == "--force" or a.startswith("--force-with-lease") or (
                a.startswith("-") and not a.startswith("--") and "f" in a):
            force = True
        elif a in ("--all", "--mirror", "--branches"):
            every_ref = True
        elif not a.startswith("-"):
            positional.append(a)
        i += 1

    if force and every_ref:
        return "force push of all branches includes main"

    current = git(cwd, "rev-parse", "--abbrev-ref", "HEAD").strip()
    refspecs = positional[1:] or ["HEAD"]  # no refspec: pushes the current branch
    for spec in refspecs:
        plus = spec.startswith("+")
        dst = spec.lstrip("+").split(":")[-1] or "HEAD"
        if dst == "HEAD":
            dst = current
        if dst.startswith("refs/heads/"):
            dst = dst[len("refs/heads/"):]
        if (force or plus) and dst in PROTECTED:
            return "force push to `%s`" % dst
    return None


def main():
    command, cwd = read_input()
    for argv, cur in commands(command, cwd):
        call = git_call(argv, cur)
        if call and call[0] == "push":
            reason = check(call[1], call[2])
            if reason:
                block("blocked %s. Rewriting shared history must be done by a human; "
                      "push to a branch and open a PR instead." % reason)


if __name__ == "__main__":
    main()
