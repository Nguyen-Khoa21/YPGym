# Package 7: form reliability

**Status:** `PLANNED`. Independent of Packages 5 and 6, but ordered after them. Web only. Browser-level tests depend on decision D-02 in [decisions.md](../decisions.md).

## Purpose

Operators must be able to type into every management form. The broadcast page showed a narrow, unstyled Message box next to a normal Title box. This package fixes the cause once, in the shared form module, and then checks the rest of the web app for the same problem. It supports goal G4 (managers can operate their branch) and keeps the broadcast flow from Package 4 usable.

## What exists today (evidence)

- `components/ui/Form.tsx` exports `Field`, `Label`, `Input` and `FieldError`. There is no `Textarea`.
- `Input` has `w-full`, a card background, border, radius, padding, focus ring, placeholder colour and a disabled state.
- The broadcast Message field is a raw `<textarea className="min-h-28 rounded-md border border-input p-3 text-sm">` in `AdminBroadcastsPage.tsx`. It has no `w-full`, no card background and no focus style, so it does not match the Title `Input` beside it.
- `Label` renders a `<label>` with no `htmlFor`, and `Input` has no `id`, so labels are not tied to their controls. `FieldError` has no id and no control references it. Across `frontend/src`, only about 20 lines mention `aria-invalid`, `aria-describedby` or `htmlFor`.
- Raw `<textarea>` elements (14) appear in 8 files: `AdminBroadcastsPage`, `AdminMemberDetailPage` (4), `AdminMembershipApprovalsPage`, `AdminAttendancePage`, `AdminClassesPage` (2), `AdminTrainersPage`, `MembershipRequestsPage` (2), `AdminTrainingPage`.
- Raw `<input>` elements appear in 13 files, among them `AdminBillingPage` (4), `AdminMembersPage` (3), `AdminTrainingPage` (6), `AdminSettingsPage`, `AdminAuditPage`, `AdminAttendancePage`, `BuyMembershipPage` (2), `MemberTrainingPage` (2).
- Modal controls are styled by `.ops-modal__panel input/select/textarea` and `.ops-modal__body textarea` in `index.css`, not by the shared components.
- Web tests are `node --test` files in `frontend/tests/` with no DOM library. `@playwright/test` is a devDependency, but there is no Playwright config and no e2e folder.

## Functional requirements

| ID | Requirement |
|---|---|
| FR-FORM-001 | `Form.tsx` exports a `Textarea` that takes standard textarea attributes and matches `Input`: full width, card background, same border, radius, padding, text size, focus ring, placeholder colour, disabled state, and a visible error state. It keeps a sensible minimum height and vertical resize. |
| FR-FORM-002 | The broadcast Message field uses `Textarea`. Title and Message render with the same width and styling. |
| FR-FORM-003 | Every label is tied to its control with `htmlFor` and `id`. The pairing is automatic wherever `Field`, `Label` and `Input` or `Textarea` are used together, so existing call sites are fixed without edits. |
| FR-FORM-004 | When a field has an error, the control has `aria-invalid="true"` and `aria-describedby` pointing at the `FieldError` element, which has a matching id. |
| FR-FORM-005 | All raw `<input>` and `<textarea>` elements are reviewed. Each is migrated to the shared components, or recorded with a reason as intentionally custom (for example a compact toolbar filter, or a modal field styled by `.ops-modal__panel`). Controls that cannot accept typing, lose controlled state, overlap their label, or render at intrinsic width are repaired. |
| FR-FORM-006 | React Hook Form registration and Zod validation keep working unchanged: `{...form.register("name")}` works on `Input` and `Textarea`, and validation messages still appear on submit. |
| FR-FORM-007 | Global and component CSS is checked for selectors that give form controls unintended flex, width, pointer-events, z-index or positioning. Findings and fixes are recorded. |
| FR-FORM-008 | Forms stay usable from 320 px to desktop width: controls are full width of their field, and no control overlaps its label or the next field. |
| FR-FORM-009 | Keyboard use works: Tab reaches each control in visual order, the focus ring is visible, and Enter inside a textarea adds a new line and does not submit the form. |
| FR-FORM-010 | Resetting or reopening the broadcast form clears the values and the validation errors. |

## Non-functional requirements

