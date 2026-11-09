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
