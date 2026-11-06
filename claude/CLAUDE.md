## Delegation
Standing authorization: spawn these custom agents (~/.claude/agents/) for delegated work. Every delegated task MUST use the most suitable one via `subagent_type`, because each agent is pinned to its own model and effort. Never use general-purpose/claude when one of these fits.
- Searches / file discovery → `Explore` (haiku, low)
- Tests, typecheck, lint runs → `test-runner` (haiku, low)
- Clearly specified implementation → `implementer` (sonnet, medium)
- Before opening a PR → `reviewer` against SPEC.md (sonnet, high)
- Non-obvious bugs → `debugger` (opus, high)
- Design questions → `architect` (opus, high)
