import assert from "node:assert/strict";
import test from "node:test";

import {
  accountListParams,
  initialStaffFilters,
  shiftListParams,
} from "../src/features/admin/staff/staffFilters.ts";
import {
  emptyStaffAccountForm,
  staffAccountSchema,
  toStaffAccountPayload,
} from "../src/features/admin/staff/staffForm.ts";

const valid = { ...emptyStaffAccountForm(), name: "Alex Nguyen", login_name: "alex.nguyen" };

test("a named account with a valid login is accepted", () => {
  assert.equal(staffAccountSchema.safeParse(valid).success, true);
});

test("the login name may not start or end with punctuation", () => {
  for (const login_name of [".alex", "alex.", "a b", "ab"]) {
    const result = staffAccountSchema.safeParse({ ...valid, login_name });
    assert.equal(result.success, false, login_name);
    assert.deepEqual(result.error.issues[0].path, ["login_name"]);
  }
});

test("a phone number is optional but must have at least 7 characters when given", () => {
  assert.equal(staffAccountSchema.safeParse({ ...valid, phone: "" }).success, true);
  assert.equal(staffAccountSchema.safeParse({ ...valid, phone: "12345" }).success, false);
  assert.equal(staffAccountSchema.safeParse({ ...valid, phone: "+66000000" }).success, true);
});

test("only staff and pt can be provisioned", () => {
  assert.equal(staffAccountSchema.safeParse({ ...valid, role: "admin" }).success, false);
  assert.equal(staffAccountSchema.safeParse({ ...valid, role: "pt" }).success, true);
});

test("the payload turns an empty phone and gym into null", () => {
  const payload = toStaffAccountPayload(valid);
  assert.equal(payload.phone, null);
  assert.equal(payload.gym_id, null);
  assert.equal(toStaffAccountPayload({ ...valid, gym_id: "g1" }).gym_id, "g1");
});

test("account params carry only search and role", () => {
  const filters = { ...initialStaffFilters, search: "alex", role: "pt", status: "open" };
  assert.equal(accountListParams(initialStaffFilters, 1).toString(), "page=1&page_size=20");
  const params = accountListParams(filters, 2);
  assert.equal(params.get("page"), "2");
  assert.equal(params.get("search"), "alex");
  assert.equal(params.get("role"), "pt");
  assert.equal(params.has("status"), false);
});

test("shift params add status and the date range", () => {
  const params = shiftListParams(
    { search: "", role: "staff", status: "closed", dateFrom: "2026-11-01", dateTo: "2026-11-10" },
    3,
  );
  assert.equal(params.get("page"), "3");
  assert.equal(params.get("role"), "staff");
  assert.equal(params.get("status"), "closed");
  assert.equal(params.get("date_from"), "2026-11-01");
  assert.equal(params.get("date_to"), "2026-11-10");
  assert.equal(params.has("search"), false);
});
