import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { CalendarDays, Clock3, MapPin } from "lucide-react";
import { toast } from "sonner";
import { Link } from "react-router-dom";

import { EmptyState, ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { MemberShell } from "@/components/layout/MemberShell";
import { Modal, StatusBadge } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { formatDateTime, formatMoney } from "@/lib/format";
import { queryClient } from "@/lib/queryClient";
import type { ClassBooking, ClassWaitlist, MemberBookings } from "@/types/operations";

export function MyBookingsPage() {
  const { token } = useAuth();
  const [confirmation, setConfirmation] = useState<{ id: string; title: string; action: "cancel" | "leave" } | null>(null);
  const query = useQuery({ queryKey: ["bookings", "me"], queryFn: ({ signal }) => apiRequest<MemberBookings>("/bookings/me", { token, signal }) });
  const cancel = useMutation({
    mutationFn: (bookingId: string) => apiRequest<ClassBooking>(`/bookings/${bookingId}/cancel`, { method: "POST", token }),
    onSuccess: async () => { setConfirmation(null); await refreshBookingQueries(); toast.success("Booking cancelled"); },
    onError: (error) => toast.error(toUiError(error).message),
  });
  const leave = useMutation({
    mutationFn: (classId: string) => apiRequest<ClassWaitlist>(`/classes/${classId}/waitlist`, { method: "DELETE", token }),
    onSuccess: async () => { setConfirmation(null); await refreshBookingQueries(); toast.success("Left waitlist"); },
    onError: (error) => toast.error(toUiError(error).message),
  });
  const hasItems = Boolean(query.data?.bookings.length || query.data?.waitlists.length);

  return <MemberShell><div className="mx-auto max-w-6xl">
    <div><p className="page-kicker">My bookings</p><h1 className="page-title">Your class queue.</h1><p className="page-description">Confirmed bookings, cancellations, waitlist positions, and promotions are shown from the real transaction state.</p></div>
    {query.isLoading ? <LoadingState className="mt-7" title="Loading your bookings" /> : null}
    {query.isError ? <ErrorState className="mt-7" title={toUiError(query.error).title} message={toUiError(query.error).message} action={<Button variant="outline" onClick={() => query.refetch()}>Retry</Button>} /> : null}
    {query.data && !hasItems ? <EmptyState className="mt-7" title="No bookings yet" message="Browse upcoming classes to book a place or join a full-class waitlist." action={<Button onClick={() => window.location.assign("/app/classes")}>Browse classes</Button>} /> : null}
    {query.data?.bookings.length ? <section className="mt-7"><h2 className="text-xl font-bold">Bookings</h2><p className="mt-1 text-sm text-muted-foreground">{query.data.cancellation_terms}</p><div className="mt-4 grid gap-4 lg:grid-cols-2">{query.data.bookings.map((booking) => <BookingCard booking={booking} pending={cancel.isPending && cancel.variables === booking.id} onCancel={() => setConfirmation({ id: booking.id, title: booking.gym_class.title, action: "cancel" })} key={booking.id} />)}</div></section> : null}
    {query.data?.waitlists.length ? <section className="mt-8"><h2 className="text-xl font-bold">Waitlists</h2><div className="mt-4 grid gap-4 lg:grid-cols-2">{query.data.waitlists.map((entry) => <WaitlistCard entry={entry} pending={leave.isPending && leave.variables === entry.gym_class.id} onLeave={() => setConfirmation({ id: entry.gym_class.id, title: entry.gym_class.title, action: "leave" })} key={entry.id} />)}</div></section> : null}
    {confirmation ? <Modal error={(confirmation.action === "cancel" ? cancel : leave).isError ? toUiError((confirmation.action === "cancel" ? cancel : leave).error).message : undefined} title={`${confirmation.action === "cancel" ? "Cancel booking for" : "Leave waitlist for"} ${confirmation.title}?`} description={confirmation.action === "cancel" ? "The seat will be released. A paid booking is marked for staff refund resolution; VNPay is not reversed automatically." : "Your waitlist place will be released."} onClose={() => setConfirmation(null)}><div className="ops-modal__body"><div className="ops-modal__actions"><Button variant="outline" onClick={() => setConfirmation(null)}>Keep unchanged</Button><Button variant="danger" disabled={cancel.isPending || leave.isPending} onClick={() => confirmation.action === "cancel" ? cancel.mutate(confirmation.id) : leave.mutate(confirmation.id)}>{cancel.isPending || leave.isPending ? "Updating..." : "Confirm"}</Button></div></div></Modal> : null}
  </div></MemberShell>;
}

function BookingCard({ booking, pending, onCancel }: { booking: ClassBooking; pending: boolean; onCancel: () => void }) {
  const item = booking.gym_class;
  return <article className="rounded-2xl border border-border bg-card p-5"><div className="flex items-start justify-between gap-3"><div><p className="text-[10px] font-black uppercase tracking-wider text-primary">{item.class_type}</p><h3 className="mt-1 text-2xl font-bold">{item.title}</h3></div><StatusBadge value={booking.refund_status === "required" ? "refund required" : booking.status} /></div><ClassMeta item={item} /><p className="mt-4 font-bold">{booking.price_vnd ? formatMoney(booking.price_vnd) : "Legacy booking"}</p>{booking.reserved_until && booking.status === "pending_payment" ? <p className="mt-2 text-xs text-muted-foreground">Seat held until {formatDateTime(booking.reserved_until)}</p> : null}{booking.invoice_id ? <Link className="mt-3 inline-flex text-sm font-bold text-primary underline" to="/app/billing">View invoice</Link> : null}{booking.payment_id && booking.status === "pending_payment" ? <Link className="mt-3 ml-4 inline-flex text-sm font-bold text-primary underline" to={`/app/payments/result?transaction_id=${booking.payment_id}&state=processing`}>Check payment</Link> : null}{booking.can_cancel ? <Button className="mt-4 block" variant="danger" disabled={pending} onClick={onCancel}>{pending ? "Cancelling..." : "Cancel booking"}</Button> : null}</article>;
}

function WaitlistCard({ entry, pending, onLeave }: { entry: ClassWaitlist; pending: boolean; onLeave: () => void }) {
  return <article className="rounded-2xl border border-border bg-card p-5"><div className="flex items-start justify-between gap-3"><div><p className="text-[10px] font-black uppercase tracking-wider text-primary">Waitlist position {entry.position}</p><h3 className="mt-1 text-2xl font-bold">{entry.gym_class.title}</h3></div><StatusBadge value={entry.status} /></div><ClassMeta item={entry.gym_class} />{entry.status === "waiting" ? <Button className="mt-4" variant="outline" disabled={pending} onClick={onLeave}>{pending ? "Leaving..." : "Leave waitlist"}</Button> : null}</article>;
}

function ClassMeta({ item }: { item: ClassBooking["gym_class"] }) { return <div className="mt-4 grid gap-2 text-sm text-muted-foreground"><p className="flex items-center gap-2"><CalendarDays className="size-4 text-primary" aria-hidden />{formatDateTime(item.start_at)}</p><p className="flex items-center gap-2"><MapPin className="size-4 text-primary" aria-hidden />{item.location}</p><p className="flex items-center gap-2"><Clock3 className="size-4 text-primary" aria-hidden />{item.remaining_capacity} places remaining</p></div>; }
async function refreshBookingQueries() { await Promise.all([queryClient.invalidateQueries({ queryKey: ["bookings"] }), queryClient.invalidateQueries({ queryKey: ["classes"] }), queryClient.invalidateQueries({ queryKey: ["dashboard"] }), queryClient.invalidateQueries({ queryKey: ["notifications"] })]); }
