import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowRight, BadgeCheck, MailCheck } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { AuthShell } from "@/components/layout/AuthShell";
import { Button } from "@/components/ui/Button";
import { Field, FieldError, Input, Label } from "@/components/ui/Form";
import { apiRequest } from "@/lib/apiClient";
import { toUiError, type UiError } from "@/lib/apiErrors";

const RESEND_COOLDOWN_SECONDS = 60;

export function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  return (
    <AuthShell
      eyebrow="Email verification"
      title={
        <>
          One more
          <br />
          <span className="text-secondary">step.</span>
        </>
      }
      description="Enter the 6-digit code we emailed you. It confirms this address before your account can buy a membership."
      detail="Codes expire after a few minutes. You can ask for a new one at any time."
    >
      {token ? (
        <LinkVerification token={token} />
      ) : (
        <CodeVerification initialEmail={searchParams.get("email") ?? ""} />
      )}
    </AuthShell>
  );
}

/** Older emails carry a one-time link; it keeps working exactly as before. */
function LinkVerification({ token }: { token: string }) {
  const verification = useQuery({
    queryKey: ["verify-email", token],
    retry: false,
    queryFn: ({ signal }) =>
      apiRequest<{ message: string }>(`/auth/verify-email?token=${encodeURIComponent(token)}`, {
        signal,
      }),
  });
  return (
    <section className="form-card p-6 text-center sm:p-8">
      {verification.isLoading ? (
        <LoadingState
          title="Verifying email"
          message="Please keep this tab open while we confirm your account."
        />
      ) : null}
      {verification.isError ? (
        <ErrorState
          title={toUiError(verification.error).title}
          message={toUiError(verification.error).message}
          action={
            <Link
              className="inline-flex rounded-full bg-primary px-4 py-2 text-sm font-extrabold text-primary-foreground"
              to="/verify-email"
            >
              Enter a code instead
            </Link>
          }
        />
      ) : null}
      {verification.isSuccess ? (
        <>
          <span className="mx-auto grid size-12 place-items-center rounded-xl bg-secondary text-foreground">
            <BadgeCheck className="size-6" aria-hidden />
          </span>
          <h2 className="mt-5 font-['Barlow_Condensed'] text-4xl font-bold uppercase leading-none">
            Email verified
          </h2>
          <p className="mt-3 text-sm leading-6 text-muted-foreground">
            {verification.data.message}
          </p>
          <Link
            className="mt-6 inline-flex items-center gap-2 rounded-full bg-primary px-5 py-3 text-sm font-extrabold text-primary-foreground"
            to="/verify-email/success"
          >
            Continue <ArrowRight className="size-4" aria-hidden />
          </Link>
        </>
      ) : null}
    </section>
  );
}

function CodeVerification({ initialEmail }: { initialEmail: string }) {
  const navigate = useNavigate();
  const [email, setEmail] = useState(initialEmail);
  const [code, setCode] = useState("");
  const [cooldown, setCooldown] = useState(0);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<UiError | null>(null);
  const [touched, setTouched] = useState(false);
  const emailValid = /^\S+@\S+\.\S+$/.test(email.trim());
  const codeValid = /^\d{6}$/.test(code);

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = window.setTimeout(() => setCooldown((value) => value - 1), 1000);
    return () => window.clearTimeout(timer);
  }, [cooldown]);

  function failed(caught: unknown) {
    const next = toUiError(caught);
    const wait = (next.details as { retry_after_seconds?: number } | undefined)
      ?.retry_after_seconds;
    if (next.code === "RATE_LIMITED" && typeof wait === "number") setCooldown(wait);
    setError(next);
  }

  const verify = useMutation({
    mutationFn: () =>
      apiRequest<{ message: string }>("/auth/verify-email/code", {
        method: "POST",
        body: { email: email.trim(), code },
      }),
    onSuccess: () => navigate("/verify-email/success", { replace: true }),
    onError: failed,
  });
  const resend = useMutation({
    mutationFn: () =>
      apiRequest<{ message: string }>("/auth/verify-email/resend", {
        method: "POST",
        body: { email: email.trim() },
      }),
    onSuccess: (response) => {
      setNotice(response.message);
      setCode("");
      setCooldown(RESEND_COOLDOWN_SECONDS);
    },
    onError: failed,
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    setTouched(true);
    if (emailValid && codeValid) verify.mutate();
  }

  return (
    <section className="form-card p-6 sm:p-8">
      <span className="grid size-11 place-items-center rounded-xl bg-secondary text-foreground">
        <MailCheck className="size-5" aria-hidden />
      </span>
      <h2 className="mt-5 font-['Barlow_Condensed'] text-4xl font-bold uppercase leading-none">
        Enter your code
      </h2>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">
        Open the YPGym email on any device and type the 6 digits here.
      </p>
      {error ? <ErrorState className="mt-5" title={error.title} message={error.message} /> : null}
      {notice ? (
        <p
          className="mt-5 rounded-2xl border border-secondary/50 bg-secondary/15 p-4 text-sm"
          role="status"
        >
          {notice}
        </p>
      ) : null}
      <form className="mt-6 space-y-4" onSubmit={submit} noValidate>
        <Field>
          <Label htmlFor="verify-email-address">Email address</Label>
          <Input
            id="verify-email-address"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
          <FieldError
            message={touched && !emailValid ? "Enter the email you registered with." : undefined}
          />
        </Field>
        <Field>
          <Label htmlFor="verify-code">6-digit code</Label>
          <Input
            id="verify-code"
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={6}
            placeholder="123456"
            className="text-center font-mono text-2xl tracking-[0.5em]"
            value={code}
            onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
          />
          <FieldError message={touched && !codeValid ? "Enter all 6 digits." : undefined} />
        </Field>
        <Button type="submit" className="w-full rounded-full" disabled={verify.isPending}>
          {verify.isPending ? (
            "Verifying..."
          ) : (
            <>
              Verify email <ArrowRight className="size-4" aria-hidden />
            </>
          )}
        </Button>
      </form>
      <div className="mt-5 flex flex-wrap items-center justify-between gap-3 text-sm">
        <Button
          type="button"
          variant="outline"
          className="rounded-full"
          disabled={!emailValid || resend.isPending || cooldown > 0}
          onClick={() => {
            setError(null);
            setNotice(null);
            resend.mutate();
          }}
        >
          {cooldown > 0
            ? `Resend in ${cooldown}s`
            : resend.isPending
              ? "Sending..."
              : "Send a new code"}
        </Button>
        <Link
          className="font-extrabold text-primary underline-offset-4 hover:underline"
          to="/login"
        >
          Back to login
        </Link>
      </div>
      <p className="sr-only" aria-live="polite">
        {cooldown > 0 ? `You can request another code in ${cooldown} seconds.` : ""}
      </p>
    </section>
  );
}
