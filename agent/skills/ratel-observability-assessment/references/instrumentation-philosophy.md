# Instrumentation philosophy: trace the mental model, not the call graph

This is the load-bearing idea behind every observability proposal. It is vendor-neutral: it holds whether you end up on Langfuse, LangSmith, PostHog, OpenTelemetry, or anything else. Each vendor `*-integrate` skill maps these concepts onto its own primitives (Langfuse traces/observations, LangSmith run trees, OTel spans, etc.) — but the thinking is the same everywhere.

## The core rule

A common failure mode is "wrap every function in a span." That produces a trace that matches the code's call graph but tells you nothing about what the agent was *trying to do*. Observability data is most useful when its structure matches the **conceptual** structure of a turn, not the source-file layout.

Three vendor-neutral concepts carry the whole model:

- **Unit of work** — one externally meaningful thing the system did: one chat turn, one job, one webhook, one scheduled run. Not "one HTTP request" if a request contains multiple agent turns; not "one model call" if a turn contains many. This is the top-level boundary every vendor records (a Langfuse trace, a LangSmith root run, an OTel root span).
- **Step** — one thing the agent did inside that unit of work: a sub-agent invocation, a tool call, a model call, a retrieval. Steps nest to reflect **delegation**, not source-file layout. (A Langfuse observation, a LangSmith child run, an OTel child span.)
- **Session** — a thread of related units of work that share a session/thread id: usually a user conversation, an agent run-id, or a job correlation id. This is what makes multi-turn analysis possible.

If you can describe a turn to a colleague in three sentences, those sentences are roughly the units of work, steps, and session you should be recording. The trace should read like that description, not like a stack trace.

## The two anti-patterns to call out

When you read the codebase, flag these two specifically in the proposal whenever you see them. They are the highest-leverage fixes and they recur in almost every first engagement.

### 1. No session boundary at all

Every turn is recorded as a fresh, unconnected unit of work with no session id. Multi-turn analysis — session length, abandoned-session rate, cost per conversation, "what did the user do before this failed" — becomes impossible because nothing ties the turns together.

The fix is almost always a single line at the agent entry point: source a stable session id (see `semantic-conventions.md` for the sourcing table) and attach it as early as possible so every step inside the unit of work carries it. Setting it only on the top-level unit and not carrying it down to the steps is the same bug in slower motion — child steps lose the thread.

### 2. Tool calls captured as untyped events

Every tool call lands as a generic, untyped event with the tool name buried in metadata, rather than as a **typed tool step** with the tool id in its name. This blocks the entire native tool-call analysis surface: "calls per tool", "error rate per tool", "p95 latency per tool", "dead-weight tools called once or never" all depend on tool calls being first-class, typed steps that the vendor can group on.

The fix is to wrap the tool-call site so each call surfaces as a typed tool step named after the stable tool id (see `semantic-conventions.md` for naming). Every vendor has a notion of a typed step — Langfuse observation `type: tool`, LangSmith run type `tool`, OTel GenAI tool spans. Use it; do not settle for an untyped event.

## How to apply this in a proposal

State *what* to capture and *why*, in these vendor-neutral terms — units of work, steps, sessions, typed tool/model steps. Leave *how* (the exact SDK calls, the exact primitive names) to the vendor `*-integrate` skill. The proposal's job is to get the mental model right; the vendor skill's job is to render it into concrete wiring.
