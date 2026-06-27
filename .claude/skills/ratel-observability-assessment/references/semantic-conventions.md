# Semantic conventions: naming, tagging, and metadata

This is the **canonical, vendor-neutral vocabulary** every observability skill in the suite assumes. `/ratel-observability-assessment` proposes it; each vendor `*-integrate` skill renders it onto its own primitives; each vendor `*-analyze` skill filters and groups by these exact keys. If the vocabulary drifts, the funnel falls apart.

Each vendor `*-integrate` skill maps these concepts onto its primitives — Langfuse traces/observations/sessions/tags/metadata, LangSmith run trees/run types/metadata, OpenTelemetry spans/attributes — but the names, tags, and keys below are the contract that stays the same across vendors. Do not re-invent. If a customer pushes back on a name, the answer is "change it everywhere — the dashboard spec and the analysis filters too" — not "fine, we'll call it something else in this one place."

The three structural concepts come from `instrumentation-philosophy.md`:

- **Unit of work** — one externally meaningful thing the system did (one chat turn, one job, one webhook).
- **Step** — one thing the agent did inside that unit (a sub-agent run, a tool call, a model call, a retrieval).
- **Session** — a thread of related units of work sharing a session/thread id.

## Unit-of-work naming

One unit of work = one externally meaningful thing. Name it after the **use case**, not the function that runs it.

| Use case | Unit-of-work name |
| --- | --- |
| One chat turn (sync HTTP) | `chat-turn` |
| One chat turn (streamed) | `chat-turn` (same — streaming is an implementation detail) |
| Async job (background research, summarisation) | `job.<job-kind>` (e.g. `job.summarise-thread`) |
| Scheduled run | `cron.<job-kind>` |
| Tool-call test from a UI | `tooling.manual-invoke` |
| Eval harness run | `eval.<dataset-name>` |

Avoid: `POST_/api/chat`, `handler-fn`, `run`, `process`. They tell you nothing at the dashboard level.

## Step naming

One step = one thing the agent did inside a unit of work. Three kinds, three naming rules. Each vendor has a typed-step notion that these map onto (Langfuse observation types, LangSmith run types, OTel span kinds).

### Agent-step (an agent role doing work)

```
supervisor
research-agent
writer-agent
critic-agent
```

Lowercase, kebab-case, role-as-noun. If the same agent role can run multiple times in a unit of work (e.g. a critic loop), suffix with iteration: `critic-agent#1`, `critic-agent#2`.

### Tool-call (a tool being invoked)

```
tool.<tool-id>
```

Where `<tool-id>` is the **stable id** the agent framework uses, not the friendly label. For MCP tools, include the upstream namespace: `tool.upstream__filesystem__read_file`.

When Ratel is present and the agent calls Ratel's unified gateway tools, the gateway tool-calls get conceptual names:

```
ratel.search_capabilities
ratel.invoke_tool
ratel.skill_search
ratel.get_skill_content
```

These are special and treated separately in each vendor skill's Ratel-hooks reference. `ratel.skill_search` and `ratel.get_skill_content` cover first-class skills (loaded, not executed — there is no `invoke_skill`). The `gateway_origin` metadata key maps the core's underlying `origin` field (`direct | agent`).

### Model-call (an LLM generation)

```
llm.<model-shortname>
```

Examples: `llm.sonnet-4-6`, `llm.gpt-4o`, `llm.haiku-4-5`. The full provider model id (e.g. `claude-sonnet-4-6-20260101`) belongs in `model_id` metadata, not in the step name. Naming the step by model family makes "cost by model" pivots trivial; naming it by exact id fragments your dashboards every time a snapshot date rolls.

## Sessions

`session_id` lives on the unit of work. Source it from the most stable identifier the system already has:

| System has | Use as `session_id` |
| --- | --- |
| Authenticated user with a chat thread | `<thread_id>` (one thread = one session, regardless of how long it lasts) |
| Anonymous chat | the browser session cookie / anonymous id |
| Background job with a correlation id | the correlation id |
| Multi-step agentic run with a run id | the run id |
| Nothing stable available | generate at the entry point, attach to the unit of work AND store wherever you'd normally keep request state |

Critical: set `session_id` *as early as possible* and carry it down to every step inside the unit of work. Setting it only on the top-level unit and not propagating it to the steps means child steps don't carry it, which breaks session-level analysis. (Each vendor has a mechanism for this — Langfuse's attribute propagation, setting `session_id` metadata on every LangSmith run, OTel context propagation. The vendor skill names the exact call.)

## User id

`user_id` lives on the unit of work and is carried down to steps the same way as `session_id`. Source it from the authenticated user where available. **Do not put PII (email, name) in `user_id`** — use a stable opaque id. If the system is anonymous, leave `user_id` empty rather than faking one.

## Tags

Tags are coarse, low-cardinality, filterable. Use them for things you'll want to *split a dashboard by*, not things you'll want to *read on a specific unit of work*.

Standard tag set:

| Tag | Values | Why |
| --- | --- | --- |
| `env` | `dev`, `staging`, `prod` | Single most-used dashboard filter |
| `stack` | `vercel-ai-sdk`, `mastra`, `langchain`, `langgraph`, `crewai`, `llamaindex`, `raw` | Lets you compare instrumentation surfaces |
| `agent_version` | `v<N>` or git short sha | Detect regressions across deploys |
| `feature_flag` | flag name + arm (e.g. `tool_pool=ratel`, `tool_pool=full`) | A/B comparison surface |

Cap tag count at ~6 per unit of work. More than that and the dashboard filter UI becomes useless. Do not put high-cardinality data in tags (no user ids, no session ids, no error messages). Vendors that have no first-class "tag" primitive (e.g. LangSmith) carry these as low-cardinality metadata keys instead — the vendor skill names the mechanism; the set above stays the same.

## Metadata / attribute keys

Metadata (or attributes, depending on the vendor) is fine-grained and can be high-cardinality. Use it for everything you'd want to *show on a specific unit-of-work detail view* or *aggregate in a dashboard*.

Required keys (set on every relevant step):

| Key | Where | Value |
| --- | --- | --- |
| `agent_role` | on every agent-step | the role name (`supervisor`, `research-agent`, ...) |
| `tool_id` | on every tool-call | the stable tool id |
| `model_id` | on every model-call | the full provider model id |
| `prompt_version` | on every model-call | the version/hash of the prompt template used |

Conditional keys (set when the matching feature is in play):

| Key | When | Value |
| --- | --- | --- |
| `user_tier` | multi-tier product | `free` / `pro` / `enterprise` |
| `gateway_origin` | Ratel present | `direct` (Ratel SDK call) vs `agent` (gateway tool-call) |
| `top_k`, `hit_count`, `replace_mode` | Ratel retrieval step | per each vendor skill's Ratel-hooks reference |
| `prompt_arm` | running a prompt A/B | arm id |
| `ground_truth_tool_id` | eval units with labels | the canonical correct tool id (for accuracy scoring) |

## Don'ts

- **Don't put dynamic content in step names.** `tool.read_file(/etc/passwd)` is a name no dashboard can group on. The name is `tool.read_file`; the argument goes in the step's input.
- **Don't reuse names across step kinds.** If `supervisor` is an agent-step, never use it as a tool name. Dashboards filter by kind + name; reusing names produces silent overlap.
- **Don't tag with anything that can be a user input.** Tags are not search; they're pivots.
- **Don't skip `session_id` on steps.** Set it on the unit of work and carry it down to every step — never inherit-by-magic. Most vendors will not back-fill if you forget.
