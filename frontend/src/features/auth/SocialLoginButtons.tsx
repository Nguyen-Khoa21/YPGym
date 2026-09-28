import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";

type Provider = "google" | "facebook";
type ProviderStatus = { provider: Provider; enabled: boolean };

function ProviderLogo({ provider }: { provider: Provider }) {
  if (provider === "facebook") {
    return <svg aria-hidden viewBox="0 0 24 24" className="size-5 shrink-0">
      <path fill="#1877F2" d="M24 12.073C24 5.405 18.627 0 12 0S0 5.405 0 12.073C0 18.1 4.388 23.094 10.125 24v-8.435H7.078v-3.492h3.047V9.414c0-3.025 1.792-4.697 4.533-4.697 1.313 0 2.686.236 2.686.236v2.971h-1.513c-1.49 0-1.956.931-1.956 1.887v2.262h3.328l-.532 3.492h-2.796V24C19.612 23.094 24 18.1 24 12.073Z" />
      <path fill="#fff" d="m16.671 15.565.532-3.492h-3.328V9.811c0-.956.466-1.887 1.956-1.887h1.513V4.953s-1.373-.236-2.686-.236c-2.741 0-4.533 1.672-4.533 4.697v2.659H7.078v3.492h3.047V24a12.17 12.17 0 0 0 3.75 0v-8.435h2.796Z" />
    </svg>;
  }
  return <svg aria-hidden viewBox="0 0 24 24" className="size-5 shrink-0">
    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.31v2.77h3.56c2.09-1.92 3.28-4.74 3.28-8.09Z" />
    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.56-2.77c-.99.66-2.24 1.06-3.72 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23Z" />
    <path fill="#FBBC05" d="M5.84 14.1A6.6 6.6 0 0 1 5.5 12c0-.73.13-1.43.34-2.1V7.06H2.18A11 11 0 0 0 1 12c0 1.77.42 3.44 1.18 4.94l3.66-2.84Z" />
    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15A10.55 10.55 0 0 0 12 1a11 11 0 0 0-9.82 6.06L5.84 9.9C6.71 7.31 9.14 5.38 12 5.38Z" />
  </svg>;
}

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
          <ProviderLogo provider={provider} />
          {busy === provider ? "Opening…" : `Continue with ${provider === "google" ? "Google" : "Facebook"}`}
        </Button>;
      })}
    </div>
    {providers.data?.every((item) => !item.enabled) ? <p className="mt-3 text-center text-xs text-muted-foreground">Social sign-in is awaiting provider configuration. Email sign-in remains available.</p> : null}
    {error ? <p className="mt-3 text-center text-sm text-destructive" role="alert">{error}</p> : null}
  </div>;
}
