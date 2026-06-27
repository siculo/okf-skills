# LangSmith value map — Ratel signals rendered as runs, charts, and Monitor dashboards

This file is the **LangSmith rendering** of the Ratel value map. The canonical "what Ratel ships when" table — feature → conceptual signal → version, shipped/rc/roadmap — lives in one place and is the single source of truth. Read it first:

[`../../ratel-observability-assessment/references/ratel-value-map.md`](../../ratel-observability-assessment/references/ratel-value-map.md)

Do not restate the version map here. When Ratel ships a new feature, that file changes; this file only changes if the *LangSmith rendering* (run name, metadata key, or chart spec) needs to.

## How Ratel signals appear in LangSmith

| Ratel feature (see source of truth for status/version) | LangSmith signal | Chart that surfaces it |
| --- | --- | --- |
| BM25 retrieval (top-K via `search_capabilities`) | `ratel.search_capabilities` `tool` runs with `top_k`, `hit_count`, `top_hit_score`, `took_ms` | Retrieval Quality |
| Replace-by-default pre-filter | `metadata.replace_mode=true` on `chat-turn` root runs; root `llm` input tokens drop 50–85% | Token Cost & Savings |
| Unified gateway tools | `metadata.gateway_origin in [direct, agent]` on every Ratel run | Gateway Origin Split |
| First-class skills | `ratel.skill_search` and `ratel.get_skill_content` `tool` runs | Skill Retrieval Health |
| TOON encoding | `metadata.encoding=toon` vs `json` on `ratel.invoke_tool`; per-call token delta | Token Cost & Savings (TOON widget) |
| MCP server ingestion | `ratel.upstream.invoke` runs with `server_name`, `tool_id` | Upstream Health |
| OAuth 2.1 / PKCE flows | `ratel.auth.*` runs | Upstream Health |

`ratel.search_capabilities`, `ratel.skill_search`, `ratel.get_skill_content`, and the `metadata.gateway_origin` key are this suite's LangSmith-side run/metadata conventions, mapping the core's `search` (with `origin` field), `skill_search`, `get_skill_content`, invoke, upstream, and auth events. There is no `invoke_skill` — skills are read via `get_skill_content`, not executed. Roadmap features (suggestions v0.1.9, decomposition v0.1.10, semantic/hybrid v0.1.12+, re-rank v0.1.14+) render as new charts when shipped; keep their placeholders in the plan's "Out of scope" section, sourced from the value map.

## LangSmith chart vocabulary (what you fill in per widget)

LangSmith custom charts have five choices. Naming all five lets the customer build the chart in the Custom Dashboard editor in a minute:

| Field | Allowed values |
| --- | --- |
| **Metric (y-axis)** | run count, latency (p50/p95/p99), total tokens, prompt/completion tokens, total cost, error rate, feedback score (numeric avg or categorical count) |
| **Filter** | `run name`, `run type` (`llm`/`tool`/`retriever`/`chain`), `tag`, `metadata.<key>`, time range, `is_root` |
| **Group by** | `tag`, `metadata.<key>`, `run name`, or `run type` — **top 5 by frequency** |
| **Data series** | manual per-series filters (use this when you need >5 groups or an explicit A/B split — this is the A/B surface, equivalent to a Langfuse tag split) |
| **Chart type** | `line` (time series) or `bar` |

The A/B comparison surface in LangSmith is **Group by tag/metadata** for the simple case and **Data Series** for an explicit two-arm split. To compare `tool_pool=full` vs `tool_pool=ratel`, either group by `tag` (top-5 picks up both arms) or add two Data Series filtered to `feature_flag:tool_pool=full` and `feature_flag:tool_pool=ratel`. Because LangSmith does not propagate metadata to child runs, A/B keys must be present on whichever run level the chart filters — put the `feature_flag` tag on the root run and chart at `is_root`, or re-attach it on the Ratel `tool` runs and chart there.

## Ratel-value charts (build on a Custom Dashboard)

### Token Cost & Savings

The headline. Shows the partner spends less per turn.

