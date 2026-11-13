"""Shared helpers for the agent-router hooks (agy and Claude Code).

The same scripts run on both platforms. The platform comes from `--platform
agy|claude` on the command line; if that is missing it is guessed from the hook
payload (Claude Code payloads carry `hook_event_name`).
"""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(HERE)


def read_payload():
    """Parse the hook's stdin JSON; return {} if it is missing or invalid."""
    try:
        raw = sys.stdin.read() if not sys.stdin.isatty() else ""
        data = json.loads(raw) if raw.strip() else {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def detect_platform(payload):
    args = sys.argv[1:]
    if "--platform" in args:
        i = args.index("--platform")
        if i + 1 < len(args) and args[i + 1] in ("agy", "claude"):
            return args[i + 1]
    if "hook_event_name" in payload or "tool_input" in payload or os.environ.get("CLAUDE_PROJECT_DIR"):
        return "claude"
    return "agy"


def agent_dirs(platform):
    """Where each platform's agents live, in increasing priority."""
    if platform == "claude":
        dirs = [os.path.join(os.path.expanduser("~"), ".claude", "agents")]
        project = os.environ.get("CLAUDE_PROJECT_DIR")
        if project:
            dirs.append(os.path.join(project, ".claude", "agents"))
        return dirs
    return [os.path.join(PLUGIN_ROOT, "agents")]


def parse_frontmatter(text):
    m = re.match(r"^﻿?---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(\r?\n|$)", text, re.S)
    if not m:
        return {}
    fields = {}
    for line in m.group(1).splitlines():
        if ":" not in line or line.startswith((" ", "\t", "-", "#")):
            continue
        k, v = line.split(":", 1)
        v = re.sub(r"\s+#.*$", "", v.strip())  # trailing comment
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        fields[k.strip()] = v
    return fields


def load_agents(platform):
    """Return {name: frontmatter} for every agent visible on this platform."""
    agents = {}
    for d in agent_dirs(platform):
        paths = glob.glob(os.path.join(d, "*.md")) + glob.glob(os.path.join(d, "*", "agent.md"))
        for path in sorted(paths):
            try:
                with open(path, encoding="utf-8") as f:
                    fields = parse_frontmatter(f.read())
            except OSError:
                continue
            if fields.get("name"):
                agents[fields["name"]] = fields
    return agents


def emit(obj):
    print(json.dumps(obj))
    sys.exit(0)
