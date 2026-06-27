# Langfuse value map — Ratel signals rendered as Langfuse observations and widgets

This file is the **Langfuse rendering** of the Ratel value map: the exact Langfuse observation names a Ratel-instrumented agent emits, and the concrete widget specs for the Ratel-value dashboard group.

The **single source of truth** for *what Ratel ships when* — feature → conceptual signal → version/status — is [`../../ratel-observability-assessment/references/ratel-value-map.md`](../../ratel-observability-assessment/references/ratel-value-map.md). Read that for the versions, the `shipped`/`rc`/`roadmap` status, and the roadmap timeline. This file does not restate the timeline; it renders the shipped signals into Langfuse observation names and widget specs, and leaves roadmap rows as placeholders pointing back to the source map.

Widget specs use the five-field vocabulary from [`widget-cheatsheet.md`](widget-cheatsheet.md). The Ratel→Langfuse observation/metadata mapping is defined in [`ratel-hooks.md`](ratel-hooks.md).

## Reserved Ratel observation names (Langfuse)

A Ratel-instrumented agent emits these observation names. They are the Langfuse-side rendering of the core's typed trace stream (ADR-0009); the core emits `search` (with an `origin` field, `direct | agent`), `skill_search`, `get_skill_content`, invoke start/end/error, gateway-tool, upstream-ingest, and auth events. There is no `invoke_skill` — skills are read via `get_skill_content`, not executed.

| Langfuse observation name | Type | From core event | Key metadata |
| --- | --- | --- | --- |
| `ratel.search_capabilities` | `tool` | `search` | `top_k`, `hit_count`, `top_hit_score`, `took_ms`, `gateway_origin` |
| `ratel.invoke_tool` | `tool` | `InvokeStart`/`InvokeEnd`/`InvokeError` | `tool_id`, `encoding` (`toon`/`json`), `gateway_origin`, `ok`/`error_type` |
| `ratel.skill_search` | `tool` | `skill_search` | `skill_id`s, `hit_count`, `gateway_origin` |
| `ratel.get_skill_content` | `tool` | `get_skill_content` | `skill_id`, `gateway_origin` |
| `ratel.upstream.invoke` | `tool` (child of `ratel.invoke_tool`) | `UpstreamInvoke`/`UpstreamError` | `server_name`, `tool_id`, `took_ms` |
| `ratel.auth.<kind>` | `event` | `AuthRefresh`/`AuthNeeds`/`AuthFlowStart`/`AuthFlowEnd` | `upstream`, `ok` |

`metadata.gateway_origin` (`direct | agent`) and `metadata.replace_mode` (top-K injected vs full catalog) are the two pivots that distinguish "Ratel as a pre-filter" from "agent reaching for the gateway" and gate the token-savings story.

## Recommended dashboards (Ratel-value group)

Include this group **only if Ratel is in or coming**. Pick the subset backed by what's actually instrumented; skip rather than fake. Roadmap dashboards belong in the plan's "Out of scope" section, footnoted with the target version from the source value map.

### Token Cost & Savings

The headline dashboard. Shows the partner is spending less per turn.

Widgets:
1. **Daily input tokens, split by feature flag** — line, sum, `dim: day, tag.feature_flag`, filter `trace_name = chat-turn`, `tag.env = prod`. Two lines: `tool_pool=full` and `tool_pool=ratel`.
2. **Daily total cost per session** — line, avg, `dim: day, tag.feature_flag`, filter same as above.
3. **Single-stat: tokens saved this week** — single-stat, sum of difference. Computed widget; if Langfuse v4 doesn't support computed widgets natively, ship two single-stats side by side and a footnote.
4. **TOON savings** — bar, avg, `dim: metadata.encoding`, metric `input_tokens`, filter `observation_name = ratel.invoke_tool`.

### Retrieval Quality

Shows Ratel is finding the right tools, not just any tools.

