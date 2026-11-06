#!/usr/bin/env python3
"""PreToolUse hook on invoke_subagent: force a custom agent and its pinned model."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_agents  # noqa: E402

# Built-ins that serve a purpose no custom agent covers.
ALLOWED_BUILTINS = {"research", "image-generator", "browser"}

tiers = {a["name"]: a.get("model", "inherit").strip("\"'") for a in load_agents()}
custom = list(tiers)

try:
    data = json.load(sys.stdin)
except Exception:
    print("{}")
    sys.exit(0)

args = (data.get("toolCall") or {}).get("args") or {}
if isinstance(args, str):
    try:
        args = json.loads(args)
    except Exception:
        args = {}
name = args.get("TypeName") or ""

if name in custom:
    want = tiers[name] or "inherit"
    if (args.get("Model") or "inherit") != want:
        # Pin the call to the tier declared in the agent's frontmatter.
        print(json.dumps({"decision": "ask", "overwrite": {"Model": want}}))
    else:
        print(json.dumps({"decision": "ask"}))
elif name in ALLOWED_BUILTINS:
    print(json.dumps({"decision": "ask"}))
else:
    print(json.dumps({
        "decision": "deny",
        "reason": f"subagent '{name or '(none)'}' is not allowed. Use the most suitable custom agent: "
                  + ", ".join(custom) + ". Each is pinned to its own model tier.",
    }))
