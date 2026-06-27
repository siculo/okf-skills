# Ratel-aware instrumentation hooks (LangSmith)

Read this only when Ratel (`@ratel-ai/sdk`, the Python `ratel-ai` package, `ratel-ai-core`, `@ratel-ai/mcp-server`, or `ratel-mcp`) is present in the codebase, or the customer is signing up to add it during the engagement. Otherwise skip — don't put Ratel scaffolding into customer code unless they're actually using or adopting it.

This is the LangSmith rendering of the Ratel trace-event stream. The Langfuse equivalent lives in the sibling skill; the underlying Ratel events are the same, only the target primitive differs (LangSmith runs instead of Langfuse observations).

## What Ratel emits

Ratel's core (`src/core/lib/src/trace/`, ADR-0009) emits a typed stream of trace events: `search` (carrying an `origin` field, `direct | agent`), `skill_search`, `get_skill_content`, invoke start/end/error, gateway-tool calls, upstream-MCP ingest, and auth events. The variants the SDK forwards to LangSmith, with this suite's run-name mapping:

| Ratel event | LangSmith run | Run name | `metadata` keys |
| --- | --- | --- | --- |
| `search` (`origin` field) | `run_type: tool` | `ratel.search_capabilities` | `query`, `top_k`, `hit_count`, `took_ms`, `gateway_origin` (`direct` or `agent`, from the core's `origin` field), `top_hit_score` |
| `skill_search` | `run_type: tool` | `ratel.skill_search` | `query`, `top_k`, `hit_count`, `skill_ids`, `took_ms`, `gateway_origin` |
| `get_skill_content` | `run_type: tool` | `ratel.get_skill_content` | `skill_id`, `took_ms`, `gateway_origin` (skills are read, not executed — there is no `invoke_skill`) |
| `InvokeStart` / `InvokeEnd` | `run_type: tool` | `ratel.invoke_tool` | `tool_id`, `args_bytes`, `took_ms`, `gateway_origin`, on end: `ok` / `error_type` |
| `InvokeError` | error on the matching invoke run | (same run) | set the run's error/end with `error_message` |
| `GatewaySearch` / `GatewayInvoke` | child of the parent agent run | `ratel.gateway.search` / `ratel.gateway.invoke` | `gateway_origin: agent`, `took_ms` |
| `UpstreamRegister` | root-level run (not per-turn) | `ratel.upstream.register` | `server_name`, `transport`, `tool_count` |
| `UpstreamInvoke` / `UpstreamError` | child of the matching `ratel.invoke_tool` | `ratel.upstream.invoke` | `server_name`, `tool_id`, `took_ms` |
| `AuthRefresh` / `AuthNeeds` / `AuthFlowStart` / `AuthFlowEnd` | child runs under the parent trace | `ratel.auth.<kind>` | `upstream`, `ok` (where applicable) |

## Setup

The `@ratel-ai/sdk` and the Python `ratel-ai` package (shipped at full parity) expose, in the v0.1.6 line, a trace sink that adapts the trace-event stream into observability backends. Two options for LangSmith:

- **Adapter via RunTree / `@traceable`** (works today): wrap each Ratel call site so the event surfaces as a child `tool` run. In Python, decorate the call site with `@traceable(run_type="tool", name="ratel.invoke_tool")` and `set_run_metadata(...)` the keys above; in TypeScript, create a `pipeline.createChild({ run_type: "tool", name: "ratel.invoke_tool", metadata: {...} })` under the current agent run. If the SDK exposes its event stream, run a small forwarder under `scripts/ratel-langsmith-forwarder.{ts,py}` that reads new events and emits runs via the LangSmith `Client` / `RunTree`. Include this file in the plan unless the Ratel version in use has a native LangSmith sink.
- **Native sink** (when available): set `trace: { kind: "langsmith", ... }` in the `ToolCatalog` constructor. The SDK does the mapping.

The Ratel runs attach as children of whatever agent run is on the active run-tree context — they do not restructure the customer's tree.

## Where the metadata goes

Every Ratel-originated run carries, in addition to the variant-specific keys above:

- `gateway_origin`: `direct` (Ratel called from library code) vs `agent` (Ratel called via the `search_capabilities` / `invoke_tool` / `get_skill_content` gateway MCP tools). This LangSmith metadata key maps the core's underlying `origin` field (`direct | agent`). Critical pivot — direct calls don't reflect agent behaviour.
- `replace_mode`: `true` if the catalog is in replace-by-default mode (top-K injected, full catalog hidden), else `false`. Determines whether token-savings charts apply.
- `top_k`: the cap on returned hits. Lets charts correlate top-K with retrieval quality and token savings.
- `session_id` (the thread key): re-attach it on every Ratel run — LangSmith does not inherit parent metadata, so a Ratel `tool` run with no thread key falls out of session-level analysis.

## Before / after annotation

The most valuable LangSmith view for the partner engagement is the comparison between "agent on its full tool catalog" (baseline) and "agent on Ratel's top-K" (Ratel arm). Two ways to wire it:

1. **Feature-flag tag on the root run**: add the tag `feature_flag:tool_pool=full` vs `feature_flag:tool_pool=ratel` to the root run. The customer runs both arms in parallel. The Ratel-value charts group by this tag, or split it as separate Data Series (the LangSmith A/B surface). See [`langsmith-value-map.md`](langsmith-value-map.md).
2. **Replay**: run the agent with the full catalog, log inputs to a LangSmith dataset, replay the same dataset through Ratel afterwards, and tag the replay runs `replay:true`. Faster to set up but doesn't measure live behaviour.

Recommend the feature-flag approach unless the agent is too costly to run twice in parallel.

## Scoring / feedback hooks (when ground truth is available)

If the agent has any ground-truth labelling — known-correct tool calls, expected outputs, manual labels — attach LangSmith **feedback** on the relevant run via `Client.create_feedback`:

| Feedback key | When | Computed from |
| --- | --- | --- |
| `tool_selection_accuracy` | every trace with a `ground_truth_tool_id` metadata key | 1 if the agent's first tool call's `tool_id` == `ground_truth_tool_id`, else 0 |
| `top_k_recall_at_5` | every `ratel.search_capabilities` run with ground truth | 1 if `ground_truth_tool_id` appears in the top 5 hits, else 0 |
| `input_tokens_saved_vs_baseline` | post-hoc, comparing matched traces | baseline input tokens minus Ratel-arm input tokens |

These feedback scores are what [`/ratel-langsmith-analyze`](../../ratel-langsmith-analyze/SKILL.md) keys on when generating its "Ratel-improvement opportunity" findings, and what the Feedback Scores charts surface.

## Don't

- Don't auto-add Ratel runs to traces where Ratel isn't actually invoked in that turn. Wire them *conditionally* — emit Ratel runs only when the Ratel path executes.
- Don't put PII or full tool args in `ratel.invoke_tool` inputs. Truncate at the same boundary as the rest of the codebase.
- Don't override the customer's own trace structure to "make room" for Ratel. Ratel runs attach as children of the current agent run; they don't restructure the tree.
