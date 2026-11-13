<!-- Generated from agents.toml by scripts/build.py. Do not edit by hand. -->
## Delegation
Standing authorization: delegate work to my custom subagents with `invoke_subagent`. Pick the best fit by `TypeName`, and set `Model` to that agent's tier (a hook enforces this): explore/test-runner → flash, implementer/reviewer → inherit, debugger/architect → pro.
- Searches / file discovery → `explore`
- Tests, typecheck, lint runs → `test-runner`
- Clearly specified implementation → `implementer`
- Before opening a PR (review against SPEC.md) → `reviewer`
- Non-obvious bugs → `debugger`
- Design / trade-off questions → `architect`
Only handle work inline if it is trivial, and say which agent you would otherwise have used. When you delegate, say which agent you picked and why, in one line. Do not use `self` when one of these fits. If you are yourself a subagent, ignore this section.
