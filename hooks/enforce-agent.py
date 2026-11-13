#!/usr/bin/env python3
"""PreToolUse hook: route subagent calls to a custom agent.

agy:         on invoke_subagent, deny `self`/unknown types and pin `Model` to
             the tier in the agent's frontmatter.
Claude Code: on Agent/Task, deny general-purpose/claude/omitted subagent_type.

Fails open: if the payload or the agent files can't be read, the call is
allowed, so a broken install never blocks your work.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import detect_platform, emit, load_agents, read_payload  # noqa: E402

# Built-ins that serve a purpose no custom agent covers.
ALLOWED_BUILTINS = {
    "agy": {"research", "image-generator", "browser"},
    "claude": {"Plan", "statusline-setup", "web-fetch", "fork", "claude-code-guide", "Explore"},
}


def match(name, agents):
    """Exact name, else case-insensitive, ignoring a `plugin:` namespace."""
    if name in agents:
        return name
    bare = name.split(":")[-1].lower()
    return next((n for n in agents if n.lower() == bare), None)


def allowed(name, platform):
    builtins = {b.lower() for b in ALLOWED_BUILTINS[platform]}
    return name.split(":")[-1].lower() in builtins


def claude(payload, agents):
    if payload.get("tool_name") not in (None, "Agent", "Task"):
        emit({})
    name = (payload.get("tool_input") or {}).get("subagent_type") or ""
    if (name and match(name, agents)) or (name and allowed(name, "claude")):
        emit({})
    emit({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            f"subagent_type '{name or '(none)'}' is not allowed. Pick the most suitable custom agent: "
            + ", ".join(agents) + ". Each has its own model and effort."),
    }})


def agy(payload, agents):
    args = (payload.get("toolCall") or {}).get("args") or {}
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except Exception:
            args = {}
    name = args.get("TypeName") or ""
    hit = match(name, agents) if name else None
    if hit:
        want = agents[hit].get("model") or "inherit"
        overwrite = {}
        if (args.get("Model") or "inherit") != want:
            overwrite["Model"] = want  # pin to the tier in the frontmatter
        if hit != name:
            overwrite["TypeName"] = hit  # normalise case / namespace
        emit({"decision": "ask", **({"overwrite": overwrite} if overwrite else {})})
    if name and allowed(name, "agy"):
        emit({"decision": "ask"})
    emit({"decision": "deny", "reason": (
        f"subagent '{name or '(none)'}' is not allowed. Use the most suitable custom agent: "
        + ", ".join(agents) + ". Each is pinned to its own model tier.")})


def main():
    payload = read_payload()
    platform = detect_platform(payload)
    try:
        agents = load_agents(platform)
    except Exception:
        agents = {}
    if not payload or not agents:
        emit({})  # fail open
    (claude if platform == "claude" else agy)(payload, agents)


if __name__ == "__main__":
    main()
