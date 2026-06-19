# M1 Verification Failure Investigation

**Date**: 2026-06-19
**Trigger**: Step A in `docs/AUDITS/M1_VERIFICATION_REPORT.md` failed with
```
failed to resolve reference "docker.io/paradedb/paradedb:stable":
docker.io/paradedb/paradedb:stable: not found
```
**Severity**: **M1 BLOCKER**. Compose up is the entry gate for every other
verification step.

---

## 1. Root Cause

The configured image tag `paradedb/paradedb:stable` does not exist on the
public Docker Hub. The repository `paradedb/paradedb` is real and
actively maintained, but its published tag inventory is structured by
PostgreSQL major-version lineage (`pg16`, `pg17`, `pg18`, `latest`) and
by explicit version pins (`0.24.0-pg17`, `v0.24.0-pg17`, etc.). There is
no `stable` alias.

Concrete data points from the Docker Hub (`/v2/repositories/paradedb/paradedb/tags`)
live snapshot as of 2026-06-19:

- `latest` → present; digest `660c6941e...`; last_pushed 2026-06-03;
  corresponds to the `pg18` lineage image.
- `pg16` → present; digest `a34d03f1b...`; published 2026-06-03.
- `pg17` → present; digest `e1914ec2f...`; published 2026-06-03.
- `pg18` → present; digest `660c6941e...`; same digest as `latest`.
- `0.24.0-pg17` and friends → present (pinned-by-version).
- `stable` → not present in the public catalog.

The image we asked for therefore matches the literal "not found"
diagnostic returned by the Docker daemon. No DNS, registry
authentication, or network issue is implied. The tag is simply a
non-existent artefact.

Authoring fault: the M1 dev compose file (commit `38a1efa`,
`docker/compose.dev.yml`) was written with an assumed `stable` alias
that does not exist in the upstream catalog. ADR-0002 explicitly stated
`The Docker image tag is set to stable for M1 verification`, which
encoded a naming assumption that turned out to be wrong.

## 2. Correct Image and Tag

Three equivalent candidates from the live Docker Hub catalog:

| Candidate | Image:Tag | Postgres major | pg_search bundled? | Last_pushed |
|---|---|---|---|---|
| **Recommended (default dev tag)** | `paradedb/paradedb:latest` | PG 18 | yes | 2026-06-03 |
| **LTS-likely** | `paradedb/paradedb:pg17` | PG 17 | yes | 2026-06-03 |
| **Maximum reproducibility** | `paradedb/paradedb:0.24.0-pg17` | PG 17 | yes (pinned version) | 2026-05-28 |

Notes:

- The image ships the `pg_search` extension libraries. The migration
  `001_extensions.up.sql` `CREATE EXTENSION IF NOT EXISTS pg_search`
  will succeed against any of these tags because the libraries are
  in the image's `$libdir` and `share/extension/`. Only `CREATE EXTENSION`
  (not `CREATE EXTENSION ... CASCADE`) is needed. **This is not
  system-breaking; the catalog presence is the only defect.**
- Both `pg16` and `pg17` tags were pushed on the same date and have
  roughly the same pg_search lineage. Picking `pg17` keeps the project
  on an LTS-style Postgres major for the dev environment, without
  forcing an immediate decision about PG 18.
- The `0.24.0-pg17` tag is fully reproducible; a developer who pulls
  it tomorrow gets the same image as today. Plain `latest`/`pgNN` tags
  can move underfoot; pinning is preferable for a dev compose but
  doubles as "drift" for project-image maintenance.

**No other assumption in the M1 stack is broken.** The schema,
migrations, indexes, fixtures, and migration runners are correct in
isolation. The compose file is the only M1 artefact that needs to
change.

## 3. ADR Implications

ADR-0002 (`docs/adr/0002-pg-search-paradedb.md`) currently states:

> The Docker image tag is set to `stable` for M1 verification and can
> be overridden per environment.

