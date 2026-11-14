import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueries, useQuery } from "@tanstack/react-query";
import { Pencil, Plus } from "lucide-react";
import { useForm } from "react-hook-form";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";

import { routePaths } from "@/app/routes";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { AdminShell } from "@/components/layout/AdminShell";
import { Modal, OperationsHeader, Panel, StatusBadge } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { Field, FieldError, Input, Label } from "@/components/ui/Form";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { formatDateTime } from "@/lib/format";
import { queryClient } from "@/lib/queryClient";
import type {
  Crowdedness,
  GymLocation,
  TrafficSummary,
  WorkforceGymAssignment,
} from "@/types/operations";
import { gymMarker, gymSelectionStore } from "../gymScope";

const locationSchema = z.object({
  name: z.string().min(2, "Use at least 2 characters.").max(160),
  slug: z
    .string()
    .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, "Lowercase letters, numbers and dashes only.")
    .min(2)
    .max(100),
  district: z.string().min(2, "District is required.").max(100),
  address: z.string().min(2, "Address is required.").max(255),
  timezone: z.string().min(3, "Timezone is required.").max(64),
  capacity: z.number().int().min(1, "At least 1.").max(5000),
  is_active: z.boolean(),
});
type LocationForm = z.infer<typeof locationSchema>;
const emptyLocation: LocationForm = {
  name: "",
  slug: "",
  district: "",
  address: "",
  timezone: "Asia/Ho_Chi_Minh",
  capacity: 100,
  is_active: true,
};

