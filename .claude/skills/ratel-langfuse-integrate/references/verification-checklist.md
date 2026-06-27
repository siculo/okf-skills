# Verification checklist

Six checks the customer can tick once instrumentation lands. Drop this section into every plan that `/ratel-langfuse-integrate` writes, so verification doesn't get skipped.

1. **One trace appears per externally meaningful unit.** Send a single chat turn / kick off a single job. Confirm exactly one trace shows up in Langfuse with the agreed trace name (e.g., `chat-turn`). If you see two traces or none, the entry-point wiring is wrong.

2. **`session_id` and `user_id` are on the trace AND on every child observation.** Open the trace, click into any child span, confirm both are present. Missing on children means propagation was set up but not invoked early enough.

3. **Sub-agent observations nest correctly.** If the trace involves a supervisor and at least one worker, the worker observation should appear *under* the supervisor in the tree view, not as a sibling. Flat siblings = lost parent context.

4. **Tool calls appear as observations of type `tool`, named `tool.<tool-id>`.** Filter the observations panel by type `tool`. Every tool the agent actually invoked should be present with the right id; no tool calls hiding inside generic `event` observations.

5. **At least one full A/B-able tag is set.** `env`, `stack`, and `agent_version` should appear on every trace. If a feature flag is in play, its arm should be set too. Dashboard pivots depend on these existing on day one — adding them later means re-running history.

6. **Cost and token usage are populated on generations.** Click a generation, confirm input/output token counts and computed cost are present. If they're empty, the provider integration isn't capturing usage (most common cause: using `from openai import OpenAI` instead of `from langfuse.openai import openai`, or missing the LangChain callback handler).

If any of these fail, fix before building the dashboards specced later in this plan. Dashboards built on missing data will mislead the team.
