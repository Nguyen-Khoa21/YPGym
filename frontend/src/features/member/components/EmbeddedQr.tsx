import { Clock3, QrCode, RefreshCw } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { Link } from "react-router-dom";

import { ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { Button } from "@/components/ui/Button";
import { toUiError } from "@/lib/apiErrors";
import { useRotatingQr } from "../useMemberQueries";

type EmbeddedQrProps = { eligible: boolean; reason: string | null };

const linkButton =
  "inline-flex min-h-11 items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

/** Rotating check-in code on the dashboard. An ineligible member sees why, and no token is requested. */
export function EmbeddedQr({ eligible, reason }: EmbeddedQrProps) {
  return (
    <section
      className="rounded-2xl border border-border bg-card p-5 sm:p-6"
      aria-labelledby="qr-heading"
    >
      <h2
        id="qr-heading"
        className="flex items-center gap-2 text-xs font-black uppercase tracking-wider text-muted-foreground"
      >
        <QrCode className="size-4" aria-hidden /> Check-in code
      </h2>
      {eligible ? (
        <ActiveQr />
      ) : (
        <div className="mt-4">
          <p className="text-lg font-bold">Access restricted</p>
          <p className="mt-2 text-sm text-muted-foreground">
            {reason ?? "Your membership does not allow gym access right now."}
          </p>
          <Link
            className={`${linkButton} mt-4 bg-primary text-primary-foreground`}
            to="/memberships"
          >
            Go to membership
          </Link>
        </div>
      )}
    </section>
  );
}

function ActiveQr() {
  const { query, secondsLeft } = useRotatingQr(true);
  const error = query.error ? toUiError(query.error) : null;
  if (query.isLoading)
    return (
      <LoadingState
        className="mt-4"
        title="Issuing your code"
        message="Checking your membership."
      />
    );
  if (error)
    return (
      <ErrorState
        className="mt-4"
        title={error.title}
        message={error.message}
        action={
          <Button variant="outline" onClick={() => void query.refetch()}>
            Try again
          </Button>
        }
      />
    );
  if (!query.data) return null;
  return (
    <div className="mt-4 flex flex-col items-center gap-4">
      <div className="rounded-xl bg-white p-3">
        <QRCodeSVG
          value={query.data.token}
          size={208}
          level="M"
          marginSize={1}
          aria-label="Rotating YPGym attendance QR code"
          className="h-auto w-full max-w-52"
        />
      </div>
      <p className="flex items-center gap-2 text-sm" aria-live="off">
        <Clock3 className="size-4" aria-hidden /> Refreshes in <strong>{secondsLeft}s</strong>
        {query.isFetching ? (
          <RefreshCw className="size-4 animate-spin" aria-label="Refreshing" />
        ) : null}
      </p>
      <Link className={`${linkButton} border border-border bg-card`} to="/app/qr">
        Open full QR page
      </Link>
    </div>
  );
}
