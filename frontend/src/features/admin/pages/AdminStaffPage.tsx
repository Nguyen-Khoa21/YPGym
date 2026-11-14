import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { AdminShell } from "@/components/layout/AdminShell";
import { OperationsHeader } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { AccountsPanel } from "@/features/admin/staff/components/AccountsPanel";
import { CreateStaffDialog } from "@/features/admin/staff/components/CreateStaffDialog";
import { ShiftsPanel } from "@/features/admin/staff/components/ShiftsPanel";
import { StaffFilterBar } from "@/features/admin/staff/components/StaffFilterBar";
import { TemporaryCredentialsDialog } from "@/features/admin/staff/components/TemporaryCredentialsDialog";
import {
  accountListParams,
  initialStaffFilters,
  shiftListParams,
  type StaffFilters,
} from "@/features/admin/staff/staffFilters";
import {
  emptyStaffAccountForm,
  staffAccountSchema,
  toStaffAccountPayload,
  type StaffAccountForm,
} from "@/features/admin/staff/staffForm";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { queryClient } from "@/lib/queryClient";
import type {
  GymLocation,
  StaffAccountCreated,
  StaffAccountPage,
  StaffShiftPage,
} from "@/types/operations";

export function AdminStaffPage() {
  const { token, user } = useAuth();
  const [accountPage, setAccountPage] = useState(1);
  const [shiftPage, setShiftPage] = useState(1);
  const [filters, setFilters] = useState(initialStaffFilters);
  const [creating, setCreating] = useState(false);
  const [created, setCreated] = useState<StaffAccountCreated | null>(null);
  const form = useForm<StaffAccountForm>({
    resolver: zodResolver(staffAccountSchema),
    defaultValues: emptyStaffAccountForm(),
  });
  const accountParams = accountListParams(filters, accountPage);
  const shiftParams = shiftListParams(filters, shiftPage);
  const accounts = useQuery({
    queryKey: ["admin", "staff-accounts", accountPage, filters.search, filters.role],
    queryFn: ({ signal }) =>
      apiRequest<StaffAccountPage>(`/admin/staff-accounts?${accountParams}`, { token, signal }),
  });
  const shifts = useQuery({
    queryKey: [
      "admin",
      "staff-shifts",
      shiftPage,
      filters.search,
      filters.role,
      filters.status,
      filters.dateFrom,
      filters.dateTo,
    ],
    queryFn: ({ signal }) =>
      apiRequest<StaffShiftPage>(`/admin/staff-shifts?${shiftParams}`, { token, signal }),
  });
  const locations = useQuery({
    queryKey: ["gyms", "active"],
    queryFn: ({ signal }) => apiRequest<GymLocation[]>("/gyms", { signal }),
    enabled: user?.role === "admin",
  });
  const create = useMutation({
    mutationFn: (values: StaffAccountForm) =>
      apiRequest<StaffAccountCreated>("/admin/staff-accounts", {
        method: "POST",
        token,
        body: toStaffAccountPayload(values),
      }),
    onSuccess: async (result) => {
      setCreating(false);
      setCreated(result);
      form.reset();
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["admin", "staff-accounts"] }),
        queryClient.invalidateQueries({ queryKey: ["admin", "trainers"] }),
        queryClient.invalidateQueries({ queryKey: ["admin", "class-trainers"] }),
      ]);
      toast.success("Workforce account created");
    },
    onError: (error) => toast.error(toUiError(error).message),
  });

  /** Search and role narrow both lists; the other filters only narrow shifts. */
  function changeFilters(patch: Partial<StaffFilters>) {
    setFilters((current) => ({ ...current, ...patch }));
    if ("search" in patch || "role" in patch) setAccountPage(1);
    setShiftPage(1);
  }
  function openCreate() {
    create.reset();
    form.reset(emptyStaffAccountForm(locations.data?.[0]?.id));
    setCreating(true);
  }

  return (
    <AdminShell>
      <div className="mx-auto max-w-7xl">
        <OperationsHeader
          kicker="Workforce operations"
          title="Individual accounts and shifts."
          description="Provision staff or PT sign-ins, reveal each temporary password once, and review server-recorded shifts."
          actions={
            <Button onClick={openCreate}>
              <Plus className="size-4" /> Create account
            </Button>
          }
        />
        <StaffFilterBar
          filters={filters}
          onChange={changeFilters}
          onClear={() => setFilters(initialStaffFilters)}
        />
        <div className="mt-7 grid items-start gap-6 xl:grid-cols-2">
          <AccountsPanel query={accounts} page={accountPage} onPage={setAccountPage} />
          <ShiftsPanel query={shifts} page={shiftPage} onPage={setShiftPage} />
        </div>
        {creating ? (
          <CreateStaffDialog
            form={form}
            isAdmin={user?.role === "admin"}
            gyms={locations.data}
            error={create.isError ? toUiError(create.error).message : undefined}
            isPending={create.isPending}
            onSubmit={(values) => create.mutate(values)}
            onClose={() => setCreating(false)}
          />
        ) : null}
        {created ? (
          <TemporaryCredentialsDialog created={created} onClose={() => setCreated(null)} />
        ) : null}
      </div>
    </AdminShell>
  );
}
