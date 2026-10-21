import { useEffect, useState } from "react";
import { CheckCircle2, RefreshCw, WifiOff } from "lucide-react";
import { useRegisterSW } from "virtual:pwa-register/react";

import { Button } from "@/components/ui/Button";

export function PwaStatus() {
  const [isOnline, setIsOnline] = useState(() => navigator.onLine);
  const [updateFailed, setUpdateFailed] = useState(false);
  const [updating, setUpdating] = useState(false);
  const {
    needRefresh: [needRefresh, setNeedRefresh],
    offlineReady: [offlineReady, setOfflineReady],
    updateServiceWorker,
  } = useRegisterSW();

  useEffect(() => {
    const online = () => setIsOnline(true);
    const offline = () => setIsOnline(false);
    window.addEventListener("online", online);
    window.addEventListener("offline", offline);
    return () => {
      window.removeEventListener("online", online);
      window.removeEventListener("offline", offline);
    };
  }, []);

  async function installUpdate() {
    setUpdating(true);
    setUpdateFailed(false);
    try {
      await updateServiceWorker(true);
    } catch {
      setUpdateFailed(true);
      setUpdating(false);
    }
  }

  if (!needRefresh && !offlineReady && isOnline) return null;

  const title = needRefresh
    ? "YPGym update available"
    : !isOnline
      ? "You are offline"
      : "YPGym is ready offline";
  const message = needRefresh
    ? updateFailed
      ? "The update could not be installed. Check your connection and try again."
      : "Reload when you are ready to use the newest version."
    : !isOnline
      ? "The saved application shell remains available. Sign-in, payments, QR codes, attendance, and account data require a connection."
      : "The application shell is saved on this device. Private gym data still requires a network connection.";
  const Icon = needRefresh ? RefreshCw : !isOnline ? WifiOff : CheckCircle2;

  return (
    <aside
      aria-live="polite"
      className="fixed bottom-4 left-4 right-4 z-[100] rounded-xl border border-border bg-card p-4 text-card-foreground shadow-lg sm:left-auto sm:max-w-md"
      role={needRefresh ? "alert" : "status"}
    >
      <div className="flex items-start gap-3">
        <span className="mt-0.5 grid size-9 shrink-0 place-items-center rounded-md bg-primary/10 text-primary">
          <Icon className={`size-5 ${updating ? "animate-spin" : ""}`} aria-hidden />
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="font-semibold">{title}</h2>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">{message}</p>
          {needRefresh ? (
            <div className="mt-3 flex flex-wrap gap-2">
              <Button disabled={updating || !isOnline} onClick={() => void installUpdate()}>
                {updating ? "Updating..." : updateFailed ? "Try update again" : "Update now"}
              </Button>
              <Button disabled={updating} variant="outline" onClick={() => setNeedRefresh(false)}>
                Later
              </Button>
            </div>
          ) : offlineReady && isOnline ? (
            <Button className="mt-3" variant="outline" onClick={() => setOfflineReady(false)}>
              Dismiss
            </Button>
          ) : null}
        </div>
      </div>
    </aside>
  );
}
