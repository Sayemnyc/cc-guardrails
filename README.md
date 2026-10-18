# cc-guardrails

Three [Claude Code](https://claude.com/claude-code) `PreToolUse` hooks that stop the agent before it does something you can't undo:

| Hook | Blocks |
|---|---|
| `rm_guard.py` | Recursive `rm` (`-r`, `-rf`, `-R`, `--recursive`) on any path outside the project folder, or on the project folder itself |
| `secret_guard.py` | `git add` / `git commit` of `.env` files, or of files containing API keys (AWS, Anthropic, OpenAI, GitHub, Slack, Google, Stripe live keys, private keys, and `api_key = "..."` style assignments) |
| `force_push_guard.py` | `git push --force` / `-f` / `--force-with-lease` / `+refspec` to `main` (or `master`) |

When a hook blocks a command, Claude sees the reason and picks another approach. Nothing else changes. Pure Python 3 stdlib, no dependencies.

## 30-second install

```bash
git clone https://github.com/Sayemnyc/cc-guardrails.git && cd cc-guardrails && ./install.sh
```

Then restart Claude Code. That's it.

`install.sh`:
- copies the hooks to `~/.claude/hooks/cc-guardrails/`
- **merges** one `PreToolUse` entry into `~/.claude/settings.json`. Your other settings and hooks are left untouched, and a backup is saved to `settings.json.bak`
- is safe to re-run (it updates its own entry rather than adding a duplicate)
- refuses to touch a `settings.json` that isn't valid JSON
- respects `CLAUDE_CONFIG_DIR` if you've set it

Requires `python3` on your `PATH`.

## What gets blocked

```text
rm -rf ~                         blocked   (outside project)
rm -rf ../other-repo             blocked
cd / && rm -rf usr               blocked   (follows cd)
rm -rf $SOME_VAR/x               blocked   (can't verify unknown variables)
rm -rf node_modules dist         allowed
rm -rf build/*                   allowed

git add .            (with an untracked .env)   blocked
git add config.py    (contains an AWS key)      blocked
git commit -am "x"   (tracked file gained key)  blocked
git add .env.example                            allowed
git add .            (.env is in .gitignore)    allowed

git push -f origin main                         blocked
git push origin +HEAD:main                      blocked
git push --force        (while on main)         blocked
git push --force origin my-feature              allowed
```

"Project folder" is `$CLAUDE_PROJECT_DIR` (set by Claude Code for hooks), falling back to the session's cwd.

## Run the tests

```bash
python3 -m unittest discover -s tests -v
```

## Uninstall

Delete `~/.claude/hooks/cc-guardrails/` and remove the `PreToolUse` entry whose commands point there from `~/.claude/settings.json` (or restore `settings.json.bak`).

## Limits

These are guardrails against slips, not a sandbox. Commands are tokenized, not executed, so the hooks don't look inside `bash -c "..."`, `eval`, `xargs`, `find -delete`, or scripts the agent writes and then runs. Secret detection is pattern-based and won't catch every key format. For hard isolation, run Claude Code in a container or VM.

## License

MIT
