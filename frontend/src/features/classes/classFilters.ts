/** The class list filters and the query string the list endpoint expects. */

export type ClassFilters = {
  search: string;
  status: string;
  gymId: string;
  trainerId: string;
  dateFrom: string;
  dateTo: string;
};

export const initialClassFilters: ClassFilters = {
  search: "",
  status: "",
  gymId: "",
  trainerId: "",
  dateFrom: "",
  dateTo: "",
};

export function classListParams(applied: ClassFilters, gymId: string, page: number) {
  const query = new URLSearchParams({ page: String(page), page_size: "25" });
  if (applied.search) query.set("search", applied.search);
  if (applied.status) query.set("status", applied.status);
  if (gymId) query.set("gym_id", gymId);
  if (applied.trainerId) query.set("trainer_id", applied.trainerId);
  if (applied.dateFrom) query.set("date_from", new Date(applied.dateFrom).toISOString());
  if (applied.dateTo) query.set("date_to", new Date(applied.dateTo).toISOString());
  return query;
}
