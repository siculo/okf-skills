---
name: ratel-langfuse-analyze
description: |
  Read a customer's live Langfuse traces, sessions, and scores via the Langfuse MCP server, pattern-match against a known-failure catalog, and write a findings report split into Ratel-flavored opportunities and stack-agnostic low-hanging fruit. Use to scan the dashboard, dig into failures, review recent sessions or the partner's traces, audit their observability, see what the agent's doing wrong, or `/ratel-langfuse-analyze`. Writes to <repo>/.ratel/ (accumulates); fails fast if MCP is down, honest-skips clean data, never edits code. Follow-up to /ratel-langfuse-integrate, reached after /ratel-observability-assessment picks Langfuse.
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Agent
---

# /ratel-langfuse-analyze — read live traces, propose fixes

Pull aggregates and outlier traces from the Langfuse MCP server, pattern-match against the catalog of known agent failure modes, and write a findings report the customer can act on this week. Two grouped outputs: Ratel-flavored opportunities (where we'd integrate or deepen Ratel) and general low-hanging fruit (anyone could fix it).

The general findings are not filler — they're how we earn trust. A consultant who only ever recommends their own product looks like a salesperson. We're not that.

## What good output looks like

A finding is good if:
1. It cites at least one **trace id** or a saved **filter URL** so the customer can verify it themselves.
2. It says **what to do**, not just what's wrong. Vague findings ("error rate is high") waste partner time.
3. It says **why** the fix matters — in one sentence the customer's PM can read.
4. It's tagged **Ratel** or **generic**. Mixing them hides the value story.
5. If it's a Ratel-flavored finding, it cites the Ratel version that solves it (today: `v0.1.6` line; future: pull from [`ratel-observability-assessment/references/ratel-value-map.md`](../ratel-observability-assessment/references/ratel-value-map.md)).

A finding is bad if:
- It's a restatement of a dashboard ("p95 latency is 4.2s"). Dashboards already show that.
- It uses qualifiers like "could potentially be improved" or "may be worth investigating". Either it's a finding or it isn't.
- It's invented to fill space.

## Workflow

### Step 1 — Verify MCP availability

Confirm the Langfuse MCP server is registered and reachable:

```bash
# Inspect Claude Code's MCP config OR use the ratel-mcp gateway's search_capabilities
# to confirm Langfuse tools are present.
```

If unreachable, fail fast:

> Langfuse MCP server not detected. Run `/ratel-langfuse-integrate` first (or wire it up manually per its setup section).

Do not proceed without MCP access. This skill is useless without live data.

### Step 2 — Scope the window

Ask the user (or accept from invocation):
- **Time range** (default: last 24h or last 100 traces, whichever is smaller).
- **Optional filters** (`user_id`, `session_id`, `trace_name`, `env`).
- **Optional Ratel feature flag arm** to focus on (e.g., `feature_flag=tool_pool=ratel`) — useful when running an A/B engagement.

Print the chosen scope back in chat so the customer knows what was analysed.

### Step 3 — Pull aggregates

Use the queries in [`references/mcp-query-patterns.md`](references/mcp-query-patterns.md) to pull, in order:

1. Trace count + p50/p95/p99 latency + total cost + error rate, for the window.
2. Top 10 traces by latency, by cost, by observation count.
3. Top 10 most-called tools, top 10 erroring tools.
4. Score distributions for any score names in use.
5. Per-`feature_flag` split if any feature flag tag is set.

This frames the rest of the analysis. It also surfaces the trivial-but-important findings ("session_id is missing on 80% of traces" — discoverable from a single aggregate).

### Step 4 — Drill into outliers

Fetch full trace bodies for:
- The single slowest trace.
- The single most-expensive trace.
- A trace from the top of the "errors per trace" list.
- The lowest-scored session (if scores exist).
- Two random traces from the typical-latency bucket as a control.

Read inputs and outputs. Don't just look at structure — what did the agent actually do? The most valuable findings come from reading transcripts.

### Step 5 — Pattern-match against the finding catalog

Open [`../ratel-observability-assessment/references/finding-catalog.md`](../ratel-observability-assessment/references/finding-catalog.md) (the vendor-neutral catalog, shared with `ratel-langsmith-analyze`). For each pattern: check whether the data the customer has emitted matches the detection heuristic. If yes, emit a finding using the pattern's template.

Don't iterate the catalog blindly — if Ratel isn't in the system, skip the entire Ratel section. If there are no scores, skip score-related patterns. The catalog is a sieve, not a checklist.

### Step 6 — Generate the findings

Each finding follows this template:

```markdown
### F<N>. <one-line title>

- **Severity**: high | medium | low
- **Category**: ratel | generic
- **Evidence**: trace ids / filter URL / aggregate value
- **Why this matters**: <one sentence>
- **Recommended action**: <concrete next step the customer can take this week>
- **Solved by Ratel?**: <no | yes, v0.1.X — feature name> (only for ratel category)
```

Severity rubric:
- **high** — affects more than 10% of traffic, or any data quality issue that breaks dashboards.
- **medium** — affects a meaningful slice but isn't load-bearing.
- **low** — observed but small; worth noting once.

Group findings by severity (high → low) within each category (ratel, generic). Cap at 10 findings per category to keep the report actionable. Above 10, write "(N more findings rolled into a follow-up batch)" and capture the rest in an appendix.

### Step 7 — Write the report

Output to `<repo>/.ratel/langfuse-analysis-<YYYY-MM-DD>.md`. Reports accumulate (one per run); don't overwrite previous ones. The directory should be the same one `/ratel-langfuse-integrate` writes to.

Structure:

```markdown
# Langfuse analysis — <date>

## Scope
- Window: <range>
- Filters: <list>
- Traces analysed: <n>
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

If the data is genuinely clean — error rate below 1%, no latency outliers, no missing-session-id issue, no scoring regressions, no tool drift — write a short report saying so:

> No findings worth acting on this week. <N> traces analysed in <window>; aggregate health is within normal ranges. The next time this might be worth re-running is when traffic grows past <threshold> or a new agent version deploys.

This is not failure — it's signal. Partners trust consultants who tell them when there's nothing to fix. **Don't manufacture findings.** A noisy report once trains the customer to ignore future reports forever.

Equally — if traffic is too thin to draw conclusions (fewer than ~20 traces in the window), say so:

> Only <N> traces in the window. Re-run after the customer's next traffic-bearing release / next test campaign. Aggregates included for reference but no findings drawn.

## Reference files

- [`../ratel-observability-assessment/references/finding-catalog.md`](../ratel-observability-assessment/references/finding-catalog.md) — the canonical, vendor-neutral catalog of detection patterns + recommended fixes + Ratel mapping; shared with `ratel-langsmith-analyze`
- [`references/mcp-query-patterns.md`](references/mcp-query-patterns.md) — vetted Langfuse MCP query shapes (aggregate, drill-down, sample); Langfuse-specific, stays local
