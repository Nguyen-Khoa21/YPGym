import { useQuery } from "@tanstack/react-query";
import { ArrowRight, BadgeCheck, MailWarning } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";

import { ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { AuthShell } from "@/components/layout/AuthShell";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";

export function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const verification = useQuery({
    queryKey: ["verify-email", token],
    enabled: Boolean(token),
    retry: false,
    queryFn: ({ signal }) => apiRequest<{ message: string }>(`/auth/verify-email?token=${encodeURIComponent(token ?? "")}`, { signal }),
  });

  return (
    <AuthShell eyebrow="Email verification" title={<>One more<br /><span className="text-secondary">step.</span></>} description="We are validating the one-time token from your registration link before your account can buy a membership." detail="The verification token remains in this URL until the backend has completed the request.">
      <section className="form-card p-6 text-center sm:p-8">
        {!token ? <><span className="mx-auto grid size-12 place-items-center rounded-xl bg-accent/15 text-accent"><MailWarning className="size-6" aria-hidden /></span><h2 className="mt-5 font-['Barlow_Condensed'] text-4xl font-bold uppercase leading-none">Link missing</h2><p className="mt-3 text-sm leading-6 text-muted-foreground">Open the complete verification link generated during registration.</p><Link className="mt-6 inline-flex rounded-full bg-primary px-5 py-3 text-sm font-extrabold text-primary-foreground" to="/login">Back to login</Link></> : null}
        {token && verification.isLoading ? <LoadingState title="Verifying email" message="Please keep this tab open while we confirm your account." /> : null}
        {token && verification.isError ? <ErrorState title={toUiError(verification.error).title} message={toUiError(verification.error).message} action={<Link className="inline-flex rounded-full bg-primary px-4 py-2 text-sm font-extrabold text-primary-foreground" to="/login">Back to login</Link>} /> : null}
        {token && verification.isSuccess ? <><span className="mx-auto grid size-12 place-items-center rounded-xl bg-secondary text-foreground"><BadgeCheck className="size-6" aria-hidden /></span><h2 className="mt-5 font-['Barlow_Condensed'] text-4xl font-bold uppercase leading-none">Email verified</h2><p className="mt-3 text-sm leading-6 text-muted-foreground">{verification.data.message}</p><Link className="mt-6 inline-flex items-center gap-2 rounded-full bg-primary px-5 py-3 text-sm font-extrabold text-primary-foreground" to="/verify-email/success">Continue <ArrowRight className="size-4" aria-hidden /></Link></> : null}
      </section>
    </AuthShell>
  );
}
