# Local release archive inventory

## September 17 corrected package

The final source package path is `C:\Users\Admin\ypgym-release-20260917.zip` (432 source files plus `ARCHIVE-CONTENTS.json`). Its exact ZIP bytes, SHA-256, base commit and exclusions are recorded in the adjacent `ypgym-release-20260917.inventory.json`. Inside the ZIP, the manifest records each source file's size and SHA-256. The inventory stays outside the archive so its checksum does not depend on itself. Corrective implementation commit: `a80dc02`; the final documentation/package checkpoint is the non-conflicting annotated local tag `v0.60.1`, preserving `v0.60.0`.

Package from the repository root after reviewing the working tree:

```powershell
git status --short
python -m unittest discover -s scripts -p 'test_*.py' -v
python scripts/package_release.py --output C:\Users\Admin\ypgym-release-20260917.zip
```

Use a new output name outside the repository for later runs; existing output is never overwritten. `git ls-files --cached --others --exclude-standard` supplies tracked files plus non-ignored additions. Review all additions before packaging: Git tracking alone is not a secret-content audit.

Included source covers backend/frontend/mobile/simulator code, tests, migrations, both npm lockfiles, Python requirements, Compose/Docker files, four placeholder environment examples, plans, technical documentation, BRD references, evidence, and six editable Draw.io sources/embedded previews. No new dependency is required.

Excluded paths cover `.git/`, `tmp/`, dependency/virtual-environment/build/cache folders, all `storage/`, uploads/generated/runtime data, private Maildir, databases, logs, private keys/certificates, editor temporary files and secret `.env*` files (only `.env.example` is eligible). Resolved source paths must remain inside the repository, including links. Three packaging tests cover exclusions, actual ZIP contents/hash manifest, and an out-of-tree symbolic link. ZIP CRC checks run automatically; release review additionally checks every manifest hash and required source paths.

The package is a local review/backup artifact, not a deployed service or published download. September 16's code and `v0.60.0` were pushed only after the user's explicit request. September 17 corrective work uses the original brief's authorized local commit/tag workflow; no new remote push is requested.

## Superseded September 16 archive

`C:\Users\Admin\ypgym-day60-20260916.zip` contains 16 runtime invoice PDFs under `backend/storage/invoices/`. The earlier claim that it excluded all generated/runtime data was incorrect. It is retained locally, superseded and unsuitable for sharing; it was not pushed/published. The replacement excludes the entire runtime storage tree. Normal application data was preserved.

## Review procedure

1. Confirm the sidecar SHA-256 matches `Get-FileHash <archive> -Algorithm SHA256`.
2. Open the ZIP and `ARCHIVE-CONTENTS.json`; confirm source/lockfiles/migrations/examples/diagrams/evidence are present and no runtime storage, real environment, private key, cache or dependency folder is present.
3. Extract to a new review folder and follow `README.md`, `mobile/README.md` and `docs/demo/demo-script.md`. Use standalone demo/test Compose projects for disposable data; preserve normal volumes.

Software checks and Android emulator evidence remain separate from missing proposal/research/human-UAT artifacts, physical phone/iOS checks, full accessibility evaluation, live settlement and deployment.

## September 17 completion record

Requirement: close Day57 documentation and Day60 local-package gaps without expanding frozen application scope. Reused the BRD/route/evidence indexes, existing API/services/models/tests and Draw.io layouts, Git inventory and Python standard library. No dependencies changed. No model, migration, constraint or normal stored-data change.

The review ZIP `C:\Users\Admin\ypgym-release-review-20260917.zip` passed CRC, all 432 per-file SHA-256 checks and required source/lockfile/migration/example checks. It contains six editable diagrams, six embedded previews and exactly four environment examples, with no prohibited runtime paths. A limited raw-content scan for private-key blocks and common GitHub/AWS/OpenAI token prefixes found zero matches; this is not an exhaustive secret audit. The final package uses the same tested filter.

