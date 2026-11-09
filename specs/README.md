# YPGym specifications

Lightweight spec-driven development for the web-first multi-gym rollout. These files describe what each remaining package must do and how it is verified. They are written from the repository at commit `e161f32` on `codex/feat/web-multigym-foundation`.

## How to use these specs

1. Read the package spec before writing code. Every requirement has a stable ID, and every task points back to requirements and acceptance criteria.
2. Implement one package at a time, in order. One package is one focused commit. Nothing is pushed without the owner's explicit approval.
3. A task is done only when its acceptance criteria pass. Record the exact test and build results in the commit report.
4. If the code and a spec disagree, stop and raise it in [decisions.md](decisions.md). Do not edit code to match a spec silently, and do not edit a spec to match a bug.

## Index

| File | Purpose |
|---|---|
| [decisions.md](decisions.md) | Open decisions that need the owner's answer before the affected package starts |
| [completed-packages.md](completed-packages.md) | What Packages 1 to 4 actually deliver, with commits, evidence and known gaps |
| [package-05-member-dashboard/spec.md](package-05-member-dashboard/spec.md) | Member web dashboard and QR page |
| [package-06-management-workspaces/spec.md](package-06-management-workspaces/spec.md) | Staff, manager and owner workspaces |
| [package-07-form-reliability/spec.md](package-07-form-reliability/spec.md) | Shared Textarea and form repairs |
| [package-08-documentation/spec.md](package-08-documentation/spec.md) | Documentation and release evidence |
| [package-09-scanner-gym-awareness/spec.md](package-09-scanner-gym-awareness/spec.md) | Scanner app shows its gym and explains gym refusals |
| [package-10-member-mobile-gyms/spec.md](package-10-member-mobile-gyms/spec.md) | Member mobile app gym support |
| [traceability.md](traceability.md) | Business goal to requirement to package to code to test |

## Conventions

- **IDs.** `FR-DASH-###` for Package 5, `FR-OPS-###` for Package 6, `FR-FORM-###` for Package 7 and `FR-DOC-###` for Package 8. Acceptance criteria use `AC-` with the same suffix, for example `AC-DASH-001`. Tasks use `T5-01`, `T6-01` and so on.
- **Acceptance format.** Given, When, Then. Each one must be checkable by a test or by a stated manual step.
- **Status labels.** `IMPLEMENTED_VERIFIED` means code and a passing test exist. `IMPLEMENTED_UNTESTED` means code exists with no test. `PARTIALLY_IMPLEMENTED`, `PLANNED` and `NOT_FOUND` mean what they say.
- **Evidence.** A statement about existing behavior names the file or endpoint it came from. Anything without evidence is marked as an assumption.
- **Scope guard.** Native mobile, the scanner app, onboarding questionnaires, recommendations and online PT services are out of scope for Packages 5 to 8.

## Source of truth

1. The repository for existing behavior.
2. The Web-First Multi-Location Master Prompt for intended behavior.
3. Existing tests, migrations and `docs/` as supporting evidence.
4. Assumptions, always labeled as such.

## Fixed project rules

- Preserve the layering: endpoint, service, repository, model, PostgreSQL. Redis is a cache and message transport only.
- Backend authorization decides access. Hiding a control in React is not security.
- Branch selection is never an authorization mechanism.
- Reuse existing components, hooks and services before adding new ones. Add no dependency unless the installed ones cannot do the job.
