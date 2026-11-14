/**
 * The admin class form: validation, defaults, and the mapping to and from the API shape.
 * This file has no React imports so the rules can be tested with node --test.
 */
import { z } from "zod";

import type { GymClass } from "@/types/operations";

export const classSchema = z
  .object({
    title: z.string().min(3, "Use at least 3 characters.").max(160),
    class_type: z.string().min(2, "Class type is required.").max(100),
    description: z.string().max(3000).optional(),
    start_at: z.string().min(1, "Start time is required."),
    end_at: z.string().min(1, "End time is required."),
    capacity: z.number().int().min(1).max(500),
    price_vnd: z.number().int().min(1, "Enter a positive VND price.").max(1_000_000_000),
    gym_id: z.string().uuid("Select a gym location."),
    trainer_id: z.string().optional(),
    location: z.string().min(2, "Location is required.").max(160),
  })
  .refine((values) => new Date(values.end_at) > new Date(values.start_at), {
    path: ["end_at"],
    message: "End time must be after start time.",
  });

export type ClassForm = z.infer<typeof classSchema>;

/** A datetime-local input value (local time, no zone) for an ISO timestamp. */
export function toLocalDateTime(value: string) {
  const dateValue = new Date(value);
  const offset = dateValue.getTimezoneOffset();
  return new Date(dateValue.getTime() - offset * 60_000).toISOString().slice(0, 16);
}

/** Tomorrow, on the hour, lasting one hour. */
export function emptyClassForm(gymId = ""): ClassForm {
  const start = new Date(Date.now() + 24 * 60 * 60 * 1000);
  start.setMinutes(0, 0, 0);
  const end = new Date(start.getTime() + 60 * 60 * 1000);
  return {
    title: "",
    class_type: "",
    description: "",
    start_at: toLocalDateTime(start.toISOString()),
    end_at: toLocalDateTime(end.toISOString()),
    capacity: 20,
    price_vnd: 150000,
    gym_id: gymId,
    trainer_id: "",
    location: "",
  };
}

export function classToForm(item: GymClass): ClassForm {
  return {
    title: item.title,
    class_type: item.class_type,
    description: item.description ?? "",
    start_at: toLocalDateTime(item.start_at),
    end_at: toLocalDateTime(item.end_at),
    capacity: item.capacity,
    price_vnd: item.price_vnd ?? 150000,
    gym_id: item.gym_id,
    trainer_id: item.trainer_id ?? "",
    location: item.location,
  };
}

/** The request body: empty optionals become null and local times become UTC ISO strings. */
export function toClassPayload(values: ClassForm) {
  return {
    ...values,
    description: values.description || null,
    trainer_id: values.trainer_id || null,
    start_at: new Date(values.start_at).toISOString(),
    end_at: new Date(values.end_at).toISOString(),
  };
}
