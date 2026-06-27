# LangSmith query patterns

A small set of vetted query shapes for pulling data out of LangSmith — via the **MCP server** (preferred) or the **`langsmith` SDK** (offline fallback). Reuse these; don't reinvent the queries each run.

LangSmith's model is **projects → traces → run trees**: a trace is a root run (`is_root = true`) with a tree of child runs, each with a `run_type` of `chain` / `llm` / `tool` / `retriever` / `parser` / `prompt` / `embedding`. Sessions/conversations are carried by a `thread_id` (or `session_id` / `conversation_id`) metadata key set on the runs.

## Two access paths

### A. MCP server (preferred)

Two flavours expose the same tool surface:
- **Remote MCP (OAuth, recommended):** `https://api.smith.langchain.com/mcp` (US cloud), `https://eu.api.smith.langchain.com/mcp` (EU), or `<host>/api/mcp` for self-hosted LangSmith v0.15+. Auth is OAuth 2.1 — the client prompts on first use; no API key or custom header required.
- **Standalone `langsmith-mcp-server`** (`langchain-ai/langsmith-mcp-server`, PyPI, run via `uvx`; LangSmith now points users at the Remote MCP but the standalone still works): auth via the `LANGSMITH-API-KEY` header. A hosted instance exists at `https://langsmith-mcp-server.onrender.com/mcp`.

### B. `langsmith` SDK (offline fallback)

When no MCP server is registered but `LANGSMITH_API_KEY` and a project name are present, drive the SDK through `Bash`:

```python
from langsmith import Client
client = Client()  # reads LANGSMITH_API_KEY / LANGSMITH_ENDPOINT from env
```

Core methods: `client.list_runs(...)`, `client.read_run(run_id, load_child_runs=True)`, and run-stats (`POST /v1/runs/stats`, surfaced by the SDK / CLI). Same data as the MCP path; only the access differs.

## Tool discovery (MCP path)

Before querying, list the tools the LangSmith MCP server actually exposes in the current environment. The Remote MCP and the standalone server expose tools for **runs/traces, conversation threads, prompts, datasets, experiments, and billing**, but exact tool names evolve. List once at the start of each session:

```
# via the Ratel gateway (preferred):
search_capabilities(query="langsmith runs traces threads prompts datasets experiments")

# or call the MCP server's tool-listing endpoint directly
```

Capture the actual tool names available. **Confirmed at authoring time:** `list_prompts`, `get_prompt_by_name`, `push_prompt` (prompts); `get_thread_history` (conversation threads, character-paginated via `page_number` / `total_pages` / `max_chars_per_page` / `preview_chars`); `list_datasets` and example tools (datasets); experiment-listing and evaluation tools; `get_billing_usage` (billing). The run/trace query tools exist but their **exact names are not pinned here** — the patterns below use **abstract names** (`langsmith_list_runs`, `langsmith_get_run`, `langsmith_run_stats`, etc.); substitute the real names from the current server's tool list. When in doubt, fall back to the SDK shapes (path B), which are stable.

## Aggregate query (Step 3 of the workflow)

Goal: get the headline numbers for the analysis window in one or two calls. Run stats over **root runs** for the per-trace headline, then over all runs for token totals.

MCP (abstract):

```
langsmith_run_stats(
  project_name = "<project>",
  is_root      = true,
  start_time   = "<window_start>",   # ISO 8601
  end_time     = "<window_end>"
)
# -> run_count, latency_p50, latency_p99, total_tokens,
#    prompt_tokens, completion_tokens, median_tokens, ...
```

SDK / REST equivalent — `POST /v1/runs/stats`:

```python
stats = client.request_with_retries(
    "POST", "/runs/stats",
    json={"session": ["<project_id>"], "is_root": True,
          "start_time": "<window_start>", "end_time": "<window_end>"},
).json()
# run_count, latency_p50, latency_p99, total_tokens, prompt_tokens, completion_tokens
```

Then a second stats call grouped for error rate (set `error=True` to count failures, compare to total):

