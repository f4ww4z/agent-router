#!/usr/bin/env python3
"""SessionStart hook: inject the custom-agent roster and routing rules."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_agents  # noqa: E402

agents = load_agents()
rows = "\n".join(f"- {a['name']} (model tier: {a.get("model", "inherit")}): {a.get('description', '')}" for a in agents)
names = ", ".join(a["name"] for a in agents)

context = f"""CUSTOM AGENT ROSTER ({len(agents)} agents, from the agent-router plugin):
{rows}

ROUTING RULES (standing user authorization to spawn these agents):
- Every delegated task MUST go to the most suitable agent above via invoke_subagent with TypeName set to its exact name and Model set to the tier shown above (a hook enforces this).
- Do NOT use the generic `self` subagent when one of these fits. A PreToolUse hook blocks it.
- At the start of your FIRST reply in this session, briefly confirm you know these {len(agents)} agents ({names}), giving each one's model tier, and say that tasks will be routed to the best fit.
- If you are yourself a subagent, ignore these routing rules."""

print(json.dumps({"injectSteps": [{"systemMessage": {"systemMessage": context}}]}))
