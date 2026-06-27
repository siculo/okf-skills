---
description: "Inspect an agent codebase to decide where tracing belongs, which dashboards prove value, and which observability vendor is in use, then write a vendor-neutral proposal whose naming/tagging vocabulary downstream skills consume. Use when mounting observability, asking where tracing goes or what to instrument/measure, designing dashboards, naming your vendor (Langfuse/LangSmith/PostHog), asking what proves Ratel's value, or `/ratel-observability-assessment`. Entry point of the funnel (reached from /ratel-assessment); routes to the matching vendor integrate skill. Writes one living markdown file to <repo>/.ratel/; does not edit code or call a vendor API; skips when there's no agent surface.\n"
---
# /ratel-observability-assessment — propose observability for an agent codebase, vendor-neutrally

Mount observability on a customer's codebase the way the Ratel team would: detect the stack, map the agent's mental model, decide one consistent naming/tagging vocabulary, decide which dashboards prove value, **detect (or ask for) the observability vendor**, and write a proposal the customer can act on — then route them to the vendor-specific integrate skill that does the concrete wiring. The proposal is the deliverable. Do not edit the agent code, and do not call any vendor API.

This skill exists because "where do I put tracing" and "what dashboards prove value" are ~80% vendor-neutral questions — only the concrete SDK wiring and widget specs are vendor-shaped. This skill owns the vendor-neutral 80%; the vendor `*-integrate` skills own the 20%. It is the entry point of the observability funnel, usually reached when [`/ratel-assessment`](../ratel-assessment/SKILL.md) flags the Observability dimension as Weak or Missing.

The vocabulary and dashboard set it lands on become the contract for the downstream vendor `*-integrate` and `*-analyze` skills, which expect the names/tags/metadata and dashboards defined here to actually show up.

## Philosophy: trace the mental model, not the call graph

A common failure mode is "wrap every function in a span." That produces data that matches the code's call graph but tells you nothing about what the agent was *trying to do*. The proposal must structure observability around the conceptual shape of a turn — **units of work**, **steps**, **sessions** — not the source-file layout. Read [`references/instrumentation-philosophy.md`](references/instrumentation-philosophy.md) for the full guidance and the two anti-patterns (no session boundary; tool calls captured as untyped events) to call out whenever you see them.

## Workflow

### Step 1 — Detect the stack

Read manifest files to identify language and framework. Stack *detection* is vendor-neutral; stack-specific *code* lives in the vendor skills.

```bash
# TypeScript / Node detection
test -f package.json && jq -r '.dependencies // {}, .devDependencies // {} | keys[]' package.json | sort -u

# Python detection
test -f pyproject.toml && grep -A 200 '^\[' pyproject.toml || true
test -f requirements.txt && cat requirements.txt
test -f uv.lock && head -50 uv.lock
```

Map dependencies to one of these stack profiles:

| Signal in manifest | Stack |
| --- | --- |
| `ai`, `@ai-sdk/*` | Vercel AI SDK |
| `@mastra/core`, hand-rolled loops calling `openai` / `@anthropic-ai/sdk` directly | TypeScript generic |
| `openai` / `anthropic` / `langchain` / `llama_index` (no agent framework) | Python generic |
| `langgraph`, `crewai`, `agno`, `autogen` | Python agentic |

If signals overlap (e.g. both a LangGraph supervisor and raw OpenAI calls inside), pick the agentic profile as primary and note the mixed-stack callout in the proposal. The vendor `*-integrate` skill carries the stack-specific code reference for whichever profile you land on.