This sentence is factually wrong with respect to Docker Hub's catalog.
The decision (use ParadeDB `pg_search`) is sound. Only the example tag
name is incorrect. The minimal ADR correction is to replace the literal
`s tag name. ADR-0002 is a non-architectural clarification of an
implementation detail documented inside an accepted ADR, which

- per AGENTS.md "Change Control Rules" / "Small documentation edits
  that restate existing decisions do not require an ADR.advances in
  the catalog; the architecture itself is unchanged.

**Recommendation**: amend the relevant paragraph in ADR-0002 in
place at the same commit that fixes the compose file. Create a brief
changelog row in `MEMORY.md`. A new ADR is **not** required because
the architecturally significant choice (ParadeDB `pg_search`) is
already captured in ADR-0002 and remains correct.

## 4. Files Requiring Updates

Files touched by this investigation:

- `docker/compose.dev.yml` (the `image:` line: change `paradedb/paradedb:stable` → picked tag).
- `docs/adr/0002-pg-search-paradedb.md` (correct the wrong tag example in the prose).
- `docs/AUDITS/M1_VERIFICATION_REPORT.md` (the Procedure section
  mentions "Postgres plus `pg_search`" but does
  not name an image; no edit needed unless we want to record the
  corrected `docker compose up -d` outcome with the chosen tag).
- `docs/HANDOFF/CURRENT_STATE.md`, `docs/HANDOFF/KNOWN_ISSUES.md`,
  `MEMORY.md`, `NEXT_AGENT.md`: add a row noting
  the image-tag correction and a new known issue if a re-verification
  pass picks up something new.
- `docs/AUDITS/M1_VERIFICATION_REPORT.md` "Results" table: add a row
  capturing Step A outcome once the corrected tag is used.
- `docs/AUDITS/FINDINGS.md` (audit follow-up): appendix F-21
  documenting the original incorrect tag, severity, and fix.

Files **not** touched:

- `migrations/*.sql` — schema is unchanged. `pg_search` extension is
  installed via `001_extensions.up.sql`, consistent with all three
  candidate images.
- `infrastructure/migrations/{apply,rollback}.sh` — correct.
- `db/fixtures/*` — correct.
- ADRs 0003 and 0004 — unrelated to the image catalog.

## 5. Whether This Changes Any ADR

No new ADR. Amend ADR-0002's example tag in place, document a
follow-up row in `MEMORY.md`, and append a row to
`docs/AUDITS/FINDINGS.md` (F-21). Reasons:

- Architecture-level decision remains `pg_search` is the lexical
  retrieval extension.
- Vendor-level decision remains ParadeDB.
- Image-level tag is a deployment-layer decision that ADR-0002
  already correctly separates from architecture.

AGENTS.md allows docs edits that restate existing decisions without
an ADR; this is precisely such an edit.

## 6. Whether M1 Verification Can Continue After the Fix

Yes. The fix is one-line in the compose file. After the developer
re-runs Step A with the corrected tag, every other step in
`docs/AUDITS/M1_VERIFICATION_REPORT.md` (B-I) remains valid and
unchanged. The M1 deliverable as a whole is otherwise sound: schema,
migrations, indexes, fixtures, and runners have been independently
audited (`docs/AUDITS/M1_REMEDIATION_REPORT.md`) and were free of
the kind of breakage that would block verification beyond Step A.

Treating F-21 as a single line item allows the developer to re-run
Step A and continue from Step B without re-validating the rest of
the pipeline.

## 7. Proposed Minimal Fix

Change the image line in `docker/compose.dev.yml` to:

```yaml
services:
  postgres:
    image: paradedb/paradedb:pg17
    environment:
```

(`pg17` chosen as the practical default — pinned to a Postgres major,
no `latest` drift, ships the required `pg_search` extension. If
the developer prefers fully-pinned reproducibility, swap
`pg17` for `0.24.0-pg17`.)

Update the relevant paragraph in ADR-0002:

> The Docker image tag is set to `stable` for M1 verification and can
> be overridden per environment.

becomes

> The Docker image used at M1 verification is
> `paradedb/paradedb:pg17` (Postgres 17 baseline; the `pg_search`
> extension ships inside the image and is activated through
> 001_extensions.up.sql). Production deployments pin the image by
> digest; the dev image is overridable through the compose file.

Add a `Known Issues` row I-012 to `docs/HANDOFF/KNOWN_ISSUES.md`
describing this finding; mark it resolved once F-21 is closed.

Add a row to `MEMORY.md` documenting the pinned image choice:

> | 2026-06-19 | Dev compose uses `paradedb/paradedb:pg17`. The `pg_search`
> extension is bundled in the image; the schema migration activates
> it via `CREATE EXTENSION IF NOT EXISTS pg_search`. Overridable per
> environment but not pinned at the schema layer. | `docker/compose.dev.yml`,
> ADR-0002 |

---

## 8. Recommendation To User

Apply the minimal fix above (one line in compose + ADR-0002
paragraph correction + audit/memory rows). All other M1 deliverable
artifacts remain correct. M1 verification can continue from Step A
onward.

Do not begin M2. Stay within M1's investigation scope.
