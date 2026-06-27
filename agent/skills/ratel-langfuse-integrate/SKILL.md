---
description: "Inspect an agent codebase and write a markdown plan wiring Langfuse tracing/observability (session/trace boundaries, sub-agent handoffs, tool wrapping, naming/tagging vocabulary) plus a Ratel-value/agent-health dashboard build-spec. Use to instrument Langfuse, wire up tracing, set up dashboards, decide where Langfuse goes or what to put on the board, onboard a just-signed partner, or `/ratel-langfuse-integrate`. Writes to <repo>/.ratel/; never edits code or calls the Langfuse API. The Langfuse branch of /ratel-observability-assessment; redirects if the vendor is LangSmith; routes to /ratel-langfuse-analyze once traces flow.\n"
---
# /ratel-langfuse-integrate — wire Langfuse coverage and dashboards for an agent

Mount Langfuse on a customer's codebase the way the Ratel team would, and spec the dashboards that prove it earned its place. One skill, two halves: **instrumentation wiring** (where tracing belongs, what to name it, how to set it up) and the **dashboard build-spec** (which boards to build, with concrete widgets). The plan is the deliverable. Do not edit the agent code, and do not call the Langfuse API — the customer builds dashboards by clicking through the Langfuse UI; that is intentional.

This is the **Langfuse branch** of the observability funnel. The generic [`/ratel-observability-assessment`](../ratel-observability-assessment/SKILL.md) decides *what* to capture and *which* dashboards matter, vendor-neutrally, and detects the vendor. When that vendor is Langfuse, it routes here to render the plan into concrete Langfuse primitives. Its downstream follow-up, once traces are flowing, is [`/ratel-langfuse-analyze`](../ratel-langfuse-analyze/SKILL.md), which reads the live data this plan produces.

## Philosophy: trace the mental model, not the call graph

A common failure mode is "wrap every function in a span." That produces traces that match the code's call graph but tell you nothing about what the agent was *trying to do*. Langfuse traces are most useful when their structure matches the conceptual structure of a turn:

- **Trace** = one externally meaningful unit of work (one chat turn, one job, one webhook). Not "one HTTP request" if a request contains multiple agent turns; not "one model call" if a turn contains many.
- **Observation** = one step the agent took inside that unit. Sub-agent invocations, tool calls, model calls, retrieval steps. Nest them to reflect delegation, not source-file layout.
- **Session** = a thread of related traces sharing a `session_id`. Usually a user conversation, an agent run-id, or a job correlation id.

The full rationale for this lives once in [`../ratel-observability-assessment/references/instrumentation-philosophy.md`](../ratel-observability-assessment/references/instrumentation-philosophy.md). The Langfuse-specific rendering of the vocabulary — which generic concept maps to which Langfuse primitive, type, and key — lives in [`references/langfuse-mapping.md`](references/langfuse-mapping.md).

### Why two groups of dashboards

The dashboard half of this skill always builds two groups, because partner startups want two different stories from the same data:

1. **"Ratel is moving the numbers"** (Ratel-value group) — token spend down, retrieval quality up, fewer "tool not found" errors, lower cost per session. These justify the engagement. Included only if Ratel is present or planned.
2. **"Our agent is healthy"** (agent-health group) — latency percentiles, error rates per tool, abandoned-session rates, score distributions. Useful regardless of Ratel; they build trust because they help the customer's own engineers find their own bugs.

Ratel-only dashboards feel like a sales pitch; agent-health-only dashboards feel like we forgot why we're there. Include both whenever Ratel is in play.

## Workflow

### Step 0 — Read the upstream observability assessment (preferred input)

Look for `<repo>/.ratel/ratel-observability-assessment.md` — the deliverable of [`/ratel-observability-assessment`](../ratel-observability-assessment/SKILL.md). If present, it is the **preferred input**: read its detected stack, topology, vendor-neutral instrumentation strategy, and recommended-dashboard list. Confirm the detected vendor is Langfuse; if it says LangSmith (or another vendor), stop and tell the user this is the Langfuse skill — they want the matching `*-integrate` skill instead.

If the file is present, you can skip the heavy detection in Steps 1–2 and jump to rendering: use its stack and topology directly, then go to Step 3.

If the file is **absent**, do not hard-block. Do your own quick stack + vendor detect (Steps 1–2) and, like a dashboard build needs a vocabulary, ask a few questions rather than refusing:

