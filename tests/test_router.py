"""Tests for the hooks (both platforms), the build and the installer.

Run: python3 -m unittest discover tests
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = os.path.join(ROOT, "hooks")


def slurp(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def run(script, payload, platform=None, home=None, extra_env=None):
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
    if home:
        env["HOME"] = home
    env.update(extra_env or {})
    args = [sys.executable, os.path.join(HOOKS, script)] + (["--platform", platform] if platform else [])
    stdin = payload if isinstance(payload, str) else json.dumps(payload)
    p = subprocess.run(args, input=stdin, capture_output=True, text=True, env=env, timeout=10)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


class ClaudeHome(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        shutil.copytree(os.path.join(ROOT, "claude", "agents"), os.path.join(self.home, ".claude", "agents"))

    def tearDown(self):
        shutil.rmtree(self.home)

    def enforce(self, subagent_type, **kw):
        tool_input = {} if subagent_type is None else {"subagent_type": subagent_type}
        payload = {"hook_event_name": "PreToolUse", "tool_name": "Agent", "tool_input": tool_input}
        return run("enforce-agent.py", payload, home=self.home, **kw)


class TestClaudeEnforce(ClaudeHome):
    def denied(self, out):
        return out.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"

    def test_custom_agent_allowed(self):
        self.assertEqual(self.enforce("debugger", platform="claude"), {})

    def test_platform_autodetected(self):
        self.assertEqual(self.enforce("debugger"), {})
        self.assertTrue(self.denied(self.enforce("general-purpose")))

    def test_generic_denied(self):
        for name in ("general-purpose", "claude", None, ""):
            self.assertTrue(self.denied(self.enforce(name, platform="claude")), name)

    def test_builtins_and_namespaced_allowed(self):
        for name in ("Plan", "fork", "Explore", "agent-router:debugger"):
            self.assertEqual(self.enforce(name, platform="claude"), {}, name)

    def test_project_agents_count(self):
        proj = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(proj, ".claude", "agents"))
            with open(os.path.join(proj, ".claude", "agents", "x.md"), "w") as f:
                f.write("---\r\nname: \"proj-agent\"\r\nmodel: haiku\r\n---\r\nhi\r\n")
            out = self.enforce("proj-agent", platform="claude", extra_env={"CLAUDE_PROJECT_DIR": proj})
            self.assertEqual(out, {})
        finally:
            shutil.rmtree(proj)

    def test_fails_open(self):
        shutil.rmtree(os.path.join(self.home, ".claude", "agents"))
        self.assertEqual(self.enforce("general-purpose", platform="claude"), {})
        self.assertEqual(run("enforce-agent.py", "not json", "claude", self.home), {})

    def test_roster(self):
        out = run("agent-roster.py", {"hook_event_name": "SessionStart"}, home=self.home)
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("debugger (model: opus, effort: medium)", ctx)
        self.assertIn("6 agents", ctx)


class TestAgy(unittest.TestCase):
    def enforce(self, type_name, model=None, as_string=False):
        args = {"TypeName": type_name, **({"Model": model} if model else {})}
        payload = {"toolCall": {"name": "invoke_subagent", "args": json.dumps(args) if as_string else args}}
        return run("enforce-agent.py", payload, "agy")

    def test_model_pinned(self):
        self.assertEqual(self.enforce("debugger", "flash"), {"decision": "ask", "overwrite": {"Model": "pro"}})
        self.assertEqual(self.enforce("debugger", "pro"), {"decision": "ask"})
        self.assertEqual(self.enforce("implementer"), {"decision": "ask"})

    def test_string_args_and_case(self):
        self.assertEqual(self.enforce("Explore", "pro", as_string=True),
                         {"decision": "ask", "overwrite": {"Model": "flash", "TypeName": "explore"}})

    def test_self_denied_builtin_allowed(self):
        self.assertEqual(self.enforce("self")["decision"], "deny")
        self.assertEqual(self.enforce("research"), {"decision": "ask"})

    def test_roster(self):
        out = run("agent-roster.py", {}, "agy")
        ctx = out["injectSteps"][0]["systemMessage"]["systemMessage"]
        self.assertIn("debugger (model tier: pro)", ctx)


class TestBuild(unittest.TestCase):
    def test_generated_files_up_to_date(self):
        p = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "build.py"), "--check"],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_agent_names_match_across_platforms(self):
        sys.path.insert(0, HOOKS)
        from common import parse_frontmatter
        for d in ("agents", os.path.join("claude", "agents")):
            for name in os.listdir(os.path.join(ROOT, d)):
                with open(os.path.join(ROOT, d, name)) as f:
                    fm = parse_frontmatter(f.read())
                self.assertTrue(fm.get("name") and fm.get("model") and fm.get("description"), name)


class TestInstall(ClaudeHome):
    def install(self, *args):
        p = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "install.py"), "claude", *args],
                           capture_output=True, text=True, env={**os.environ, "HOME": self.home})
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return p.stdout

    def path(self, *parts):
        return os.path.join(self.home, ".claude", *parts)

    def test_install_is_idempotent_and_preserves_user_content(self):
        with open(self.path("settings.json"), "w") as f:
            json.dump({"model": "opus", "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": []}]}}, f)
        with open(self.path("CLAUDE.md"), "w") as f:
            f.write("# Mine\nkeep me\n\n## Delegation\nold rule\n\n## Other\nalso keep\n")
        with open(self.path("agents", "debugger.md"), "a") as f:
            f.write("my tweak\n")

        out = self.install()
        self.install()  # second run must not duplicate anything

        settings = json.loads(slurp(self.path("settings.json")))
        self.assertEqual(settings["model"], "opus")
        self.assertEqual(len(settings["hooks"]["PreToolUse"]), 2)
        self.assertEqual(len(settings["hooks"]["SessionStart"]), 1)
        md = slurp(self.path("CLAUDE.md"))
        self.assertIn("keep me", md)
        self.assertIn("also keep", md)
        self.assertNotIn("old rule", md)
        self.assertEqual(md.count("agent-router:start"), 1)
        self.assertIn("my tweak", slurp(self.path("agents", "debugger.md")))
        self.assertIn("--force", out)

        # The installed hook works from its new location.
        cmd = settings["hooks"]["PreToolUse"][1]["hooks"][0]["command"]
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           input=json.dumps({"tool_name": "Agent", "tool_input": {"subagent_type": "claude"}}))
        self.assertIn("deny", p.stdout)

        self.install("--uninstall")
        settings = json.loads(slurp(self.path("settings.json")))
        self.assertEqual(settings["hooks"], {"PreToolUse": [{"matcher": "Bash", "hooks": []}]})
        md = slurp(self.path("CLAUDE.md"))
        self.assertNotIn("agent-router", md)
        self.assertIn("also keep", md)

    def test_force_replaces_with_backup(self):
        with open(self.path("agents", "debugger.md"), "a") as f:
            f.write("my tweak\n")
        self.install("--force")
        self.assertNotIn("my tweak", slurp(self.path("agents", "debugger.md")))
        self.assertIn("my tweak", slurp(self.path("agents", "debugger.md.bak")))


if __name__ == "__main__":
    unittest.main()
