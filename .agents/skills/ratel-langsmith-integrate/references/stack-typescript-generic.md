# Stack reference — TypeScript generic (Mastra, raw provider SDKs)

Detection signal: `@mastra/core`, or `openai` / `@anthropic-ai/sdk` / `@google/generative-ai` used directly with hand-rolled agent loops. No `ai` / `@ai-sdk/*` package.

## Setup

Install:

```bash
pnpm add langsmith
```

Env vars (tracing is on when `LANGSMITH_TRACING=true`):

```
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=ls_...
LANGSMITH_PROJECT=<project-name>
LANGSMITH_ENDPOINT=https://api.smith.langchain.com   # or https://eu.api.smith.langchain.com (EU)
```

## Path A — `traceable` + `wrapOpenAI` (primary)

`wrapOpenAI` traces every completion as an `llm` run with usage; `traceable` wraps your functions so nested calls form a run tree.

```ts
import { OpenAI } from "openai";
import { traceable } from "langsmith/traceable";
import { wrapOpenAI } from "langsmith/wrappers";

const openai = wrapOpenAI(new OpenAI());

const researchAgent = traceable(
  async (message: string, sessionId: string): Promise<string> => {
    const res = await openai.chat.completions.create({
      model: "gpt-4o-mini",
      messages: [{ role: "user", content: message }],
    });
    return res.choices[0].message.content ?? "";
  },
  {
    name: "research-agent",
    run_type: "chain",
    metadata: { agent_role: "research-agent" },
  },
);

// Entry point — the root run. Thread key goes on EVERY run (no inheritance).
const handleChat = traceable(
  async (message: string, sessionId: string) => researchAgent(message, sessionId),
  {
    name: "chat-turn",
    run_type: "chain",
    tags: ["env:prod", "stack:mastra", "agent_version:v3"],
    metadata: { session_id: sessionId },
  },
);
```

Pass the thread key per call when it isn't known at wrap time:

```ts
await researchAgent(message, sessionId, {
  langsmithExtra: { metadata: { session_id: sessionId } },
});
```

## Path B — RunTree (explicit control)

Best for hand-rolled supervisor → worker loops where you want to construct the tree by hand:

```ts
import { RunTree } from "langsmith";

const pipeline = new RunTree({
  name: "chat-turn",
  run_type: "chain",
  inputs: { message },
  tags: ["env:prod", "stack:mastra"],
  metadata: { session_id: sessionId },
});
await pipeline.postRun();

const worker = await pipeline.createChild({
  name: "research-agent",
  run_type: "chain",
  metadata: { agent_role: "research-agent", session_id: sessionId },
});
await worker.postRun();

const gen = await worker.createChild({
  name: "llm.sonnet-4-6",
  run_type: "llm",
  inputs: { messages },
  metadata: { model_id: "claude-sonnet-4-6", session_id: sessionId },
});
const completion = await anthropic.messages.create({ /* ... */ });
gen.end({ outputs: completion });
await gen.patchRun();

worker.end({ outputs: result });
await worker.patchRun();
pipeline.end({ outputs: { answer } });
await pipeline.patchRun();
```

`createChild` carries the parent pointer but **not** its metadata — re-pass `session_id` on each child.

## Mastra-specific notes

Mastra emits OpenTelemetry spans. Point its OTLP export at LangSmith's OTel endpoint:

```ts
import { Mastra } from "@mastra/core";

export const mastra = new Mastra({
  telemetry: {
    serviceName: "<service-name>",
    enabled: true,
    export: {
      type: "otlp",
      endpoint: "https://api.smith.langchain.com/otel/v1/traces",
      headers: {
        "x-api-key": process.env.LANGSMITH_API_KEY!,
        "Langsmith-Project": process.env.LANGSMITH_PROJECT!,
      },
    },
  },
  agents: { /* ... */ },
});
```

Mastra agents and workflows emit spans automatically. Still set the thread key explicitly — Mastra does not infer `session_id` from request context; attach it as a span attribute named `session_id`.

## Tool wrapping

Wrap each tool invocation as a `tool` run:

```ts
const callTool = traceable(
  async (toolId: string, args: unknown, sessionId: string) =>
    tools[toolId].execute(args),
  { name: "tool", run_type: "tool" },
);

await callTool(toolId, args, sessionId, {
  langsmithExtra: {
    name: `tool.${toolId}`,
    metadata: { tool_id: toolId, session_id: sessionId },
  },
});
```

Cap serialized input/output sizes — large blobs blow up trace storage and clutter charts.

## Common gotchas

- **`new OpenAI()` without `wrapOpenAI` is not traced.** Only the wrapped client emits `llm` runs with usage.
- **Flushing**: serverless / short-lived processes drop runs on exit. Create a `Client` and `await client.flush()` in the response path. With `RunTree`, ensure every `postRun()` / `patchRun()` has resolved before returning.
- **Thread key on children**: passing `session_id` only on the root loses thread attribution on children (no inheritance, especially across `Promise.all`). Re-pass it on each child / `langsmithExtra`.
- **Mastra without `serviceName`** emits unnamed spans that don't group in charts.

## What the plan should specify per file

1. Which path (A `traceable` or B `RunTree`) — picked once, applied everywhere.
2. The single file where the wrapped client / RunTree root is created.
3. For each agent function: run name, `run_type`, metadata, where input/output get truncated.
4. The thread-key propagation point on every run.
5. The flush strategy (per-request flush vs interval-based).