1. What's the canonical trace name for one chat turn / one job?
2. What `env`, `stack`, and `agent_version` tag values are in use (or planned)?
3. Is Ratel instrumented in any form (gateway, SDK, or planned)?

Proceed with answers in hand. Dashboards built on guessed vocabulary look right but pivot wrong.

### Step 1 — Detect the stack

(Skip if the upstream assessment already names the stack.) Read manifest files to identify language and framework. Branch into the matching reference for stack-specific patterns.

```bash
# TypeScript / Node detection
test -f package.json && cat package.json | jq -r '.dependencies // {}, .devDependencies // {} | keys[]' | sort -u

# Python detection
test -f pyproject.toml && cat pyproject.toml | grep -A 200 '^\[' || true
test -f requirements.txt && cat requirements.txt
test -f uv.lock && head -50 uv.lock
```

Map dependencies to one of these stack profiles:

| Signal in manifest | Stack | Reference |
| --- | --- | --- |
| `ai`, `@ai-sdk/*` | Vercel AI SDK | [`references/stack-vercel-ai-sdk.md`](references/stack-vercel-ai-sdk.md) |
| `@mastra/core`, hand-rolled loops calling `openai` / `@anthropic-ai/sdk` directly | TypeScript generic | [`references/stack-typescript-generic.md`](references/stack-typescript-generic.md) |
| `langfuse` + `openai` / `anthropic` / `langchain` / `llama_index` | Python generic | [`references/stack-python-generic.md`](references/stack-python-generic.md) |
| `langgraph`, `crewai`, `agno`, `autogen` | Python agentic | [`references/stack-python-agentic.md`](references/stack-python-agentic.md) |

If signals overlap (e.g., both a LangGraph supervisor and raw OpenAI calls inside), pick the agentic reference as primary and note the mixed-stack callout in the plan.

