#!/usr/bin/env python3
"""Generate every per-platform file from agents.toml.

    python3 scripts/build.py          # write generated files
    python3 scripts/build.py --check  # exit 1 if any generated file is stale
"""
import json
import os
import re
import sys
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEADER = "<!-- Generated from agents.toml by scripts/build.py. Do not edit by hand. -->"
TIER_LABELS = {"flash": "Gemini 3.8 Flash", "pro": "Gemini 4 Argon", "inherit": "session model"}
README_START, README_END = "<!-- roster:start -->", "<!-- roster:end -->"


def load():
    with open(os.path.join(ROOT, "agents.toml"), "rb") as f:
        data = tomllib.load(f)
    for key, a in data.items():
        for field in ("when", "description", "prompt", "access", "agy", "claude"):
            if field not in a:
                sys.exit(f"agents.toml: [{key}] is missing '{field}'")
    return data


def yaml_scalar(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    # Quote only when plain YAML would misread the value.
    if s == "" or re.search(r"(^[\s\-?:,\[\]{}#&*!|>'\"%@`])|(: )|( #)|(\s$)", s):
        return json.dumps(s)
    return s


def frontmatter(fields):
    lines = ["---"]
    for k, v in fields.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            lines += [f"    - {yaml_scalar(i)}" for i in v]
        else:
            lines.append(f"{k}: {yaml_scalar(v)}")
    lines.append("---")
    return "\n".join(lines)


def platform_fields(key, a, platform):
    p = dict(a[platform])
    name = p.pop("name", key)
    desc = p.pop("description", a["description"])
    return {"name": name, "description": desc, **p}


def agy_agent(key, a):
    return f"{frontmatter(platform_fields(key, a, 'agy'))}\n\n# Agent System Instructions\n\n{a['prompt']}\n"


def claude_agent(key, a):
    return f"{frontmatter(platform_fields(key, a, 'claude'))}\n{a['prompt']}\n"


def agy_rule(agents):
    tiers = {}
    for key, a in agents.items():
        tiers.setdefault(a["agy"]["model"], []).append(platform_fields(key, a, "agy")["name"])
    tier_text = ", ".join(f"{'/'.join(n)} → {t}" for t, n in tiers.items())
    lines = [
        HEADER,
        "## Delegation",
        "Standing authorization: delegate work to my custom subagents with `invoke_subagent`. Pick the best fit by "
        f"`TypeName`, and set `Model` to that agent's tier (a hook enforces this): {tier_text}.",
    ]
    lines += [f"- {a['when']} → `{platform_fields(k, a, 'agy')['name']}`" for k, a in agents.items()]
    lines.append(
        "Only handle work inline if it is trivial, and say which agent you would otherwise have used. When you "
        "delegate, say which agent you picked and why, in one line. Do not use `self` when one of these fits. "
        "If you are yourself a subagent, ignore this section."
    )
    return "\n".join(lines) + "\n"


def claude_rule(agents):
    lines = [
        HEADER,
        "## Delegation",
        "Standing authorization: spawn these custom agents (~/.claude/agents/) for delegated work. Every delegated "
        "task MUST use the most suitable one via `subagent_type`, because each agent is pinned to its own model and "
        "effort. Never use general-purpose/claude when one of these fits.",
    ]
    for k, a in agents.items():
        f = platform_fields(k, a, "claude")
        lines.append(f"- {a['when']} → `{f['name']}` ({f.get('model', 'inherit')}, {f.get('effort', 'default')})")
    return "\n".join(lines) + "\n"


def readme(agents):
    path = os.path.join(ROOT, "README.md")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    rows = [
        "| Agent | Role | `agy` Model Tier | Claude Code (`model` / `effort`) | Access |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]
    for k, a in agents.items():
        tier = a["agy"]["model"]
        c = platform_fields(k, a, "claude")
        rows.append(
            f"| `{k}` | {a['when']} | `{tier}` ({TIER_LABELS.get(tier, tier)}) | "
            f"`{c.get('model', 'inherit')}` / `{c.get('effort', 'default')}` | {a['access']} |"
        )
    block = f"{README_START}\n" + "\n".join(rows) + f"\n{README_END}"
    if README_START not in text:
        sys.exit("README.md is missing the roster markers")
    return re.sub(re.escape(README_START) + r".*?" + re.escape(README_END), lambda _: block, text, flags=re.S)


def outputs():
    agents = load()
    out = {}
    for k, a in agents.items():
        out[f"agents/{k}.md"] = agy_agent(k, a)
        out[f"claude/agents/{k}.md"] = claude_agent(k, a)
    out["rules/AGENTS.md"] = agy_rule(agents)
    out["claude/CLAUDE.md"] = claude_rule(agents)
    out["README.md"] = readme(agents)
    return out


def main():
    check = "--check" in sys.argv[1:]
    stale = []
    expected = outputs()
    # Agent files that no longer exist in agents.toml are stale too.
    for d in ("agents", "claude/agents"):
        for name in os.listdir(os.path.join(ROOT, d)):
            rel = f"{d}/{name}"
            if name.endswith(".md") and rel not in expected:
                stale.append(rel)
                if not check:
                    os.remove(os.path.join(ROOT, rel))
    for rel, content in expected.items():
        path = os.path.join(ROOT, rel)
        try:
            with open(path, encoding="utf-8") as f:
                current = f.read()
        except FileNotFoundError:
            current = None
        if current != content:
            stale.append(rel)
            if not check:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
    if check and stale:
        print("Stale generated files (run scripts/build.py):\n  " + "\n  ".join(stale))
        sys.exit(1)
    print(("Updated: " + ", ".join(stale)) if stale else "Everything up to date.")


if __name__ == "__main__":
    main()
