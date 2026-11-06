#!/usr/bin/env python3
"""SessionStart hook: inject the custom-agent roster and routing rules."""
import glob
import json
import os
import re

AGENTS_DIR = os.path.expanduser("~/.claude/agents")


def frontmatter(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    fields = {}
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                fields[k.strip()] = v.strip()
    return fields


agents = []
for path in sorted(glob.glob(os.path.join(AGENTS_DIR, "*.md"))):
    fm = frontmatter(path)
    if fm.get("name"):
        agents.append(fm)

rows = "\n".join(
    f"- {a['name']} (model: {a.get('model', 'inherit')}, effort: {a.get('effort', 'default')}): {a.get('description', '')}"
    for a in agents
)
names = ", ".join(a["name"] for a in agents)

context = f"""CUSTOM AGENT ROSTER ({len(agents)} agents, defined in ~/.claude/agents/):
{rows}

ROUTING RULES (standing user authorization to spawn these agents):
- Every delegated task MUST go to the most suitable agent above via the Agent tool's subagent_type, so it runs on that agent's model and effort.
- Do NOT use general-purpose, claude, or an omitted subagent_type when one of these fits. A PreToolUse hook blocks those calls.
- At the start of your FIRST reply in this session, briefly confirm you know these {len(agents)} agents ({names}), giving each one's model and effort, and say that tasks will be routed to the best fit."""

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": context,
    }
}))
