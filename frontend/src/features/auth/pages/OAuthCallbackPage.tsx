import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { AuthShell } from "@/components/layout/AuthShell";
import { useAuth } from "@/features/auth/AuthContext";
import { workspacePathForRole } from "@/features/auth/workspace";
import { toUiError } from "@/lib/apiErrors";

export function OAuthCallbackPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { completeOAuth } = useAuth();
  const exchangeStarted = useRef(false);
  const provider = params.get("provider");
  const code = params.get("code");
  const providerError = params.get("error");
  const initialError = providerError
    ? callbackError(providerError)
    : (((provider !== "google" && provider !== "facebook") || !code) ? "The sign-in callback is invalid or expired." : "");
  const [error, setError] = useState(initialError);

  useEffect(() => {
    if ((provider !== "google" && provider !== "facebook") || !code || providerError) return;
    if (exchangeStarted.current) return;
    exchangeStarted.current = true;
    void completeOAuth(provider, code)
      .then((user) => navigate(workspacePathForRole(user.role), { replace: true }))
      .catch((caught) => setError(toUiError(caught).message));
  }, [code, completeOAuth, navigate, provider, providerError]);

  return <AuthShell eyebrow="Secure sign-in" title={<>Finishing your<br /><span className="text-secondary">session.</span></>} description="YPGym is validating the one-time provider response.">
    {error ? <ErrorState title="Sign-in could not be completed" message={error} action={<Link className="font-semibold text-primary underline" to="/login">Return to sign in</Link>} /> : <LoadingState title="Completing sign-in" />}
  </AuthShell>;
}

function callbackError(code: string) {
  const messages: Record<string, string> = {
    oauth_provider_denied: "The provider sign-in was cancelled. You can return to sign in and try again.",
    oauth_state_invalid: "This sign-in request is invalid, expired, or has already been used. Start again from YPGym.",
    oauth_callback_replayed: "This sign-in response has already been processed. Return to sign in if your session did not open.",
    oauth_email_unverified: "The provider did not confirm a usable email address.",
    oauth_identity_conflict: "That provider identity is already connected to another YPGym account.",
    oauth_temporarily_unavailable: "The provider could not be reached. Return to sign in and try again.",
  };
  return messages[code] ?? "The provider sign-in could not be completed safely.";
}
