# Verification checklist (LangSmith)

Six checks the customer can tick once instrumentation lands. Drop this section into every plan `/ratel-langsmith-integrate` writes, so verification doesn't get skipped.

1. **One trace appears per externally meaningful unit.** Send a single chat turn / kick off a single job. Confirm exactly one trace shows up in the LangSmith project with the agreed root run name (e.g. `chat-turn`). Two traces or none means the entry-point wiring is wrong.

2. **The thread key is on the root AND every child run.** Open the trace, click into any child run, confirm `session_id` (or `thread_id` / `conversation_id`) is present in its metadata, and confirm the trace appears under a thread in the Threads view. Missing on children is the most common LangSmith mistake — metadata is **not** inherited, so it must be re-attached per run.

3. **Sub-agent runs nest correctly.** If the trace involves a supervisor and at least one worker, the worker run should appear *under* the supervisor in the run tree, not as a sibling. Flat siblings = lost parent run-tree context.

4. **Tool calls appear as runs of type `tool`, named `tool.<tool-id>`.** Filter the project's runs by `run type = tool`. Every tool the agent actually invoked should be present with the right id; no tool calls hiding inside `chain` or `llm` runs.

5. **At least one full A/B-able tag is set on the root run.** `env`, `stack`, and `agent_version` should appear on every root run. If a feature flag is in play, its arm (`feature_flag:tool_pool=...`) should be set too. Charts group by these (top 5); adding them later means re-running history.

6. **Cost and token usage are populated on `llm` runs.** Click an `llm` run, confirm prompt/completion/total token counts and computed cost are present. If empty, the model call isn't wrapped — most common cause: `from openai import OpenAI` / `new OpenAI()` without `wrap_openai` / `wrapOpenAI`, or an AI SDK call not routed through `wrapAISDK` / `experimental_telemetry`.

If any of these fail, fix before designing dashboards or running [`/ratel-langsmith-analyze`](../../ratel-langsmith-analyze/SKILL.md). Charts and analysis built on missing data mislead the team.