```python
errors = client.request_with_retries(
    "POST", "/runs/stats",
    json={"session": ["<project_id>"], "is_root": True, "error": True,
          "start_time": "<window_start>", "end_time": "<window_end>"},
).json()
error_rate = errors["run_count"] / max(stats["run_count"], 1)
```

`/runs/stats` returns `latency_p50` / `latency_p99` but **not** a custom percentile set. If you need p95 specifically, list runs and compute it locally (see below).

## Outlier runs (Step 4)

Fetch top-N root runs by a metric. The filter query language supports `gte` / `gt` / `lte` / `lt` / `eq` / `neq` / `has` / `search`, combined with `and(...)` / `or(...)`, over fields including `latency`, `total_tokens`, `start_time`, `run_type`, `name`, `error`, `tags`, `feedback_key`, `feedback_score`. `latency` is in **seconds**.

Slowest root runs (list + sort locally, since `list_runs` orders by start time, not latency):

```python
from datetime import datetime, timedelta
runs = list(client.list_runs(
    project_name="<project>",
    is_root=True,
    start_time=datetime.now() - timedelta(hours=24),
    select=["id", "trace_id", "name", "latency", "total_tokens", "error"],
    limit=1000,
))
slowest = sorted(runs, key=lambda r: r.latency or 0, reverse=True)[:10]
priciest = sorted(runs, key=lambda r: r.total_tokens or 0, reverse=True)[:10]
# p95 latency locally:
lats = sorted(r.latency for r in runs if r.latency is not None)
p95 = lats[int(0.95 * (len(lats) - 1))] if lats else None
```

Or narrow server-side with a latency floor so you only page the tail:

```python
client.list_runs(
    project_name="<project>",
    is_root=True,
    filter='gt(latency, 5)',          # root runs slower than 5s
    start_time=datetime.now() - timedelta(hours=24),
)
```

MCP (abstract):

```
langsmith_list_runs(
  project_name = "<project>",
  is_root      = true,
  filter       = 'gt(latency, 5)',
  start_time   = "<window_start>",
  limit        = 10
)
```

## Erroring runs

```python
client.list_runs(
    project_name="<project>",
    start_time="<window_start>",
    error=True,            # only runs that errored
    select=["id", "trace_id", "name", "run_type", "error"],
)
```

`error=True` is a first-class `list_runs` argument (also `filter='eq(error, true)'`). Group the results by `name` / `run_type` locally to find the noisiest failure site.

## Tool usage (run-type filter)

List `tool` runs and aggregate by name. To attribute tools to their parent trace, group by `trace_id`:

```python
tool_runs = client.list_runs(
    project_name="<project>",
    start_time="<window_start>",
    run_type="tool",
    select=["trace_id", "name", "run_type", "error", "latency"],
)
from collections import Counter
calls   = Counter(r.name for r in tool_runs)
errors  = Counter(r.name for r in tool_runs if r.error)
```

This flattened tool-usage export (list `tool` runs, then batch-fetch their root runs by `trace_id`) is the canonical LangSmith way to ask "which tools does each trace use" — see the export-traces docs. MCP exposes the same via the abstract `langsmith_list_runs(run_type="tool", ...)`.

## Thread / session filters

Sessions are a `thread_id` (or `session_id` / `conversation_id`) metadata key. Filter on it, or pull a whole conversation:

```python
# all root runs for one thread
client.list_runs(
    project_name="<project>",
    is_root=True,
    filter='eq(metadata_key, "thread_id") AND eq(metadata_value, "<thread>")',
)
```

To detect the **missing-`thread_id`** data-quality finding, count root runs with vs. without the key over the window (a single aggregate split). On the MCP path, `get_thread_history` returns the full message history for a thread with character-based pagination.

## Feature-flag / A/B split

This is the single most valuable query in a Ratel A/B engagement — equivalent to Langfuse's `feature_flag` tag split. The arm is carried as a tag or a metadata key (e.g. `feature_flag` / `tool_pool`). Pull each arm and compare aggregates:

