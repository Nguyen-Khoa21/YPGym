import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { CalendarDays, MapPin, Search, UsersRound } from "lucide-react";
import { toast } from "sonner";

import { EmptyState, ErrorState, LoadingState, PermissionState } from "@/components/common/FeedbackState";
import { MemberShell } from "@/components/layout/MemberShell";
import { Modal, StatusBadge } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { PTCard } from "@/features/classes/components/PTCard";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { formatDateTime } from "@/lib/format";
import { queryClient } from "@/lib/queryClient";
import type { ClassBooking, ClassWaitlist, MemberClass, MemberClassList } from "@/types/operations";

export function MemberClassesPage() {
  const { token } = useAuth();
  const [search, setSearch] = useState("");
  const [day, setDay] = useState("all");
  const [confirmation, setConfirmation] = useState<{ item: MemberClass; action: "book" | "join" | "leave" } | null>(null);
  const classes = useQuery({ queryKey: ["classes", "upcoming"], queryFn: ({ signal }) => apiRequest<MemberClassList>("/classes/upcoming", { token, signal }) });
  const book = useMutation({
    mutationFn: (classId: string) => apiRequest<ClassBooking>(`/classes/${classId}/book`, { method: "POST", token }),
    onSuccess: async () => { setConfirmation(null); await Promise.all([queryClient.invalidateQueries({ queryKey: ["classes"] }), queryClient.invalidateQueries({ queryKey: ["bookings"] }), queryClient.invalidateQueries({ queryKey: ["dashboard"] })]); toast.success("Class booked"); },
    onError: (error) => toast.error(toUiError(error).message),
  });
  const waitlist = useMutation({
    mutationFn: ({ classId, leave }: { classId: string; leave: boolean }) => apiRequest<ClassWaitlist>(`/classes/${classId}/waitlist`, { method: leave ? "DELETE" : "POST", token }),
    onSuccess: async (_, variables) => { setConfirmation(null); await Promise.all([queryClient.invalidateQueries({ queryKey: ["classes"] }), queryClient.invalidateQueries({ queryKey: ["bookings"] }), queryClient.invalidateQueries({ queryKey: ["dashboard"] })]); toast.success(variables.leave ? "Left waitlist" : "Joined waitlist"); },
    onError: (error) => toast.error(toUiError(error).message),
  });
  const visible = useMemo(() => (classes.data?.items ?? []).filter((item) => {
    const term = search.trim().toLowerCase();
    if (term && !`${item.title} ${item.class_type} ${item.trainer?.display_name ?? ""}`.toLowerCase().includes(term)) return false;
    if (day === "all") return true;
    const target = new Date();
    if (day === "tomorrow") target.setDate(target.getDate() + 1);
    const itemDate = new Date(item.start_at);
    return itemDate.getFullYear() === target.getFullYear() && itemDate.getMonth() === target.getMonth() && itemDate.getDate() === target.getDate();
  }), [classes.data?.items, day, search]);

  return <MemberShell><div className="mx-auto max-w-6xl">
    <div><p className="page-kicker">Class booking</p><h1 className="page-title">Find your next session.</h1><p className="page-description">Live capacity, trainer profiles, and your current booking state come directly from the class service.</p></div>
    <div className="mt-7 grid gap-3 rounded-2xl border border-border bg-card p-4 sm:grid-cols-[1fr_auto]"><label className="flex h-11 items-center gap-2 rounded-md border border-input px-3"><Search className="size-4 text-muted-foreground" aria-hidden /><span className="sr-only">Search classes or trainers</span><input className="min-w-0 flex-1 bg-transparent text-sm outline-none" placeholder="Search classes or trainers" value={search} onChange={(event) => setSearch(event.target.value)} /></label><select aria-label="Filter classes by day" className="h-11 rounded-md border border-input bg-card px-3 text-sm" value={day} onChange={(event) => setDay(event.target.value)}><option value="all">All upcoming</option><option value="today">Today</option><option value="tomorrow">Tomorrow</option></select></div>
    {classes.isLoading ? <LoadingState className="mt-5" title="Loading upcoming classes" /> : null}
    {classes.isError ? <ErrorState className="mt-5" title={toUiError(classes.error).title} message={toUiError(classes.error).message} action={<Button variant="outline" onClick={() => classes.refetch()}>Retry</Button>} /> : null}
    {classes.data && !classes.data.booking_eligible ? <PermissionState className="mt-5" title="Booking unavailable" message={classes.data.eligibility_reason ?? "An eligible membership is required."} /> : null}
    {classes.data && visible.length === 0 ? <EmptyState className="mt-5" title="No upcoming classes match" message="Change the search or day filter and try again." /> : null}
    {visible.length ? <section className="mt-5 grid gap-5 lg:grid-cols-2">{visible.map((item) => <ClassCard item={item} eligible={classes.data?.booking_eligible ?? false} pending={(book.isPending && book.variables === item.id) || (waitlist.isPending && waitlist.variables?.classId === item.id)} onBook={() => setConfirmation({ item, action: "book" })} onWaitlist={() => setConfirmation({ item, action: item.member_state === "waitlisted" ? "leave" : "join" })} key={item.id} />)}</section> : null}
    {confirmation ? <Modal error={(confirmation.action === "book" ? book : waitlist).isError ? toUiError((confirmation.action === "book" ? book : waitlist).error).message : undefined} title={`${confirmation.action === "book" ? "Book" : confirmation.action === "join" ? "Join waitlist for" : "Leave waitlist for"} ${confirmation.item.title}?`} onClose={() => setConfirmation(null)}><div className="ops-modal__body"><p className="text-sm text-muted-foreground">{formatDateTime(confirmation.item.start_at)} / {confirmation.item.location}</p><div className="ops-modal__actions"><Button variant="outline" onClick={() => setConfirmation(null)}>Keep unchanged</Button><Button disabled={book.isPending || waitlist.isPending} onClick={() => confirmation.action === "book" ? book.mutate(confirmation.item.id) : waitlist.mutate({ classId: confirmation.item.id, leave: confirmation.action === "leave" })}>{book.isPending || waitlist.isPending ? "Updating..." : "Confirm"}</Button></div></div></Modal> : null}
  </div></MemberShell>;
}

