# Langfuse mapping — render the generic conventions onto Langfuse primitives

This file is the **Langfuse rendering** of the vendor-neutral semantic conventions. The *rationale* — why a unit of work is a trace, why a step is an observation, why a session is a thread, what belongs in tags vs metadata — lives once in [`../../ratel-observability-assessment/references/semantic-conventions.md`](../../ratel-observability-assessment/references/semantic-conventions.md). Read that first. This file only answers: **given the generic vocabulary, what is the exact Langfuse primitive, type, and key to use?**

Do not re-derive the naming rules here. If the generic conventions change, change them there and re-render here.

## The mapping at a glance

| Generic concept | Langfuse primitive | How to set it |
| --- | --- | --- |
| Unit of work | **trace** | one trace per externally meaningful unit; `name` = the use case |
| Step (agent role) | **observation, `type: span`** | nest to reflect delegation, not source layout |
| Step (tool call) | **observation, `type: tool`** | tool id in `name`, args in `input` |
| Step (model call) | **observation, `type: generation`** | model family in `name`, full id in `metadata.model_id` |
| Session / thread | **`session_id` on the trace** | set early, `propagate_attributes(session_id=...)` |
| User | **`user_id` on the trace** | stable opaque id, propagated like `session_id` |
| Coarse pivot dimension | **tag** | low-cardinality, ~6 max per trace |
| Fine-grained attribute | **`metadata.<key>`** | high-cardinality allowed; per-observation |

## Trace naming (unit of work → Langfuse `name`)

One trace = one externally meaningful unit of work. Name it after the **use case**, not the function that runs it.

| Use case | Trace name |
| --- | --- |
| One chat turn (sync HTTP) | `chat-turn` |
| One chat turn (streamed) | `chat-turn` (same — streaming is an implementation detail) |
| Async job (background research, summarisation) | `job.<job-kind>` (e.g. `job.summarise-thread`) |
| Scheduled run | `cron.<job-kind>` |
| Tool-call test from a UI | `tooling.manual-invoke` |
| Eval harness run | `eval.<dataset-name>` |

Avoid: `POST_/api/chat`, `handler-fn`, `run`, `process`. They tell you nothing at the dashboard level.

## Observation naming (step kind → Langfuse observation type)

One observation = one step inside a trace. Three step kinds, three Langfuse observation types, three naming rules.

### Agent role steps → `type: span`

```
supervisor
research-agent
writer-agent
critic-agent
```

Lowercase, kebab-case, role-as-noun. If the same agent type can run multiple times in a turn (e.g., critic loop), suffix with iteration: `critic-agent#1`, `critic-agent#2`.

### Tool steps → `type: tool`

```
tool.<tool-id>
```

Where `<tool-id>` is the **stable id** the agent framework uses, not the friendly label. For MCP tools, include the upstream namespace: `tool.upstream__filesystem__read_file`.

When Ratel is present and the agent calls Ratel's unified gateway tools, the observation names are reserved (see [`langfuse-value-map.md`](langfuse-value-map.md) and [`ratel-hooks.md`](ratel-hooks.md)):

```
ratel.search_capabilities
ratel.invoke_tool
ratel.skill_search
ratel.get_skill_content
```

`ratel.skill_search` and `ratel.get_skill_content` cover first-class skills (loaded, not executed — there is no `invoke_skill`). The `metadata.gateway_origin` key maps the core's underlying `origin` field (`direct | agent`).

### Model steps → `type: generation`

```
llm.<model-shortname>
```

Examples: `llm.sonnet-4-6`, `llm.gpt-4o`, `llm.haiku-4-5`. The full provider model id (e.g., `claude-sonnet-4-6-20260101`) belongs in `metadata.model_id`, not in the name. Naming the observation by model family makes "cost by model" pivots trivial; naming it by exact id fragments dashboards every time a snapshot date rolls.

## Sessions → `session_id` + `propagate_attributes`

`session_id` lives on the trace. Source it from the most stable identifier the system already has:

| System has | Use as `session_id` |
| --- | --- |
| Authenticated user with a chat thread | `<thread_id>` (one thread = one session, regardless of how long it lasts) |
| Anonymous chat | the browser session cookie / anonymous id |
| Background job with a correlation id | the correlation id |
| Multi-step agentic run with a run id | the run id |
| Nothing stable available | generate at the entry point, attach to the trace AND store wherever you'd normally keep request state |

Critical: set `session_id` *as early as possible* and propagate it. In Langfuse v4 this is `propagate_attributes(session_id=...)` — setting it only on the trace and not propagating means child observations don't carry it, which breaks session-level analysis.

## User id → `user_id`

`user_id` lives on the trace and propagates the same way as `session_id`. Source it from the authenticated user where available. **Do not put PII (email, name) in `user_id`** — use a stable opaque id. If the system is anonymous, leave `user_id` empty rather than faking one.

## Tags

Tags are coarse, low-cardinality, filterable. Use them for things you'll want to *split a dashboard by*, not things you'll want to *read on a specific trace*.

Standard tag set:

| Tag | Values | Why |
| --- | --- | --- |
| `env` | `dev`, `staging`, `prod` | Single most-used dashboard filter |
| `stack` | `vercel-ai-sdk`, `mastra`, `langchain`, `langgraph`, `crewai`, `llamaindex`, `raw` | Lets you compare instrumentation surfaces |
| `agent_version` | `v<N>` or git short sha | Detect regressions across deploys |
| `feature_flag` | flag name + arm (e.g. `tool_pool=ratel`, `tool_pool=full`) | A/B comparison surface |

Cap tag count at ~6 per trace. More than that and the dashboard filter UI becomes useless. Do not put high-cardinality data in tags (no user ids, no session ids, no error messages).

## Metadata keys

Metadata is fine-grained and can be high-cardinality. Use it for everything you'd want to *show on a specific trace's detail view* or *aggregate in a dashboard*.

Required keys (set on every relevant observation):

| Key | Where | Value |
| --- | --- | --- |
| `agent_role` | on every agent-role span | the role name (`supervisor`, `research-agent`, ...) |
| `tool_id` | on every tool observation | the stable tool id |
| `model_id` | on every generation | the full provider model id |
| `prompt_version` | on every generation | the version/hash of the prompt template used |

Conditional keys (set when the matching feature is in play):

| Key | When | Value |
| --- | --- | --- |
| `user_tier` | multi-tier product | `free` / `pro` / `enterprise` |
| `gateway_origin` | Ratel present | `direct` (Ratel SDK call) vs `agent` (gateway tool call) |
| `top_k`, `hit_count`, `replace_mode` | Ratel retrieval observation | per [`ratel-hooks.md`](ratel-hooks.md) |
| `prompt_arm` | running a prompt A/B | arm id |
| `ground_truth_tool_id` | eval traces with labels | the canonical correct tool id (for accuracy scoring) |

## Don'ts (Langfuse-specific failure modes)

- **Don't put dynamic content in observation names.** `tool.read_file(/etc/passwd)` is a name no dashboard can group on. The name is `tool.read_file`; the argument goes in `input`.
- **Don't reuse names across types.** If `supervisor` is a span, never use it as a tool name. Langfuse dashboards filter by type + name; reusing names produces silent overlap.
- **Don't tag with anything that can be a user input.** Tags are not search; they're pivots.
- **Don't skip `session_id` on observations.** Set it on the trace and propagate — never inherit-by-magic. Langfuse v4 will not back-fill if you forget.
- **Don't capture tool calls as untyped `event` observations.** A tool call captured as a generic `event` with the tool name in `metadata` blocks the entire native tool-call dashboard surface. Use `type: tool` with the id in `name`.
