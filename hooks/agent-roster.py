#!/usr/bin/env python3
"""SessionStart hook: inject the custom-agent roster and routing rules.

Works on agy and Claude Code (see common.py). Never fails the session: on any
error it prints an empty result.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import detect_platform, emit, load_agents, read_payload  # noqa: E402


def describe(platform, a):
    if platform == "claude":
        return f"model: {a.get('model', 'inherit')}, effort: {a.get('effort', 'default')}"
    return f"model tier: {a.get('model', 'inherit')}"


def build(platform):
    agents = load_agents(platform)
    if not agents:
        return None
    rows = "\n".join(f"- {n} ({describe(platform, a)}): {a.get('description', '')}" for n, a in agents.items())
    names = ", ".join(agents)
    if platform == "claude":
        how = ("via the Agent tool with subagent_type set to its exact name, so it runs on that agent's model and "
               "effort. Do not pass a model or effort override; the agent's frontmatter decides.")
        generic = "general-purpose, claude, or an omitted subagent_type"
        spec = "model and effort"
    else:
        how = ("via invoke_subagent with TypeName set to its exact name and Model set to the tier shown above "
               "(a hook enforces this).")
        generic = "the generic `self` subagent"
        spec = "model tier"
    return f"""CUSTOM AGENT ROSTER ({len(agents)} agents, from the agent-router plugin):
{rows}

ROUTING RULES (standing user authorization to spawn these agents):
- Every delegated task MUST go to the most suitable agent above {how}
- Do NOT use {generic} when one of these fits. A PreToolUse hook blocks it.
- Only handle work inline when it is trivial, and say which agent you would otherwise have used.
- At the start of your FIRST reply in this session, briefly confirm you know these {len(agents)} agents ({names}), giving each one's {spec}, and say that tasks will be routed to the best fit.
- If you are yourself a subagent, ignore these routing rules."""


def main():
    payload = read_payload()
    platform = detect_platform(payload)
    try:
        context = build(platform)
    except Exception:
        context = None
    if not context:
        emit({})
    if platform == "claude":
        emit({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}})
    emit({"injectSteps": [{"systemMessage": {"systemMessage": context}}]})


if __name__ == "__main__":
    main()
