import type { QueryClient } from "@tanstack/react-query";

export type ManagementMutationScope = "broadcasts" | "classes" | "configuration" | "trainers";

export const managementMutationQueryKeys: Record<ManagementMutationScope, readonly (readonly string[])[]> = {
  broadcasts: [["admin", "broadcasts"], ["dashboard"]],
  classes: [
    ["admin", "classes"],
    ["admin", "class-trainers"],
    ["admin", "trainers"],
    ["trainers"],
    ["trainer", "me"],
    ["classes"],
    ["bookings"],
    ["dashboard"],
  ],
  configuration: [["admin", "configuration"]],
  trainers: [
    ["admin", "trainers"],
    ["admin", "class-trainers"],
    ["admin", "classes"],
    ["trainers"],
    ["trainer", "me"],
    ["classes"],
    ["bookings"],
    ["dashboard"],
  ],
};

export async function refreshManagementQueries(
  client: Pick<QueryClient, "invalidateQueries">,
  scope: ManagementMutationScope,
) {
  await Promise.all(
    managementMutationQueryKeys[scope].map((queryKey) =>
      client.invalidateQueries({ queryKey: [...queryKey] }),
    ),
  );
}

type TrainerListItem = { id: string; display_name: string; is_active: boolean };

export function updateTrainerListForFilter<T extends TrainerListItem>(
  current: T[] | undefined,
  item: T,
  filter: string,
): T[] | undefined {
  if (!current) return current;
  const matches = filter === "" || filter === String(item.is_active);
  const withoutItem = current.filter((trainer) => trainer.id !== item.id);
  if (!matches) return withoutItem;
  return [...withoutItem, item].sort((left, right) =>
    left.display_name.localeCompare(right.display_name),
  );
}

export function configurationDraftState(
  rawValue: string,
  currentValue: number,
  minimum: number,
  maximum: number,
) {
  const value = Number(rawValue);
  const valid = rawValue.trim() !== "" && Number.isInteger(value) && value >= minimum && value <= maximum;
  return { value, valid, changed: valid && value !== currentValue };
}
