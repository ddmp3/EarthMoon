# T51 AI assistant for scientists (optional, after T50)

Read first: `CLAUDE.md`, `docs/plan/README.md` sections 1 to 3, and `docs/ARCHITECTURE.md`. Branch: `feat/T51-assistant`. Start only if David confirms after T50.

## Goal
Help a scientist ask questions in plain language ("where are terrains like mare plains with basaltic rock, at rover scale?") and get the corresponding query and an explanation of the results, without the assistant becoming a source of truth.

## Principles (non-negotiable)
These come from the ALAS doctrine in `_dev.project/CLAUDE.md`: the local truth engine computes, the LLM translates; the external oracle is the truth, never the LLM.
- The assistant **never computes or invents a number**. It translates a question into an API query (scenario, environment, criteria) and explains the API response, citing the fields and sources it returned.
- Every answer shows the query it ran, so it can be reproduced without the assistant.
- If the data cannot answer, the assistant says so.

## Steps
1. **ADR:** model and provider (default to the latest Claude model; read the `claude-api` skill before writing code), cost, where the API key lives (server side, never in the repository or the browser), rate limits, logging without personal data, prompt-injection risks.
2. **Evaluation set first:** 30 or more questions with expected queries and expected refusals. The test passes only if the assistant's queries match.
3. **Prototype:** an API endpoint that uses tool calls over the v3 endpoints only, and a chat panel in the UI behind a feature flag.
4. **Security review:** inputs, outputs, cost limits, dependencies.

## Done when
The evaluation set passes at a threshold David accepts, the security review is done, and the assistant is off by default.
