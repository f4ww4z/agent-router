# agent-router

Task-based subagent routing with lifecycle hooks for **Google Antigravity (`agy`)** and **Claude Code**.

Defines **6 specialized subagents**—each pinned to its own model tier and toolset—along with an always-on routing rule and two lifecycle hooks (`SessionStart` + `PreToolUse`) that automatically route delegated tasks and block generic fallback subagents.

## Subagent Roster

<!-- roster:start -->
| Agent | Role | `agy` Model Tier | Claude Code (`model` / `effort`) | Access |
| :--- | :--- | :--- | :--- | :--- |
| `explore` | Searches / file discovery | `flash` (Gemini 3.8 Flash) | `haiku` / `low` | Read-only |
| `test-runner` | Tests, typecheck, lint runs | `flash` (Gemini 3.8 Flash) | `haiku` / `low` | Read + shell |
| `implementer` | Clearly specified implementation | `inherit` (session model) | `sonnet` / `medium` | Full read/write |
| `reviewer` | Before opening a PR (review against SPEC.md) | `inherit` (session model) | `sonnet` / `high` | Read-only |
| `debugger` | Non-obvious bugs | `pro` (Gemini 4 Argon) | `opus` / `medium` | Full read/write |
| `architect` | Design / trade-off questions | `pro` (Gemini 4 Argon) | `opus` / `high` | Read + web search |
<!-- roster:end -->

## How It Works

Everything is generated from one file, [`agents.toml`](./agents.toml), so the two platforms can't drift apart. The same hook scripts in [`hooks/`](./hooks) run on both, and each is told its platform with `--platform agy|claude`.

1. **Always-On Rule (`rules/AGENTS.md` / `CLAUDE.md`)**: Grants standing authorization to delegate tasks to the 6 subagents and specifies which task category maps to which agent.
2. **`SessionStart` Hook (`hooks/agent-roster.py`)**: Scans the agent frontmatter files at session start and injects the live agent roster + routing instructions into the system prompt.
3. **`PreToolUse` Hook (`hooks/enforce-agent.py`)**: Intercepts `invoke_subagent` (in `agy`) or `Agent`/`Task` (in Claude Code):
   - Denies generic subagents (`self` in `agy`; `general-purpose`/`claude` in Claude Code) when a specialized agent fits.
   - Allows built-in utility subagents (`research`, `image-generator`, `browser` in `agy`).
   - In `agy`, automatically overwrites the `Model` argument on `invoke_subagent` so each custom agent always runs on the tier declared in its frontmatter.
   - Fails open: if the payload or the agent files can't be read, the call goes through instead of blocking your work.

## Install

```bash
git clone https://github.com/f4ww4z/agent-router.git && cd agent-router
python3 scripts/install.py claude   # Claude Code
python3 scripts/install.py agy      # Antigravity
python3 scripts/install.py all      # both
```

Add `--dry-run` to preview the changes. Re-running is safe.

**Claude Code** (`install.py claude`):
- Copies agents into `~/.claude/agents/`. If you already have an agent file with different contents, it's kept unless you pass `--force`; replaced files are saved as `*.md.bak`.
- Copies hooks into `~/.claude/hooks/agent-router/`.
- Merges the `SessionStart` and `PreToolUse` hook entries into `~/.claude/settings.json` without touching your other settings, and writes `settings.json.bak` first.
- Puts the routing rule in a marked block in `~/.claude/CLAUDE.md`. The rest of the file is left alone.
- `python3 scripts/install.py claude --uninstall` removes the hooks and the rule.

**Antigravity** (`install.py agy`): runs `agy plugin install` when `agy` is on your PATH. Otherwise it symlinks this checkout to `~/.gemini/config/plugins/agent-router`. To verify:

```bash
agy plugin list
agy plugin validate ~/.gemini/config/plugins/agent-router --strict
```

## Changing an agent

Edit [`agents.toml`](./agents.toml), then regenerate and re-install:

```bash
python3 scripts/build.py            # rewrites agents/, claude/agents/, rules/AGENTS.md, claude/CLAUDE.md and the table above
python3 -m unittest discover tests  # hook + build tests
python3 scripts/install.py all
```

`python3 scripts/build.py --check` exits non-zero when a generated file is out of date. Building needs Python 3.11+; the hooks and installer run on 3.8+.