If you cannot identify any agent surface at all (no LLM client imports, no agent framework, no model calls), use the [honest skip path](#honest-skip-path).

### Step 2 — Map the agent's topology

(Skip / reuse if the upstream assessment already has a topology diagram.) Launch one **Explore** agent (or do it directly for very small repos) to answer four questions, citing file paths:

1. **Where does a turn begin?** — entry points: an HTTP handler, a CLI verb, a queue consumer, a chat-platform webhook. This is where `session_id` lives.
2. **What are the agent units?** — supervisor function, sub-agent factories, role-specialised loops. Anything that takes a user message and returns a response. These become trace boundaries.
3. **Where are tools defined and called?** — tool registries (`tools: [...]`), `@tool` decorators, MCP server wiring. Each tool needs to surface as an observation of type `tool` (Langfuse v4).
4. **Where do sub-agents hand off to other sub-agents?** — supervisor → worker, parallel fan-out, graph node transitions. These are the spots that need `propagate_attributes()` (or the framework equivalent) so session/user/tag context survives the boundary.

Capture this as a small topology diagram in the plan (ASCII or Mermaid). It does not need to be exhaustive — it needs to give the customer a single picture they can point at while implementing.

### Step 3 — Render the Langfuse naming/mapping table

Read [`references/langfuse-mapping.md`](references/langfuse-mapping.md) and apply it to the topology:

- One trace name per externally meaningful unit (`chat-turn`, `summarize-thread`, `nightly-research-job`).
- One observation name per role (`supervisor`, `research-agent`, `writer-agent`) and per tool (`tool.<tool-id>`); model calls as `llm.<model-shortname>` generations.
- `session_id` and `user_id` on the trace, set early and propagated (`propagate_attributes(...)`).
- Tags: stack identifier, environment (`dev` / `staging` / `prod`), agent version, feature flag arm if relevant.
- Metadata keys: a small consistent set so dashboards can pivot — `agent_role`, `tool_id`, `model_id`, `prompt_version`, `user_tier`, `gateway_origin` (when Ratel is present).

The plan should list every name/tag/metadata key it introduces in one table the customer can paste into a shared doc, citing `references/langfuse-mapping.md`. The dashboard spec (Step 5) and `/ratel-langfuse-analyze` both read this table; if it's missing they can't function. The mapping renders the vendor-neutral conventions at [`../ratel-observability-assessment/references/semantic-conventions.md`](../ratel-observability-assessment/references/semantic-conventions.md) onto Langfuse primitives — do not re-derive the rules.

### Step 4 — Spec the per-file instrumentation changes

For each file that needs wiring, cite the matching pattern from the stack reference (`references/stack-*.md`) rather than re-deriving it. Each entry: file path, what to wrap, which observation type to use (`span` / `tool` / `generation`), and what name/tags/metadata to attach per the Step 3 table.

### Step 5 — Spec the dashboards (two groups)

Open [`references/langfuse-value-map.md`](references/langfuse-value-map.md), [`../ratel-observability-assessment/references/general-agent-dashboards.md`](../ratel-observability-assessment/references/general-agent-dashboards.md), and [`references/widget-cheatsheet.md`](references/widget-cheatsheet.md). Pick the subset that matches what's actually instrumented in this customer's setup.

Default selection:

- **Ratel-value group** (only if Ratel is in or coming): Token Cost & Savings, Retrieval Quality, Gateway Origin Split, Upstream Health, Skill Retrieval Health (skills shipped in the v0.1.6 line). Add roadmap-conditional ones only if the customer is on a Ratel pre-release that has the feature, or has explicitly signed up to adopt it (e.g., Suggestion Adoption for v0.1.9). Names and widget specs come from [`references/langfuse-value-map.md`](references/langfuse-value-map.md).
- **Agent-health group**: Latency & Cost Overview, Error Surface, Tool Usage, Session Quality, Model & Prompt Drift. From [`../ratel-observability-assessment/references/general-agent-dashboards.md`](../ratel-observability-assessment/references/general-agent-dashboards.md).

For each dashboard section, in this order:

1. **Name** — short, action-oriented (`Token Cost & Savings`, not `Dashboard 1`).
2. **Why it matters** — one paragraph, plain English; the customer's PM should know whether it's for them.
3. **Required data** — the trace name(s), observation type(s), tags, and metadata keys it depends on. Anything missing from the Step 3 table is a TODO blocker listed here.
4. **Widgets** — for each, fill in the five fields from [`references/widget-cheatsheet.md`](references/widget-cheatsheet.md): data source (traces / observations / scores); metric; aggregation; dimension(s); filter(s); plus the visualization.
5. **Pivots / drill-downs** — what to click when the dashboard shows something odd, and where that drill-down lives (a saved trace-filter URL the customer pastes in once the dashboard exists).
6. **Roadmap footnote** (Ratel dashboards only) — if a dashboard would benefit from a Ratel feature that hasn't shipped, name the feature and target version. Reuse the version map in [`../ratel-observability-assessment/references/ratel-value-map.md`](../ratel-observability-assessment/references/ratel-value-map.md) so this stays current.

Drop any dashboard whose backing data isn't instrumented. Skip rather than fake.

### Step 6 — Decide Ratel-aware hooks (only if Ratel is or will be present)

Check whether `@ratel-ai/sdk`, the Python `ratel-ai` package, `ratel-ai-core`, or the `ratel-mcp` / `@ratel-ai/mcp-server` package appears anywhere in the manifest. If yes — or if the customer is signing up to add Ratel as part of this engagement — read [`references/ratel-hooks.md`](references/ratel-hooks.md) and add a section to the plan covering:

- Mapping each Ratel trace event onto a Langfuse observation (`search` → observation type `tool` named `ratel.search_capabilities`, `skill_search` → `ratel.skill_search`, `get_skill_content` → `ratel.get_skill_content`, `InvokeStart`/`InvokeEnd` → observation type `tool` named `ratel.invoke_tool`, etc.). Names are reserved in [`references/langfuse-value-map.md`](references/langfuse-value-map.md).
- Required metadata on each observation: `gateway_origin` (`direct` vs `agent`), `top_k`, `hit_count`, `replace_mode`, score of top hit, latency.
- A "before / after" annotation strategy so the customer can run an A/B comparison once Ratel is wired in (the `feature_flag` tag split is the A/B surface).

If Ratel is not present and there is no plan to introduce it, **skip this section entirely**. Do not pre-bake a Ratel sales pitch into a customer-owned doc — keep the plan honest.

### Step 7 — Write the plan

Write the plan to `<repo>/.ratel/ratel-langfuse-integrate.md` (create the `.ratel/` directory if it doesn't exist; ask the user to confirm the path if the repo already uses a different docs convention).

The plan must contain, in this order:

1. **Summary** — one paragraph: stack detected, agent topology, what's already instrumented (if anything), what this plan adds (wiring + dashboards), how many dashboards in each group.
2. **Setup** — SDK install commands, env vars, **Langfuse MCP server registration** steps (for the customer's Claude Code / Cursor), and a working "hello trace" snippet they can paste and verify.
3. **Topology** — the diagram from Step 2.
4. **Langfuse naming/mapping table** — the table from Step 3, citing [`references/langfuse-mapping.md`](references/langfuse-mapping.md).
5. **Per-file instrumentation changes** — from Step 4, citing the matching `references/stack-*.md`.
6. **Dashboard build-spec** — the two groups (Ratel-value + agent-health) from Step 5, citing [`references/langfuse-value-map.md`](references/langfuse-value-map.md), [`../ratel-observability-assessment/references/general-agent-dashboards.md`](../ratel-observability-assessment/references/general-agent-dashboards.md), and [`references/widget-cheatsheet.md`](references/widget-cheatsheet.md).
7. **Ratel hooks** (conditional, per Step 6), citing [`references/ratel-hooks.md`](references/ratel-hooks.md).
8. **Verification checklist** — copy from [`references/verification-checklist.md`](references/verification-checklist.md): six items the customer can tick once instrumentation lands.
9. **Out of scope (for now)** — dashboards we'd add once the customer adopts a roadmapped Ratel feature at v<X.Y.Z>; dashboards needing data we don't have today.

Print the table of contents inline in the chat — the section list plus the numbered dashboard list with each "why it matters" one-liner — and tell the user the file path. Do not paste the full plan body or full widget specs into the chat; the file is the artifact.

Tell the user the next step once traces are flowing: run [`/ratel-langfuse-analyze`](../ratel-langfuse-analyze/SKILL.md) to read the live data and propose fixes.

## Honest skip path

Several skip cases — stop and say so; never fabricate a deliverable:

1. **No agent surface detected.** If after Step 1 you cannot find a single LLM client import, agent loop, or model call, stop. Do not write a plan. Tell the user:

   > No agent surface detected — only checked `<files looked at>`. If this codebase has agent code in a non-standard location, point me at it and I'll re-run.

   Forced instrumentation plans on a non-agent codebase produce dead documents and waste partner trust.

2. **Stack we don't have a reference for** (e.g., Ruby, Go, niche framework). Still produce a plan — but mark the stack-specific sections "by analogy with the Python generic reference" and ask the user whether to spawn a follow-up to author a new reference. Don't fake confidence.

3. **Customer wants only Ratel-value dashboards and has no Ratel.** Ratel dashboards need at least the gateway path wired up. Recommend a small Ratel pilot (the gateway alone is a half-day integration) before designing dashboards that depend on it. Do not stuff Ratel hooks into an agent that isn't using Ratel — render the agent-health group instead and note the Ratel-value group is blocked on adopting Ratel.

4. **Instrumentation/dashboards but no live data yet.** Build the plan, but mark every dashboard "blocked: no data — re-evaluate after first prod traffic." Empty dashboards demoralise teams.

## Reference files

- [`references/stack-vercel-ai-sdk.md`](references/stack-vercel-ai-sdk.md)
- [`references/stack-typescript-generic.md`](references/stack-typescript-generic.md)
- [`references/stack-python-generic.md`](references/stack-python-generic.md)
- [`references/stack-python-agentic.md`](references/stack-python-agentic.md)
- [`references/langfuse-mapping.md`](references/langfuse-mapping.md) — Langfuse rendering of the generic semantic conventions
- [`references/langfuse-value-map.md`](references/langfuse-value-map.md) — Ratel observation names + Ratel-value dashboard widget specs
- [`references/ratel-hooks.md`](references/ratel-hooks.md) — Ratel events → Langfuse observations
- [`references/widget-cheatsheet.md`](references/widget-cheatsheet.md) — Langfuse v4 widget vocabulary
- [`references/verification-checklist.md`](references/verification-checklist.md)

Shared, vendor-neutral references (owned by `/ratel-observability-assessment`, linked not duplicated):

- [`../ratel-observability-assessment/references/instrumentation-philosophy.md`](../ratel-observability-assessment/references/instrumentation-philosophy.md)
- [`../ratel-observability-assessment/references/semantic-conventions.md`](../ratel-observability-assessment/references/semantic-conventions.md)
- [`../ratel-observability-assessment/references/general-agent-dashboards.md`](../ratel-observability-assessment/references/general-agent-dashboards.md)
- [`../ratel-observability-assessment/references/ratel-value-map.md`](../ratel-observability-assessment/references/ratel-value-map.md)
