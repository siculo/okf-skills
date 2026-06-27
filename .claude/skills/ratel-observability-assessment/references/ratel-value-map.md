# Ratel value map — feature → signal → version

This is the **single source of truth for what Ratel ships when** and the observable signal each capability produces, expressed vendor-neutrally. **Update this file whenever Ratel ships a new feature** — `ratel-assessment`, `ratel-observability-assessment`, both vendor `*-integrate` skills, and both vendor `*-analyze` skills all read it.

Each vendor skill **renders** these conceptual signals into concrete observation/run names and widget specs (Langfuse observation names like `ratel.search_capabilities`; LangSmith `tool`/`llm` runs with metadata; the exact dashboard widgets). This file does *not* carry those vendor-specific names — it describes the signal conceptually so every vendor skill can render it its own way.

Each row has:
- **Feature** — the Ratel capability, with the version that shipped (or will ship) it.
- **Status** — `shipped` / `rc` / `roadmap`. Signals for `roadmap` features go in a proposal's "Out of scope" section, not in the active dashboard list.
- **Signal** — the observable data, described conceptually (which step kind, carrying which attributes), that proves the feature is working.
- **Dashboard** — which dashboard owns the widget that surfaces it (the vendor skill renders the widget).

## Shipped today (v0.1.6 line)

| Feature | Status | Signal (conceptual) | Dashboard |
| --- | --- | --- | --- |
| BM25 retrieval (top-K tools + skills via `search_capabilities`) | shipped | a retrieval/tool step for the capability search, carrying `top_k`, `hit_count`, `top_hit_score`, `took_ms` | Retrieval Quality |
| Replace-by-default pre-filter (top-K injected, full catalog hidden) | shipped | `replace_mode=true` on `chat-turn` units of work; the root model-call's `input_tokens` drops by 50–85% | Token Cost & Savings |
| Unified gateway tools (`search_capabilities`, `invoke_tool`, `get_skill_content`) | shipped | `gateway_origin in [direct, agent]` on every Ratel step; count by origin | Gateway Origin Split |
| First-class skills (`SkillCatalog`, ranked via `search_capabilities` skills bucket) | shipped | a skill-search step (skill ids, hit counts) and a skill-content-load step | Skill Retrieval Health |
| TOON encoding | shipped | `encoding=toon` vs `json` on the gateway invoke step; per-call token delta | Token Cost & Savings ("TOON savings" widget) |
| MCP server ingestion (upstream namespace prefix) | shipped | an upstream-invoke step carrying `server_name` and `tool_id` | Upstream Health |
| OAuth 2.1 / PKCE auth flows | shipped | auth events: refresh, needs, flow-start, flow-end | Upstream Health |
| Trace stream (JSONL sink + future vendor sink) | shipped | every signal above is exported to the observability vendor | foundation for all dashboards |

Note: the conceptual signals above (capability-search step, skill-search step, skill-content-load step, the `gateway_origin` attribute) are the suite's observability-side conventions. The core (ADR-0009) emits `search` (with an `origin` field, `direct | agent`), `skill_search`, `get_skill_content`, invoke start/end/error, gateway-tool, upstream-ingest, and auth events. **There is no `invoke_skill`** — skills are read via `get_skill_content`, not executed. Each vendor `*-integrate` skill maps these core events onto its primitives (Langfuse observation names, LangSmith run types, etc.).

## Coming soon (next minor versions)

| Feature | Status | Signal it will add (conceptual) | Dashboard impact |
| --- | --- | --- | --- |
| LLM-driven suggestions (v0.1.9) | roadmap | a suggestion-generated event; a `suggestion_adopted` score | New "Suggestion Adoption" dashboard |
| Multi-agent decomposition hints (v0.1.10) | roadmap | a decomposition-proposed event; per-sub-agent catalog sizes | New "Decomposition Outcome" dashboard |
| Semantic search + hybrid ranking (v0.1.12–v0.1.13) | roadmap | a `ranker = bm25 | semantic | hybrid` attribute on retrieval; per-ranker top-hit score | Retrieval Quality adds a "Ranker comparison" widget |
| Re-ranking (v0.1.14 LLM, v0.1.15 XGBoost) | roadmap | a re-rank step carrying `before_order` / `after_order` | Retrieval Quality adds a "Re-rank lift" widget |
| Chat compaction (v0.2.x) | roadmap | a compaction step carrying token-in / token-out | New "Compaction" dashboard |
| Memory orchestration (v0.3.x) | roadmap | a memory-retrieve step carrying hit count, ranking | New "Memory Recall" dashboard |

## How the dashboards use these signals

The Ratel-value dashboard *group* (Token Cost & Savings, Retrieval Quality, Gateway Origin Split, Skill Retrieval Health, Upstream Health, and the roadmap placeholders) is named here and proposed vendor-neutrally by `/ratel-observability-assessment`. The concrete widget specs — exact step/observation/run names, metrics, aggregations, dimensions, filters, and visualizations — live in each vendor `*-integrate` skill's value-map reference, because they depend on the vendor's primitive names and widget vocabulary. This file stays the contract for *what Ratel ships when and what signal proves it*; the vendor skills own *how that signal is rendered*.
