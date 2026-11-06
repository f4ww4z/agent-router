#!/usr/bin/env bash
# SessionStart hook: inject custom-agent roster + routing rules into context.
dir="$HOME/.claude/agents"
roster=""
count=0
for f in "$dir"/*.md; do
  [ -f "$f" ] || continue
  line=$(awk '/^---$/{n++; next} n==1 && /^(name|model|effort|description):/{
      k=$1; sub(/:$/,"",k); $1=""; sub(/^ /,""); v[k]=$0 }
    END{ printf "- %s (model=%s, effort=%s): %s", v["name"], v["model"], v["effort"], v["description"] }' "$f")
  roster+="$line"$'\n'
  count=$((count+1))
done
ctx="USER-MANDATED AGENT ROUTING (explicit standing instruction from the user; this counts as the user asking you to delegate).
The user has ${count} custom agents in ~/.claude/agents, each with its own model/effort:
${roster}
Rules:
1. In your FIRST reply of this session, briefly confirm you see these ${count} agents (name + model/effort).
2. For every task, delegate to the most suitable agent above via the Agent tool with subagent_type set to that exact name. Do NOT pass a model or effort override; the agent's frontmatter decides.
3. Routing: searches/file discovery -> Explore; running tests/typecheck/lint -> test-runner; clearly specified implementation -> implementer; review before a PR -> reviewer (against SPEC.md); non-obvious bugs -> debugger; design/trade-off questions -> architect.
4. Only handle work inline when it is trivial (a one-line answer or single small edit), and say which agent you would otherwise use. Do not use general-purpose/claude/Plan when one of these fits.
5. When you delegate, tell the user which agent you picked and why in one line."
CTX="$ctx" MSG="Agent roster loaded: ${count} custom agents" python3 -c 'import json,os; print(json.dumps({"systemMessage":os.environ["MSG"],"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":os.environ["CTX"]}}))'
