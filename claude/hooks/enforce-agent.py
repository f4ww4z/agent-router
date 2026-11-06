#!/usr/bin/env python3
"""PreToolUse hook on Agent: deny generic subagents so tasks use a custom agent."""
import glob
import json
import os
import re
import sys

AGENTS_DIR = os.path.expanduser("~/.claude/agents")
# Built-ins that serve a purpose no custom agent covers.
ALLOWED_BUILTINS = {"Plan", "statusline-setup", "web-fetch", "fork"}

custom = []
for path in sorted(glob.glob(os.path.join(AGENTS_DIR, "*.md"))):
    with open(path, encoding="utf-8") as f:
        m = re.search(r"^name:\s*(.+)$", f.read(), re.M)
    if m:
        custom.append(m.group(1).strip())

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

agent = (data.get("tool_input") or {}).get("subagent_type") or ""

if agent in custom or agent in ALLOWED_BUILTINS:
    sys.exit(0)

reason = (
    f"subagent_type '{agent or '(none)'}' is not allowed. Pick the most suitable custom agent: "
    + ", ".join(custom)
    + ". Each has its own model and effort."
)
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }
}))
