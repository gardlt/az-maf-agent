# Stage 5 operator runbook

This runbook describes procedures awaiting hosted drill evidence. It is not a record that the drills passed. Use an independently authenticated operator workstation; never put its credentials in the agent, MCP, prompts, or tool configuration.

## One-call denial and component isolation

Read control policy status. Disable the named reviewed capability using its current epoch. Check the returned policy epoch and read it again in a new process. Watch all active revisions for stopped follow-on dispatch. A denied call has no permission to retry through another tool or endpoint. A component disable changes the epoch and invalidates older runs and approvals.

## One-run cancellation

The owning authenticated caller can inspect `GET /runs/{id}` and cancel through `POST /runs/{id}/cancel`. Cancellation is durable shared state. A cancellation acknowledgement is not evidence that a downstream provider stopped billing or that an accepted effect was undone. Inspect call receipts and unresolved status before attempting another operation. Session reset independently fences history commits and preserves counters.

## Global stop and control outage

Read status and run the separate operator `stop --expected-epoch N` command. Verify persisted global stop, blocked new admission, and absence of new protected dispatch after the declared ten-second containment target. Inventory every active revision and replica. If the policy store, shared state, audit store, or their authentication is unavailable, keep the service closed; do not select a local policy or reset the accounting document as a fallback.

A timed-out conditional write may have committed. Never blindly repeat consequential dispatch. Read the owner-scoped receipt and accounting through an independent successful request. Only confirmed ETag precondition failures can be automatically retried.

## Independent Azure stop

Prepare a dedicated synthetic worker with no consequential external effects. First persist global stop. Record all active revisions, replicas, queued work, and UTC start time from Azure. Use the operator's Azure control-plane authority to stop or isolate every worker revision. Independently query actual running status and replica inventory until no affected worker remains; a successful submission alone does not pass. Verify attempts to restart application work while policy is stopped cannot dispatch. A harmless negative permission probe must show that runtime identities lack this operator authority.

Do not perform the unresponsive-worker drill against the working learner app. Do not remove management/audit access. Record propagation times and any provider request already accepted. Platform stop cannot undo committed work or guarantee an immediate provider invoice stop.

## Reconciliation and recovery

Review outstanding reservations, observed usage receipts, approval consumption and simulated effect receipts. Preserve conservative reservations for unknown outcomes. Do not fabricate usage, clear state, or compensate a real effect without separate authorization. If a worker must be manually classified as contained with unknown usage, record independent platform evidence and the operator decision; a ledger repair tool for that decision remains to be implemented.

Repair or replace the affected component and validate its digest, identity, secrets and reviewed configuration. Keep global stop through deployment. After reconciliation, use explicit `recover --expected-epoch N`. Recovery preserves disabled capabilities. Enable a repaired component separately, then use a fresh session/run and newly issued approval for the canary. Confirm old approvals, queues and history cannot resume. Re-stop on recurrence.

## Rollback and credentials

Keep the prior digest and deployment parameters. Roll back the image while retaining the shared stopped policy, epoch, reservations and audit. Do not downgrade code past the shared-state schema it can validate; fail closed rather than reinterpret state. Check health privately before reopening dispatch.

For credential compromise, stop first, revoke/rotate the compromised credential at its issuer, update the approved secret reference, and check that the old credential fails. Never copy secret values into runbooks, evidence, logs or chat. Review protected audit access and retention separately from supplemental traces. The precise hosted Key Vault/rotation and image rollback drills remain release gates.
