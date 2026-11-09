import assert from "node:assert/strict";
import test from "node:test";

const { checkoutGymId, isExpiredStatus, readRenewalIntent, renewalSearch } = await import("../src/features/memberships/renewalIntent.ts");

test("only an expired membership counts as expired", () => {
  assert.equal(isExpiredStatus("expired"), true);
  for (const status of ["active", "expiring_soon", "frozen", "cancelled", "revoked", "pending_verification", null, undefined]) {
    assert.equal(isExpiredStatus(status), false, String(status));
  }
});

test("renew and change intents round-trip through the query string", () => {
  assert.equal(renewalSearch({ mode: "renew", gymId: "gym 1" }), "?gym=gym%201");
  assert.equal(renewalSearch({ mode: "change" }), "?change=1");
  assert.equal(renewalSearch({ mode: "default" }), "");
  assert.deepEqual(readRenewalIntent(new URLSearchParams("gym=g1")), { mode: "renew", gymId: "g1" });
  assert.deepEqual(readRenewalIntent(new URLSearchParams("change=1")), { mode: "change" });
  assert.deepEqual(readRenewalIntent(new URLSearchParams("")), { mode: "default" });
});

test("checkout preselection: renew keeps the home gym, change preselects nothing", () => {
  const base = { homeGymId: "d1", hasMembership: true, recommendedGymId: "d11" };
  assert.equal(checkoutGymId({ ...base, chosen: "", intent: { mode: "renew", gymId: "d1" } }), "d1");
  assert.equal(checkoutGymId({ ...base, chosen: "", intent: { mode: "change" } }), "");
  assert.equal(checkoutGymId({ ...base, chosen: "d11", intent: { mode: "change" } }), "d11");
  assert.equal(checkoutGymId({ ...base, chosen: "", intent: { mode: "default" } }), "d1");
});

test("a recommendation preselects only for a member with no membership at all", () => {
  const none = { homeGymId: null, chosen: "", intent: { mode: "default" }, recommendedGymId: "d11" };
  assert.equal(checkoutGymId({ ...none, hasMembership: false }), "d11");
  assert.equal(checkoutGymId({ ...none, hasMembership: true }), "");
  assert.equal(checkoutGymId({ ...none, hasMembership: false, recommendedGymId: null }), "");
});
