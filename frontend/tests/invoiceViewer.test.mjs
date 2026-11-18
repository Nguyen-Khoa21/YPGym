import assert from "node:assert/strict";
import test from "node:test";

const { invoiceFileName, isPdfBlob } = await import("../src/features/billing/invoiceViewer.ts");

test("invoice file names are sanitised and always end in .pdf", () => {
  assert.equal(invoiceFileName("YPG-20261110-AB12CD34"), "YPG-20261110-AB12CD34.pdf");
  assert.equal(invoiceFileName("../../etc/passwd"), "etc-passwd.pdf");
  assert.equal(invoiceFileName("   "), "invoice.pdf");
  assert.equal(invoiceFileName("a b\\c\"d"), "a-b-c-d.pdf");
});

test("only a non-empty PDF payload can reach the viewer", () => {
  assert.equal(isPdfBlob(new Blob(["%PDF-1.4"], { type: "application/pdf" })), true);
  assert.equal(isPdfBlob(new Blob([""], { type: "application/pdf" })), false);
  assert.equal(isPdfBlob(new Blob(["{}"], { type: "application/json" })), false);
  assert.equal(isPdfBlob(new Blob(["<html>"], { type: "text/html" })), false);
});

test("server-built invoice links are not prefixed with the API path twice", async () => {
  const { API_BASE_URL, apiUrl } = await import("../src/lib/apiClient.ts");
  const id = "961c8cb9-76a9-4779-a8b5-67dbf5b0a580";
  const expected = `${API_BASE_URL}/billing/me/invoices/${id}`;
  assert.equal(apiUrl(`/api/v1/billing/me/invoices/${id}`), expected);
  assert.equal(apiUrl(`/billing/me/invoices/${id}`), expected);
  assert.equal(apiUrl("https://cdn.example.test/file.pdf"), "https://cdn.example.test/file.pdf");
});
