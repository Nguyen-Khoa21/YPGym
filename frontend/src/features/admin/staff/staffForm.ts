import { z } from "zod";

export const staffAccountSchema = z.object({
  name: z.string().min(2, "Use at least 2 characters.").max(160),
  login_name: z
    .string()
    .min(3)
    .max(64)
    .regex(
      /^[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9]$/,
      "Use letters, numbers, periods, hyphens or underscores.",
    ),
  role: z.enum(["staff", "pt"]),
  phone: z
    .string()
    .refine((value) => value.length === 0 || value.length >= 7, "Use at least 7 characters."),
  gym_id: z.string(),
});

export type StaffAccountForm = z.infer<typeof staffAccountSchema>;

export function emptyStaffAccountForm(gymId = ""): StaffAccountForm {
  return { name: "", login_name: "", role: "staff", phone: "", gym_id: gymId };
}

/** Empty optionals become null, as the create endpoint expects. */
export function toStaffAccountPayload(values: StaffAccountForm) {
  return { ...values, phone: values.phone || null, gym_id: values.gym_id || null };
}