export function AdminBranchesPage() {
  const { token } = useAuth();
  const [editing, setEditing] = useState<GymLocation | "new" | null>(null);
  const locations = useQuery({
    queryKey: ["admin", "gym-locations"],
    queryFn: ({ signal }) => apiRequest<GymLocation[]>("/admin/gym-locations", { token, signal }),
  });
  const assignments = useQuery({
    queryKey: ["admin", "workforce-assignments"],
    queryFn: ({ signal }) =>
      apiRequest<WorkforceGymAssignment[]>("/admin/gym-locations/workforce/assignments", {
        token,
        signal,
      }),
  });
  const active = (locations.data ?? []).filter((gym) => gym.is_active);
  const form = useForm<LocationForm>({
    resolver: zodResolver(locationSchema),
    defaultValues: emptyLocation,
  });
  const refresh = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ["admin", "gym-locations"] }),
      queryClient.invalidateQueries({ queryKey: ["gyms"] }),
      queryClient.invalidateQueries({ queryKey: ["admin", "workforce-assignments"] }),
    ]);
  const save = useMutation({
    mutationFn: ({ id, values }: { id?: string; values: LocationForm }) =>
      apiRequest<GymLocation>(id ? `/admin/gym-locations/${id}` : "/admin/gym-locations", {
        method: id ? "PATCH" : "POST",
        token,
        body: values,
      }),
    onSuccess: async (_, variables) => {
      setEditing(null);
      form.reset(emptyLocation);
      await refresh();
      toast.success(
        variables.id
          ? "Location updated and recorded in the audit log"
          : "Location created and recorded in the audit log",
      );
    },
    onError: (error) => toast.error(toUiError(error).message),
  });
  const reassign = useMutation({
    mutationFn: (input: { user_id: string; gym_id: string }) =>
      apiRequest<WorkforceGymAssignment>("/admin/gym-locations/workforce/assignments", {
        method: "PUT",
        token,
        body: input,
      }),
    onSuccess: async (result) => {
      await refresh();
      toast.success(
        `${result.user_name} now works at ${result.gym_name}. The change is in the audit log.`,
      );
    },
    onError: (error) => toast.error(toUiError(error).message),
  });
  function openNew() {
    form.reset(emptyLocation);
    setEditing("new");
  }
  function openEdit(gym: GymLocation) {
    form.reset({
      name: gym.name,
      slug: gym.slug,
      district: gym.district,
      address: gym.address,
      timezone: gym.timezone,
      capacity: gym.capacity,
      is_active: gym.is_active,
    });
    setEditing(gym);
  }

  return (
    <AdminShell>
      <div className="mx-auto max-w-7xl">
        <OperationsHeader
          kicker="Owner workspace"
          title="Every branch, side by side."
          description="Each card shows one gym on its own. Percentages from different gyms are never added together."
          actions={
            <Button onClick={openNew}>
              <Plus className="size-4" /> Add location
            </Button>
          }
        />
        {locations.isLoading ? <LoadingState title="Loading branches" /> : null}
        {locations.isError ? (
          <ErrorState
            title={toUiError(locations.error).title}
            message={toUiError(locations.error).message}
            action={
              <Button variant="outline" onClick={() => void locations.refetch()}>
                Retry
              </Button>
            }
          />
        ) : null}
        {active.length ? (
          <section className="grid gap-4 lg:grid-cols-2" aria-label="Branch overview">
            {active.map((gym) => (
              <BranchCard gym={gym} key={gym.id} />
            ))}
          </section>
        ) : locations.isSuccess ? (
          <EmptyState title="No active branches" message="Add a location to start." />
        ) : null}

        <Panel
          className="mt-6"
          title="Locations"
          detail="Create and edit gym locations. Changes are audited."
        >
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-border text-xs text-muted-foreground">
                  <th className="p-3">Name</th>
                  <th>District</th>
                  <th>Capacity</th>
                  <th>Timezone</th>
                  <th>Status</th>
                  <th>
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {(locations.data ?? []).map((gym) => (
                  <tr className="border-b border-border/60" key={gym.id}>
                    <td className="p-3 font-semibold">{gym.name}</td>
                    <td>{gym.district}</td>
                    <td>{gym.capacity}</td>
                    <td>{gym.timezone}</td>
                    <td>
                      <StatusBadge value={gym.is_active ? "active" : "inactive"} />
                    </td>
                    <td>
                      <Button
                        variant="outline"
                        onClick={() => openEdit(gym)}
                        aria-label={`Edit ${gym.name}`}
                      >
                        <Pencil className="size-4" /> Edit
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel
          className="mt-6"
          title="Workforce assignments"
          detail="Each manager, staff member and trainer works at one gym. Moving someone takes effect on their next request; staff must clock in again at the new gym."
        >
          {assignments.isLoading ? (
            <LoadingState className="m-4" title="Loading assignments" />
          ) : null}
          {assignments.isError ? (
            <ErrorState
              className="m-4"
              title={toUiError(assignments.error).title}
              message={toUiError(assignments.error).message}
            />
          ) : null}
          {assignments.data?.length === 0 ? (
            <EmptyState
              className="m-4"
              title="No assignments"
              message="Workforce accounts are assigned when they are created."
            />
          ) : null}
          {assignments.data?.length ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-border text-xs text-muted-foreground">
                    <th className="p-3">Person</th>
                    <th>Role</th>
                    <th>Gym</th>
                    <th>Since</th>
                  </tr>
                </thead>
                <tbody>
                  {assignments.data.map((item) => (
                    <tr className="border-b border-border/60" key={item.id}>
                      <td className="p-3">
                        <strong>{item.user_name}</strong>
                        <p className="text-xs text-muted-foreground">{item.user_email}</p>
                      </td>
                      <td>{item.assigned_role}</td>
                      <td>
                        <select
                          aria-label={`Gym for ${item.user_name}`}
                          className="h-9 rounded-md border border-input bg-card px-2"
                          value={item.gym_id}
                          disabled={reassign.isPending}
                          onChange={(event) => {
                            if (event.target.value !== item.gym_id)
                              reassign.mutate({
                                user_id: item.user_id,
                                gym_id: event.target.value,
                              });
                          }}
                        >
                          {active.map((gym) => (
                            <option value={gym.id} key={gym.id}>
                              {gym.name}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td>{formatDateTime(item.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </Panel>

        {editing ? (
          <Modal
            error={save.isError ? toUiError(save.error).message : undefined}
            title={editing === "new" ? "Add a gym location" : `Edit ${editing.name}`}
            description="Slug, timezone and capacity are validated by the server."
            onClose={() => setEditing(null)}
          >
            <form
              className="ops-modal__body"
              onSubmit={form.handleSubmit((values) =>
                save.mutate({ id: editing === "new" ? undefined : editing.id, values }),
              )}
            >
              <div className="grid gap-4 sm:grid-cols-2">
                <Field>
                  <Label>Name</Label>
                  <Input {...form.register("name")} />
                  <FieldError message={form.formState.errors.name?.message} />
                </Field>
                <Field>
                  <Label>Slug</Label>
                  <Input {...form.register("slug")} />
                  <FieldError message={form.formState.errors.slug?.message} />
                </Field>
                <Field>
                  <Label>District</Label>
                  <Input {...form.register("district")} />
                  <FieldError message={form.formState.errors.district?.message} />
                </Field>
                <Field>
                  <Label>Capacity</Label>
                  <Input
                    type="number"
                    min="1"
                    {...form.register("capacity", { valueAsNumber: true })}
                  />
                  <FieldError message={form.formState.errors.capacity?.message} />
                </Field>
                <Field className="sm:col-span-2">
                  <Label>Address</Label>
                  <Input {...form.register("address")} />
                  <FieldError message={form.formState.errors.address?.message} />
                </Field>
                <Field>
                  <Label>Timezone</Label>
                  <Input {...form.register("timezone")} />
                  <FieldError message={form.formState.errors.timezone?.message} />
                </Field>
                <label className="flex items-center gap-2 text-sm font-semibold sm:self-end">
                  <input type="checkbox" {...form.register("is_active")} /> Active
                </label>
              </div>
              <div className="ops-modal__actions">
                <Button type="button" variant="outline" onClick={() => setEditing(null)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={save.isPending}>
                  {save.isPending ? "Saving..." : "Save location"}
                </Button>
              </div>
            </form>
          </Modal>
        ) : null}
      </div>
    </AdminShell>
  );
}

function BranchCard({ gym }: { gym: GymLocation }) {
  const { token } = useAuth();
  const marker = gymMarker(gym.id);
  const [occupancy, traffic] = useQueries({
    queries: [
      {
        queryKey: ["attendance", "crowdedness", marker],
        queryFn: ({ signal }: { signal: AbortSignal }) =>
          apiRequest<Crowdedness>(`/gyms/${gym.id}/crowdedness`, { token, signal }),
        refetchInterval: 30_000,
      },
      {
        queryKey: ["attendance", "traffic-summary", marker],
        queryFn: ({ signal }: { signal: AbortSignal }) =>
          apiRequest<TrafficSummary>(`/admin/analytics/traffic-summary?gym_id=${gym.id}`, {
            token,
            signal,
          }),
        staleTime: 300_000,
      },
    ],
  });
  return (
    <article className="rounded-2xl border border-border bg-card p-5" aria-label={gym.name}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold">{gym.name}</h2>
          <p className="text-xs text-muted-foreground">
            {gym.district} · capacity {gym.capacity}
          </p>
        </div>
        {occupancy.data ? <StatusBadge value={occupancy.data.status} /> : null}
      </div>
      {occupancy.isError ? (
        <p className="mt-3 text-sm text-destructive">{toUiError(occupancy.error).message}</p>
      ) : (
        <p className="mt-4 font-['Barlow_Condensed'] text-4xl font-bold uppercase">
          {occupancy.data
            ? `${occupancy.data.active_count} in gym · ${occupancy.data.percentage}%`
            : "Loading"}
        </p>
      )}
      {traffic.isError ? (
        <p className="mt-3 text-sm text-destructive">{toUiError(traffic.error).message}</p>
      ) : null}
      {traffic.data ? (
        traffic.data.data_sufficient ? (
          <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt className="text-xs text-muted-foreground">Busiest last month</dt>
              <dd className="font-semibold">{traffic.data.busiest_window?.label ?? "-"}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Quietest last month</dt>
              <dd className="font-semibold">{traffic.data.quietest_window?.label ?? "-"}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Visits</dt>
              <dd className="font-semibold">{traffic.data.visits}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Unique members</dt>
              <dd className="font-semibold">{traffic.data.unique_members}</dd>
            </div>
          </dl>
        ) : (
          <p className="mt-4 text-sm text-muted-foreground">Not enough attendance data yet.</p>
        )
      ) : null}
      {traffic.data?.contains_demo_data ? (
        <p className="mt-2 text-xs text-muted-foreground">Includes demonstration data.</p>
      ) : null}
      {occupancy.data ? (
        <p className="mt-3 text-xs text-muted-foreground">
          Updated {formatDateTime(occupancy.data.calculated_at)}
        </p>
      ) : null}
      <Link
        className="mt-4 inline-flex text-sm font-bold text-primary"
        to={routePaths.adminAttendance}
        onClick={() => gymSelectionStore.set(gym.id)}
      >
        Open this branch's attendance
      </Link>
    </article>
  );
}