Widgets:
1. **Top-hit score distribution** — histogram, `metric: metadata.top_hit_score`, filter `observation_name = ratel.search_capabilities`.
2. **Recall@5 (with ground truth)** — line, avg, `dim: day, tag.feature_flag`, filter `score_name = top_k_recall_at_5`. Only shown when ground-truth labelling is in place (per [`ratel-hooks.md`](ratel-hooks.md)).
3. **Hit count over time** — line, avg of `metadata.hit_count`, `dim: day`.
4. **Ranker comparison** (v0.1.12+) — line, avg `metadata.top_hit_score`, `dim: day, metadata.ranker`.
5. **Re-rank lift** (v0.1.14+) — scatter, `metadata.before_order_top_hit` vs `metadata.after_order_top_hit`, filter `observation_name = ratel.rerank`.

### Gateway Origin Split

Shows whether the agent is using Ratel as a pre-filter or as a discovery surface.

Widgets:
1. **Daily observations by origin** — stacked-bar, count, `dim: day, metadata.gateway_origin`.
2. **Agent-origin invokes (the agent reached for `search_capabilities`)** — single-stat, count, filter `observation_name = ratel.search_capabilities`, `metadata.gateway_origin = agent`.
3. **Top tools called via gateway** — table, count, `dim: metadata.tool_id`, filter `observation_name = ratel.invoke_tool`, `metadata.gateway_origin = agent`. Top 20.

### Upstream Health

Shows MCP upstreams aren't quietly failing.

Widgets:
1. **Daily upstream invokes, by server** — stacked-bar, count, `dim: day, metadata.server_name`, filter `observation_name = ratel.upstream.invoke`.
2. **Upstream error rate, by server** — line, ratio of errors, `dim: day, metadata.server_name`.
3. **Auth events** — table, count, `dim: observation_name, metadata.upstream`, filter `observation_name starts with ratel.auth`.

### Skill Retrieval Health

Shows first-class skills are being found and loaded. Skills are surfaced via the `search_capabilities` skills bucket and read on demand via `get_skill_content` — they are loaded, not executed (there is no `invoke_skill`). Mirrors Gateway Origin Split / Retrieval Quality.

Widgets:
1. **Daily skill searches** — line, count, `dim: day`, filter `observation_name = ratel.skill_search`.
2. **Top skills retrieved** — table, count, `dim: metadata.skill_id`, filter `observation_name = ratel.skill_search`. Top 20.
3. **Skill hit-count distribution** — histogram, `metric: metadata.hit_count`, filter `observation_name = ratel.skill_search`.
4. **Skill content loads** — single-stat, count, filter `observation_name = ratel.get_skill_content`. The ratio of loads to searches shows how often a retrieved skill is actually read.

## Roadmap placeholders

These dashboards activate when the matching Ratel feature ships. Do not put them in the active dashboard list; footnote them in the plan's "Out of scope" section with the target version from [`../../ratel-observability-assessment/references/ratel-value-map.md`](../../ratel-observability-assessment/references/ratel-value-map.md).

### Suggestion Adoption (v0.1.9+)

Placeholder for when LLM suggestions ship.

Widgets (when ready):
1. **Suggestions generated per week** — bar, count, `dim: week`, filter `observation_name = ratel.suggestion.generated`.
2. **Adoption rate** — line, avg of `score_value`, filter `score_name = suggestion_adopted`.
3. **Accuracy delta of adopted suggestions** — bar, `dim: metadata.suggestion_kind` (description rewrite / new skill / merge / etc.), metric `score_value` of `tool_selection_accuracy` after vs before.

### Decomposition Outcome (v0.1.10+)

Placeholder. When ready:
1. **Decomposition proposals over time** — line.
2. **Pre/post catalog sizes per sub-agent** — bar.
3. **Accuracy of decomposed agents vs monolith** — line, score split by `metadata.decomposition_arm`.
