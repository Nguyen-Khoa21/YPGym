import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { AuthShell } from "@/components/layout/AuthShell";
import { useAuth } from "@/features/auth/AuthContext";
import { workspacePathForRole } from "@/features/auth/workspace";
import { toUiError } from "@/lib/apiErrors";

export function OAuthCallbackPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { completeOAuth } = useAuth();
  const provider = params.get("provider");
  const code = params.get("code");
  const providerError = params.get("error");
  const initialError = providerError?.replaceAll("_", " ")
    ?? (((provider !== "google" && provider !== "facebook") || !code) ? "The sign-in callback is invalid or expired." : "");
  const [error, setError] = useState(initialError);

  useEffect(() => {
    if ((provider !== "google" && provider !== "facebook") || !code || providerError) return;
    void completeOAuth(provider, code)
      .then((user) => navigate(workspacePathForRole(user.role), { replace: true }))
      .catch((caught) => setError(toUiError(caught).message));
  }, [code, completeOAuth, navigate, provider, providerError]);

  return <AuthShell eyebrow="Secure sign-in" title={<>Finishing your<br /><span className="text-secondary">session.</span></>} description="YPGym is validating the one-time provider response.">
    {error ? <ErrorState title="Sign-in could not be completed" message={error} /> : <LoadingState title="Completing sign-in" />}
  </AuthShell>;
}
