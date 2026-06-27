# Ratel-aware instrumentation hooks

Read this only when Ratel (`@ratel-ai/sdk`, the Python `ratel-ai` package, `ratel-ai-core`, `@ratel-ai/mcp-server`, or `ratel-mcp`) is present in the codebase, or the customer is signing up to add it during the engagement. Otherwise skip — don't put Ratel scaffolding into customer code unless they're actually using or adopting it.

## What Ratel emits

Ratel's core (`src/core/lib/src/trace/`, ADR-0009) emits a typed stream of trace events: `search` (carrying an `origin` field, `direct | agent`), `skill_search`, `get_skill_content`, invoke start/end/error, gateway-tool calls, upstream-MCP ingest, and auth events. The variants the SDK forwards to Langfuse, with the suite's own observation-name mapping:

| Ratel event | Langfuse mapping | Observation name | `metadata` keys |
| --- | --- | --- | --- |
| `search` (`origin` field) | `type: tool` | `ratel.search_capabilities` | `query`, `top_k`, `hit_count`, `took_ms`, `gateway_origin` (`direct` or `agent`, from the core's `origin` field), `top_hit_score` |
| `skill_search` | `type: tool` | `ratel.skill_search` | `query`, `top_k`, `hit_count`, `skill_ids`, `took_ms`, `gateway_origin` |
| `get_skill_content` | `type: tool` | `ratel.get_skill_content` | `skill_id`, `took_ms`, `gateway_origin` (skills are read, not executed — there is no `invoke_skill`) |
| `InvokeStart` / `InvokeEnd` | `type: tool` | `ratel.invoke_tool` | `tool_id`, `args_bytes`, `took_ms`, `gateway_origin`, on end: `ok` / `error_type` |
| `InvokeError` | error attribute on the matching invoke observation | (same observation) | `error_message` |
| `GatewaySearch` / `GatewayInvoke` | child of the parent agent span | `ratel.gateway.search` / `ratel.gateway.invoke` | `gateway_origin: agent`, `took_ms` |
| `UpstreamRegister` | trace-level event (not per-turn) | `ratel.upstream.register` | `server_name`, `transport`, `tool_count` |
| `UpstreamInvoke` / `UpstreamError` | child of the matching `ratel.invoke_tool` | `ratel.upstream.invoke` | `server_name`, `tool_id`, `took_ms` |
| `AuthRefresh` / `AuthNeeds` / `AuthFlowStart` / `AuthFlowEnd` | event observations under the parent trace | `ratel.auth.<kind>` | `upstream`, `ok` (where applicable) |

## Setup

The `@ratel-ai/sdk` and the Python `ratel-ai` package (shipped at full parity) expose, in the v0.1.6 line, a Langfuse sink that adapts the trace-event stream into Langfuse observations. Until that ships in the version the customer is pinned to:

- **Adapter-side option** (works today): point Ratel's JSONL sink at a directory, run a small forwarder that reads new lines and emits Langfuse observations via the SDK. Forwarder lives in the customer repo under `scripts/ratel-langfuse-forwarder.{ts,py}`. The plan should include this file unless the Ratel version in use is >= the one with the native sink.
- **Native sink** (when available): set `trace: { kind: "langfuse", ... }` in the `ToolCatalog` constructor. The SDK does the mapping.

## Where the metadata goes

Every Ratel-originated observation should carry, in addition to the variant-specific keys above:

- `gateway_origin`: `direct` (Ratel called from library code) vs `agent` (Ratel called via the `search_capabilities` / `invoke_tool` / `get_skill_content` gateway MCP tools). This Langfuse key maps the core's underlying `origin` field (`direct | agent`). Critical pivot — direct calls don't reflect agent behaviour.
- `replace_mode`: `true` if the catalog is in replace-by-default mode (top-K injected, full catalog hidden), `false` otherwise. This determines whether token-savings dashboards apply.
- `top_k`: the cap on returned hits. Lets dashboards correlate top-K with retrieval quality and token savings.

## Before / after annotation

For the partner-startup engagement, the most valuable Langfuse view is the comparison between "agent on its full tool catalog" (baseline) and "agent on Ratel's top-K" (Ratel arm). Two ways to wire this:

1. **Feature flag on the trace**: add `feature_flag: "tool_pool=full"` vs `feature_flag: "tool_pool=ratel"` as a tag on the trace. The customer runs both arms in parallel. Skill #2's Ratel-value dashboards pivot on this tag.
2. **Replay**: run the agent normally with full catalog, log inputs to a dataset, replay the same dataset through Ratel afterwards, and tag the replay traces `replay: true`. Faster to set up but doesn't measure live behaviour.

The plan should recommend the feature-flag approach unless the customer's agent is too costly to run twice in parallel.

## Scoring hooks (when ground truth is available)

If the customer's agent has any form of ground-truth labelling — known-correct tool calls, expected outputs, manual labels — wire a programmatic score on every trace:

| Score | When | Computed from |
| --- | --- | --- |
| `tool_selection_accuracy` | every trace with a `ground_truth_tool_id` metadata key | 1 if the agent's first tool call's `tool_id` == `ground_truth_tool_id`, else 0 |
| `top_k_recall_at_5` | every `ratel.search_capabilities` observation with ground truth | 1 if `ground_truth_tool_id` appears in the top 5 hits, else 0 |
| `input_tokens_saved_vs_baseline` | post-hoc, comparing matched traces | baseline input tokens minus Ratel-arm input tokens |

These scores are what skill #3 keys on when generating its "Ratel-improvement opportunity" findings.

## Don't

- Don't auto-add Ratel observations to traces if Ratel isn't actually invoked in that turn. The plan should specify *conditional* wiring — emit Ratel observations only when the Ratel path executes.
- Don't put PII or full tool args in `ratel.invoke_tool` input. Truncate at the same boundary as the rest of the codebase.
- Don't override the customer's own trace structure to "make room" for Ratel. Ratel observations attach as children to whatever agent span is current; they don't restructure the tree.
