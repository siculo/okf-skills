# Stack reference — Vercel AI SDK (TypeScript)

Detection signal: `ai` and/or `@ai-sdk/*` in `package.json`. Often paired with Next.js, but the instrumentation patterns below are framework-agnostic.

## Setup

Install:

```bash
pnpm add langfuse @vercel/otel @opentelemetry/api
# or npm / yarn / bun equivalent
```

Env vars (per Langfuse SDK):

```
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_HOST=https://cloud.langfuse.com  # or self-hosted URL
```

Wire OTel once at process start (Next.js: `instrumentation.ts` at the project root):

```ts
import { registerOTel } from "@vercel/otel";
import { LangfuseExporter } from "langfuse-vercel";

export function register() {
  registerOTel({
    serviceName: "<service-name>",
    traceExporter: new LangfuseExporter(),
  });
}
```

For Next.js, also enable `experimental.instrumentationHook = true` in `next.config.ts` if the project is on a version that still requires it.

## Per-call instrumentation

The Vercel AI SDK has built-in OTel telemetry. Enable it per call and pass a `functionId` matching the trace naming convention:

```ts
const result = await generateText({
  model,
  prompt,
  tools,
  experimental_telemetry: {
    isEnabled: true,
    functionId: "chat-turn",            // → Langfuse trace name
    metadata: {
      sessionId,                         // → Langfuse session
      userId,                            // → Langfuse user
      tags: ["env:prod", "stack:vercel-ai-sdk", "agent_version:v3"],
      langfuseUpdateParent: true,        // attach to the outer trace
    },
  },
});
```

Tools wrapped via `tool({...})` automatically surface as observations under the parent generation — no manual wrapping needed. Each tool call lands as an observation; in late-2025 Langfuse this maps cleanly to `type: tool`.

For multi-step `generateText`/`streamText` agent loops (`maxSteps > 1`), each step appears as a child generation under the parent. The naming convention applies at the outer call (`functionId: "chat-turn"`); the inner generations get auto-named by the SDK.

## Sub-agent handoff

When one `generateText` call delegates to another (e.g., supervisor → worker), nest them inside a manual span so the parent/child relationship and the role name survive:

```ts
import { trace } from "@opentelemetry/api";

const tracer = trace.getTracer("agent");

await tracer.startActiveSpan("research-agent", { attributes: { "langfuse.agent_role": "research-agent" } }, async (span) => {
  try {
    const out = await generateText({
      model,
      prompt: subAgentPrompt,
      experimental_telemetry: { isEnabled: true, functionId: "research-agent" },
    });
    span.setAttribute("output.summary", out.text.slice(0, 200));
    return out;
  } finally {
    span.end();
  }
});
```

`langfuse.<key>` attributes flow through to Langfuse metadata via the exporter.

## Tool wrapping detail

If the project hand-rolls tool execution (rather than letting the SDK do it), wrap each tool invocation in a span typed as `tool`:

```ts
await tracer.startActiveSpan(
  `tool.${toolId}`,
  { attributes: { "langfuse.observation.type": "tool", "tool_id": toolId } },
  async (span) => {
    span.setAttribute("input", JSON.stringify(args).slice(0, 4000));
    const result = await tools[toolId].execute(args);
    span.setAttribute("output", JSON.stringify(result).slice(0, 4000));
    return result;
  },
);
```

Cap input/output sizes when serialising — large blobs blow up trace storage and clutter dashboards.

## Common gotchas

- **`functionId` is what becomes the trace name.** If left empty, Langfuse falls back to `ai.generateText` and every trace looks identical.
- **Streaming**: telemetry is emitted on stream completion, not on stream start. If the process dies mid-stream, the trace is lost. For long-lived streams set a heartbeat span.
- **Edge runtime**: `@vercel/otel` works on Node.js runtime; for Edge, use the manual OTel + Langfuse exporter route. Note this on the per-file plan if any agent code is `runtime: "edge"`.
- **`maxSteps` agent loops** without `experimental_telemetry.isEnabled = true` produce one giant generation observation with no inner steps visible. Always enable telemetry on multi-step calls.

## What the plan should specify per file

For each file the agent touches:

1. Whether to enable `experimental_telemetry` and the `functionId` to use.
2. Whether the call is a leaf agent (single `generateText`) or a delegator (needs a wrapping span).
3. Where `sessionId` and `userId` are sourced.
4. Which tags apply (`env`, `stack`, `agent_version`, optional `feature_flag`).
