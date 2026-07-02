import { useQuery } from "@tanstack/react-query";
import { CheckCircle2 } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";

import { ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { AppFrame } from "@/components/layout/AppFrame";
import { ButtonLink } from "@/components/ui/Button";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";

export function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");

  const verification = useQuery({
    queryKey: ["verify-email", token],
    enabled: Boolean(token),
    retry: false,
    queryFn: () =>
      apiRequest<{ message: string }>(
        `/auth/verify-email?token=${encodeURIComponent(token ?? "")}`,
      ),
  });

  return (
    <AppFrame>
      <main className="mx-auto max-w-xl px-5 py-10">
        {!token ? (
          <ErrorState
            title="Verification link is missing"
            message="Open the full verification link generated during registration."
          />
        ) : verification.isLoading ? (
          <LoadingState title="Verifying email" />
        ) : verification.isError ? (
          <ErrorState
            title={toUiError(verification.error).title}
            message={toUiError(verification.error).message}
            action={
              <ButtonLink asChild>
                <Link to="/login">Back to login</Link>
              </ButtonLink>
            }
          />
        ) : (
          <section className="rounded-lg border border-secondary/30 bg-card p-6 shadow-sm">
            <CheckCircle2 className="size-9 text-secondary" aria-hidden />
            <h1 className="mt-4 text-3xl font-bold">Email Verification Success</h1>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              {verification.data?.message} You can now log in and continue to
              membership plans.
            </p>
            <ButtonLink asChild className="mt-5">
              <Link to="/login">Continue to login</Link>
            </ButtonLink>
          </section>
        )}
      </main>
    </AppFrame>
  );
}
