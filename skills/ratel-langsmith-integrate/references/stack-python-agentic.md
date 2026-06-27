# Stack reference — Python agentic frameworks (LangGraph, CrewAI, Agno, AutoGen)

Detection signal: `langgraph`, `crewai`, `agno`, `autogen`, or a similar multi-agent orchestration framework. May coexist with the generic Python stack — apply this reference *in addition* to that one for the framework-specific bits.

These frameworks model multi-agent workflows as a graph or a crew of named roles. The instrumentation goal is to preserve role identity and handoff topology in the run tree. LangGraph and LangChain are first-class in LangSmith and trace automatically; the others need a wrapper.

## LangGraph (and LangChain) — zero-code auto-tracing

LangGraph runs on LangChain primitives, so it is traced automatically the moment the env vars are set — no callback handler, no decorator:

```
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=ls_...
LANGSMITH_PROJECT=<project-name>
```

Each graph node becomes a child run named after the node. Name nodes the way you want them in charts — `supervisor`, `research-agent`, `writer-agent` map directly. Set the thread key and metadata through the run config:

```python
result = graph.invoke(
    {"messages": [HumanMessage("...")]},
    config={
        "run_name": "chat-turn",
        "tags": ["env:prod", "stack:langgraph", "agent_version:v3"],
        "configurable": {"thread_id": thread_id},     # → LangSmith thread key
        "metadata": {"session_id": thread_id, "agent_role": "supervisor"},
    },
)
```

LangGraph's checkpointer keys durable state off `configurable.thread_id`; passing the same value as `metadata.session_id` keeps the LangSmith thread aligned with the LangGraph thread on resume.

## CrewAI

CrewAI is auto-traced by LangSmith when the env vars are set (it is one of the supported integrations). Agents and tasks map to child runs named after their role and goal. Specify role names that match [`langsmith-mapping.md`](langsmith-mapping.md) (`research-agent`, not `Researcher Person With Long Title`) by overriding `agent.role` / `task.name` to short stable strings.

For `@tool`-decorated tools that you want captured explicitly with args, stack `@traceable` above the framework decorator:

```python
from crewai.tools import tool
from langsmith import traceable

@traceable(run_type="tool", name="tool.search_web")
@tool
def search_web(query: str) -> str:
    ...
```

Decorator order matters — `@traceable` must be above `@tool`.

## Agno

Agno emits OpenTelemetry spans. Point them at LangSmith's OTel endpoint (LangSmith accepts OTLP):

```python
import os
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "https://api.smith.langchain.com/otel"
os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = (
    f"x-api-key={os.environ['LANGSMITH_API_KEY']},Langsmith-Project={os.environ['LANGSMITH_PROJECT']}"
)
```

Then enable Agno's tracing per its telemetry API. Set `session_id` via Agno's session management so it lands on the spans; LangSmith reads the `session_id` span attribute as the thread key.

## AutoGen

AutoGen has no first-class LangSmith hook; instrument manually with `@traceable`:

```python
from langsmith import traceable

class TracedAssistant(AssistantAgent):
    @traceable(run_type="llm")
    def generate_reply(self, *args, **kwargs):
        return super().generate_reply(*args, **kwargs)
```

Apply the wrapper to every agent class. Wrap tool functions with `@traceable(run_type="tool")` as in the generic Python reference.

## Handoff modelling

Across all four frameworks, sub-agent handoffs should land as **nested child runs**, not siblings. The framework handles this when the parent run is on the active run-tree context as the child starts. Flat sibling structures in your test traces mean the parent context isn't being carried — fix it before continuing. For parallel sub-agents (LangGraph `Send`, CrewAI parallel tasks), each branch is a sibling under the dispatching run, each with its own `agent_role` metadata.

## Common gotchas

- **Thread key lost on graph resume**: LangGraph thread state survives a pause; the LangSmith thread does not unless you pass the same `configurable.thread_id` and mirror it into `metadata.session_id` on every invoke/resume.
- **Metadata not inherited**: LangSmith does not propagate parent metadata to children. Framework auto-tracing sets run-level metadata from `config["metadata"]` at the invoke boundary, but deep child runs you add by hand still need the thread key re-attached.
- **CrewAI task names**: default to the full (multi-line) task description. Override `task.name` to a short stable string.
- **AutoGen user proxy** "thinks" too — name those runs `user-proxy` so they're distinguishable from real model calls, or exclude them.
- **Tool runs missing inputs**: most adapters capture the tool name and output but not the args. Wrap with an explicit `@traceable(run_type="tool")` that captures both.

## What the plan should specify per file

1. The single framework primary, with a callout if any agent escapes it (raw provider SDK call inside a node — wrap with `wrap_openai`).
2. The exact node / agent / task name overrides matching the mapping.
3. The entry point that starts the trace and sets the thread key, tags, and `agent_role`.
4. Whether checkpointing / resume is in use (changes how `thread_id` is threaded).
5. Any tools needing manual `@traceable(run_type="tool")` on top of the framework's auto-capture.
