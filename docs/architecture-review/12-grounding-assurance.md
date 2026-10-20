# 12 — Grounding assurance and limits of the proof

**Review question:** what evidence shows the agent uses relevant authorized sources, produces supportable answers and stays within authority? **Current answer:** source retrieval and enforceable action boundaries are evidenced; bounded quality checks pass; universal sentence-level grounding is not established.

## Separate the claims

| Assurance dimension | Current evidence | Claim that is not yet justified |
| --- | --- | --- |
| Source access | Pinned TMDB search/details GET adapter; stable source IDs/contract label; actual model→MCP traces | Every factual statement was retrieved, or upstream data is immutable/complete |
| Answer accuracy | Fixed expected title/year/ID marker checks pass 10/10 benign cases on both routes; selected public-movie replies reviewed | Full factuality or faithfulness for every response/domain/language |
| Faithfulness | Bounded tool results are supplied as untrusted context; model may use prior bounded context | Automatic per-sentence source citation/entailment or zero hallucination |
| Action authority | Exact tools/arguments, identity, current policy, budgets and dispatch gates; zero forbidden capabilities in finite audit exercises | Universal resistance to prompt injection or authorized consequential writes |
| User/data isolation | Trusted ownership, consent, Blob partition/fencing and local cross-user tests; hosted same-user lifecycle | Two-real-user hosted isolation or cross-replica race acceptance already completed |
| Freshness and transparency | Source-labeled records and trace/model/config versions; bounded not-found behavior | A guaranteed TMDB snapshot, completeness, freshness SLA or permanent model-version availability |

## What the application currently enforces

The dispatcher, not the model, controls which tool can run, its argument shape, the destination and its authority. Movie results cannot turn into shell/network/admin/write tools. Durable preferences require explicit owner consent and are untrusted data. Skills are reviewed guidance rather than authorization. These are hard application boundaries tested even with a fake model that follows malicious text.

TMDB is an external source of movie data, not an authorization source. Its `tmdb-v1` label versions the adapter contract, not the upstream record's historical state. Search returns a bounded result list, not a claim to list every movie. A model can answer directly or use earlier conversation context without making a fresh tool call. The current loop validates response/tool shape and limits; it does not validate every output sentence against retrieved facts. Do not present this implementation as an always-retrieve, citation-enforcing RAG product.

The separate 50-query read test proves the path returns source records. The 50-session adversarial exercise and Stage 6 audit add bounded no-forbidden-effect evidence. Neither proves that generated free text contains no unsupported factual claim. Model refusal, HTTP status and tool-call presence are each insufficient on their own.

## Demonstrated review chain

For a controlled movie lookup, retained evidence can bind the application source/image, configuration, user-scope checks, route, actual provider model, run/trace, approved tool dispatch, observed usage and unchanged backend state. Stage 6 verifies the expected movie marker while avoiding retention of private content. This supports the bounded claim: **the selected dev agent can retrieve TMDB facts and complete expected movie tasks through enforced read-only interfaces under the tested conditions**.

The quality result is 10 benign cases with coarse field markers, plus three selected same-user history responses. It is not a production grounding score. The film-analysis turn demonstrates useful general model knowledge and context retention; it is not evidence that every interpretive claim came from TMDB.

## Proposed extension R04 — evidence needed for stronger grounding

Before claiming broader grounded answering, agree a versioned public/synthetic fixture set and thresholds, then test both routes. Include exact expected movie facts/source IDs, relevant/irrelevant retrieval, ambiguity, no match, truncation, conflicting or stale values, malicious synopsis instructions and unsupported questions. Use owner-approved synthetic data for preferences and multi-user cases.

Distinguish deterministic field correctness, source-use/provenance coverage, unsupported-claim rate, appropriate uncertainty/abstention, permission/effect checks and acceptable task completion. Review sampled answers against exact returned fixture records; an LLM evaluator may assist but cannot grant permissions or alone establish truth. Freeze datasets/graders before scoring and retain failed results.

If product requirements call for source IDs/citations on every catalog fact or rejection of unsupported assertions, implement and validate that contract explicitly. Do not assume a prompt promising citations enforces it. New diagnostic content capture requires a reviewed data-minimization and retention policy; routine production traces remain content-free.

R04 is a proposed architectural assurance extension, not a completed feature or an authorization to deploy new infrastructure. The review must decide the required assurance level and accountable domain/quality owner.

## Source and evidence references

- [Actual adapter normalization and source labels](https://github.com/gardlt/az-maf-agent/blob/d65b5fc480a6eb8e593ac9fe0fd020dffd644b50/apps/movie-catalog-mcp/src/movie_catalog_mcp/tmdb.py)
- [Current tool loop and final text validation](https://github.com/gardlt/az-maf-agent/blob/d65b5fc480a6eb8e593ac9fe0fd020dffd644b50/apps/agent/src/az_maf_agent/model_tools.py)
- [Frozen evaluation inputs](https://github.com/gardlt/az-maf-agent/blob/d65b5fc480a6eb8e593ac9fe0fd020dffd644b50/config/stage5-evaluation.json)
- [Frozen marker grader](https://github.com/gardlt/az-maf-agent/blob/d65b5fc480a6eb8e593ac9fe0fd020dffd644b50/config/stage5-evaluation-grader.json)
- [Measured quality and limitations](https://github.com/gardlt/az-maf-agent/blob/d65b5fc480a6eb8e593ac9fe0fd020dffd644b50/docs/validation/stage-6-model-routing.md)
- [Protected no-forbidden-effect evidence](https://github.com/gardlt/az-maf-agent/blob/d65b5fc480a6eb8e593ac9fe0fd020dffd644b50/docs/validation/stage-6-security.json)
- [Two-user scenario still open](https://github.com/gardlt/az-maf-agent/blob/d65b5fc480a6eb8e593ac9fe0fd020dffd644b50/cybersecurity.md)

Related: [review index](README.md), [evidence register](09-evidence-register.md), [open review gates](10-review-gaps.md).
