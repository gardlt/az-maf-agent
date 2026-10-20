# Stage 9: Sensitive-data guardrails — PII, payment data and receipts

Status: **planned, documentation only**, 2026-10-20. No sensitive-data upload, payment processing or new storage/detection service is enabled.

[All stages](../README.md) · [Tasks](../../tasks/stage-9-sensitive-data.md) · [Validation plan](validation/README.md) · [Stage 8 general DLP](../../tasks/stage-8-operational-readiness.md)

## Goal and scope

Prevent inappropriate collection, disclosure, persistence or reuse of personally identifiable information (PII), payment-card/account data and receipt contents throughout the agent lifecycle. Apply policy before model/tool dispatch, storage and output publication—not just a prompt asking the model to be careful.

Stage 8 defines general injection, data-egress, output and authority controls. Stage 9 specializes them with a field-level sensitive-data policy, receipt/document ingestion boundaries, payment-data exclusions and lifecycle assurance. Existing Stage 4 movie preferences do not authorize saving financial documents or new classes of personal data. Existing simulated-action receipts are authorization/accounting records, not uploaded merchant receipts or proof of payment.

Start with synthetic fixtures. Real receipt ingestion, OCR, external PII detectors, storage, jurisdiction/retention decisions and any financial action require a separately selected scope. Do not silently turn the movie agent into a payment processor, expense system or sensitive-document repository.

## Enforcement layers: Foundry models, Foundry agents and our application

The same named Foundry guardrail can be assigned to models or supported agents, but supported controls/intervention points differ. A policy assignment is not proof that every risk or tool is scanned. The following reflects Microsoft documentation reviewed on 2026-10-20 and must be re-verified against the selected region, model, API version and tool during implementation.

| Layer | Scope and implementation requirement | Stage 9 validation |
| --- | --- | --- |
| Foundry model deployment | Service-side prompt/response filtering; not a modification to model weights. Inventory and explicitly verify effective assignments on both GPT-5 mini and GPT-5, including supported PII controls, actions and API behavior. | Direct calls to each deployment, blocked/allowed synthetic cases, streaming/error annotations, routing changes and drift; do not infer protection from a portal label. |
| Foundry Agent Service | Agent guardrails are preview. Supported agent/tool configurations can add tool-call and tool-response intervention points. A custom agent guardrail overrides its model policy; without one, the agent inherits the underlying deployment policy. This is not automatically a union or strictest-policy merge. | If this runtime is adopted later, prove effective inheritance/override, applicable controls and supported tool moderation; no weaker or missing control may be silently accepted. |
| Our Container Apps agent and FastMCP | The current application is not a Foundry Agent Service agent. Agents view/control-plane visibility does not automatically enable those agent-level controls. Enforce sensitive-data checks around our own input, model context, tool arguments/results, memory/checkpoints and output publication. | Probe paths that do not call a model, poisoned tool responses, foreign-user data, direct storage access and raw-data rejection before dispatch; model-level output filtering alone is insufficient. |
| Resource and identity boundaries | Separate ownership/RBAC, storage/key/token-vault authority, network/destination controls, audit/retention and Stage 7 quarantine apply independently of content classification. | Cached/alternate credential bypass, re-identification, prohibited persistence and detector/controller outages; zero unauthorized sensitive effects. |

For receipts, minimize/redact/reject before sending text or images into model context. Recheck tool boundaries and final/streamed output; do not rely on output filtering to undo an earlier disclosure. A PII control's supported category, intervention point, redaction/block action and region/version must be verified explicitly. If unavailable, implement a reviewed independent gate or reject that route; never silently skip the check.

Bind guardrail selection to trusted deployment/server configuration. User headers, prompt text, retrieved content and tool arguments cannot select a weaker policy or enable annotation-only behavior. Verify annotations versus actual blocking, unsupported controls, fallback/routing behavior and any request-time override paths. Guardrail service calls themselves are data disclosures to a processor and belong in the approved destination inventory.

