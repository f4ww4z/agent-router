# agent-router

Task-based subagent routing with lifecycle hooks for **Google Antigravity (`agy`)** and **Claude Code**.

Defines **6 specialized subagents**—each pinned to its own model tier and toolset—along with an always-on routing rule and two lifecycle hooks (`SessionStart` + `PreToolUse`) that automatically route delegated tasks and block generic fallback subagents.

## Subagent Roster

| Agent | Role | `agy` Model Tier | Claude Code (`model` / `effort`) | Access |
| :--- | :--- | :--- | :--- | :--- |
| `explore` | Fast codebase search & file discovery | `flash` (Gemini 3.8 Flash) | `haiku` / `low` | Read-only |
| `test-runner` | Run test suites, typecheck, or lint; report only failures | `flash` (Gemini 3.8 Flash) | `haiku` / `low` | Read + shell |
| `implementer` | Well-scoped features, refactors & tests from a clear spec | `inherit` (session model) | `sonnet` / `medium` | Full read/write |
| `reviewer` | Pre-PR diff review against `SPEC.md` | `inherit` (session model) | `sonnet` / `high` | Read-only |
| `debugger` | Root-cause analysis & regression tests for non-obvious bugs | `pro` (Gemini 4 Argon) | `opus` / `high` | Full read/write |
| `architect` | Design decisions, migration plans & trade-off analysis | `pro` (Gemini 4 Argon) | `opus` / `high` | Read + web search |

## How It Works

1. **Always-On Rule (`rules/AGENTS.md` / `CLAUDE.md`)**: Grants standing authorization to delegate tasks to the 6 subagents and specifies which task category maps to which agent.
2. **`SessionStart` Hook (`hooks/agent-roster.py`)**: Scans the agent frontmatter files at session start and injects the live agent roster + routing instructions into the system prompt.
3. **`PreToolUse` Hook (`hooks/enforce-agent.py`)**: Intercepts `invoke_subagent` (in `agy`) or `Agent`/`Task` (in Claude Code):
   - Denies generic subagents (`self` in `agy`; `general-purpose`/`claude` in Claude Code) when a specialized agent fits.
   - Allows built-in utility subagents (`research`, `image-generator`, `browser` in `agy`).
   - In `agy`, automatically overwrites the `Model` argument on `invoke_subagent` so each custom agent always runs on the tier declared in its frontmatter.

## Install in Antigravity (`agy`)

Clone directly into your global Antigravity plugins directory:

```bash
mkdir -p ~/.gemini/config/plugins
git clone https://github.com/f4ww4z/agent-router.git ~/.gemini/config/plugins/agent-router
```

Or install from a local checkout:

```bash
agy plugin install ./agent-router
```

Verify installation:

```bash
agy plugin list
agy plugin validate ~/.gemini/config/plugins/agent-router --strict
```

## Install in Claude Code

Copy the files under [`claude/`](./claude) into `~/.claude/`:

```bash
cp claude/CLAUDE.md ~/.claude/CLAUDE.md
cp -r claude/agents claude/hooks ~/.claude/
```

Then add the `SessionStart` and `PreToolUse` hook entries to `~/.claude/settings.json`.
