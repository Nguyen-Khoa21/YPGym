import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { QueryState } from "@/components/common/QueryState";
import { AdminShell } from "@/components/layout/AdminShell";
import { DataTable } from "@/components/operations/DataTable";
import {
  MetricCard,
  OperationsHeader,
  Pagination,
  Panel,
} from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { classColumns } from "@/features/classes/classColumns";
import { classListParams, initialClassFilters } from "@/features/classes/classFilters";
import {
  classSchema,
  classToForm,
  emptyClassForm,
  toClassPayload,
  type ClassForm,
} from "@/features/classes/classForm";
import { CancelClassDialog } from "@/features/classes/components/CancelClassDialog";
import { ClassFilterBar } from "@/features/classes/components/ClassFilterBar";
import { ClassFormDialog } from "@/features/classes/components/ClassFormDialog";
import { NextClassCard } from "@/features/classes/components/NextClassCard";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { refreshManagementQueries } from "@/lib/managementMutations";
import { queryClient } from "@/lib/queryClient";
import type { ClassPage, GymClass, GymLocation, Trainer } from "@/types/operations";

export function AdminClassesPage() {
  const { token } = useAuth();
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState(initialClassFilters);
  const [applied, setApplied] = useState(initialClassFilters);
  const [editing, setEditing] = useState<GymClass | "new" | null>(null);
  const [cancelling, setCancelling] = useState<GymClass | null>(null);
  const gyms = useQuery({
    queryKey: ["gyms", "active"],
    queryFn: ({ signal }) => apiRequest<GymLocation[]>("/gyms", { signal }),
  });
  const gymId = applied.gymId || gyms.data?.[0]?.id || "";
  const query = classListParams(applied, gymId, page);
  const classes = useQuery({
    queryKey: ["admin", "classes", query.toString()],
    queryFn: ({ signal }) => apiRequest<ClassPage>(`/admin/classes?${query}`, { token, signal }),
    enabled: Boolean(gymId),
  });
  const trainers = useQuery({
    queryKey: ["admin", "class-trainers"],
    queryFn: ({ signal }) => apiRequest<Trainer[]>("/admin/classes/trainers", { token, signal }),
  });
  const form = useForm<ClassForm>({
    resolver: zodResolver(classSchema),
    defaultValues: emptyClassForm(),
  });
  const save = useMutation({
    mutationFn: ({ id, values }: { id?: string; values: ClassForm }) =>
      apiRequest<GymClass>(id ? `/admin/classes/${id}` : "/admin/classes", {
        method: id ? "PATCH" : "POST",
        token,
        body: toClassPayload(values),
      }),
    onSuccess: async (_, variables) => {
      setEditing(null);
      form.reset(emptyClassForm(gymId));
      await refreshManagementQueries(queryClient, "classes");
      toast.success(variables.id ? "Class updated" : "Class scheduled", { id: "class-save" });
    },
    onError: (error) => toast.error(toUiError(error).message, { id: "class-save" }),
  });
  const cancel = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      apiRequest<GymClass>(`/admin/classes/${id}/cancel`, {
        method: "POST",
        token,
        body: { reason },
      }),
    onSuccess: async () => {
      setCancelling(null);
      await refreshManagementQueries(queryClient, "classes");
      toast.success("Class cancelled", { id: "class-cancel" });
    },
    onError: (error) => toast.error(toUiError(error).message, { id: "class-cancel" }),
  });

  function openNew() {
    form.reset(emptyClassForm(gymId));
    setEditing("new");
  }
  function openEdit(item: GymClass) {
    form.reset(classToForm(item));
    setEditing(item);
  }
  const columns = classColumns({
    gymNames: new Map(gyms.data?.map((gym) => [gym.id, gym.name])),
    onEdit: openEdit,
    onCancel: setCancelling,
  });
  const nextClass = classes.data?.items.find((item) => item.status === "scheduled");
  return (
    <AdminShell>
      <div className="mx-auto max-w-7xl">
        <OperationsHeader
          kicker="Class and schedule management"
          title="Program the week."
          description="Create, update, filter, and explicitly cancel real classes with trainer, location, capacity, timezone, and overlap validation."
          actions={
            <Button onClick={openNew}>
              <Plus className="size-4" /> Add class
            </Button>
          }
        />
        {classes.data ? (
          <div className="ops-metrics">
            <MetricCard label="Filtered classes" value={classes.data.page.total} />
            <MetricCard label="Scheduled" value={classes.data.scheduled_count} tone="forest" />
            <MetricCard label="Cancelled" value={classes.data.cancelled_count} tone="coral" />
            <MetricCard
              label="Available trainers"
              value={trainers.data?.length ?? "-"}
              tone="lime"
            />
          </div>
        ) : null}
        <div className="grid gap-5 xl:grid-cols-[1.35fr_0.65fr]">
          <Panel
            title="Class schedule"
            detail="The visible filters are enforced by the list endpoint."
          >
            <ClassFilterBar
              filters={filters}
              setFilters={setFilters}
              gymId={gymId}
              gyms={gyms.data}
              trainers={trainers.data}
              onApply={() => {
                setApplied(filters);
                setPage(1);
              }}
            />
            <QueryState
              query={classes}
              className="m-4"
              loading={{ title: "Loading class schedule" }}
              retry
              empty={{
                title: "No classes match",
                message: "Adjust the schedule filters or add a future class.",
              }}
              isEmpty={(data) => data.items.length === 0}
            >
              {(data) => (
                <>
                  <DataTable
                    columns={columns}
                    data={data.items}
                    getRowId={(row) => row.id}
                    label="Admin class schedule"
                  />
                  <Pagination
                    page={page}
                    pages={data.page.pages}
                    total={data.page.total}
                    onPage={setPage}
                  />
                </>
              )}
            </QueryState>
          </Panel>
          <div className="grid content-start gap-5">
            <NextClassCard item={nextClass} onEdit={openEdit} />
            <Panel title="Paid session rules" detail="One price per scheduled session.">
              <p className="p-5 text-sm leading-6 text-muted-foreground">
                Future price edits apply only to new checkouts. Pending and paid bookings retain
                their price snapshot.
              </p>
            </Panel>
          </div>
        </div>
        {editing ? (
          <ClassFormDialog
            editing={editing}
            form={form}
            gyms={gyms.data}
            trainers={trainers.data}
            error={save.isError ? toUiError(save.error).message : undefined}
            isPending={save.isPending}
            onSubmit={(values) =>
              save.mutate({ id: editing === "new" ? undefined : editing.id, values })
            }
            onClose={() => setEditing(null)}
          />
        ) : null}
        {cancelling ? (
          <CancelClassDialog
            item={cancelling}
            error={cancel.isError ? toUiError(cancel.error).message : undefined}
            isPending={cancel.isPending}
            onConfirm={(reason) => cancel.mutate({ id: cancelling.id, reason })}
            onClose={() => setCancelling(null)}
          />
        ) : null}
      </div>
    </AdminShell>
  );
}
