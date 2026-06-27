# Vendor detection

How to detect which AI-observability vendor a codebase already uses, so `/ratel-observability-assessment` can route to the matching vendor `*-integrate` skill. Scan three places per vendor: **manifest dependencies**, **environment variables**, and **typical init/import sites** in code. Treat a manifest dependency or an init/import site as a strong signal; an env var alone (it may be a leftover or a half-finished setup) as a weak signal — confirm with code where possible. Report a confidence level (high / medium / low) for the detected vendor in the proposal.

The vendor list below seeds from the observability vendors `ratel-assessment` already detects (Langfuse, LangSmith, OTel, OpenInference, OpenLLMetry, Helicone, homegrown), extended with the rest of the supported set.

## Langfuse

- **Manifest deps**: `langfuse` (Python), `langfuse` / `langfuse-langchain` (JS/TS), `langfuse.openai`.
- **Env vars**: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` (or `LANGFUSE_BASEURL`).
- **Init / import sites**: `from langfuse import Langfuse` / `get_client`; `from langfuse.openai import openai`; `from langfuse.decorators import observe` or `@observe`; `new Langfuse(...)` in JS; `import { Langfuse } from "langfuse"`; `CallbackHandler` from `langfuse.callback` wired into LangChain.

## LangSmith

- **Manifest deps**: `langsmith` (Python and JS/TS). Often alongside `langchain` / `langgraph` but not required (LangSmith traces non-LangChain code too).
- **Env vars**: `LANGSMITH_TRACING=true` (or legacy `LANGCHAIN_TRACING_V2=true`), `LANGSMITH_API_KEY` (or legacy `LANGCHAIN_API_KEY`), `LANGSMITH_PROJECT` / `LANGCHAIN_PROJECT`, `LANGSMITH_ENDPOINT`.
- **Init / import sites**: `from langsmith import Client` / `traceable`; `@traceable` decorator; `wrap_openai` from `langsmith.wrappers`; `RunTree`; in JS `import { Client } from "langsmith"` and `traceable` from `langsmith/traceable`. Any LangChain/LangGraph app with tracing env vars set is auto-traced to LangSmith even without explicit import sites.

## PostHog

- **Manifest deps**: `posthog` (Python), `posthog-js` / `posthog-node` (JS/TS). LLM-observability via `@posthog/ai` or the `posthog.ai` wrappers.
- **Env vars**: `POSTHOG_API_KEY` / `POSTHOG_PROJECT_API_KEY`, `POSTHOG_HOST`.
- **Init / import sites**: `posthog.capture(...)`; `from posthog.ai.openai import OpenAI` (the instrumented LLM wrapper); `new PostHog(apiKey, { host })` in JS; LLM events captured as `$ai_generation` / `$ai_span` events.

## Arize Phoenix

- **Manifest deps**: `arize-phoenix`, `arize-phoenix-otel`, `openinference-instrumentation-*` (e.g. `openinference-instrumentation-openai`, `-langchain`, `-llama-index`).
- **Env vars**: `PHOENIX_COLLECTOR_ENDPOINT`, `PHOENIX_CLIENT_HEADERS`, `PHOENIX_API_KEY`, `PHOENIX_PROJECT_NAME`.
- **Init / import sites**: `import phoenix as px` / `px.launch_app()`; `from phoenix.otel import register`; `register(project_name=...)`; `OpenAIInstrumentor().instrument()` and other OpenInference instrumentors. OpenInference is the semantic layer; Phoenix is the backend.

## Helicone

- **Manifest deps**: usually **no SDK** — Helicone is a proxy, so detection is configuration-shaped. May see `helicone` / `@helicone/helpers` for async logging or session helpers.
- **Env vars**: `HELICONE_API_KEY`, and a base-URL override pointing at Helicone (`oai.helicone.ai`, `gateway.helicone.ai`, or `*.helicone.ai`).
- **Init / import sites**: an OpenAI/Anthropic client whose `base_url` / `baseURL` is set to a Helicone gateway; `Helicone-Auth` header (`Bearer sk-helicone-...`) or other `Helicone-*` headers set on requests. The tell-tale is the rewritten base URL, not an import.

## OpenLLMetry / OpenTelemetry GenAI

- **Manifest deps**: `traceloop-sdk` (OpenLLMetry), `opentelemetry-sdk` + `opentelemetry-exporter-otlp`, `opentelemetry-instrumentation-*`, GenAI semantic-convention instrumentors (e.g. `opentelemetry-instrumentation-openai-v2`). In JS, `@traceloop/node-server-sdk`, `@opentelemetry/sdk-node`.
- **Env vars**: `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_HEADERS`, `OTEL_SERVICE_NAME`, `TRACELOOP_API_KEY`, `TRACELOOP_BASE_URL`.
- **Init / import sites**: `from traceloop.sdk import Traceloop` / `Traceloop.init()`; OTel `TracerProvider` setup with an OTLP span exporter; `@workflow` / `@task` decorators from Traceloop. Note this is a *protocol/backend-agnostic* path — the spans may land in any OTLP-compatible backend; treat it as "OTel GenAI" and ask the user which backend receives the spans.

## Braintrust

- **Manifest deps**: `braintrust` (Python and JS/TS), `autoevals`.
- **Env vars**: `BRAINTRUST_API_KEY`.
- **Init / import sites**: `import braintrust` / `from braintrust import init_logger, traced, wrap_openai`; `@traced` decorator; `wrap_openai(...)`; `Eval(...)` harness definitions; in JS `import { initLogger, traced, wrapOpenAI } from "braintrust"`.

## When nothing is detected

If none of the above produce even a weak signal, do **not** guess. Fall back to the AskUserQuestion step in the skill: ask which AI-observability tool the team uses (offer the supported vendors plus "none yet" and "other"). A wrong auto-detection routes the customer to the wrong integrate skill, which is worse than asking.

## Vendor → skill routing

| Detected vendor | Route to |
| --- | --- |
| Langfuse | [`/ratel-langfuse-integrate`](../../ratel-langfuse-integrate/SKILL.md) |
| LangSmith | [`/ratel-langsmith-integrate`](../../ratel-langsmith-integrate/SKILL.md) |
| PostHog | No concrete skill yet — the generic plan applies; `/ratel-posthog-integrate` can be authored on request. |
| Arize Phoenix | No concrete skill yet — the generic plan applies; `/ratel-phoenix-integrate` can be authored on request. |
| Helicone | No concrete skill yet — the generic plan applies; `/ratel-helicone-integrate` can be authored on request. |
| OpenLLMetry / OTel GenAI | No concrete skill yet — the generic plan applies; `/ratel-otel-integrate` can be authored on request. |
| Braintrust | No concrete skill yet — the generic plan applies; `/ratel-braintrust-integrate` can be authored on request. |
| None yet | Recommend adopting Langfuse or LangSmith, then route to the matching integrate skill. |

For any vendor without a concrete skill, the vendor-neutral proposal this skill writes is still fully actionable — it states what to instrument and which dashboards to build; only the exact SDK wiring and widget specs are deferred until a vendor skill is authored.
