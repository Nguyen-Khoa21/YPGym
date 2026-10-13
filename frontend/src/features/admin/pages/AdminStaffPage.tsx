import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Clipboard, Plus, UsersRound } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { EmptyState, ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { AdminShell } from "@/components/layout/AdminShell";
import { Modal, OperationsHeader, Pagination, Panel, StatusBadge } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { Field, FieldError, Input, Label } from "@/components/ui/Form";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { formatDateTime } from "@/lib/format";
import { queryClient } from "@/lib/queryClient";
import type { StaffAccountCreated, StaffAccountPage, StaffShiftPage } from "@/types/operations";

const accountSchema = z.object({
  name: z.string().min(2, "Use at least 2 characters.").max(160),
  login_name: z.string().min(3).max(64).regex(/^[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9]$/, "Use letters, numbers, periods, hyphens or underscores."),
  role: z.enum(["staff", "pt"]),
  phone: z.string().refine((value) => value.length === 0 || value.length >= 7, "Use at least 7 characters."),
});
type AccountForm = z.infer<typeof accountSchema>;

function durationLabel(minutes: number) {
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
}

export function AdminStaffPage() {
  const { token } = useAuth();
  const [accountPage, setAccountPage] = useState(1);
  const [shiftPage, setShiftPage] = useState(1);
  const [search, setSearch] = useState("");
  const [role, setRole] = useState("");
  const [status, setStatus] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [creating, setCreating] = useState(false);
  const [created, setCreated] = useState<StaffAccountCreated | null>(null);
  const form = useForm<AccountForm>({ resolver: zodResolver(accountSchema), defaultValues: { name: "", login_name: "", role: "staff", phone: "" } });
  const accountParams = new URLSearchParams({ page: String(accountPage), page_size: "20" });
  if (search) accountParams.set("search", search);
  if (role) accountParams.set("role", role);
  const shiftParams = new URLSearchParams({ page: String(shiftPage), page_size: "20" });
  if (search) shiftParams.set("search", search);
  if (role) shiftParams.set("role", role);
  if (status) shiftParams.set("status", status);
  if (dateFrom) shiftParams.set("date_from", dateFrom);
  if (dateTo) shiftParams.set("date_to", dateTo);
  const accounts = useQuery({ queryKey: ["admin", "staff-accounts", accountPage, search, role], queryFn: ({ signal }) => apiRequest<StaffAccountPage>(`/admin/staff-accounts?${accountParams}`, { token, signal }) });
  const shifts = useQuery({ queryKey: ["admin", "staff-shifts", shiftPage, search, role, status, dateFrom, dateTo], queryFn: ({ signal }) => apiRequest<StaffShiftPage>(`/admin/staff-shifts?${shiftParams}`, { token, signal }) });
  const create = useMutation({
    mutationFn: (values: AccountForm) => apiRequest<StaffAccountCreated>("/admin/staff-accounts", { method: "POST", token, body: { ...values, phone: values.phone || null } }),
    onSuccess: async (result) => { setCreating(false); setCreated(result); form.reset(); await Promise.all([queryClient.invalidateQueries({ queryKey: ["admin", "staff-accounts"] }), queryClient.invalidateQueries({ queryKey: ["admin", "trainers"] }), queryClient.invalidateQueries({ queryKey: ["admin", "class-trainers"] })]); toast.success("Workforce account created"); },
    onError: (error) => toast.error(toUiError(error).message),
  });

  return <AdminShell><div className="mx-auto max-w-7xl">
    <OperationsHeader kicker="Workforce operations" title="Individual accounts and shifts." description="Provision staff or PT sign-ins, reveal each temporary password once, and review server-recorded shifts." actions={<Button onClick={() => { create.reset(); form.reset(); setCreating(true); }}><Plus className="size-4" /> Create account</Button>} />
    <div className="mt-7 grid gap-3 sm:grid-cols-2 lg:grid-cols-5"><Field className="lg:col-span-2"><Label htmlFor="staff-search">Name or login</Label><Input id="staff-search" value={search} onChange={(event) => { setSearch(event.target.value); setAccountPage(1); setShiftPage(1); }} /></Field><Field><Label htmlFor="staff-role">Role</Label><select id="staff-role" className="h-11 w-full rounded-md border border-input bg-card px-3 text-sm" value={role} onChange={(event) => { setRole(event.target.value); setAccountPage(1); setShiftPage(1); }}><option value="">All roles</option><option value="staff">Staff</option><option value="pt">PT</option></select></Field><Field><Label htmlFor="shift-status">Shift status</Label><select id="shift-status" className="h-11 w-full rounded-md border border-input bg-card px-3 text-sm" value={status} onChange={(event) => { setStatus(event.target.value); setShiftPage(1); }}><option value="">All shifts</option><option value="open">Open</option><option value="closed">Closed</option></select></Field><div className="flex items-end"><Button className="w-full" variant="outline" onClick={() => { setSearch(""); setRole(""); setStatus(""); setDateFrom(""); setDateTo(""); }}>Clear filters</Button></div></div>
    <div className="mt-5 grid gap-3 sm:grid-cols-2"><Field><Label htmlFor="shift-from">Shift date from</Label><Input id="shift-from" type="date" value={dateFrom} onChange={(event) => { setDateFrom(event.target.value); setShiftPage(1); }} /></Field><Field><Label htmlFor="shift-to">Shift date to</Label><Input id="shift-to" type="date" value={dateTo} min={dateFrom || undefined} onChange={(event) => { setDateTo(event.target.value); setShiftPage(1); }} /></Field></div>
    <div className="mt-7 grid items-start gap-6 xl:grid-cols-2">
      <Panel title="Workforce accounts" detail={accounts.data ? `Internal sign-ins use @${accounts.data.internal_email_domain}. This is not a claimed mailbox domain.` : "Distinct staff and PT credentials."}>
        {accounts.isLoading ? <LoadingState className="m-4" title="Loading accounts" /> : null}{accounts.isError ? <ErrorState className="m-4" title={toUiError(accounts.error).title} message={toUiError(accounts.error).message} action={<Button variant="outline" onClick={() => void accounts.refetch()}>Retry</Button>} /> : null}{accounts.data?.items.length === 0 ? <EmptyState className="m-4" title="No workforce accounts" message="Create the first individual staff or PT account." /> : null}
        {accounts.data?.items.length ? <div className="divide-y divide-border">{accounts.data.items.map((account) => <article className="flex flex-wrap items-start justify-between gap-4 p-4" key={account.id}><div><strong>{account.name}</strong><p className="mt-1 text-xs text-muted-foreground">{account.email}{account.phone ? ` · ${account.phone}` : ""}</p><p className="mt-2 text-xs">{account.trainer_profile_id ? "Linked PT profile" : account.role === "staff" ? "Staff operations access" : "PT profile pending"}</p></div><div className="grid justify-items-end gap-2"><StatusBadge value={account.role} /><StatusBadge value={account.must_change_password ? "password change required" : "active"} /></div></article>)}</div> : null}{accounts.data ? <Pagination page={accountPage} pages={accounts.data.page.pages} total={accounts.data.page.total} onPage={setAccountPage} /> : null}
      </Panel>
      <Panel title="Shift report" detail={shifts.data ? `Displayed in ${shifts.data.gym_timezone}` : "UTC records rendered in gym local time."}>
        {shifts.isLoading ? <LoadingState className="m-4" title="Loading shifts" /> : null}{shifts.isError ? <ErrorState className="m-4" title={toUiError(shifts.error).title} message={toUiError(shifts.error).message} action={<Button variant="outline" onClick={() => void shifts.refetch()}>Retry</Button>} /> : null}{shifts.data?.items.length === 0 ? <EmptyState className="m-4" title="No matching shifts" message="Shift records appear after staff or PT users clock in." /> : null}
        {shifts.data?.items.length ? <div className="divide-y divide-border">{shifts.data.items.map((shift) => <article className="p-4" key={shift.id}><div className="flex flex-wrap items-start justify-between gap-3"><div><strong>{shift.staff_name}</strong><p className="mt-1 text-xs text-muted-foreground">{shift.staff_email} · {shift.role.toUpperCase()}</p></div><StatusBadge value={shift.status} /></div><p className="mt-3 text-sm">{formatDateTime(shift.clocked_in_at, shifts.data.gym_timezone)} → {shift.clocked_out_at ? formatDateTime(shift.clocked_out_at, shifts.data.gym_timezone) : "Open"}</p><p className="mt-1 text-xs text-muted-foreground">Duration {durationLabel(shift.duration_minutes)}</p></article>)}</div> : null}{shifts.data ? <Pagination page={shiftPage} pages={shifts.data.page.pages} total={shifts.data.page.total} onPage={setShiftPage} /> : null}
      </Panel>
    </div>
    {creating ? <Modal title="Create workforce account" description="Managers can create staff and PT accounts only. Admin roles cannot be provisioned here." error={create.isError ? toUiError(create.error).message : undefined} onClose={() => setCreating(false)}><form className="ops-modal__body" onSubmit={form.handleSubmit((values) => create.mutate(values))}><div className="grid gap-4"><Field><Label htmlFor="staff-name">Full name</Label><Input id="staff-name" autoComplete="name" {...form.register("name")} /><FieldError message={form.formState.errors.name?.message} /></Field><Field><Label htmlFor="staff-login">Login name</Label><Input id="staff-login" autoCapitalize="none" placeholder="alex.nguyen" {...form.register("login_name")} /><FieldError message={form.formState.errors.login_name?.message} /></Field><Field><Label htmlFor="staff-account-role">Role</Label><select id="staff-account-role" className="h-11 w-full rounded-md border border-input bg-card px-3 text-sm" {...form.register("role")}><option value="staff">Staff</option><option value="pt">Personal trainer</option></select></Field><Field><Label htmlFor="staff-phone">Phone (optional)</Label><Input id="staff-phone" autoComplete="tel" {...form.register("phone")} /><FieldError message={form.formState.errors.phone?.message} /></Field></div><div className="ops-modal__actions"><Button variant="outline" onClick={() => setCreating(false)}>Cancel</Button><Button type="submit" disabled={create.isPending}>{create.isPending ? "Creating..." : "Create account"}</Button></div></form></Modal> : null}
    {created ? <Modal title="Copy temporary credentials" description={created.message} onClose={() => setCreated(null)}><div className="ops-modal__body"><div className="rounded-xl border border-border bg-muted/40 p-4"><p className="text-xs font-black uppercase tracking-wider text-muted-foreground">Login</p><code className="mt-1 block break-all text-sm font-bold">{created.account.email}</code><p className="mt-4 text-xs font-black uppercase tracking-wider text-muted-foreground">Temporary password</p><code className="mt-1 block break-all text-sm font-bold">{created.temporary_password}</code></div><p className="text-sm leading-6 text-muted-foreground">Share these credentials privately. The user must replace the password at first login. This internal login domain is not presented as a deliverable email inbox.</p><div className="ops-modal__actions"><Button variant="outline" onClick={() => void navigator.clipboard.writeText(`${created.account.email}\n${created.temporary_password}`).then(() => toast.success("Credentials copied"))}><Clipboard className="size-4" /> Copy</Button><Button onClick={() => setCreated(null)}><UsersRound className="size-4" /> Done</Button></div></div></Modal> : null}
  </div></AdminShell>;
}