If you cannot identify any agent surface at all (no LLM client imports, no agent framework, no model calls), use the [honest skip path](#honest-skip-path).

### Step 2 — Map the agent's topology

Launch one **Explore** agent (or do it directly for very small repos) to answer four questions, citing file paths:

1. **Where does a turn begin?** — entry points: an HTTP handler, a CLI verb, a queue consumer, a chat-platform webhook. This is where `session_id` lives.
2. **What are the units of work?** — supervisor function, sub-agent factories, role-specialised loops. Anything that takes a user message and returns a response. These become the top-level boundaries.
3. **Where are tools defined and called?** — tool registries (`tools: [...]`), `@tool` decorators, MCP server wiring. Each tool call must surface as a typed tool-call step.
4. **Where do sub-agents hand off to other sub-agents?** — supervisor → worker, parallel fan-out, graph node transitions. These are the spots where session/user/tag context must survive the boundary.

Capture this as a small topology diagram in the proposal (ASCII or Mermaid). It does not need to be exhaustive — it needs to give the customer a single picture they can point at while implementing.

### Step 3 — Detect the observability vendor

Read [`references/vendor-detection.md`](references/vendor-detection.md) and scan manifest deps, env vars, and init/import sites for each supported vendor (Langfuse, LangSmith, PostHog, Arize Phoenix, Helicone, OpenLLMetry/OTel GenAI, Braintrust). Reuse the vendor signals `ratel-assessment` already gathers if you have them. Record the detected vendor and a confidence level (high / medium / low) per that reference's rules — a manifest dep or init site is a strong signal; an env var alone is weak.

### Step 4 — If no vendor found, ask the user

If Step 3 produces no signal (or only a weak, ambiguous one), do not guess. Use **AskUserQuestion** to ask which AI-observability tool the team uses, offering: **Langfuse**, **LangSmith**, **PostHog**, **other**, **none yet**.

- If they pick a supported vendor, proceed with that as the detected vendor (confidence: stated).
- If they pick **other**, capture the name; the generic proposal still applies and you route to "author on request" (Step 8).
- If they pick **none yet**, recommend adopting one (Langfuse or LangSmith are the two with concrete integrate skills) and still deliver the full generic proposal, then route to the recommended vendor's integrate skill.

### Step 5 — Propose instrumentation, vendor-neutrally

Apply [`references/instrumentation-philosophy.md`](references/instrumentation-philosophy.md) (mental model, not call graph; the two anti-patterns) and [`references/semantic-conventions.md`](references/semantic-conventions.md) (unit-of-work naming, step kinds, session/thread sourcing, tags, metadata keys) to the topology from Step 2. State *what* to capture — which units of work, which steps, which session id source, which names/tags/metadata — and *why*. Leave *how* (the exact SDK calls, the exact primitive names) to the vendor skill.

List every name/tag/metadata key the proposal introduces in one table the customer can paste into a shared doc. The downstream skills read this table; if it's missing they can't function.

### Step 6 — Propose dashboards, vendor-neutrally

From [`references/general-agent-dashboards.md`](references/general-agent-dashboards.md), pick the agent-health dashboards the instrumentation will support: Latency & Cost Overview, Error Surface, Tool Usage, Session Quality, Model & Prompt Drift. These are useful regardless of Ratel.

Add the **Ratel-value group** *conditionally* — only if Ratel is present in the manifest or the customer has signed up to adopt it. Name those dashboards from [`references/ratel-value-map.md`](references/ratel-value-map.md) (Token Cost & Savings, Retrieval Quality, Gateway Origin Split, Skill Retrieval Health, Upstream Health), and footnote any roadmap-conditional ones with their target Ratel version. If Ratel is not present and there is no plan to introduce it, skip this group entirely — do not pre-bake a Ratel pitch into a customer-owned doc.

List *which* dashboards and *why* each matters (one plain-English line per dashboard). The concrete widget specs are the vendor skill's job; do not render widgets here.

### Step 7 — Write the proposal

Write to `<repo>/.ratel/ratel-observability-assessment.md` — a **single living file, not date-stamped**, so the downstream vendor `*-integrate` skill always reads a stable path. Create the `.ratel/` directory if it doesn't exist; ask the user to confirm the path if the repo already uses a different docs convention. Overwrite on re-run.

The proposal must contain, in this order:

1. **Summary** — one paragraph: stack detected, agent topology, what's already instrumented (if anything), what this proposal adds.
2. **Detected vendor** — the vendor and confidence level (or the user's stated answer from Step 4).
3. **Topology** — the diagram from Step 2.
4. **Vendor-neutral instrumentation strategy** — the naming/tagging/metadata table and the session-boundary plan from Step 5; call out either anti-pattern you found.
5. **Recommended dashboards** — the agent-health group and, conditionally, the Ratel-value group from Step 6, each with its one-line "why".
6. **Ratel angle** (conditional, only if Ratel is present or planned) — which findings map to which Ratel feature/version per `references/ratel-value-map.md`.
7. **Recommended next step** — the matching vendor `*-integrate` skill, per the routing table below.

Print the table of contents inline in the chat — seven bullets max — the detected vendor, and the recommended next-step skill. Do not paste the full proposal body into the chat; the file is the artifact.

### Step 8 — Route to the matching vendor integrate skill

End the proposal and the inline summary with the route:

| Vendor | Route to |
| --- | --- |
| Langfuse | [`/ratel-langfuse-integrate`](../ratel-langfuse-integrate/SKILL.md) |
| LangSmith | [`/ratel-langsmith-integrate`](../ratel-langsmith-integrate/SKILL.md) |
| PostHog / Arize Phoenix / Helicone / OpenLLMetry-OTel / Braintrust | No concrete skill yet — this vendor-neutral proposal fully applies; a `/ratel-<vendor>-integrate` skill can be authored on request. |
| None yet | Recommend adopting Langfuse or LangSmith, then route to that vendor's integrate skill. |

The integrate skill reads `.ratel/ratel-observability-assessment.md` as its input. Tell the user that.

## Honest skip path

If after Step 1 you cannot find a single LLM client import, agent loop, or model call in the codebase, stop. Do not write a proposal. Tell the user:

> No agent surface detected — only checked `<files looked at>`. If this codebase has agent code in a non-standard location, point me at it and I'll re-run.

Forced observability proposals on a non-agent codebase produce dead documents and waste partner trust. Better to skip and ask.

If the stack is one the vendor skills don't yet have a code reference for (e.g. Ruby, Go, or a niche framework), still produce the vendor-neutral proposal — the instrumentation strategy and dashboard set are stack-agnostic — but mark the stack-specific wiring "to be derived by analogy with the Python generic patterns" and ask whether to spawn a follow-up to author a new stack reference. Don't fake confidence.

## Reference files

- [`references/instrumentation-philosophy.md`](references/instrumentation-philosophy.md) — "trace the mental model, not the call graph" + the two anti-patterns
- [`references/semantic-conventions.md`](references/semantic-conventions.md) — vendor-neutral naming/tagging/metadata vocabulary; shared with both vendor families
- [`references/general-agent-dashboards.md`](references/general-agent-dashboards.md) — stack-agnostic agent-health dashboard catalog
- [`references/ratel-value-map.md`](references/ratel-value-map.md) — the single source of truth for what Ratel ships when → conceptual signal → version; read by `ratel-assessment` and both `*-analyze` skills
- [`references/vendor-detection.md`](references/vendor-detection.md) — per-vendor detection signals + the vendor → skill routing table
- [`references/finding-catalog.md`](references/finding-catalog.md) — vendor-neutral catalog of agent failure modes; shared by both `*-analyze` skills
