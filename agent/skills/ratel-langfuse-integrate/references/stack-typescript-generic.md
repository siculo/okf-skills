# Stack reference — TypeScript generic (Mastra, raw provider SDKs)

Detection signal: `@mastra/core`, or `openai` / `@anthropic-ai/sdk` / `@google/generative-ai` used directly with hand-rolled agent loops. No `ai` / `@ai-sdk/*` package.

## Setup

Install:

```bash
pnpm add langfuse @opentelemetry/api @opentelemetry/sdk-trace-node @opentelemetry/exporter-trace-otlp-http
```

Env vars:

```
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_HOST=https://cloud.langfuse.com
```

Two instrumentation paths — pick one and stick with it across the codebase. Mixed approaches produce broken trace hierarchies.

### Path A — native Langfuse SDK (`langfuse` v5+)

Best for hand-rolled loops where you want explicit control.

```ts
import { Langfuse } from "langfuse";

const langfuse = new Langfuse();

const trace = langfuse.trace({
  name: "chat-turn",
  sessionId,
  userId,
  tags: ["env:prod", "stack:mastra"],
});

const generation = trace.generation({
  name: "llm.sonnet-4-6",
  model: "claude-sonnet-4-6",
  input: messages,
});
const completion = await anthropic.messages.create({...});
generation.end({ output: completion.content, usage: { input: completion.usage.input_tokens, output: completion.usage.output_tokens } });

await langfuse.flushAsync();
```

### Path B — OpenTelemetry + Langfuse exporter

Better when the codebase already runs OTel for other reasons.

```ts
import { NodeSDK } from "@opentelemetry/sdk-trace-node";
import { LangfuseExporter } from "langfuse-vercel"; // works outside Vercel too

new NodeSDK({
  serviceName: "<service-name>",
  traceExporter: new LangfuseExporter(),
}).start();
```

Then wrap each agent unit with a span using `@opentelemetry/api` `startActiveSpan`. Same pattern as the Vercel AI SDK reference but without the SDK's auto-wrapping.

## Mastra-specific notes

Mastra has built-in telemetry hooks. Set them at the `Mastra` instance level:

```ts
import { Mastra } from "@mastra/core";

export const mastra = new Mastra({
  telemetry: {
    serviceName: "<service-name>",
    enabled: true,
    export: { type: "otlp", endpoint: process.env.LANGFUSE_OTLP_ENDPOINT },
  },
  agents: { ... },
});
```

Mastra agents and workflows emit OTel spans automatically. The plan should still specify `sessionId` and `userId` propagation since Mastra does not infer them from request context.

## Agent loop pattern (raw provider SDK)

For a hand-rolled supervisor → worker loop, the shape is:

```ts
// Entry point — start the trace
const trace = langfuse.trace({ name: "chat-turn", sessionId, userId, tags });

// Supervisor decides who to route to
const supervisorSpan = trace.span({ name: "supervisor", metadata: { agent_role: "supervisor" } });
const decision = await supervisorModel(...);
supervisorSpan.end({ output: decision });

// Worker handles the actual work
const workerSpan = trace.span({ name: "research-agent", metadata: { agent_role: "research-agent" } });
const workerGeneration = workerSpan.generation({
  name: "llm.sonnet-4-6",
  model: "claude-sonnet-4-6",
  input: workerPrompt,
});
const result = await workerModel(...);
workerGeneration.end({ output: result, usage });

// Tool call inside worker
const toolObs = workerSpan.event({
  name: "tool.read_file",
  metadata: { tool_id: "read_file", "langfuse.observation.type": "tool" },
  input: args,
});
const toolResult = await tools.read_file(args);
toolObs.end({ output: toolResult });

workerSpan.end();
```

Notes:
- Anywhere a sub-agent is spawned in parallel, each gets its own `trace.span(...)` child — the SDK handles concurrency.
- The `langfuse.observation.type` metadata key is the override for marking events as tool observations when using the JS SDK pre-v5; v5+ has a dedicated `trace.tool(...)` constructor — prefer that if the project is on v5.

## Common gotchas

- **Flushing**: serverless / short-lived processes drop trace events on exit. Always `await langfuse.flushAsync()` before responding.
- **Sub-agent context loss**: passing `sessionId` only at the top of the trace and never threading it to spawned sub-agents (especially across `Promise.all`) loses session attribution on the children. Pass the same `trace` object down, or use `propagateAttributes` if on v5.
- **Mastra without `serviceName` set** emits unnamed spans that don't group well in dashboards.

## What the plan should specify per file

1. Which path (A or B) the codebase will use — picked once, applied everywhere.
2. The single file where the Langfuse client / OTel SDK is initialised.
3. For each agent function: the trace name, observation type, metadata to attach, where the input/output get truncated.
4. The flush strategy (per-request flush vs interval-based).