1. **Daily input tokens, split by A/B arm** — line; metric `prompt tokens` (sum); filter `run name = chat-turn`, `is_root`, `tag env:prod`; group by `tag` (picks up `feature_flag:tool_pool=full` and `=ratel`), or two Data Series for an explicit split.
2. **Daily cost per session** — line; metric `total cost` (avg); same filter and grouping.
3. **Tokens saved this week** — single value via a bar with one bucket, or two side-by-side series (baseline vs Ratel arm) with a footnote, since LangSmith charts don't compute cross-series differences natively.
4. **TOON savings** — bar; metric `total tokens` (avg); filter `run name = ratel.invoke_tool`; group by `metadata.encoding` (`toon` vs `json`).

### Retrieval Quality

Shows Ratel finds the right tools.

1. **Top-hit score over time** — line; metric `metadata.top_hit_score` (avg); filter `run name = ratel.search_capabilities`.
2. **Recall@5 (with ground truth)** — line; metric `feedback score` (avg) for `top_k_recall_at_5`; group by `tag` (A/B arm). Only when ground-truth feedback is wired (see [`ratel-hooks.md`](ratel-hooks.md)).
3. **Hit count over time** — line; metric `metadata.hit_count` (avg); filter `run name = ratel.search_capabilities`.
4. **Ranker comparison** (v0.1.12+) — line; metric `metadata.top_hit_score` (avg); group by `metadata.ranker`.
5. **Re-rank lift** (v0.1.14+) — line; metric `metadata.after_order_top_hit` minus baseline via two Data Series; filter `run name = ratel.rerank`.

### Gateway Origin Split

Shows whether the agent uses Ratel as a pre-filter or a discovery surface.

1. **Daily Ratel runs by origin** — bar; metric `run count`; filter `run name in [ratel.search_capabilities, ratel.invoke_tool, ratel.skill_search, ratel.get_skill_content]`; group by `metadata.gateway_origin`.
2. **Agent-origin searches** — single value (bar, one bucket); metric `run count`; filter `run name = ratel.search_capabilities`, `metadata.gateway_origin = agent`.
3. **Top tools called via gateway** — bar; metric `run count`; filter `run name = ratel.invoke_tool`, `metadata.gateway_origin = agent`; group by `metadata.tool_id` (top 5; for a longer list use the run table filtered the same way).

### Upstream Health

Shows MCP upstreams aren't quietly failing.

1. **Daily upstream invokes, by server** — bar; metric `run count`; filter `run name = ratel.upstream.invoke`; group by `metadata.server_name`.
2. **Upstream error rate, by server** — line; metric `error rate`; filter `run name = ratel.upstream.invoke`; group by `metadata.server_name`.
3. **Auth events** — bar; metric `run count`; filter `run name` starts with `ratel.auth`; group by `run name`.

### Skill Retrieval Health

Shows first-class skills are found and loaded (read via `get_skill_content`, not executed — there is no `invoke_skill`).

1. **Daily skill searches** — line; metric `run count`; filter `run name = ratel.skill_search`.
2. **Top skills retrieved** — bar; metric `run count`; filter `run name = ratel.skill_search`; group by `metadata.skill_id` (top 5).
3. **Skill content loads** — single value; metric `run count`; filter `run name = ratel.get_skill_content`. Ratio of loads to searches shows how often a retrieved skill is actually read.

## What the built-in Monitor tab already gives you for free

Don't rebuild these as custom charts — the prebuilt per-project dashboard (Monitoring → the project's dashboard) already shows Traces (count, latency, error rate), LLM Calls, Cost & Tokens (by token type), Tools (top 5 by frequency), Run Types (immediate children of the root), and Feedback Scores. Use custom dashboards only for the Ratel-value and A/B charts above, and for any agent-health chart the prebuilt view doesn't cover. The agent-health catalog is vendor-neutral — see [`../../ratel-observability-assessment/references/general-agent-dashboards.md`](../../ratel-observability-assessment/references/general-agent-dashboards.md) for which to add, then render each as a LangSmith chart using the vocabulary above (a Langfuse "observation" filter becomes a `run type`/`run name` filter; a Langfuse "trace" filter becomes `is_root`).
