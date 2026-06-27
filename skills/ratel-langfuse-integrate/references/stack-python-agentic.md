# Stack reference — Python agentic frameworks (LangGraph, CrewAI, Agno, AutoGen)

Detection signal: `langgraph`, `crewai`, `agno`, `autogen`, or similar multi-agent orchestration framework. May coexist with the generic Python stack — apply this reference *in addition* to that one for the framework-specific bits.

These frameworks all model multi-agent workflows as a graph or a crew of named roles. The instrumentation challenge is preserving role identity and handoff topology in the trace tree.

## LangGraph

Setup is the same as the generic Python stack plus:

```python
from langfuse.langchain import CallbackHandler
```

LangGraph runs on LangChain primitives, so the LangChain callback handler captures node executions as observations automatically:

```python
handler = CallbackHandler()
result = graph.invoke({"messages": [HumanMessage("...")]}, config={"callbacks": [handler]})
```

Each node becomes an observation named after the node. Use that to your advantage — name nodes the way you want them to appear in dashboards. `supervisor`, `research-agent`, `writer-agent` map directly.

For checkpointed runs (durable execution across pauses), use `langfuse.create_trace_id(seed=<thread_id>)` so resumes attach to the same trace.

## CrewAI

```python
from crewai import Crew
from crewai.tracking import enable_tracing

enable_tracing("langfuse")  # built-in adapter in current versions
```

CrewAI's `Task` and `Agent` objects map to spans named after their role and goal. The plan should specify role names that match the [`langfuse-mapping.md`](langfuse-mapping.md) format (`research-agent`, not `Researcher Person With Long Title`).

For tools (`@tool` decorated):

```python
from crewai.tools import tool
from langfuse import observe

@observe(name="tool.search_web", as_type="tool")
@tool
def search_web(query: str) -> str:
    ...
```

Decorator order matters — `@observe` must be above `@tool`.

## Agno

Agno emits OpenInference-format spans natively. Use the OpenInference Langfuse exporter:

```python
from openinference.instrumentation.agno import AgnoInstrumentor
AgnoInstrumentor().instrument()
```

Set `session_id` / `user_id` via Agno's session-management API; they propagate through to the spans.

## AutoGen

AutoGen has no first-class Langfuse hook; instrument manually. The pattern:

```python
from langfuse import observe

class TracedAssistant(AssistantAgent):
    @observe(as_type="generation")
    def generate_reply(self, *args, **kwargs):
        return super().generate_reply(*args, **kwargs)
```

Apply the wrapper to every agent class in the system. For tool calls, wrap the tool function with `@observe(as_type="tool")` as in the generic Python reference.

## Handoff modelling

Across all four frameworks, sub-agent handoffs should land in the trace tree as **nested spans**, not sibling spans. The framework usually handles this if the parent observation is on the OTel context when the child starts. If you see flat sibling structures in your test traces, that means the parent context isn't being carried — fix it before continuing.

For parallel sub-agents (LangGraph `Send` API, CrewAI parallel tasks), each parallel branch should be a sibling under the dispatching span. Each gets its own `agent_role` metadata so dashboards can pivot.

## Common gotchas

- **`session_id` lost on graph resume**: LangGraph thread state survives a pause, but the Langfuse session does not unless you seed the trace id deterministically.
- **CrewAI task names**: by default they're the literal task description (multi-line!). Override `task.name` to a short stable string.
- **AutoGen's user proxy**: the user proxy "thinks" too — its replies look like generations to the framework. Either exclude its turns or name them `user-proxy` so they're distinguishable from real model calls.
- **Tool-call observations missing inputs**: most framework adapters capture tool name and output but not the args. Always wrap with an explicit `@observe(as_type="tool")` that captures both.

## What the plan should specify per file

1. The single framework primary, with a callout if any agent escapes the framework (raw provider SDK call inside a node).
2. The exact node / agent / task name overrides matching the naming convention.
3. The entry point that starts the trace and sets `session_id` / `user_id` / `tags`.
4. Whether checkpointing / resume is in use (changes trace id seeding).
5. Any tools that need manual `@observe(as_type="tool")` wrapping on top of the framework's auto-capture.
