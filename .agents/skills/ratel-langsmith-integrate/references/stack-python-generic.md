# Stack reference — Python generic (raw SDKs, LangChain, LlamaIndex)

Detection signal: a provider SDK (`openai`, `anthropic`) or `langchain` / `llama_index`, with no multi-agent framework like LangGraph or CrewAI. LangSmith may or may not be installed yet.

## Setup

Install:

```bash
uv pip install -U langsmith openai
# OR for LangChain
uv pip install -U langsmith langchain langchain-openai
```

Env (tracing is on when `LANGSMITH_TRACING=true`):

```
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=ls_...
LANGSMITH_PROJECT=<project-name>          # optional; "default" if unset
LANGSMITH_ENDPOINT=https://api.smith.langchain.com   # or https://eu.api.smith.langchain.com (EU)
LANGSMITH_WORKSPACE_ID=<workspace-id>     # required only for org-scoped API keys
```

No client init is required for the decorator path — `@traceable` lazily creates a `Client` from env. Create one explicitly only when you need to `flush()` (see below).

## Instrumentation paths

Three idiomatic options. Pick one primary; use the others where the primary doesn't reach.

### Path A — `@traceable` decorator (primary recommendation)

```python
from langsmith import traceable
from langsmith.run_helpers import set_run_metadata

@traceable(run_type="chain", name="chat-turn", tags=["env:prod", "stack:langchain", "agent_version:v3"])
def handle_chat(user_id: str, session_id: str, message: str):
    # session_id MUST be on every run — see the threads note below
    set_run_metadata(session_id=session_id, user_id=user_id)
    return run_agent(message, session_id)

@traceable(run_type="chain", name="research-agent")
def run_agent(message: str, session_id: str):
    set_run_metadata(session_id=session_id, agent_role="research-agent")
    plan = supervisor(message)
    return worker(plan)
```

Inputs and outputs are auto-captured. `run_type` accepts `chain`, `llm`, `tool`, `retriever`, `agent`, `prompt`, `parser`, `embedding`.

### Path B — `wrap_openai` for model calls (use alongside Path A)

The wrapper auto-traces every completion as an `llm` run with token usage and cost:

```python
import openai
from langsmith.wrappers import wrap_openai

client = wrap_openai(openai.OpenAI())   # drop-in replacement

@traceable(run_type="chain", name="chat-turn")
def pipeline(user_input: str):
    result = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": user_input}],
    )
    return result.choices[0].message.content
```

There is an equivalent `wrap_anthropic` for the Anthropic SDK. Use the wrapper rather than hand-rolling an `llm` run — it captures usage automatically.

### Path C — LangChain / LlamaIndex auto-tracing

LangChain and LangGraph are traced automatically when `LANGSMITH_TRACING=true` — no callback handler needed (the env var alone enables it). Attach per-run metadata and the thread key through `RunnableConfig`:

```python
result = chain.invoke(
    {"input": "..."},
    config={
        "run_name": "chat-turn",
        "tags": ["env:prod", "stack:langchain"],
        "metadata": {"session_id": session_id, "agent_role": "research-agent"},
    },
)
```

For LlamaIndex, set the LangSmith global handler:

```python
from langchain_core.globals import set_global_handler
set_global_handler("langsmith")
```

## Session / thread propagation

LangSmith does **not** propagate metadata from parent runs to children. Set the thread key (`session_id`, or `thread_id` / `conversation_id`) on **every** run:

- Decorator path: call `set_run_metadata(session_id=...)` at the top of each `@traceable`, or pass `langsmith_extra={"metadata": {"session_id": sid}}` on each call.
- LangChain path: put `session_id` in `config["metadata"]` on every `.invoke()` / `.stream()`.

Setting it only on the root run leaves children unthreaded and breaks thread-level analysis.

## Tool calls

For hand-rolled tool dispatch, wrap the dispatcher so each call is a `tool` run:

```python
@traceable(run_type="tool", name=lambda tool_id, **_: f"tool.{tool_id}")
def call_tool(tool_id: str, args: dict, session_id: str):
    set_run_metadata(tool_id=tool_id, session_id=session_id)
    return TOOLS[tool_id](**args)
```

If a dynamic `name=` callable is awkward in your codebase, use a fixed `@traceable(run_type="tool")` and set the run name via `langsmith_extra={"name": f"tool.{tool_id}"}` at call time.

## Common gotchas

- **`from openai import OpenAI` is not traced.** Only `wrap_openai(...)` auto-instruments. Mixing both produces missing `llm` runs with no token usage.
- **`@traceable` on async functions** works; keep it the *outermost* decorator (above `@app.post`, etc.).
- **Background tasks / Celery / asyncio** lose the run-tree context across task boundaries. Carry it explicitly with `get_current_run_tree()` and re-parent, or start a fresh root run keyed off the correlation id.
- **Flushing**: short-lived processes (lambdas, CLIs) can exit before runs upload. Create an explicit `Client`, pass it to `@traceable(client=client)`, and `client.flush()` in the handler return path.

## What the plan should specify per file

1. Which model-call path is on (`wrap_openai` / `wrap_anthropic` wrapper? LangChain auto-tracing? LlamaIndex global handler?).
2. The entry-point function that gets `@traceable(run_type="chain", name="chat-turn")`.
3. The thread-key propagation point — where `session_id` is set on each run.
4. Per agent / per tool: run name, `run_type`, metadata keys.
5. The flush strategy.
