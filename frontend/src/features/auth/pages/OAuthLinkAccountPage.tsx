import { useQuery } from "@tanstack/react-query";
import { Mail, ShieldCheck } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { AuthShell } from "@/components/layout/AuthShell";
import { Button } from "@/components/ui/Button";
import { Field, Input, Label } from "@/components/ui/Form";
import { useAuth } from "@/features/auth/AuthContext";
import { workspacePathForRole } from "@/features/auth/workspace";
import { apiRequest } from "@/lib/apiClient";
import { toUiError, type UiError } from "@/lib/apiErrors";

type PendingLink = {
  provider: "google" | "facebook";
  masked_email: string;
  password_confirmation_available: boolean;
  email_confirmation_available: boolean;
  expires_at: string;
};

export function OAuthLinkAccountPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { completeOAuthLink } = useAuth();
  const code = params.get("code");
  const emailToken = params.get("email_token");
  const emailConfirmationStarted = useRef(false);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<UiError | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [emailQueued, setEmailQueued] = useState(false);

  const pending = useQuery({
    queryKey: ["oauth", "pending-link", code],
    queryFn: ({ signal }) => apiRequest<PendingLink>(`/auth/oauth/link/pending?code=${encodeURIComponent(code!)}`, { signal }),
    enabled: Boolean(code),
    retry: false,
  });

  useEffect(() => {
    if (!emailToken || emailConfirmationStarted.current) return;
    emailConfirmationStarted.current = true;
    void completeOAuthLink("/auth/oauth/link/email/confirm", { token: emailToken })
      .then((user) => navigate(workspacePathForRole(user.role), { replace: true }))
      .catch((caught) => setError(toUiError(caught)));
  }, [completeOAuthLink, emailToken, navigate]);

  async function confirmPassword(event: FormEvent) {
    event.preventDefault();
    if (!code || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const user = await completeOAuthLink("/auth/oauth/link/password", { code, password });
      navigate(workspacePathForRole(user.role), { replace: true });
    } catch (caught) {
      setError(toUiError(caught));
    } finally {
      setSubmitting(false);
    }
  }

  async function sendEmail() {
    if (!code || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      await apiRequest("/auth/oauth/link/email", { method: "POST", body: { code } });
      setEmailQueued(true);
    } catch (caught) {
      setError(toUiError(caught));
    } finally {
      setSubmitting(false);
    }
  }

  if (emailToken && !error) {
    return <AuthShell eyebrow="Secure account link" title={<>Confirming your<br /><span className="text-secondary">sign-in method.</span></>} description="This one-time link proves ownership of your existing YPGym email."><LoadingState title="Connecting provider" /></AuthShell>;
  }

  const loadError = error ?? (pending.isError ? toUiError(pending.error) : null);
  return <AuthShell eyebrow="Account protection" title={<>Connect your<br /><span className="text-secondary">existing account.</span></>} description="A YPGym account already uses this verified provider email. Confirm ownership before the accounts are connected.">
    {loadError ? <ErrorState title={loadError.title} message={loadError.message} action={<Link className="font-semibold text-primary underline" to="/login">Start sign-in again</Link>} /> : null}
    {!loadError && pending.isLoading ? <LoadingState title="Loading secure link" /> : null}
    {!loadError && pending.data ? <div className="space-y-5">
      <div className="rounded-xl border border-border bg-card p-5"><div className="flex gap-3"><ShieldCheck className="mt-0.5 size-5 text-primary" aria-hidden /><div><strong className="capitalize">Connect {pending.data.provider}</strong><p className="mt-1 text-sm text-muted-foreground">Existing YPGym email: {pending.data.masked_email}</p></div></div></div>
      {pending.data.password_confirmation_available ? <form className="space-y-4" onSubmit={confirmPassword}>
        <Field><Label htmlFor="link-password">Current YPGym password</Label><Input id="link-password" type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} /></Field>
        <Button className="w-full" disabled={submitting || !password}>{submitting ? "Confirming…" : "Sign in and connect"}</Button>
      </form> : <p className="rounded-xl bg-muted p-4 text-sm text-muted-foreground">This account does not have a YPGym password. Use the verified email confirmation below or sign in with an already connected provider.</p>}
      {pending.data.email_confirmation_available ? <div className="border-t border-border pt-5"><p className="mb-3 text-sm text-muted-foreground">Forgot your password? Send a short-lived confirmation link to the verified YPGym email.</p><Button className="w-full" variant="outline" disabled={submitting || emailQueued} onClick={() => void sendEmail()}><Mail className="size-4" /> {emailQueued ? "Confirmation email queued" : "Email me a secure link"}</Button></div> : null}
      <p className="text-xs leading-5 text-muted-foreground">Nothing is connected until one confirmation succeeds. This request expires automatically.</p>
    </div> : null}
  </AuthShell>;
}