function ClassCard({ item, eligible, pending, onBook, onWaitlist }: { item: MemberClass; eligible: boolean; pending: boolean; onBook: () => void; onWaitlist: () => void }) {
  const actionable = item.member_state === "available" && eligible;
  return <article className="grid content-start gap-4 rounded-2xl border border-border bg-card p-5 shadow-[0_1rem_3rem_-2.5rem_hsl(var(--foreground)/0.3)]">
    <div className="flex items-start justify-between gap-4"><div><p className="text-[10px] font-black uppercase tracking-[0.12em] text-primary">{item.class_type}</p><h2 className="mt-2 font-['Barlow_Condensed'] text-4xl font-bold uppercase leading-none">{item.title}</h2></div><StatusBadge value={item.member_state} /></div>
    <div className="grid gap-2 text-sm text-muted-foreground"><p className="flex items-center gap-2"><CalendarDays className="size-4 text-primary" aria-hidden />{formatDateTime(item.start_at)} to {new Date(item.end_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</p><p className="flex items-center gap-2"><MapPin className="size-4 text-primary" aria-hidden />{item.location}</p><p className="flex items-center gap-2"><UsersRound className="size-4 text-primary" aria-hidden />{item.remaining_capacity} of {item.capacity} places remaining</p></div>
    {item.description ? <p className="text-sm leading-6 text-muted-foreground">{item.description}</p> : null}
    {item.trainer ? <PTCard trainer={item.trainer} compact /> : <p className="rounded-xl bg-muted/50 p-4 text-sm text-muted-foreground">Trainer assignment pending.</p>}
    {item.member_state === "full" || item.member_state === "waitlisted" ? <Button variant={item.member_state === "waitlisted" ? "outline" : "primary"} disabled={!eligible || pending} onClick={onWaitlist}>{pending ? "Updating..." : item.member_state === "waitlisted" ? `Leave waitlist (position ${item.waitlist_position ?? "-"})` : "Join waitlist"}</Button> : <Button disabled={!actionable || pending} onClick={onBook}>{pending ? "Booking..." : item.member_state === "booked" ? "Booked" : item.member_state === "cancelled" ? "Class cancelled" : item.member_state === "ineligible" ? "Membership required" : "Book class"}</Button>}
  </article>;
}
