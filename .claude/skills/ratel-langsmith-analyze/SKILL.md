---
name: ratel-langsmith-analyze
description: |
  Read a customer's live LangSmith runs, traces, threads, and feedback scores via the LangSmith MCP server (or langsmith SDK fallback), pattern-match against the shared finding catalog, and write a findings report split into Ratel-flavored improvements and stack-agnostic low-hanging fruit. Use to scan the LangSmith dashboard, dig into the run tree or failed runs, review this week's runs, audit their observability, see what the agent's doing wrong, or `/ratel-langsmith-analyze`. Writes to <repo>/.ratel/ (accumulates); fails fast without a reachable server or API key, honest-skips clean data, never edits code. Follow-up to /ratel-langsmith-integrate.
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Agent
---

# /ratel-langsmith-analyze — read live runs, propose fixes

Pull aggregates and outlier runs from the LangSmith MCP server (or the `langsmith` SDK as a fallback), pattern-match against the catalog of known agent failure modes, and write a findings report the customer can act on this week. Two grouped outputs: Ratel-flavored opportunities (where we'd integrate or deepen Ratel) and general low-hanging fruit (anyone could fix it).

The general findings are not filler — they're how we earn trust. A consultant who only ever recommends their own product looks like a salesperson. We're not that.

LangSmith's data model is **projects → traces → run trees**. A trace is a root run with a tree of child runs; each run has a `run_type` of `chain`, `llm`, `tool`, `retriever`, `parser`, `prompt`, or `embedding`. Sessions/conversations are carried as a `thread_id` / `session_id` metadata key set on the runs. Keep this model in mind: a "trace" in the Langfuse sense maps to a **root run** here, and an "observation" maps to a **child run**.

## What good output looks like

A finding is good if:
1. It cites at least one **run id** or **trace id**, or a saved **filter URL** / filter string, so the customer can verify it themselves.
2. It says **what to do**, not just what's wrong. Vague findings ("error rate is high") waste partner time.
3. It says **why** the fix matters — in one sentence the customer's PM can read.
4. It's tagged **Ratel** or **generic**. Mixing them hides the value story.
5. If it's a Ratel-flavored finding, it cites the Ratel version that solves it — pull the conceptual signal → version mapping from the shared [`ratel-value-map.md`](../ratel-observability-assessment/references/ratel-value-map.md) (vendor-neutral source of truth; today's baseline is the `v0.1.6` line).

A finding is bad if:
- It's a restatement of a dashboard ("p50 latency is 4.2s"). The LangSmith Monitor tab already shows that.
- It uses qualifiers like "could potentially be improved" or "may be worth investigating". Either it's a finding or it isn't.
- It's invented to fill space.

## Workflow

### Step 1 — Verify MCP availability (or fall back to the SDK)

Confirm a LangSmith read surface is reachable. There are two MCP options and one SDK fallback:

```bash
# Preferred: confirm LangSmith MCP tools are present.
# Via the Ratel gateway: search_capabilities(query="langsmith runs traces threads datasets")
# Or inspect Claude Code's MCP config for one of:
#   - the Remote MCP (OAuth):      https://api.smith.langchain.com/mcp
#     (EU region: https://eu.api.smith.langchain.com/mcp; self-hosted: <host>/api/mcp, LangSmith v0.15+)
#   - the standalone server:       langsmith-mcp-server (uvx / PyPI; LANGSMITH-API-KEY header)
```

If **no LangSmith MCP server** is reachable, fail fast:

> LangSmith MCP server not detected. Run `/ratel-langsmith-integrate` first to register the Remote MCP (`https://api.smith.langchain.com/mcp`, OAuth) or the standalone `langsmith-mcp-server`, then re-run this skill.

**SDK fallback (offline / no MCP).** If MCP can't be registered but `LANGSMITH_API_KEY` and a project name are available, you may analyze directly with the `langsmith` Python SDK — `Client.list_runs(...)`, `read_run(run_id, load_child_runs=True)`, and run-stats — driving it through `Bash`. The query shapes for both paths live in [`references/query-patterns.md`](references/query-patterns.md). When you use the SDK path, say so in the report header (the data is the same; only the access path differs).

Do not proceed without one of these. This skill is useless without live data.

### Step 2 — Scope the window

Ask the user (or accept from invocation):
- **Time range** (default: last 24h or last 100 root runs, whichever is smaller).
- **Project** — LangSmith partitions runs by project; you must know which `project_name` to read.
- **Optional filters** (`thread_id` / `session_id`, run `name`, `run_type`, `tags`, env metadata).
- **Optional Ratel feature-flag arm** to focus on (e.g., a `feature_flag` / `tool_pool` metadata value or tag) — useful when running an A/B engagement.

Print the chosen scope back in chat so the customer knows what was analysed.

### Step 3 — Pull aggregates

Use the queries in [`references/query-patterns.md`](references/query-patterns.md) to pull, in order:

1. Root-run count + p50/p99 latency + total tokens/cost + error rate, for the window (run-stats over `is_root` runs).
2. Top 10 root runs by latency, by token/cost, by child-run count.
3. Top 10 most-called tools (`run_type = "tool"`), top 10 erroring runs (`error = true`).
4. Feedback-score distributions for any feedback keys in use.
5. Per-`feature_flag` (or per-`tool_pool`) split if any such tag / metadata key is set.

