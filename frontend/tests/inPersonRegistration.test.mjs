import assert from "node:assert/strict";
import test from "node:test";

const { isFinalPaymentStatus, newPaymentKey, paymentStatusLabel, qrValue } = await import("../src/features/staff/inPersonRegistration.ts");

test("polling stops on final statuses only", () => {
  for (const status of ["succeeded", "failed", "cancelled", "expired", "paid_review"]) assert.equal(isFinalPaymentStatus(status), true, status);
  for (const status of ["pending", "paid", "anything-else"]) assert.equal(isFinalPaymentStatus(status), false, status);
});

test("status labels never rely on colour alone", () => {
  assert.equal(paymentStatusLabel("succeeded").tone, "ok");
  assert.equal(paymentStatusLabel("pending").tone, "wait");
  assert.match(paymentStatusLabel("expired").label, /expired/i);
  assert.match(paymentStatusLabel("paid_review").label, /review/i);
});

test("the QR encodes the payOS payload and falls back to the checkout link", () => {
  assert.equal(qrValue({ qr_code: "0002-bank", checkout_url: "https://pay.example/x" }), "0002-bank");
  assert.equal(qrValue({ qr_code: "  ", checkout_url: "https://pay.example/x" }), "https://pay.example/x");
  assert.equal(qrValue({ checkout_url: "https://pay.example/x" }), "https://pay.example/x");
});

test("payment keys are unique, prefixed and long enough for the API", () => {
  const a = newPaymentKey("cash");
  const b = newPaymentKey("cash");
  assert.notEqual(a, b);
  assert.ok(a.startsWith("cash-") && a.length >= 8 && a.length <= 120);
  assert.ok(newPaymentKey("qr").startsWith("qr-"));
});
