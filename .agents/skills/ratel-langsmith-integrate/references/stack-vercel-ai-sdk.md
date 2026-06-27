# Stack reference — Vercel AI SDK (TypeScript)

Detection signal: `ai` and/or `@ai-sdk/*` in `package.json`. Often paired with Next.js, but the patterns below are framework-agnostic.

LangSmith ships a first-party AI SDK wrapper, `wrapAISDK`. It is the recommended path on AI SDK v5 and `langsmith >= 0.3.63`. For older AI SDK / langsmith versions, fall back to the OpenTelemetry exporter path below.

## Setup

Install:

```bash
pnpm add langsmith ai @ai-sdk/openai
# or npm / yarn / bun equivalent
```

Env vars:

```
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=ls_...
LANGSMITH_PROJECT=<project-name>
LANGSMITH_ENDPOINT=https://api.smith.langchain.com   # or https://eu.api.smith.langchain.com (EU)
```

## Path A — `wrapAISDK` (primary, AI SDK v5 + langsmith ≥ 0.3.63)

Wrap the `ai` module once; the wrapped `generateText` / `streamText` / `generateObject` / `streamObject` trace automatically, and tool calls inside multi-step loops surface as child `tool` runs:

```ts
import { wrapAISDK } from "langsmith/experimental/vercel";
import * as ai from "ai";
import { openai } from "@ai-sdk/openai";

// Defaults applied to every traced run
const { generateText, streamText, generateObject, streamObject } = wrapAISDK(ai, {
  metadata: { stack: "vercel-ai-sdk" },
  tags: ["env:prod", "agent_version:v3"],
});

const result = await generateText({
  model: openai("gpt-4o-mini"),
  prompt,
  tools,
});
```

Per-call run name, thread key, and metadata via `createLangSmithProviderOptions`:

```ts
import { createLangSmithProviderOptions } from "langsmith/experimental/vercel";

const ls = createLangSmithProviderOptions({
  name: "chat-turn",                          // → root run name
  metadata: { session_id: sessionId, user_id: userId },
});

const result = await generateText({
  model: openai("gpt-4o-mini"),
  prompt,
  tools,
  providerOptions: { langsmith: ls },
});
```

`session_id` in metadata is the thread key; set it on every traced call (no inheritance). Tools wrapped via `tool({...})` surface as child `tool` runs automatically — no manual wrapping. Multi-step loops (`stopWhen` / multiple steps) appear as nested `llm` and `tool` runs under the root.

## Path B — OpenTelemetry exporter (older AI SDK / langsmith, or existing OTel)

When the project predates `wrapAISDK` or already runs OTel, use the AI SDK's native telemetry with LangSmith's OTLP endpoint. In `instrumentation.ts` (Next.js: project root):

```ts
import { registerOTel } from "@vercel/otel";
import { OTLPHttpProtoTraceExporter } from "@vercel/otel";

export function register() {
  registerOTel({
    serviceName: "<service-name>",
    traceExporter: new OTLPHttpProtoTraceExporter({
      url: "https://api.smith.langchain.com/otel/v1/traces",
      headers: {
        "x-api-key": process.env.LANGSMITH_API_KEY!,
        "Langsmith-Project": process.env.LANGSMITH_PROJECT!,
      },
    }),
  });
}
```

Then enable telemetry per call:

```ts
const result = await generateText({
  model,
  prompt,
  tools,
  experimental_telemetry: {
    isEnabled: true,
    functionId: "chat-turn",                   // → root run name
    metadata: {
      session_id: sessionId,                   // → thread key
      userId,
      tags: ["env:prod", "stack:vercel-ai-sdk", "agent_version:v3"],
    },
  },
});
```

## Sub-agent handoff

When one `generateText` call delegates to another (supervisor → worker), nest them under a wrapping run so the role name and parent/child link survive. With `wrapAISDK`, call the worker from inside a `traceable` wrapper:

```ts
import { traceable } from "langsmith/traceable";

const researchAgent = traceable(
  async (subPrompt: string, sessionId: string) =>
    generateText({
      model: openai("gpt-4o-mini"),
      prompt: subPrompt,
      providerOptions: {
        langsmith: createLangSmithProviderOptions({
          name: "research-agent",
          metadata: { session_id: sessionId, agent_role: "research-agent" },
        }),
      },
    }),
  { name: "research-agent", run_type: "chain", metadata: { agent_role: "research-agent" } },
);
```

## Common gotchas

- **`name` / `functionId` is what becomes the root run name.** Left empty, every trace is named `ai.generateText` and they all look identical.
- **Streaming**: telemetry is emitted on stream completion, not start. If the process dies mid-stream the run is lost; for long streams add a heartbeat or flush periodically.
- **Edge runtime**: `wrapAISDK` and the OTel exporter run on the Node.js runtime. For Edge functions, route through the OTel exporter from a Node.js boundary, or fall back to manual `traceable` from `langsmith/traceable`. Note this per-file if any agent code is `runtime: "edge"`.
- **Multi-step loops without telemetry/wrapper** produce one opaque run with no inner steps. Always wrap (Path A) or enable `experimental_telemetry.isEnabled` (Path B).
- **Thread key**: pass `session_id` on every call — no parent→child metadata inheritance.

## What the plan should specify per file

1. Path A (`wrapAISDK`) or Path B (OTel) — picked once based on the AI SDK / langsmith versions.
2. The root run name (`name` / `functionId`) per entry point.
3. Whether the call is a leaf agent (single `generateText`) or a delegator (needs a wrapping `traceable` run).
4. Where `session_id` and `user_id` are sourced and re-passed on each call.
5. Which tags apply (`env`, `stack`, `agent_version`, optional `feature_flag`).
