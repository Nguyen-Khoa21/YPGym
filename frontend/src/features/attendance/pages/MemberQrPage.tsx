import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Clock3, Gauge, QrCode, RefreshCw, ShieldCheck } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";

import { EmptyState, ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { MemberShell } from "@/components/layout/MemberShell";
import { MetricCard, OperationsHeader, Panel, StatusBadge } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { formatDateTime } from "@/lib/format";
import type { AttendancePage, Crowdedness, QrToken } from "@/types/operations";

export function MemberQrPage() {
  const { token, user } = useAuth();
  const qr = useQuery({
    queryKey: ["attendance", "qr-token"],
    queryFn: ({ signal }) => apiRequest<QrToken>("/attendance/qr-token/me", { token, signal }),
    retry: false,
    refetchOnWindowFocus: true,
  });
  const attendance = useQuery({
    queryKey: ["attendance", "me", "qr-summary"],
    queryFn: ({ signal }) => apiRequest<AttendancePage>("/attendance/me?page=1&page_size=5", { token, signal }),
  });
  const crowdedness = useQuery({
    queryKey: ["attendance", "crowdedness"],
    queryFn: ({ signal }) => apiRequest<Crowdedness>("/attendance/crowdedness", { token, signal }),
    refetchInterval: 30_000,
  });
  const secondsLeft = useSecondsLeft(qr.data?.expires_at);
  const qrExpiresAt = qr.data?.expires_at;
  const refetchQr = qr.refetch;

  useEffect(() => {
    if (!qrExpiresAt) return;
    const refreshIn = Math.max(1_000, new Date(qrExpiresAt).getTime() - Date.now() - 5_000);
    const timer = window.setTimeout(() => { void refetchQr(); }, refreshIn);
    return () => window.clearTimeout(timer);
  }, [qrExpiresAt, refetchQr]);

  const qrError = qr.error ? toUiError(qr.error) : null;
  return <MemberShell><div className="mx-auto max-w-6xl">
    <OperationsHeader kicker="Rotating access pass" title="Your check-in code." description="A signed, short-lived code replaces static membership screenshots and refreshes before it expires." actions={<Button variant="outline" disabled={qr.isFetching} onClick={() => void qr.refetch()}><RefreshCw className={`size-4 ${qr.isFetching ? "animate-spin" : ""}`} /> Refresh now</Button>} />
    {crowdedness.data ? <div className="ops-metrics"><MetricCard label="Current occupancy" value={`${crowdedness.data.active_count}/${crowdedness.data.capacity}`} tone="forest" /><MetricCard label="Capacity used" value={`${crowdedness.data.percentage}%`} tone="lime" /><MetricCard label="Facility status" value={crowdedness.data.status} /><MetricCard label="Access state" value={qr.data?.membership_status ?? "Checking"} tone="coral" /></div> : null}
    {qr.isLoading ? <LoadingState className="mt-6" title="Issuing your rotating QR code" message="Membership eligibility and token state are being checked." /> : null}
    {qrError ? <ErrorState className="mt-6" title={qrError.title} message={qrError.message} action={<Button variant="outline" onClick={() => void qr.refetch()}>Check access again</Button>} /> : null}
    {qr.data ? <div className="mt-6 grid gap-5 lg:grid-cols-[0.82fr_1.18fr]">
      <Panel title="Check-in pass" detail="Present this code to the registered scanner."><div className="p-5 sm:p-7"><div className="qr-pass"><header><div><h3>{user?.name}</h3><p>Member ID: {user?.id.slice(0, 8)}</p></div><StatusBadge value={qr.data.membership_status} /></header><div className="qr-pass__code"><QRCodeSVG value={qr.data.token} size={256} level="M" marginSize={2} aria-label="Rotating YPGym attendance QR code" /></div><div className="qr-pass__timer"><Clock3 className="size-4" /><span>Refreshes in <strong>{secondsLeft}s</strong></span></div></div><p className="mt-4 flex items-start gap-2 rounded-xl bg-muted p-3 text-xs leading-5 text-muted-foreground"><ShieldCheck className="mt-0.5 size-4 shrink-0" /> Tokens are signed, superseded on refresh, and accepted only while Redis confirms the active token ID.</p></div></Panel>
      <div className="grid gap-5"><Panel title="Facility capacity" detail="PostgreSQL sessions are the source of truth; Redis is reconciled for fast reads.">{crowdedness.isLoading ? <LoadingState className="m-4" title="Loading facility status" /> : null}{crowdedness.isError ? <ErrorState className="m-4" title={toUiError(crowdedness.error).title} message={toUiError(crowdedness.error).message} /> : null}{crowdedness.data ? <div className="p-5"><div className="flex items-end justify-between gap-4"><div><p className="text-xs font-black uppercase tracking-wider text-muted-foreground">{crowdedness.data.status}</p><strong className="font-['Barlow_Condensed'] text-5xl uppercase">{crowdedness.data.percentage}%</strong></div><Gauge className="size-10 text-primary" /></div><div className="mt-4 h-3 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-secondary" style={{ width: `${Math.min(crowdedness.data.percentage, 100)}%` }} /></div><p className="mt-3 text-xs text-muted-foreground">Calculated {formatDateTime(crowdedness.data.calculated_at)}</p></div> : null}</Panel>
      <Panel title="Recent attendance" detail="Your five latest persisted sessions.">{attendance.isLoading ? <LoadingState className="m-4" title="Loading recent visits" /> : null}{attendance.isError ? <ErrorState className="m-4" title={toUiError(attendance.error).title} message={toUiError(attendance.error).message} /> : null}{attendance.data?.items.length === 0 ? <EmptyState className="m-4" title="No visits yet" message="Your first successful scanner check-in will appear here." /> : null}<div className="grid gap-2 p-4">{attendance.data?.items.map((item) => <article className="flex items-center gap-3 rounded-xl border border-border p-3" key={item.id}><span className="grid size-9 place-items-center rounded-xl bg-secondary"><QrCode className="size-4" /></span><div className="min-w-0 flex-1"><strong className="block text-sm">{formatDateTime(item.checked_in_at)}</strong><small className="text-xs text-muted-foreground">{item.device_id ?? item.source}</small></div><StatusBadge value={item.status} /></article>)}</div></Panel></div>
    </div> : null}
  </div></MemberShell>;
}

function useSecondsLeft(expiresAt?: string) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1_000);
    return () => window.clearInterval(timer);
  }, []);
  if (!expiresAt) return 0;
  return Math.max(0, Math.ceil((new Date(expiresAt).getTime() - now) / 1_000));
}
