# Stage 9 validation and evidence plan

Status: **planned; no Stage 9 tests or sensitive-data processing executed**. [Stage guide](../README.md) · [Tasks](../../../tasks/stage-9-sensitive-data.md).

## Planned artifacts

| Artifact | Evidence required |
| --- | --- |
| `data-scope.md`, `sensitive-data-policy.json` | Approved purpose/categories/actors, PCI applicability review, allow/redact/tokenize/reject rules and real owners |
| `intake-results.json`, `detector-decision.md` | Selected formats/processors, parser isolation/resource bounds, destination approval and detector version/support |
| `redaction-evaluation.json` | Frozen synthetic ground truth, per-category precision/recall and errors, supported languages/formats, redaction/re-extraction/render checks |
| `boundary-results.json`, `storage-design.md` | Model/tool/stream/output/egress denials, owner/purpose-bound references, key/vault scope and negative access tests |
| `receipt-results.json` | Extracted-field integrity, uncertainty, duplicate/tamper cases, ownership and no implicit payment/action authorization |
| `lifecycle-results.json` | Actual copy inventory, retention/deletion deadlines, provider/backup limits, concurrent access/delete and cleanup outcomes |
| `incident-audit-results.json`, `adversarial-results.json` | Redacted incident metadata, outages/recovery, injection/exfiltration/cross-scope tests, failed/blocked cases and effect checks |
| `guardrail-layer-matrix.md`, `guardrail-layer-results.json` | Actual model assignments on both routes, supported intervention/actions, Agent Service applicability/inheritance/override if used, app/resource fallback gates and trusted policy selection |
| `user-data-controls-results.json` | Owner inspection/correction/delete/forget behavior, reviewed hold/backup limits, active-run/summary/checkpoint fences and foreign-owner denial |
| `sensitive-action-scope-results.json` | Tenant/user/agent/tool/resource/purpose binding, no cross-context consent/reference/approval reuse and positive controls |
| `sensitive-rendering-results.json` | Sanitized markup, streaming fragments, links/images/previews/exports and controlled synthetic-canary egress effects |
| `sensitive-data-review.md` | Exact release/policy/detector/format scope, reviewers, approval boundaries, residual risks and required re-evaluation triggers |

These are future deliverables, not placeholder pass results. Use synthetic fixtures or officially designated non-production test values; never capture real customer PII, usable payment credentials or raw sensitive inputs in evidence. Reports should retain category/decision/count metadata, scoped random references and hashes of approved artifacts, not hashes of low-entropy sensitive values that can be guessed.

## Adversarial scenarios (all pending)

1. Direct PII/card-like text in chat/tool arguments, logs, traces, errors and memory-save attempts; rejection before unauthorized dispatch/persistence.
2. Receipt photos, scanned PDFs, text layers, annotations, metadata and QR/barcodes containing identity/payment fields; redaction must survive re-extraction and export.
3. Unicode lookalikes, separators, OCR substitutions, encoded/fragmented data, multilingual fields and streaming chunk boundaries; measure misses and avoid overclaiming coverage.
4. Receipt instructions demanding policy override, secret disclosure, foreign-record access, external URL fetch or reimbursement; zero unauthorized effects.
5. Two real authorized owners with synthetic receipts, guessed IDs, shared-agent substitution, unapproved vault token/re-identification and confused-deputy attempts; positive owner controls and foreign-data denial.
6. Detector/parser timeout, service outage, unsupported/encrypted files, oversized/compressed input and missing policy; fail-closed or secure human-review behavior, no raw fallback.
7. Duplicate/tampered receipt, inconsistent totals/currency/dates, missing fields and uncertain extraction; no fabricated facts or implied payment/approval.
8. Delete/expiry/hold changes during active runs, checkpoints, exports and cleanup; no stale sensitive-data resurrection and explicit treatment of backups/provider copies.
9. Model/tool output reconstructs hidden values, embeds secrets in links/images or splits them across messages; unauthorized disclosure blocked before publication in the selected scope.
10. Alert/audit/evaluation failure paths; no sensitive payload dumps, unauthorized incident access or budget/accounting reset.

11. Model versus agent/app boundary tests: direct GPT-5 mini and GPT-5 calls, unsupported PII actions/intervention points, annotation-only versus blocking behavior, non-model MCP/storage paths, poisoned tool results and streaming. Test missing/weaker assignments, untrusted policy override attempts and drift; if using Foundry Agent Service later, verify custom-agent override/inheritance and actual tool support rather than assuming policies stack.

12. Sensitive-memory view/edit/delete/forget, current-purpose authorization, changed consent and active summary/checkpoint races; no hidden-value disclosure or stale resurrection.
13. Cross-user/tool/purpose permission reuse and generated link/image/HTML/preview/export exfiltration, including encoded and chunk-split payloads; measure actual controlled endpoint requests.

Freeze quality/safety thresholds before evaluation, classify each local versus hosted result, and record detector/provider/configuration changes. Synthetic passing tests support engineering review; they do not establish PCI certification, legal compliance or perfect anonymization.
