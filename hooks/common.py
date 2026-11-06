"""Shared helpers: parse agent frontmatter from this plugin's agents/ dir."""
import glob
import os
import re

AGENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agents")


def load_agents():
    agents = []
    paths = glob.glob(os.path.join(AGENTS_DIR, "*.md")) + glob.glob(os.path.join(AGENTS_DIR, "*", "agent.md"))
    for path in sorted(paths):
        with open(path, encoding="utf-8") as f:
            m = re.match(r"^---\s*\n(.*?)\n---", f.read(), re.S)
        if not m:
            continue
        fields = {}
        for line in m.group(1).splitlines():
            if ":" in line and not line.startswith((" ", "\t", "-")):
                k, v = line.split(":", 1)
                fields[k.strip()] = v.strip()
        if fields.get("name"):
            agents.append(fields)
    return agents
