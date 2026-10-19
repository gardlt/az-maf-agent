# Stage 3 — Approved Markdown skills

Stage 3 is implemented for the single-replica, non-commercial teaching environment.
Both user-selected skills are enabled in dev: `movie-research@1.0.0` compares movies,
and `movie-night@1.0.0` builds a shortlist from session preferences. Each adds reviewed
guidance to the same bounded TMDB tools. Neither grants authority or durable memory.
See [validation evidence](stage-3-validation.md).

## Trust and selection decisions

The approved registry is `skills/approved.json`, reviewed with its Markdown in Git and
shipped in the digest-pinned agent image. The index pins ID/version, owner, purpose,
input/output expectations, tool capabilities, and the SHA-256 of the exact UTF-8 bytes.
This uses a reviewed application-owned index rather than external artifact signatures.
An arbitrary file with no approved manifest/digest is rejected. Marketplace artifacts,
composition, dependencies, executable code, and automatic file/link expansion are
unsupported. Unexpected manifest fields, including dependencies, are rejected.

The two skills were chosen by the user. Research guides comparison and attribution;
planning guides preference questions and shortlist structure. Direct movie commands
remain useful for individual lookups. Separate bounded skills were preferred over a
generic agent that could install or compose arbitrary guidance. Revisit this choice
if evaluation shows no benefit over direct tool use; composition requires a new review.

## Run the skills

```sh
uv run --locked agent-chat --api https://ca-maf-agent-dev-eus2-01.kindisland-49d1cad2.eastus2.azurecontainerapps.io --skill movie-research
uv run --locked agent-chat --api https://ca-maf-agent-dev-eus2-01.kindisland-49d1cad2.eastus2.azurecontainerapps.io --skill movie-night
```

Try comparing two movie titles or asking for a movie-night suggestion. `--skill-version`
selects an exact approved version (default `1.0.0`). The API accepts `skill_id` and
`skill_version` on authenticated chat. An unconfigured server denies skill requests.
The CLI reuses its encrypted Entra cache. The deterministic offline boundary exercise
is `uv run --locked pytest -q apps/agent/tests/test_skills.py`; it needs no credentials.

## Runtime configuration and authority

The dev Bicep enables the existing Foundry `gpt-5` adapter and model-selected movie reads,
and sets `SKILL_BUNDLE=/app/skills`, `SKILL_CONTROL_RESOURCE_ID` to the existing dev
resource group, and `SKILL_ALLOWED_USERS` from the approved caller list.
The system-assigned workload identity has Reader on that resource group for control
reads and Foundry User on the existing Foundry account for inference. Its MCP calls
continue using the separately configured identity with only `Catalog.Read`.
Operator/deployment permissions are not given to the workload.

The control record lives in the resource group's `maf-skill-control` Azure tag. It is
non-secret metadata; the workload reads it through its managed identity and cannot
update tags. No additional Azure resource was created for this store. Operators need
tags/write on the group. The 256-character tag bound is enforced; this deliberately
small store supports the two-skill lesson, not a production control plane.

The loader looks up IDs before filesystem access, bounds regular-file reads to 8 KiB,
refuses final-component symlinks and escaping filenames, verifies the pinned digest,
and consumes the same immutable bytes. The root and ancestor directories are trusted
operator-owned paths. Caller, application, agent, and manifest capabilities intersect;
the caller callback defaults to no tools and is checked again at dispatch. Existing
MCP schemas, budgets, deadlines, ownership, reset, and cancellation remain enforced.
Model text cannot create a file, network, write, memory, or recursive-skill tool.

## Review, publication, and rollback

1. Review the skill's task, metadata, capabilities, and Markdown. Keep secrets out.
2. Give changed content a new version and version-specific filename; do not replace
   a published version's content. Calculate the SHA-256 from the exact bytes and add
   the manifest to the reviewed index. Retain older approved artifacts for rollback.
3. Run local boundary tests, lint, and integrity checks. Review the content and index
   together, commit, and deploy the digest-pinned image through the agent workflow.
   Changes to `skills/**` trigger CI and deployment.
4. Verify the selected version/digest in the response and content-free run audit.
   Roll back by selecting an older currently approved, non-revoked version and record
   the reviewed release/selection. A revoked version remains blocked.

Process-local `SkillRegistry.publish` rejects version conflicts. Production release
approval and image review remain operator responsibilities; no model-facing publication
endpoint exists. Adding a bundle version requires a reviewed deployment; disabling an
existing version does not.

## Disable, restore, and revoke without redeploy

Set `MAF_SKILL_CONTROL_RESOURCE_ID` to the existing dev resource group's Azure resource ID.
Run these commands under an operator Azure CLI sign-in:

```sh
uv run --locked python scripts/skill_control_azure.py status --resource-id "$MAF_SKILL_CONTROL_RESOURCE_ID"
uv run --locked python scripts/skill_control_azure.py disable --resource-id "$MAF_SKILL_CONTROL_RESOURCE_ID" --skill movie-night
uv run --locked python scripts/skill_control_azure.py enable --resource-id "$MAF_SKILL_CONTROL_RESOURCE_ID" --skill movie-night
```

`init` only initializes an absent record; it never clears existing controls. `revoke`
permanently blocks a version and `enable` refuses revoked versions. Operator commands
print action/version/control generation without private content. Run one operator at
a time: the workstation lock serializes local invocations, while cross-workstation
conditional updates require the Stage 5 control backend. Do not manually roll back
the control record. Capacity overflow fails rather than dropping revocations.

Every model attempt (including retries), tool dispatch, load, and final history commit
checks current control state without a cache. HTTP requests use a three-second timeout and at most one transient read retry;
load/dispatch gates have a ten-second overall bound under the existing run deadline.
A lower generation observed by the running process, missing/invalid control state,
redirect, or unavailable store denies work. An active accepted external call is not
undone; later model/tool work and history commits are fenced. Shared production
propagation, monotonic state across adversarial operator rollback/restarts, and global
shutdown remain Stage 5 work.

For local operator fixtures, the existing `SKILL_CONTROL` file adapter uses bounded,
validated state with atomic replacement and a local operator lock. Mount its directory
read-only to the app; only the separate operator identity may write it.

## Audit and limits

Run and load events bind policy, hashed caller reference, run ID, skill version/digest,
and registry/control generations without retaining Markdown, prompts, or movie text.
Unknown skill requests are represented by a hash; known loader denials include the
approved manifest binding. Backend invocation counts and unchanged-record comparisons
provide absence-of-effects evidence, independently of model refusal.

Case 4 remains mandatory Stage 4 work: once durable memory exists, test another user's
records and writes without consent at the actual memory layer. Stage 3 already denies
unavailable memory tool requests while keeping isolated short-term history. Stage 1's
remaining shared-session and expired-ingress-token gates are tracked separately.
