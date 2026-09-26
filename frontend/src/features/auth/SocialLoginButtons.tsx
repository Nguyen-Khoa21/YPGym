import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";

type Provider = "google" | "facebook";
type ProviderStatus = { provider: Provider; enabled: boolean };

export function SocialLoginButtons() {
  const [busy, setBusy] = useState<Provider | null>(null);
  const [error, setError] = useState("");
  const providers = useQuery({
    queryKey: ["auth", "providers"],
    queryFn: () => apiRequest<ProviderStatus[]>("/auth/providers"),
  });

  async function start(provider: Provider) {
    setBusy(provider);
    setError("");
    try {
      const response = await apiRequest<{ authorization_url: string }>(`/auth/oauth/${provider}/start?platform=web`);
      window.location.assign(response.authorization_url);
    } catch (caught) {
      setError(toUiError(caught).message);
      setBusy(null);
    }
  }

  return <div className="mt-6 border-t border-border pt-6">
    <p className="mb-3 text-center text-xs font-bold uppercase tracking-wider text-muted-foreground">Or continue with</p>
    <div className="grid gap-3 sm:grid-cols-2">
      {(["google", "facebook"] as const).map((provider) => {
        const enabled = providers.data?.find((item) => item.provider === provider)?.enabled ?? false;
        return <Button key={provider} type="button" variant="outline" disabled={!enabled || busy !== null} onClick={() => void start(provider)}>
          {busy === provider ? "Opening…" : `Continue with ${provider === "google" ? "Google" : "Facebook"}`}
        </Button>;
      })}
    </div>
    {providers.data?.every((item) => !item.enabled) ? <p className="mt-3 text-center text-xs text-muted-foreground">Social sign-in is awaiting provider configuration. Email sign-in remains available.</p> : null}
    {error ? <p className="mt-3 text-center text-sm text-destructive" role="alert">{error}</p> : null}
  </div>;
}