Primary references: [Foundry guardrails overview and inheritance](https://learn.microsoft.com/en-us/azure/foundry/guardrails/guardrails-overview), [intervention points and tool support](https://learn.microsoft.com/en-us/azure/foundry/guardrails/intervention-points), [configuration and deployment assignment](https://learn.microsoft.com/en-us/azure/foundry/guardrails/how-to-create-guardrails). These describe capabilities, not current configuration or passing tests for this repository.

## Proposed default data policy to review before implementation

| Data | Default agent handling | Required review boundary |
| --- | --- | --- |
| Names, addresses, email/phone, government identifiers and other identifying fields | Minimize/reject unless necessary for the approved purpose; redact or replace with scoped opaque references before general model/tool use | Actual data categories, purpose, authority, permitted viewers/destinations, detector coverage and privacy obligations |
| Full primary account number (PAN) and other raw cardholder data | No general-model, ordinary tool, history, memory, trace or evidence payload; reject or route outside the agent to an approved payment boundary | Receiving/transmitting such data may itself affect PCI scope; redaction is not an out-of-scope guarantee |
| CVV/CVC, PIN/PIN block, full track data and other sensitive authentication data | Not accepted or retained by this application; fail before onward dispatch/storage and keep raw values out of error handling | PCI requirements and any specialized issuing/payment use case require qualified review; encryption is not a reason to retain prohibited data |
| Masked/truncated card details and payment-provider tokens | Only reviewed minimal fields/references; no assumption that masking or tokenization makes all data nonsensitive | Masking, truncation, reversible tokenization, access scope and re-identification are different controls |
| Merchant receipts, invoices and transaction records | Approved structured fields only; bind owner/purpose; redact identity/payment fields and inspect images, text layers, metadata, QR/barcodes and attachments | Receipts may combine PII, payment data and sensitive purchasing information; define authorized extraction and retention explicitly |
| Model output, streams, logs, audit, evaluation data and exports | Content-free metadata or approved redacted fields; prevent reassembly/disclosure across chunks, runs and destinations | Detection failures, false positives, downstream copies and incident evidence policy |

Use least-privileged service identities, encrypted transport/storage and scoped references. Keep any reversible token vault/re-identification authority outside the model-facing agent; not every workflow needs reversible tokens. Never invent an encryption scheme or put encryption keys in prompts/config artifacts. Shared-resource controls must preserve unrelated users/agents and independent incident response.

## Receipt/document processing boundary (planned)

Authorize owner and purpose → bound/validate file type and size → isolate parser/OCR → classify extracted text and nontext content → minimize/redact/reject → validate allowed structured receipt fields → dispatch only approved derived data → recheck output/egress → apply reviewed retention/deletion.

Document content is untrusted instruction input. Embedded prompts cannot change policy, reveal another receipt, select a destination, authorize reimbursement or trigger a payment. Validate totals/currencies/dates and mark extraction uncertainty; do not invent missing fields or treat a receipt as proof that an external transaction settled. Model-proposed edits/refunds/reimbursements stay outside this stage unless separately authorized through Stage 8 action controls.

Visible black boxes or masked UI text do not establish permanent redaction of original files. Test hidden text, searchable layers, image crops/thumbnails, annotations, metadata, encoded data and generated exports. Limit parser resources, reject unsupported/encrypted content under the frozen policy and prevent automatic URL/attachment fetching.

## Lifecycle and failure behavior

Inventory raw inputs, sanitized records, checkpoints, sessions, prompts, temporary files, caches, OCR/detector jobs, Blob copies/versions/backups, exports and provider retention. Define retention/deletion and any legal hold per data purpose with a real accountable owner; do not inherit the 30-day movie preference policy for receipts. Consent alone does not establish permission to collect every data type or override payment-data restrictions.

An unavailable detector, unsupported language/format, low-confidence extraction, timeout or ambiguous classification must use an explicit fail-closed/review policy before sensitive dispatch; it cannot silently pass raw input to the model. Human review needs its own secure viewer and access policy. The model cannot approve exceptions or re-identify records. Incidents retain only authorized evidence and trigger scoped containment; no payload dump into alert notifications.

## User control, action scope and rendering

[S9-13–15](../../tasks/stage-9-sensitive-data.md) explicitly extend existing controls: users can inspect, correct and delete approved sensitive derived memories; permissions/consent cannot be reused across users, tools or purposes; and generated Markdown/HTML, links, images, previews and exports must not disclose protected data. These tasks specialize Stage 4 memory lifecycle and Stage 8 authority/rendering controls. They do not authorize raw payment-data memory, new financial actions or sensitive receipt collection.

## Microsoft and PCI SSC references

Reviewed 2026-10-20; re-verify the selected standard/version, service and deployment during implementation.

- [PCI SSC FAQ 1280 — card verification codes](https://www.pcisecuritystandards.org/faqs/1280/): explains restrictions on storage of card verification codes after authorization. This application selects the stricter scope of not accepting them.
- [PCI SSC FAQ 1146 — masking versus truncation](https://www.pcisecuritystandards.org/faqs/1146/): display concealment does not by itself remove the underlying stored account number.
- [Azure Language PII overview](https://learn.microsoft.com/en-us/azure/ai-services/language-service/personally-identifiable-information/overview): candidate text/conversation/document classification and redaction capabilities; no service is selected by this plan.
- [Microsoft PII transparency note](https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/language-service/transparency-note-personally-identifiable-information): detection has coverage/performance limits that must be evaluated for the intended use.

These are engineering tasks, not a claim of PCI certification, legal compliance, automatic anonymization or perfect PII detection. Establish actual applicability and scope with the responsible privacy/security/payment reviewers before processing real data.