| Changed file | Purpose |
|---|---|
| `.gitignore` | Version diagram sources/previews; ignore backups |
| `README.md` | Correct verification/push status; package commands |
| `docs/HANDOFF.md`, `handoff.md` | Recovery checkpoint and historical pointer |
| `scripts/package_release.py` | Filtered ZIP, source hashes and sidecar |
| `scripts/test_package_release.py` | Runtime/case/path/link/manifest regression checks |
| `docs/api/classes-booking-dashboard.md` | Actual PT-owned endpoint contract |
| `docs/architecture/system-architecture.md` | Release topology, Swagger, ports and PT boundary |
| `docs/database/erd.md` | Migration chain and table equivalents |
| `docs/policies/roles.md` | PT/member/backend permission boundaries |
| `docs/policies/security.md` | Archive privacy controls and limits |
| `docs/progress/day-43-60-tracker.md` | Dated milestone evidence |
| `docs/release/requirements-traceability.md` | FR1–FR39 platform/code/test matrix |
| `docs/release/bug-list.md`, `docs/release/feature-freeze.md` | Resolved blockers and remaining backlog |
| `docs/release/archive-inventory.md` | Archive correction and reproduction record |
| `docs/diagrams/README.md` | Available source authority and diagram index |
| `docs/diagrams/architecture.mmd`, `docs/diagrams/use-cases.mmd` | Worker/scanner/PT sketches |
| `docs/diagrams/backend-uml.mmd` | Actual representative classes |
| `docs/diagrams/ypgym-architecture.drawio`, `docs/diagrams/ypgym-architecture.drawio.png` | Expo/worker/transport labels and embedded preview |
| `docs/diagrams/ypgym-use-case.drawio`, `docs/diagrams/ypgym-use-case.drawio.png` | Staff/scanner/PT actions and wrapped legend |
| `docs/diagrams/ypgym-backend-uml.drawio`, `docs/diagrams/ypgym-backend-uml.drawio.png` | New editable UML and preview |
| `docs/diagrams/ypgym-domain-relationships.drawio`, `docs/diagrams/ypgym-domain-relationships.drawio.png` | Release/schema labels and refreshed preview |
| `docs/diagrams/ypgym-erd.drawio`, `docs/diagrams/ypgym-erd.drawio.png` | Existing source and full uncropped preview |
| `docs/diagrams/ypgym-membership-state-transition.drawio`, `docs/diagrams/ypgym-membership-state-transition.drawio.png` | Access/request/terminal notes and preview |

Verification commands executed from the repository root:

```powershell
git status --short
git log -5 --oneline
git tag --list 'v0.60.*'
python -m unittest discover -s scripts -p 'test_*.py' -v
docker compose config --quiet
docker compose -p ypgym-tests -f compose.test.yml config --quiet
docker compose -p ypgym-demo -f compose.demo.yml config --quiet
docker compose exec -T backend-api alembic current
docker compose exec -T backend-api alembic check
Invoke-RestMethod http://localhost:8001/api/v1/health | ConvertTo-Json -Compress
python scripts/package_release.py --output C:\Users\Admin\ypgym-release-review-20260917.zip
git diff --check
git diff --stat
git diff
git diff --cached --check
git diff --cached --stat
git commit -m "fix: exclude runtime data from release packages and reconcile documentation"
git commit -m "docs: record verified release package and recovery checkpoint"
python scripts/package_release.py --output C:\Users\Admin\ypgym-release-20260917.zip
git tag -a v0.60.1 -m "Corrected local source package, traceability and editable release diagrams"
```

All three packaging tests passed with no skips. Compose/health/Alembic checks passed. Application lint/build/102-test backend/native results are dated September16, not rerun for this packaging/documentation change. Draw.io `validate.py` ran against all six sources: zero errors; retained routing warnings are architecture37, use-case13, UML1, domain74, ERD217 and membership3. Exports used installed draw.io30.4.1 with `-x -f png -e --width <2000/2500/5000> -o <preview> <source>` via hidden `Start-Process`; `repair_png.py` ran after each embedded export. Previews were visually reviewed. Embedded XML/PNG CRC and ZIP manifest hashes were checked with Python without printing source or secret values.

Manual acceptance: rerun the packaging tests, choose a new outside-repository ZIP name, and check the sidecar hash/manifest/exclusions. Open the six diagrams and trace the mobile/API/PT/device/worker boundaries. Application journeys use the unchanged `docs/demo/demo-script.md` and `mobile/README.md`.

Remaining limitations: diagram crossings, physical phone/iOS and full accessibility checks; partial native account/lifecycle/email coverage; missing proposal/research/participant-UAT evidence; deferred FR39 without inferred approval. Suggested next task: real participant UAT and supplied research/proposal reconciliation. Frozen software features require a new requirement.
