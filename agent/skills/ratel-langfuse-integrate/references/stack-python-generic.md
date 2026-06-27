# Stack reference — Python generic (raw SDKs, LangChain, LlamaIndex)

Detection signal: `langfuse` plus one of `openai`, `anthropic`, `langchain`, `llama_index` (or sibling packages). Project does not use a multi-agent framework like LangGraph or CrewAI.

## Setup

Install:

```bash
uv pip install langfuse openai
# OR for LangChain
uv pip install langfuse langchain langchain-openai
```

Env:

```
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_HOST=https://cloud.langfuse.com
```

Initialise once at module import:

```python
from langfuse import get_client

langfuse = get_client()
```

The SDK is OTel-native in v4. All instrumentation routes through the active OTel context.

## Instrumentation paths

Three idiomatic options. Pick one primary, use the others only where the primary doesn't fit.

### Path A — `@observe()` decorator (primary recommendation)

```python
from langfuse import observe, get_client

@observe(name="chat-turn")
def handle_chat(user_id: str, session_id: str, message: str):
    langfuse = get_client()
    langfuse.update_current_trace(
        user_id=user_id,
        session_id=session_id,
        tags=["env:prod", "stack:langchain", "agent_version:v3"],
    )
    return run_agent(message)

@observe(name="research-agent", as_type="span")
def run_agent(message: str):
    plan = supervisor(message)
    return worker(plan)
```

Inputs and outputs are auto-captured. `as_type` accepts `span`, `generation`, `tool`.

### Path B — context manager

For finer-grained control or when the decorator can't reach (lambdas, generators):

```python
with langfuse.start_as_current_observation(name="research-agent", as_type="span") as obs:
    obs.update(metadata={"agent_role": "research-agent"})
    result = work(...)
    obs.update(output=result)
```

### Path C — provider-specific integration

For OpenAI and Anthropic, the drop-in wrappers auto-instrument generations:

```python
from langfuse.openai import openai  # drop-in replacement
# now every openai.chat.completions.create(...) call lands as a generation
```

For LangChain, attach the callback handler:

```python
from langfuse.langchain import CallbackHandler
handler = CallbackHandler()
result = chain.invoke({"input": "..."}, config={"callbacks": [handler]})
```

For LlamaIndex, use the OpenInference instrumentor:

```python
from openinference.instrumentation.llama_index import LlamaIndexInstrumentor
LlamaIndexInstrumentor().instrument()
```

These integrations produce well-typed generations / tool observations automatically. Use them in addition to the decorator, not instead of it.

## Session / user propagation

The Langfuse v4 propagation model attaches attributes to the *trace* and they propagate to all child observations *if* `propagate_attributes` is called early. The decorator does this for the outermost frame, but if you set attributes on a child span those attributes do not propagate downward unless re-propagated.

Rule: set `user_id`, `session_id`, and `tags` on the **outermost** observation only, immediately after entry. Anything deeper inherits.

```python
@observe(name="chat-turn")
def handle_chat(session_id, user_id, message):
    langfuse.update_current_trace(session_id=session_id, user_id=user_id)
    return run_agent(message)
```

## Tool calls

For hand-rolled tool dispatching:

```python
@observe(name=f"tool.{tool_id}", as_type="tool")
def call_tool(tool_id: str, args: dict):
    langfuse.update_current_observation(metadata={"tool_id": tool_id})
    return TOOLS[tool_id](**args)
```

For LangChain tools, the callback handler captures tool calls automatically. The plan should still specify the metadata keys to attach via `RunnableConfig.metadata`.

## Common gotchas

- **`langfuse.openai` vs `from openai import OpenAI`**: only the wrapped import auto-instruments. Mixing both produces missing generations.
- **`@observe` on async functions**: works, but the decorator must be the *outermost* decorator (above `@app.post`, etc.).
- **Background tasks / Celery / asyncio**: the OTel context does not survive across task boundaries unless you carry it explicitly. Use `langfuse.create_trace_id(seed=correlation_id)` to keep the same trace id deterministically.
- **Flushing**: `langfuse.flush()` before process exit. Lambdas / Cloud Functions: call `flush()` in the handler return path.

## What the plan should specify per file

1. Which integration is on (Path C choices: OpenAI wrapper? LangChain callback? LlamaIndex instrumentor?).
2. The entry point function that gets the `@observe(name="chat-turn")` decorator.
3. The propagation point (`langfuse.update_current_trace(...)` call).
4. Per agent / per tool: name, `as_type`, metadata keys.
5. The flush strategy.
