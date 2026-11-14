export type StaffFilters = {
  search: string;
  role: string;
  status: string;
  dateFrom: string;
  dateTo: string;
};

export const initialStaffFilters: StaffFilters = {
  search: "",
  role: "",
  status: "",
  dateFrom: "",
  dateTo: "",
};

const PAGE_SIZE = "20";

/** Accounts honour the search and role filters only. */
export function accountListParams(filters: StaffFilters, page: number) {
  const params = new URLSearchParams({ page: String(page), page_size: PAGE_SIZE });
  if (filters.search) params.set("search", filters.search);
  if (filters.role) params.set("role", filters.role);
  return params;
}

/** Shifts honour every filter. */
export function shiftListParams(filters: StaffFilters, page: number) {
  const params = accountListParams(filters, page);
  if (filters.status) params.set("status", filters.status);
  if (filters.dateFrom) params.set("date_from", filters.dateFrom);
  if (filters.dateTo) params.set("date_to", filters.dateTo);
  return params;
}
