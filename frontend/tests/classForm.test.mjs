import assert from "node:assert/strict";
import test from "node:test";

import { initialClassFilters, classListParams } from "../src/features/classes/classFilters.ts";
import {
  classSchema,
  classToForm,
  emptyClassForm,
  toClassPayload,
  toLocalDateTime,
} from "../src/features/classes/classForm.ts";

const GYM = "3f2b8c1e-5a4d-4e6f-9b7a-1c2d3e4f5a6b";

function validForm(overrides = {}) {
  return { ...emptyClassForm(GYM), title: "Morning HIIT", class_type: "HIIT", location: "Studio A", ...overrides };
}

test("a default form with a title, type, gym and room is valid", () => {
  assert.equal(classSchema.safeParse(validForm()).success, true);
});

test("the end time must be after the start time", () => {
  const result = classSchema.safeParse(validForm({ start_at: "2030-01-01T10:00", end_at: "2030-01-01T10:00" }));
  assert.equal(result.success, false);
  assert.deepEqual(result.error.issues[0].path, ["end_at"]);
});

test("a gym must be chosen", () => {
  const result = classSchema.safeParse(validForm({ gym_id: "" }));
  assert.equal(result.success, false);
  assert.deepEqual(result.error.issues[0].path, ["gym_id"]);
});

test("the empty form starts on the hour tomorrow and lasts one hour", () => {
  const form = emptyClassForm(GYM);
  const start = new Date(form.start_at);
  assert.equal(start.getMinutes(), 0);
  assert.equal(new Date(form.end_at).getTime() - start.getTime(), 60 * 60 * 1000);
  assert.ok(start.getTime() > Date.now());
  assert.equal(form.gym_id, GYM);
});

test("toLocalDateTime round-trips to the same minute", () => {
  const iso = "2030-06-15T03:30:00.000Z";
  assert.equal(new Date(toLocalDateTime(iso)).toISOString(), iso);
});

test("an existing class maps to form values with safe defaults for missing optionals", () => {
  const form = classToForm({
    title: "Yoga", class_type: "Yoga", description: null, start_at: "2030-06-15T03:30:00.000Z",
    end_at: "2030-06-15T04:30:00.000Z", capacity: 12, price_vnd: null, gym_id: GYM, trainer_id: null, location: "Room 2",
  });
  assert.equal(form.description, "");
  assert.equal(form.trainer_id, "");
  assert.equal(form.price_vnd, 150000);
  assert.equal(form.capacity, 12);
});

test("the payload turns empty optionals into null and local times into UTC", () => {
  const payload = toClassPayload(validForm({ description: "", trainer_id: "", start_at: "2030-06-15T10:00", end_at: "2030-06-15T11:00" }));
  assert.equal(payload.description, null);
  assert.equal(payload.trainer_id, null);
  assert.equal(payload.start_at, new Date("2030-06-15T10:00").toISOString());
  assert.equal(payload.end_at, new Date("2030-06-15T11:00").toISOString());
});

test("list params carry only the filters that are set", () => {
  assert.equal(classListParams(initialClassFilters, "", 1).toString(), "page=1&page_size=25");
  const params = classListParams({ ...initialClassFilters, search: "yoga", status: "scheduled", trainerId: "t1" }, GYM, 3);
  assert.equal(params.get("page"), "3");
  assert.equal(params.get("search"), "yoga");
  assert.equal(params.get("status"), "scheduled");
  assert.equal(params.get("gym_id"), GYM);
  assert.equal(params.get("trainer_id"), "t1");
  assert.equal(params.has("date_from"), false);
});
