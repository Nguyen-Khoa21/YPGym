Part of the [post-multigym master prompt](../post-multigym-master-prompt.md). Read its sections 0 to 3 first (operating rules, evidence, defaults, cross-cutting rules).

# Package 15: Invoices: fix download, add a Gmail-style viewer

**Goal.** Invoice PDFs download reliably and open in an in-page viewer, like previewing an attachment in Gmail.

### Step 1: diagnose before changing code

1. Reproduce with a member token: `GET /api/v1/billing/me/invoices/{id}` for a membership invoice **and** for a class-booking invoice (the screenshot has both).
2. Read the backend log for that request. Check that `INVOICE_STORAGE_DIR` is writable by the container user and survives restarts (compose volume), that `generate_pdf` receives the fields each product type needs, and that the response is `application/pdf`.
3. Write the confirmed root cause in the commit report. Do not guess. If it cannot be reproduced, say so and still deliver the hardening below.

### Requirements

| ID | Requirement |
|---|---|
| FR-INV-001 | Fix the confirmed cause. Add a regression test with an invoice of each product type: `200`, `application/pdf`, body starts with `%PDF`; another member's invoice is `404`. |
| FR-INV-002 | If PDF generation or file access fails, return a structured error (for example `503 INVOICE_PDF_UNAVAILABLE`) instead of an unhandled `500`. Prefer reading a stored file when it exists and regenerating only when missing; make generation write to a temporary name and rename so a half-written file is never served. Keep deletion behavior in the owner's uncommitted `remove_pdfs` untouched. |
| FR-INV-003 | Add a blob-aware request helper to `lib/apiClient.ts` that reuses the existing error parsing, so a failed download shows the real code and message, not "Unexpected error". Use it on the billing page. |
| FR-INV-004 | New in-page viewer on the billing page: clicking an invoice opens a full-screen dialog with the invoice number as title and a toolbar: **Download**, **Print**, **Open in new tab**, **Close** (Esc closes, focus is trapped and restored). The PDF is fetched with the bearer token as a blob and shown through a `blob:` URL in an `iframe` or `object`. Revoke the object URL on close. Show loading and error states with a Retry. Keep a plain Download button on each card. |
| FR-INV-005 | Update the page CSP so the viewer works in the production build: allow `frame-src 'self' blob:` (and `object-src blob:` only if you use `<object>`). Change the narrowest directive. `frontend/nginx.production.conf` already has uncommitted owner edits: add only your line and stage only your hunk. Also check the Vite dev server and `index.html` for a CSP meta tag. |
| FR-INV-006 | Mobile: open the invoice through the platform viewer or share sheet using a package already in `mobile/package.json` (check for `expo-sharing`, `expo-file-system`, `expo-web-browser`). If none is installed, list the smallest option and **ask the owner** before adding a dependency. The mobile invoices screen currently only lists records. |
| FR-INV-007 | Keep access rules: the invoice must belong to the signed-in user; no token in the URL or query string; no PDF path or filesystem detail in any response or log. |

### Acceptance criteria

- **AC-INV-001.** Clicking an invoice opens the viewer and shows the PDF in Chrome, Edge and Firefox on desktop.
- **AC-INV-002.** Download saves `{invoice_number}.pdf`; Print opens the print dialog for the PDF.
- **AC-INV-003.** When the API returns an error, the banner shows that error's title and message.
- **AC-INV-004.** The viewer works in the Nginx production container, not only in dev.
- **AC-INV-005.** Opening another member's invoice id returns `404` and the UI shows a clear message.

### Tasks

T15-01 diagnosis note. T15-02 backend fix and hardening and tests. T15-03 blob helper. T15-04 viewer dialog. T15-05 CSP change. T15-06 mobile viewer (or the owner question). T15-07 manual test script.


### Implementation record

- **Root cause (not reproduced).** The Docker stack was not run in this session, so the reported "Unexpected error" was not reproduced against a live container. Code reading shows the download endpoint regenerated the PDF on every request with no error handling, so any storage or renderer failure surfaced as an unhandled 500. The hardening below removes that path; confirm on the owner's stack that `INVOICE_STORAGE_DIR` is writable by the container user.
- **FR-INV-001, 002, 007.** `BillingService.get_invoice_file` serves the stored PDF when it is a non-empty file inside the storage directory, regenerates otherwise, and maps any failure to `503 INVOICE_PDF_UNAVAILABLE` (logs the exception type and invoice id only). `generate_pdf` renders to a temporary name and renames it. Tests: `backend/app/tests/integration/test_invoice_download.py` (written, **not run**: pytest and the compose test stack are not available in this session).
- **FR-INV-003, 004.** `downloadApiFile` (existing blob helper with API error parsing) is used by `InvoiceViewerDialog` and the card's plain Download button. The dialog uses a native `<dialog>` (focus trap, Esc, focus restore), a `blob:` iframe, Download, Print, Open in new tab, Close, loading and error states with Retry, and revokes the object URL on close. Test: `frontend/tests/invoiceViewer.test.mjs`.
- **FR-INV-005.** `frame-src 'self' blob:` added to the CSP in `frontend/nginx.production.conf` (file uses CRLF line endings; only this one directive changed). No CSP meta tag exists in `index.html` or the Vite config.
- **FR-INV-006 (blocked on owner).** `mobile/package.json` has `expo-web-browser` but neither `expo-file-system` nor `expo-sharing`. Opening an authenticated PDF needs a file download, so the smallest option is adding `expo-file-system` and `expo-sharing` (share sheet shows the system PDF viewer). Alternatively a short-lived signed URL could use `expo-web-browser`, but that puts a credential in a URL, which FR-INV-007 forbids. No dependency was added; the mobile invoices screen is unchanged. **Owner decision needed.**
- Not verified in a browser: AC-INV-001, 002, 004 (viewer in Chrome/Edge/Firefox and in the Nginx container).
