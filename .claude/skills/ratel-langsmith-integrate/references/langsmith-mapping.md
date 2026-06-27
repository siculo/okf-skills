# LangSmith mapping — generic conventions onto run trees

This file renders the vendor-neutral semantic conventions onto LangSmith primitives. The conventions themselves — what a unit of work is, what a step is, what a session is — live in the source of truth and are not restated here. Read it first:

[`../../ratel-observability-assessment/references/semantic-conventions.md`](../../ratel-observability-assessment/references/semantic-conventions.md)

Everything below is the LangSmith *rendering* of those concepts. `/ratel-langsmith-integrate` writes this mapping into the customer's plan; [`/ratel-langsmith-analyze`](../../ratel-langsmith-analyze/SKILL.md) filters and groups by these exact names and metadata keys. If they drift, the pair falls apart.

## LangSmith's model in one paragraph

A **project** is a container for all traces of one application. A **trace** is the collection of runs for one operation (one chat turn, one job). A **run** is a single unit of work — a span — and runs nest into a **run tree**. Every run has a **run type** (`chain`, `llm`, `tool`, `retriever`, plus `agent`, `prompt`, `parser`, `embedding`). Traces are linked into a **thread** when their runs share one of the recognized thread metadata keys. Runs carry **tags** (low-cardinality strings) and **metadata** (key/value pairs).

## Concept → LangSmith primitive

| Generic concept | LangSmith primitive | How to set it |
| --- | --- | --- |
| Unit of work (one chat turn / job) | **root run** (the trace) | the outermost `@traceable` / `traceable` function, `run_type="chain"`, named after the use case |
| Step (sub-agent, retrieval, reasoning) | **child run**, `run_type="chain"` | a nested `@traceable` function (auto-nests on the active run tree) |
| Model call | **child run**, `run_type="llm"` | `wrap_openai` / `wrapOpenAI`, or `@traceable(run_type="llm")`, or framework auto-tracing |
| Tool call | **child run**, `run_type="tool"` | `@traceable(run_type="tool")` on the dispatcher, or framework tool auto-capture |
| Retrieval step | **child run**, `run_type="retriever"` | `@traceable(run_type="retriever")` (LangSmith renders retriever runs with a document UI) |
| Session / thread | **thread metadata key** on every run | `session_id` (or `thread_id` / `conversation_id`) in `metadata`, set on the root AND propagated |
| Split dimension (env, stack, A/B arm) | **tags** | `tags=[...]` on the root run |
| Per-run detail / pivot key | **metadata** | `metadata={...}` on the run; `set_run_metadata(...)` mid-run |

## Run naming

One run name per externally meaningful unit. Name it after the **use case**, not the function.

| Use case | Root run name | `run_type` |
| --- | --- | --- |
| One chat turn (sync or streamed) | `chat-turn` | `chain` |
| Async job (research, summarisation) | `job.<job-kind>` (e.g. `job.summarise-thread`) | `chain` |
| Scheduled run | `cron.<job-kind>` | `chain` |
| Eval / experiment run | `eval.<dataset-name>` | `chain` |

Set the name with the `name=` argument to `@traceable` / `traceable` (do not rely on the function name — it is unstable across refactors). Avoid `POST_/api/chat`, `handler`, `run`, `process`.

Child runs:

| Step kind | Child run name | `run_type` |
| --- | --- | --- |
| Agent role | `supervisor`, `research-agent`, `writer-agent`, `critic-agent` (kebab-case, role-as-noun; suffix loops `critic-agent#1`) | `chain` |
| Tool | `tool.<tool-id>` (stable id, not the friendly label; MCP tools keep the upstream namespace: `tool.upstream__filesystem__read_file`) | `tool` |
| Model | `llm.<model-shortname>` (`llm.sonnet-4-6`, `llm.gpt-4o`); full provider id goes in `metadata.model_id`, not the name | `llm` |
| Retrieval | `retrieve.<store>` (`retrieve.pgvector`, `retrieve.ratel`) | `retriever` |

## Threads — the one rule that bites everyone

LangSmith groups traces into a thread when their runs carry a recognized thread metadata key: **`session_id`**, **`thread_id`**, or **`conversation_id`** (pick one and use it consistently). Source it from the most stable identifier the system already has — chat thread id, run id, correlation id — exactly as the generic conventions describe.

**Critical:** LangSmith does **not** propagate metadata or tags from a parent run to its children. Setting `session_id` only on the root run leaves child runs unthreaded, which breaks thread-level analysis. You must attach the thread key on **every run** in the tree. Two ways:

- With `@traceable`: read the active run tree and set it at every level, or pass `langsmith_extra={"metadata": {"session_id": sid}}` at each call.
- Cleaner: set it once on the root via `langsmith_extra`, then in each child call re-pass the same metadata. The verification checklist tests for this explicitly.

For LangGraph, set `configurable.thread_id` on the `config` — LangGraph's LangSmith integration maps it to the thread key on the runs it emits.

## Tags

Coarse, low-cardinality, filterable. Use them for what you split a dashboard or chart by, not for what you read on one run. Standard set: `env:<dev|staging|prod>`, `stack:<vercel-ai-sdk|mastra|langchain|langgraph|crewai|raw>`, `agent_version:<v-N or sha>`, and the A/B arm `feature_flag:<flag=arm>` (e.g. `feature_flag:tool_pool=ratel`). LangSmith charts group by tag (top 5 by frequency), so keep tag count ≈6. No user ids, no error messages, no high-cardinality values in tags.

## Metadata keys

Fine-grained, can be high-cardinality. Required on the relevant runs:

| Key | Where | Value |
| --- | --- | --- |
| `agent_role` | every agent-role child run | the role name (`supervisor`, `research-agent`, ...) |
| `tool_id` | every `tool` run | the stable tool id |
| `model_id` | every `llm` run | the full provider model id (e.g. `claude-sonnet-4-6-20260101`) |
| `prompt_version` | every `llm` run | the version/hash of the prompt template used |
| `session_id` (or `thread_id`) | **every** run | the thread key (see Threads above) |

Conditional keys (set when the matching feature is in play): `user_tier` (`free`/`pro`/`enterprise`); the Ratel keys `gateway_origin`, `top_k`, `hit_count`, `replace_mode` per [`ratel-hooks.md`](ratel-hooks.md); `prompt_arm` when running a prompt A/B; `ground_truth_tool_id` on labelled eval runs.

## Don'ts

- **Don't put dynamic content in run names.** `tool.read_file(/etc/passwd)` cannot be grouped on. The name is `tool.read_file`; the argument goes in inputs.
- **Don't rely on metadata inheritance.** LangSmith does not propagate parent metadata/tags to children — re-attach on every run.
- **Don't reuse names across run types.** Charts group by name within a run type; reusing a name across types produces silent overlap.
- **Don't tag with user input.** Tags are pivots, not search.
- **Don't name `llm` runs by exact model snapshot id.** Use the family shortname so charts survive snapshot-date rolls.
