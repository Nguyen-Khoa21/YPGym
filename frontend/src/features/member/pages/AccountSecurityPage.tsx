import { useMutation, useQuery } from "@tanstack/react-query";
import { Link2, ShieldCheck, Unlink } from "lucide-react";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { toast } from "sonner";

import { ErrorState, LoadingState } from "@/components/common/FeedbackState";
import { MemberShell } from "@/components/layout/MemberShell";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest } from "@/lib/apiClient";
import { toUiError } from "@/lib/apiErrors";
import { queryClient } from "@/lib/queryClient";

type Provider = "google" | "facebook";
type Identities = { password_enabled: boolean; identities: { provider: Provider; email: string | null; email_verified: boolean; last_login_at: string | null }[] };

export function AccountSecurityPage() {
  const { token } = useAuth();
  const [params, setParams] = useSearchParams();
  const [linking, setLinking] = useState<Provider | null>(null);
  const identities = useQuery({ queryKey: ["account", "identities"], queryFn: () => apiRequest<Identities>("/account/identities", { token }) });
  const unlink = useMutation({
    mutationFn: (provider: Provider) => apiRequest<Identities>(`/account/identities/${provider}`, { method: "DELETE", token }),
    onSuccess: (data) => { queryClient.setQueryData(["account", "identities"], data); toast.success("Sign-in provider disconnected"); },
    onError: (caught) => toast.error(toUiError(caught).message),
  });
  useEffect(() => {
    const linked = params.get("linked");
    if (linked === "google" || linked === "facebook") {
      toast.success(`${linked[0].toUpperCase()}${linked.slice(1)} sign-in connected`);
      setParams({}, { replace: true });
    }
  }, [params, setParams]);
  async function link(provider: Provider) {
    setLinking(provider);
    try {
      const response = await apiRequest<{ authorization_url: string }>(`/account/identities/${provider}/link/start?platform=web`, { method: "POST", token });
      window.location.assign(response.authorization_url);
    } catch (caught) { toast.error(toUiError(caught).message); setLinking(null); }
  }
  function disconnect(provider: Provider) {
    if (window.confirm(`Disconnect ${provider} from this YPGym account?`)) unlink.mutate(provider);
  }
  return <MemberShell><div className="mx-auto max-w-4xl">
    <p className="page-kicker">Account security</p><h1 className="page-title">Sign-in methods.</h1><p className="page-description">Connect provider identities only after signing in. YPGym never links accounts from matching email alone.</p>
    {identities.isLoading ? <LoadingState className="mt-7" title="Loading sign-in methods" /> : null}
    {identities.isError ? <ErrorState className="mt-7" title="Security settings unavailable" message={toUiError(identities.error).message} /> : null}
    {identities.data ? <div className="mt-7 space-y-4">
      <div className="surface-card flex items-center gap-4 p-5"><ShieldCheck className="size-6 text-primary" /><div><strong>Email and password</strong><p className="text-sm text-muted-foreground">{identities.data.password_enabled ? "Available" : "No password has been set for this provider-created account."}</p></div></div>
      {(["google", "facebook"] as const).map((provider) => {
        const linked = identities.data.identities.find((item) => item.provider === provider);
        return <div className="surface-card flex flex-col gap-4 p-5 sm:flex-row sm:items-center" key={provider}><div className="flex-1"><strong className="capitalize">{provider}</strong><p className="text-sm text-muted-foreground">{linked ? `Connected${linked.email ? ` · ${linked.email}` : ""}` : "Not connected"}</p></div>{linked ? <Button variant="outline" disabled={unlink.isPending} onClick={() => disconnect(provider)}><Unlink className="size-4" /> Disconnect</Button> : <Button disabled={linking !== null} onClick={() => void link(provider)}><Link2 className="size-4" /> {linking === provider ? "Opening provider…" : "Connect"}</Button>}</div>;
      })}
      <p className="text-xs leading-5 text-muted-foreground">Connecting or disconnecting requires a sign-in from the last 10 minutes. Sign in again if the server requests recent authentication. The final usable method cannot be removed.</p>
    </div> : null}
  </div></MemberShell>;
}
