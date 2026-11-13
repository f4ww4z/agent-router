#!/usr/bin/env python3
"""Install agent-router for Claude Code and/or agy.

    python3 scripts/install.py claude [--force] [--dry-run]
    python3 scripts/install.py agy    [--dry-run]
    python3 scripts/install.py claude --uninstall

Claude Code install is idempotent and non-destructive:
  * agents   -> ~/.claude/agents/*.md (an existing file that differs is kept
                unless --force; the replaced file is saved as *.md.bak)
  * hooks    -> ~/.claude/hooks/agent-router/
  * settings -> hook entries merged into ~/.claude/settings.json (other
                settings and hooks are left alone; a backup is written first)
  * rule     -> a marked block in ~/.claude/CLAUDE.md (the rest of the file is
                left alone; an unmarked `## Delegation` section is replaced)
"""
import argparse
import filecmp
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.path.expanduser("~")
CLAUDE = os.path.join(HOME, ".claude")
HOOK_DIR = os.path.join(CLAUDE, "hooks", "agent-router")
TAG = "agent-router"
START, END = f"<!-- {TAG}:start -->", f"<!-- {TAG}:end -->"
HOOK_FILES = ("common.py", "agent-roster.py", "enforce-agent.py")


class Installer:
    def __init__(self, dry_run):
        self.dry_run = dry_run

    def say(self, msg):
        print(("[dry-run] " if self.dry_run else "") + msg)

    def write(self, path, text):
        self.say(f"write {path}")
        if not self.dry_run:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(text)
            os.replace(tmp, path)

    def copy(self, src, dst):
        self.say(f"copy {os.path.relpath(src, ROOT)} -> {dst}")
        if not self.dry_run:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)


def read(path, default=""):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return default


def hook_cmd(script):
    return f'python3 "{os.path.join(HOOK_DIR, script)}" --platform claude'


def ours(entry):
    return any(TAG in (h.get("command") or "") for h in entry.get("hooks", []))


def load_settings(path):
    text = read(path, "{}")
    try:
        data = json.loads(text) if text.strip() else {}
    except json.JSONDecodeError as e:
        sys.exit(f"{path} is not valid JSON ({e}); fix it and re-run.")
    return data


def merge_hooks(settings, install):
    hooks = settings.setdefault("hooks", {})
    for event in ("SessionStart", "PreToolUse"):
        kept = [e for e in hooks.get(event, []) if not ours(e)]
        if kept:
            hooks[event] = kept
        else:
            hooks.pop(event, None)
    if install:
        hooks.setdefault("SessionStart", []).append(
            {"hooks": [{"type": "command", "command": hook_cmd("agent-roster.py"), "timeout": 10}]})
        hooks.setdefault("PreToolUse", []).append(
            {"matcher": "Agent|Task",
             "hooks": [{"type": "command", "command": hook_cmd("enforce-agent.py"), "timeout": 10}]})
    if not hooks:
        settings.pop("hooks")
    return settings


def merge_rule(text, rule):
    block = f"{START}\n{rule.strip()}\n{END}\n" if rule else ""
    if START in text and END in text:
        return re.sub(re.escape(START) + r".*?" + re.escape(END) + r"\n?", lambda _: block, text, flags=re.S)
    # Replace a hand-pasted (unmarked) Delegation section from an older install.
    m = re.search(r"^## Delegation\n.*?(?=^#{1,2} |\Z)", text, re.S | re.M)
    if m:
        return text[:m.start()] + block + ("\n" if block and text[m.end():] else "") + text[m.end():]
    if not block:
        return text
    return text.rstrip("\n") + ("\n\n" if text.strip() else "") + block


def install_claude(inst, force):
    # Agents
    src_dir = os.path.join(ROOT, "claude", "agents")
    dst_dir = os.path.join(CLAUDE, "agents")
    skipped = []
    for name in sorted(os.listdir(src_dir)):
        src, dst = os.path.join(src_dir, name), os.path.join(dst_dir, name)
        if os.path.exists(dst):
            if filecmp.cmp(src, dst, shallow=False):
                continue
            if not force:
                skipped.append(dst)
                continue
            inst.copy(dst, dst + ".bak")
        inst.copy(src, dst)

    # Hooks
    for name in HOOK_FILES:
        inst.copy(os.path.join(ROOT, "hooks", name), os.path.join(HOOK_DIR, name))

    # settings.json
    path = os.path.join(CLAUDE, "settings.json")
    settings = load_settings(path)
    before = json.dumps(settings, sort_keys=True)
    merge_hooks(settings, install=True)
    if json.dumps(settings, sort_keys=True) != before:
        if os.path.exists(path):
            inst.copy(path, path + ".bak")
        inst.write(path, json.dumps(settings, indent=2) + "\n")

    # CLAUDE.md rule
    path = os.path.join(CLAUDE, "CLAUDE.md")
    rule = read(os.path.join(ROOT, "claude", "CLAUDE.md"))
    rule = "\n".join(l for l in rule.splitlines() if not l.startswith("<!-- Generated"))
    old = read(path)
    new = merge_rule(old, rule)
    if new != old:
        inst.write(path, new)

    if skipped:
        print("\nKept your existing (different) agent files; re-run with --force to replace them (backups are kept):")
        for p in skipped:
            print(f"  {p}")
    print("\nClaude Code: done. Start a new session to load the hooks.")


def uninstall_claude(inst):
    path = os.path.join(CLAUDE, "settings.json")
    if os.path.exists(path):
        settings = load_settings(path)
        before = json.dumps(settings, sort_keys=True)
        merge_hooks(settings, install=False)
        if json.dumps(settings, sort_keys=True) != before:
            inst.write(path, json.dumps(settings, indent=2) + "\n")
    path = os.path.join(CLAUDE, "CLAUDE.md")
    old = read(path)
    new = merge_rule(old, "")
    if new != old:
        inst.write(path, new)
    if os.path.isdir(HOOK_DIR):
        inst.say(f"remove {HOOK_DIR}")
        if not inst.dry_run:
            shutil.rmtree(HOOK_DIR)
    print("\nRemoved hooks and the CLAUDE.md rule. Agent files in ~/.claude/agents were left in place.")


def install_agy(inst):
    if shutil.which("agy"):
        inst.say(f"agy plugin install {ROOT}")
        if not inst.dry_run:
            subprocess.run(["agy", "plugin", "install", ROOT], check=True)
        return
    dst = os.path.join(HOME, ".gemini", "config", "plugins", "agent-router")
    if os.path.realpath(dst) == os.path.realpath(ROOT):
        print(f"agy: already linked at {dst}")
        return
    if os.path.lexists(dst):
        sys.exit(f"{dst} already exists and is not this checkout; remove it first.")
    inst.say(f"symlink {dst} -> {ROOT}")
    if not inst.dry_run:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        os.symlink(ROOT, dst)
    print("agy: done (agy not found on PATH, so the plugin was linked into ~/.gemini/config/plugins).")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("platform", choices=["claude", "agy", "all"])
    p.add_argument("--force", action="store_true", help="replace agent files that differ (backups kept)")
    p.add_argument("--dry-run", action="store_true", help="show what would change")
    p.add_argument("--uninstall", action="store_true", help="Claude Code only: remove hooks and rule")
    a = p.parse_args()
    if sys.version_info < (3, 8):
        sys.exit("Python 3.8+ is required.")
    inst = Installer(a.dry_run)
    if a.platform in ("claude", "all"):
        uninstall_claude(inst) if a.uninstall else install_claude(inst, a.force)
    if a.platform in ("agy", "all") and not a.uninstall:
        install_agy(inst)


if __name__ == "__main__":
    main()