- **NFR-FORM-001.** No new runtime dependency. Use React and the existing utilities (`cn`). A new `devDependency` configuration is allowed only if decision D-02 says so.
- **NFR-FORM-002.** Visual change is limited to what is needed to make controls consistent. Pages that already look right must not change appearance.
- **NFR-FORM-003.** Modal forms are migrated only after confirming the result is identical to the current `.ops-modal__panel` look, because those styles currently override the controls.

## Design note (recommended, smallest change)

Let `Field` create an id with React `useId` and share it through a small context. `Label`, `Input`, `Textarea` and `FieldError` read it to set `htmlFor`, `id`, and the error id. Controls that need a different id can still pass `id`. This fixes FR-FORM-003 and FR-FORM-004 for every existing `Field` without touching call sites. `Field` does not know whether it has an error, so `aria-invalid` and `aria-describedby` are set when `FieldError` receives a message; the simplest way is for the page to pass `aria-invalid` from `formState.errors`, or for `FieldError` to register its id with `Field`. The implementer picks one and records it.

## Acceptance criteria

Steps marked **(browser)** need a real browser and depend on decision D-02. The others can be checked with `renderToStaticMarkup` in the existing `node --test` setup.

**AC-FORM-001** Given the shared module, when `Textarea` is rendered, then its markup contains `w-full`, the card background class, the focus ring classes and the disabled classes used by `Input`.

**AC-FORM-002** Given a `Field` containing `Label`, `Input` and `FieldError`, when it is rendered, then the label's `htmlFor` equals the input's `id`, and the error element has an id that the input lists in `aria-describedby` when an error is present.

**AC-FORM-003** Given the broadcast page, when it renders, then the Message control is the shared `Textarea` and the Title and Message controls have the same class for width and border. **(browser)** Their rendered widths differ by at most 1 px.

**AC-FORM-004 (browser)** Given the broadcast form, when the user clicks Title, types "Maintenance window", then deletes the last word and types "notice", then the field shows "Maintenance notice".

**AC-FORM-005 (browser)** Given the broadcast form, when the user clicks Message and types two lines separated by Enter, then the field contains both lines and the form is not submitted.

**AC-FORM-006 (browser)** Given an empty broadcast form, when the user submits it, then Title and Message show validation messages, both controls have `aria-invalid="true"`, and each control's `aria-describedby` points to its message.

**AC-FORM-007 (browser)** Given valid values, when the user submits, then the request to `/admin/broadcasts` contains the typed title and message, and after success the form fields are empty with no errors.

**AC-FORM-008 (browser)** Given a 375 px wide viewport, when the broadcast page renders, then the Message control's width equals the Title control's width, and the Message label's bottom edge is above the Message control's top edge.

**AC-FORM-009** Given the audit, when it is finished, then a list of every raw `<input>` and `<textarea>` exists with a disposition (migrated or intentionally custom, with the reason), and no raw control remains unclassified.

**AC-FORM-010 (browser)** Given each repaired form from the audit, when the user focuses, types into and tabs out of every text control, then the typed text appears and focus moves to the next control in visual order.

## Tasks

- **T7-01** Add `Textarea` to `Form.tsx` and implement the `Field` id sharing for `Label`, `Input`, `Textarea` and `FieldError`. Closes FR-FORM-001, 003, 004, 006, AC-FORM-001, 002.
- **T7-02** Replace the broadcast raw textarea with `Textarea`. Closes FR-FORM-002, 010, AC-FORM-003.
- **T7-03** Write the audit of all raw `<input>` and `<textarea>` elements (list in the evidence section) as a short table in the commit report or `docs/`. Migrate the forms that are not modal-styled. Migrate modal fields only when NFR-FORM-003 is satisfied. Closes FR-FORM-005, AC-FORM-009.
- **T7-04** Audit `index.css` and component styles for selectors that affect form controls. Record findings and fix any real conflict. Closes FR-FORM-007.
- **T7-05** Add `node --test` tests using `react-dom/server` for AC-FORM-001 and AC-FORM-002. Closes AC-FORM-001, 002.
- **T7-06** Browser tests for AC-FORM-004 to 008 and 010, if D-02 approves Playwright. Otherwise a written manual script with screenshots at 375 px and 1280 px is the evidence. Closes FR-FORM-008, 009.
- **T7-07** `npm run lint`, `npm run build`, `npm test`. Confirm no page that already looked right changed appearance. Closes NFR-FORM-002.

## Out of scope

Redesigning the visual system, changing validation rules, and any backend change.

## Dependencies

Decision D-02 for the browser steps. The Package 4 broadcast page is the primary target.
