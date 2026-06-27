# Langfuse MCP query patterns

A small set of vetted query shapes for pulling data out of Langfuse via the MCP server. Reuse these; don't reinvent the queries each run.

## Tool discovery

Before querying, list the tools the Langfuse MCP server actually exposes in the current environment. The official Langfuse MCP server (released late 2025) exposes documentation search plus authenticated trace/session/score access; community variants may add or omit. List once at the start of each session:

```
# via the Ratel gateway (preferred):
search_capabilities(query="langfuse traces sessions scores observations metrics")

# or directly call the MCP server's tool-listing endpoint
```

Capture the actual tool names available. The patterns below use **abstract names** (`langfuse_get_traces`, `langfuse_get_metrics`, etc.); substitute the real names from the current server.

## Aggregate query (Step 3 of the workflow)

Goal: get the headline numbers for the analysis window in one or two calls.

```
langfuse_get_metrics(
  data_source = "traces",
  metrics = ["count", "latency_ms", "total_cost"],
  aggregations = ["count", "avg", "p50", "p95", "p99", "sum"],
  dimensions = ["day"],
  filters = [
    { "field": "tag.env", "op": "eq", "value": "prod" },
    { "field": "start_time", "op": "gte", "value": "<window_start>" },
    { "field": "start_time", "op": "lte", "value": "<window_end>" }
  ]
)
```

Then a second call for error rate:

```
langfuse_get_metrics(
  data_source = "traces",
  metrics = ["count"],
  aggregations = ["count"],
  dimensions = ["day", "status"],
  filters = [<same as above>]
)
```

If the MCP server doesn't expose a metrics endpoint, fall back to listing traces and aggregating locally — but flag that the customer's server is missing a metrics surface (it's part of standard Langfuse v4).

## Outlier traces (Step 4)

Fetch top-N traces by a metric. Repeat for latency, cost, error count.

```
langfuse_list_traces(
  filters = [<env, time-window>],
  sort = { "field": "latency_ms", "order": "desc" },
  limit = 10,
  include_observations = true
)
```

For "single most-expensive trace":

```
langfuse_list_traces(
  filters = [<env, time-window>],
  sort = { "field": "total_cost", "order": "desc" },
  limit = 5,
  include_observations = true,
  include_input_output = true
)
```

Always include observations and IO when drilling. Aggregate listings without IO are cheaper but useless for actual analysis.

## Score queries

```
langfuse_list_scores(
  filters = [
    { "field": "name", "op": "in", "value": ["tool_selection_accuracy", "top_k_recall_at_5"] },
    { "field": "created_at", "op": "gte", "value": "<window_start>" }
  ]
)
```

Then aggregate locally. If the server exposes score aggregation natively, prefer that.

## Feature-flag split

```
langfuse_get_metrics(
  data_source = "traces",
  metrics = ["input_tokens", "total_cost", "count"],
  aggregations = ["avg", "sum"],
  dimensions = ["tag.feature_flag", "day"],
  filters = [<env, time-window>]
)
```

This is the single most valuable query in a Ratel A/B engagement. If `feature_flag` isn't a populated tag, the customer hasn't completed the engagement setup — skip the comparison and add a finding pointing back to `/ratel-langfuse-integrate` for tag setup.

## Tool usage and errors

```
langfuse_list_observations(
  filters = [
    { "field": "type", "op": "eq", "value": "tool" },
    { "field": "start_time", "op": "gte", "value": "<window_start>" }
  ],
  group_by = ["name"],
  metrics = ["count", "p95_latency_ms", "error_rate"],
  limit = 50
)
```

If the server can't group observations natively, list a sample and aggregate locally.

## Reading a single trace in full

When drilling into a specific finding:

```
langfuse_get_trace(
  trace_id = "<id>",
  include_observations = true,
  include_input_output = true,
  include_metadata = true,
  include_scores = true
)
```

Limit to one or two of these per finding — fetching trace bodies is the most expensive operation and shouldn't be done speculatively.

## Pitfalls

- **Time bounds are required for most metric calls.** Always pass `start_time` bounds. Unbounded queries on a busy customer can stall the analysis and rate-limit subsequent calls.
- **Cache the tool list per session.** Don't call `search_capabilities` for every query — the MCP server's surface is stable for the session.
- **Page large result sets.** If a list call returns 1000+ results and `has_more`, paginate. Truncated drill-downs miss outliers.
- **Don't query `cloud.langfuse.com` directly via WebFetch.** It's authenticated; the MCP server is the only sanctioned path.
- **Score names must match what's been wired.** The catalog assumes `tool_selection_accuracy`, `top_k_recall_at_5`, etc., but the actual customer may have used different names. Read `.ratel/ratel-langfuse-integrate.md` to confirm before filtering.
