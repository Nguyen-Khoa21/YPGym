import { useQuery } from "@tanstack/react-query";
import { Clock3, QrCode, RefreshCw, ShieldCheck } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";

import { QueryState } from "@/components/common/QueryState";
import { MemberShell } from "@/components/layout/MemberShell";
import { OperationsHeader, Panel, StatusBadge } from "@/components/operations/OperationsUi";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { ExpiredMembershipPanel } from "@/features/member/components/ExpiredMembershipPanel";
import { OccupancyCard } from "@/features/member/components/OccupancyCard";
import { TrafficHistory } from "@/features/member/components/TrafficHistory";
import {
  useHomeCrowdedness,
  useRotatingQr,
  useTrafficSummary,
} from "@/features/member/useMemberQueries";
import { apiRequest } from "@/lib/apiClient";
import { formatDateTime } from "@/lib/format";
import type { AttendancePage, MemberDashboardPayload } from "@/types/operations";

export function MemberQrPage() {
  const { token, user } = useAuth();
  const { query: qr, secondsLeft } = useRotatingQr();
  const attendance = useQuery({
    queryKey: ["attendance", "me", "qr-summary"],
    queryFn: ({ signal }) =>
      apiRequest<AttendancePage>("/attendance/me?page=1&page_size=5", { token, signal }),
  });
  const dashboard = useQuery({
    queryKey: ["dashboard", "me"],
    queryFn: ({ signal }) => apiRequest<MemberDashboardPayload>("/dashboard/me", { token, signal }),
  });
  const crowdedness = useHomeCrowdedness();
  const traffic = useTrafficSummary();

  const gymLine = traffic.data
    ? `${traffic.data.gym_name} · ${traffic.data.district}`
    : crowdedness.data?.gym_name;
  return (
    <MemberShell>
      <div className="mx-auto max-w-6xl">
        <OperationsHeader
          kicker={gymLine ? `Your gym: ${gymLine}` : "Rotating access pass"}
          title="Your check-in code."
          description="A signed, short-lived code replaces static membership screenshots and refreshes before it expires."
          actions={
            <Button variant="outline" disabled={qr.isFetching} onClick={() => void qr.refetch()}>
              <RefreshCw className={`size-4 ${qr.isFetching ? "animate-spin" : ""}`} /> Refresh now
            </Button>
          }
        />
        <div className="mt-6">
          <ExpiredMembershipPanel membership={dashboard.data?.membership} />
        </div>
        <QueryState
          query={qr}
          className="mt-6"
          loading={{
            title: "Issuing your rotating QR code",
            message: "Membership eligibility and token state are being checked.",
          }}
          retry="Check access again"
        >
          {(qrToken) => (
            <div className="mt-6 grid gap-5 lg:grid-cols-[0.82fr_1.18fr]">
              <Panel title="Check-in pass" detail="Present this code to the registered scanner.">
                <div className="p-5 sm:p-7">
                  <div className="qr-pass">
                    <header>
                      <div>
                        <h3>{user?.name}</h3>
                        <p>Member ID: {user?.id.slice(0, 8)}</p>
                      </div>
                      <StatusBadge value={qrToken.membership_status} />
                    </header>
                    <div className="qr-pass__code">
                      <QRCodeSVG
                        value={qrToken.token}
                        size={256}
                        level="M"
                        marginSize={2}
                        aria-label="Rotating YPGym attendance QR code"
                      />
                    </div>
                    <div className="qr-pass__timer">
                      <Clock3 className="size-4" />
                      <span>
                        Refreshes in <strong>{secondsLeft}s</strong>
                      </span>
                    </div>
                  </div>
                  <p className="mt-4 flex items-start gap-2 rounded-xl bg-muted p-3 text-xs leading-5 text-muted-foreground">
                    <ShieldCheck className="mt-0.5 size-4 shrink-0" /> Tokens are signed, superseded
                    on refresh, and accepted only while Redis confirms the active token ID.
                  </p>
                </div>
              </Panel>
              <div className="grid content-start gap-5">
                <QueryState
                  query={crowdedness}
                  loading={{ title: "Loading facility status" }}
                  retry
                >
                  {(data) => <OccupancyCard data={data} />}
                </QueryState>
                <Panel title="Recent attendance" detail="Your five latest persisted sessions.">
                  <QueryState
                    query={attendance}
                    className="m-4"
                    loading={{ title: "Loading recent visits" }}
                    empty={{
                      title: "No visits yet",
                      message: "Your first successful scanner check-in will appear here.",
                    }}
                    isEmpty={(data) => data.items.length === 0}
                  >
                    {(data) => (
                      <div className="grid gap-2 p-4">
                        {data.items.map((item) => (
                          <article
                            className="flex items-center gap-3 rounded-xl border border-border p-3"
                            key={item.id}
                          >
                            <span className="grid size-9 place-items-center rounded-xl bg-secondary">
                              <QrCode className="size-4" />
                            </span>
                            <div className="min-w-0 flex-1">
                              <strong className="block text-sm">
                                {formatDateTime(item.checked_in_at)}
                              </strong>
                              <small className="text-xs text-muted-foreground">
                                {item.device_id ?? item.source}
                              </small>
                            </div>
                            <StatusBadge value={item.status} />
                          </article>
                        ))}
                      </div>
                    )}
                  </QueryState>
                </Panel>
              </div>
            </div>
          )}
        </QueryState>
        <div className="mt-5">
          <TrafficHistory
            query={traffic}
            gymName={crowdedness.data?.gym_name ?? dashboard.data?.membership?.home_gym_name}
          />
        </div>
      </div>
    </MemberShell>
  );
}