```python
for arm in ("ratel", "baseline"):
    runs = client.list_runs(
        project_name="<project>",
        is_root=True,
        start_time="<window_start>",
        filter=f'and(eq(metadata_key, "tool_pool"), eq(metadata_value, "{arm}"))',
        select=["latency", "total_tokens", "error"],
    )
    # compute count / avg latency / avg tokens / error rate per arm locally
```

If the arm tag / metadata key isn't populated, the customer hasn't completed the engagement setup — skip the comparison and add a finding pointing back to `/ratel-langsmith-integrate` for tag/metadata setup.

## Child-run predicates (tree filters)

`trace_filter` narrows by a predicate on **any** run in the trace; `tree_filter` narrows by a predicate on runs **within** the trace tree. Use them to find root runs whose tree contains a specific child, then hydrate:

```python
candidate_roots = client.list_runs(
    project_name="<project>",
    is_root=True,
    start_time=datetime.now() - timedelta(days=7),
    tree_filter='and(eq(run_type, "tool"), eq(name, "<tool_name>"))',
    select=["id"],
)
for c in candidate_roots:
    root = client.read_run(c.id, load_child_runs=True)   # full tree, inputs/outputs
    # walk root.child_runs recursively to inspect the transcript
```

## Reading one run tree in full (Step 4 drill-down)

```python
root = client.read_run("<root_run_id>", load_child_runs=True)
# root.inputs, root.outputs, and recursively root.child_runs[*].{inputs,outputs,run_type,error}
```

MCP (abstract): `langsmith_get_run(run_id="<id>", load_child_runs=true)`. Limit to one or two of these per finding — hydrating a full run tree is the most expensive operation and shouldn't be done speculatively.

## Filter query language cheat-sheet

- Comparators: `gte`, `gt`, `lte`, `lt`, `eq`, `neq`, `has`, `search`.
- Combinators: `and(...)`, `or(...)`.
- Common fields: `id`, `name`, `run_type`, `start_time`, `end_time`, `latency` (seconds), `total_tokens`, `error`, `execution_order`, `tags`, `feedback_key`, `feedback_score`.
- Metadata: `eq(metadata_key, "<k>") AND eq(metadata_value, "<v>")`, or `has(metadata, '{"<k>": "<v>"}')`.
- Tags: `has(tags, "<tag>")`.
- `filter` applies to the run itself; `trace_filter` to any run in the trace; `tree_filter` to runs in the tree. They compose.

## Pitfalls

- **Time bounds are required for sane queries.** Always pass `start_time` (and usually `end_time`). Unbounded queries on a busy project page forever and rate-limit subsequent calls.
- **Know your project.** Runs are partitioned by project; a query with no `project_name` returns nothing useful. Confirm the project before scoping.
- **`latency` is in seconds, not milliseconds.** A `gt(latency, 5)` filter means 5 seconds. `/runs/stats` reports latency in **milliseconds** — don't mix the units when you report numbers.
- **`list_runs` orders by start time.** It does not sort by latency or tokens. To get top-N by a metric, either narrow with a `filter` floor and page the tail, or list and sort locally. Don't assume the first page is the slowest.
- **`select` aggressively when listing many runs.** Fetching `inputs`/`outputs` for thousands of runs is slow; request only `id` / `trace_id` / `name` / metric fields until you drill in.
- **Page large result sets.** `list_runs` is a generator; iterate it (it pages automatically). For raw REST, follow the `cursors.next` token. Truncated drill-downs miss outliers.
- **Don't hit `smith.langchain.com` directly via WebFetch.** It's authenticated; the MCP server or the SDK (with `LANGSMITH_API_KEY`) is the only sanctioned path.
- **Metadata keys must match what's been wired.** The catalog assumes a session key like `thread_id` and an A/B key like `tool_pool` / `feature_flag`, but the customer may have used different names. Read `.ratel/ratel-langsmith-integrate.md` to confirm the actual keys before filtering.
