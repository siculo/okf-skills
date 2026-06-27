# Langfuse widget cheatsheet

The vocabulary every widget spec in the dashboard plan should use. Langfuse v4 widgets are built from five orthogonal choices; if you can name all five, you can build the widget in the UI in under a minute.

## The five fields

| Field | What it answers | Allowed values |
| --- | --- | --- |
| **Data source** | What rows to look at | `traces`, `observations`, `scores` |
| **Metric** | What to measure | `count`, `latency_ms`, `total_cost`, `input_tokens`, `output_tokens`, `total_tokens`, `score_value`, `custom_metadata_numeric` |
| **Aggregation** | How to summarise the metric | `count`, `sum`, `avg`, `p50`, `p95`, `p99`, `min`, `max`, `distinct_count` |
| **Dimension(s)** | What to group by | time bucket (`hour`, `day`, `week`), `user_id`, `session_id`, `trace_name`, `observation_name`, `observation_type`, `model`, any `tag`, any `metadata.<key>` |
| **Filter(s)** | What rows to exclude | `tag in [...]`, `metadata.<key> in [...]`, `observation_type = tool`, `trace_name = chat-turn`, `score_name = <name>`, time range |

Plus one presentational choice:

| Field | Allowed values |
| --- | --- |
| **Visualization** | `line` (time-series), `bar`, `stacked-bar`, `table`, `single-stat`, `pie`, `scatter`, `histogram` |

## Worked examples

### Token cost per session over time

- Data source: `traces`
- Metric: `total_cost`
- Aggregation: `sum`
- Dimensions: `day`, `tag.feature_flag`
- Filters: `tag.env = prod`, `trace_name = chat-turn`
- Visualization: `line`

### p95 tool latency by tool id

- Data source: `observations`
- Metric: `latency_ms`
- Aggregation: `p95`
- Dimensions: `observation_name`
- Filters: `observation_type = tool`, `tag.env = prod`
- Visualization: `bar`

### Tool selection accuracy (with ground truth)

- Data source: `scores`
- Metric: `score_value`
- Aggregation: `avg`
- Dimensions: `day`, `tag.feature_flag`
- Filters: `score_name = tool_selection_accuracy`
- Visualization: `line` (one line per feature flag arm)

### Ratel gateway origin split

- Data source: `observations`
- Metric: `count`
- Aggregation: `count`
- Dimensions: `metadata.gateway_origin`, `day`
- Filters: `observation_name in [ratel.search_capabilities, ratel.invoke_tool, ratel.skill_search, ratel.get_skill_content]`
- Visualization: `stacked-bar`

### Skill retrieval over time

- Data source: `observations`
- Metric: `count`
- Aggregation: `count`
- Dimensions: `day`
- Filters: `observation_name = ratel.skill_search`
- Visualization: `line`

## Common mistakes

- **Choosing the wrong data source for a metric.** `total_cost` lives on traces (Langfuse aggregates from generations). Don't try to pivot `total_cost` by `observation_name` — it isn't observation-level data.
- **Filtering and dimensioning by the same field.** If you filter `tag.env = prod` and also dimension by `tag.env`, you'll get one bar per dashboard. Pick one.
- **Forgetting `observation_type = tool` on tool dashboards.** Without it, the dashboard picks up generations and spans too and the numbers get inflated.
- **High-cardinality dimensions.** Dimensioning by `session_id` produces thousands of buckets and is unreadable. Use it as a filter, not a dimension. Top-N tables are the exception.
- **Time bucket too small for the data volume.** Hourly buckets on a low-traffic customer produce sparse, jittery charts. Default to daily unless the customer has >10k traces / day.
