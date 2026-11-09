import assert from "node:assert/strict";
import test from "node:test";

import { QueryClient } from "@tanstack/react-query";

import { attendanceAuthFrame, attendanceEventGymId, invalidateAttendanceQueries } from "../src/lib/attendanceRealtime.ts";
import { effectiveOwnerGym, gymIdFromQueryKey, gymMarker, gymSelectionStore, matchesEventGym, realtimeGymStore, resetGymScope } from "../src/features/operations/gymScope.ts";

const D1 = "11111111-1111-1111-1111-111111111111";
const D11 = "22222222-2222-2222-2222-222222222222";

test("owner defaults to the first branch, and an empty string means all branches", () => {
  assert.equal(effectiveOwnerGym(null, D1), D1);
  assert.equal(effectiveOwnerGym(D11, D1), D11);
  assert.equal(effectiveOwnerGym("", D1), "");
  assert.equal(effectiveOwnerGym(null, undefined), "");
});

test("a query key can name its gym and an event refreshes only that gym", () => {
  const d1 = ["attendance", "admin", gymMarker(D1), "page=1"];
  assert.equal(gymIdFromQueryKey(d1), D1);
  assert.equal(matchesEventGym(d1, D1), true);
  assert.equal(matchesEventGym(d1, D11), false);
  assert.equal(matchesEventGym(["attendance", "qr-token"], D11), true);
  assert.equal(matchesEventGym(d1, null), true);
});

test("a District 11 event marks only District 11 queries stale", async () => {
  const client = new QueryClient();
  const d1 = client.getQueryCache().build(client, { queryKey: ["attendance", "crowdedness", gymMarker(D1)], queryFn: async () => 1 });
  const d11 = client.getQueryCache().build(client, { queryKey: ["attendance", "crowdedness", gymMarker(D11)], queryFn: async () => 1 });
  const member = client.getQueryCache().build(client, { queryKey: ["dashboard", "me"], queryFn: async () => 1 });
  await Promise.all([d1.fetch(), d11.fetch(), member.fetch()]);
  await invalidateAttendanceQueries(client, D11);
  assert.equal(d1.state.isInvalidated, false);
  assert.equal(d11.state.isInvalidated, true);
  assert.equal(member.state.isInvalidated, true);
});

test("the realtime frame carries a gym only when one is chosen", () => {
  assert.deepEqual(attendanceAuthFrame("token", D11), { type: "authenticate", access_token: "token", gym_id: D11 });
  assert.deepEqual(attendanceAuthFrame("token", null), { type: "authenticate", access_token: "token" });
  assert.equal(attendanceEventGymId({ type: "occupancy_changed", gym_id: D1 }), D1);
  assert.equal(attendanceEventGymId({ type: "resync_required" }), null);
});

test("signing out forgets the owner's branch and socket scope", () => {
  gymSelectionStore.set(D11);
  realtimeGymStore.set(D11);
  resetGymScope();
  assert.equal(gymSelectionStore.get(), null);
  assert.equal(realtimeGymStore.get(), null);
});