This frames the rest of the analysis. It also surfaces the trivial-but-important findings ("`thread_id` is missing on 80% of root runs" — discoverable from a single aggregate).

### Step 4 — Drill into outliers

Fetch full run trees for:
- The single slowest root run.
- The single most-expensive (highest-token) root run.
- A root run from the top of the "errors" list.
- The lowest-scored thread (if feedback exists).
- Two random root runs from the typical-latency bucket as a control.

Load child runs (`read_run(..., load_child_runs=True)` or the MCP equivalent) and read inputs and outputs. Don't just look at the run tree's shape — what did the agent actually do? The most valuable findings come from reading transcripts.

### Step 5 — Pattern-match against the shared finding catalog

Open the shared [`finding-catalog.md`](../ratel-observability-assessment/references/finding-catalog.md) (vendor-neutral; owned by `ratel-observability-assessment`). For each pattern: check whether the data the customer has emitted matches the detection heuristic, translating the catalog's generic vocabulary onto LangSmith primitives (unit-of-work → root run, step → child run, tool call → `tool` run, model call → `llm` run, session → `thread_id`). If it matches, emit a finding using the pattern's template.

Don't iterate the catalog blindly — if Ratel isn't in the system, skip the entire Ratel section. If there are no feedback scores, skip score-related patterns. The catalog is a sieve, not a checklist.

### Step 6 — Generate the findings

Each finding follows this template:

```markdown
### F<N>. <one-line title>

- **Severity**: high | medium | low
- **Category**: ratel | generic
- **Evidence**: run ids / trace ids / filter string / filter URL / aggregate value
- **Why this matters**: <one sentence>
- **Recommended action**: <concrete next step the customer can take this week>
- **Solved by Ratel?**: <no | yes, v0.1.X — feature name> (only for ratel category)
```

Severity rubric:
- **high** — affects more than 10% of traffic, or any data quality issue that breaks the Monitor tab / custom dashboards.
- **medium** — affects a meaningful slice but isn't load-bearing.
- **low** — observed but small; worth noting once.

Group findings by severity (high → low) within each category (ratel, generic). Cap at 10 findings per category to keep the report actionable. Above 10, write "(N more findings rolled into a follow-up batch)" and capture the rest in an appendix.

For the Ratel category, take the conceptual signal → Ratel version mapping from the shared [`ratel-value-map.md`](../ratel-observability-assessment/references/ratel-value-map.md). Don't hard-code version claims here.

### Step 7 — Write the report

Output to `<repo>/.ratel/langsmith-analysis-<YYYY-MM-DD>.md`. Reports accumulate (one per run); don't overwrite previous ones. The directory should be the same one `/ratel-langsmith-integrate` writes to.

Structure:

```markdown
# LangSmith analysis — <date>

## Scope
- Project: <project_name>
- Window: <range>
- Access path: <Remote MCP | standalone MCP | langsmith SDK fallback>
- Filters: <list>
- Root runs analysed: <n>
- Findings: <n total>, <n ratel>, <n generic>

## Aggregates at a glance
<3-5 bullets with the headline numbers>

## Findings — Ratel-flavored
<F1, F2, ... in severity order>

## Findings — Generic
<G1, G2, ... in severity order>

## Honest skip (if applicable)
<see honest skip path below>

## Appendix — raw query results
<the aggregates from step 3, formatted as tables>
```

Print the top 3 findings (across both categories, highest severity) inline in chat with one-line summaries. Tell the user the file path for the rest.

## Honest skip path

If the data is genuinely clean — error rate below 1%, no latency outliers, no missing-`thread_id` issue, no feedback regressions, no tool drift — write a short report saying so:

> No findings worth acting on this week. <N> root runs analysed in <window>; aggregate health is within normal ranges. The next time this might be worth re-running is when traffic grows past <threshold> or a new agent version deploys.

This is not failure — it's signal. Partners trust consultants who tell them when there's nothing to fix. **Don't manufacture findings.** A noisy report once trains the customer to ignore future reports forever.

Equally — if traffic is too thin to draw conclusions (fewer than ~20 root runs in the window), say so:

> Only <N> root runs in the window. Re-run after the customer's next traffic-bearing release / next test campaign. Aggregates included for reference but no findings drawn.

## Reference files

- [`references/query-patterns.md`](references/query-patterns.md) — vetted LangSmith MCP tool query shapes + `langsmith` SDK `list_runs` filter patterns (aggregate, drill-down, sample)
- [`finding-catalog.md`](../ratel-observability-assessment/references/finding-catalog.md) — the shared, vendor-neutral catalog of detection patterns + recommended fixes + Ratel mapping (owned by `ratel-observability-assessment`)
- [`ratel-value-map.md`](../ratel-observability-assessment/references/ratel-value-map.md) — the shared, vendor-neutral source of truth for "what Ratel ships when" (conceptual signal → version), read when tagging Ratel-flavored findings

## Where this sits in the arc

This skill is the follow-up that `/ratel-langsmith-integrate` routes to once tracing is live. Upstream: `/ratel-assessment` → `/ratel-observability-assessment` (vendor detection + neutral proposal) → `/ratel-langsmith-integrate` (concrete wiring + dashboards) → **this skill** (read the live data, propose fixes).
