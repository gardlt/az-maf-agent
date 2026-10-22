# Movie Guide response boundaries

All movie-tool chat runs receive the shared instructions in
`apps/agent/src/az_maf_agent/response_policy.py`, before any selected skill guidance.
They apply to ordinary API/AG-UI chat and explicitly selected skills. The separate
text-only offline teaching assistant has no movie tools and retains its own scope.

The guidance covers environment/configuration disclosure, script requests and their
follow-ups, internal service enumeration, accurate capability descriptions, and public
TMDB attribution. It tells the model to avoid retrieval commands, unsupported offers,
private endpoint guesses, and invented knowledge-cutoff or execution claims. Ordinary
movie titles with security-related words remain valid requests.

The model receives the conversation history needed to resolve “them” and “run it”.
If history has been cleared or trimmed, the agent may need clarification; it cannot
recover missing context. This is response guidance, not an intent classifier or a
security boundary. The application still exposes only the approved read tools and
validates every dispatch. No keyword filter or automatic identity-disable trigger
was introduced.

## Verification

`apps/agent/tests/test_response_policy.py` checks that the shared instructions and
follow-up context reach ordinary chat and all approved skill versions, that attempted
environment/script/network tool calls fail before effects, and that a movie title
containing “Secrets” can still use movie search. These deterministic transport fixtures
do not establish live model compliance.

After deploying the candidate image, run the hosted evaluation with an authorized
operator's cached agent CLI sign-in:

```sh
uv run --locked python scripts/evaluate_response_policy.py --report /private/tmp/response-policy-chat.json
uv run --locked python scripts/evaluate_response_policy.py --skill movie-night --skill-version 1.1.0 --report /private/tmp/response-policy-night.json
uv run --locked python scripts/evaluate_response_policy.py --skill movie-research --skill-version 1.1.0 --report /private/tmp/response-policy-research.json
```

The fixed dev runner uses eight cases / ten turns per invocation, creates an isolated
session for each case, clears its history afterward, and respects existing budgets.
It stops on HTTP failures; budget/service errors are not counted as successful refusals.
Reports are created exclusively with owner-only permissions and retain answers for
human review. Keep them local: a model failing this evaluation could emit sensitive
content. No token or response body is printed to the terminal. Cross-reference run IDs
with the deployed revision and protected dispatch audit before accepting results.

Review the expectations in `config/response-policy-evaluation.json`. Require all
security cases to decline the unsupported action without retrieval code, false claims,
or sensitive values, and require the legitimate movie/public-source cases to remain
helpful. Verify pronoun resolution across both multi-turn cases. Repeat for supported
model routes and skill versions before promoting a model or prompt change. A finite
passing sample is evidence, not a guarantee about every possible prompt.

Current evidence: local deterministic checks only; no hosted model-response pass is
claimed until the updated deployment has been exercised and its outputs reviewed.


## Flexible response pattern

This is an application convention, not an industry-mandated refusal standard:

1. State the specific capability or access limitation in plain language.
2. Give a brief reason only when it helps the user understand what to do next.
3. Offer one supported next step, such as movie lookup or contacting the deployment
   administrator for configuration issues.

Aim for one to three natural sentences, adapting wording to the conversation.
Do not repeat a generic refusal preamble on every follow-up. A mixed request may have
an unsupported portion and a legitimate movie question; answer the supported part.
Public-source questions should receive a direct answer, not an unnecessary refusal.
These are model instructions; exact wording is not guaranteed or enforced by a
keyword-based response filter.
