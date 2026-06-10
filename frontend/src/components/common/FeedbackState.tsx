import type { ReactNode } from "react";
import { AlertCircle, Loader2, Lock, SearchX } from "lucide-react";

import { cn } from "@/lib/utils";

type FeedbackStateProps = {
  title: string;
  message?: string;
  action?: ReactNode;
  className?: string;
};

export function LoadingState({
  title = "Loading",
  message = "Please wait while the latest information is loaded.",
  className,
}: Partial<FeedbackStateProps>) {
  return (
    <StateShell
      icon={<Loader2 className="size-5 animate-spin" aria-hidden />}
      title={title}
      message={message}
      className={className}
    />
  );
}

export function EmptyState({
  title,
  message,
  action,
  className,
}: FeedbackStateProps) {
  return (
    <StateShell
      icon={<SearchX className="size-5" aria-hidden />}
      title={title}
      message={message}
      action={action}
      className={className}
    />
  );
}

export function ErrorState({
  title,
  message,
  action,
  className,
}: FeedbackStateProps) {
  return (
    <StateShell
      icon={<AlertCircle className="size-5" aria-hidden />}
      title={title}
      message={message}
      action={action}
      className={className}
      tone="danger"
    />
  );
}

export function PermissionState({
  title = "Access unavailable",
  message = "Your role does not allow this action.",
  action,
  className,
}: Partial<FeedbackStateProps>) {
  return (
    <StateShell
      icon={<Lock className="size-5" aria-hidden />}
      title={title}
      message={message}
      action={action}
      className={className}
      tone="muted"
    />
  );
}

type StateShellProps = FeedbackStateProps & {
  icon: ReactNode;
  tone?: "default" | "danger" | "muted";
};

function StateShell({
  icon,
  title,
  message,
  action,
  className,
  tone = "default",
}: StateShellProps) {
  return (
    <div
      className={cn(
        "rounded-lg border bg-card p-5 text-card-foreground shadow-sm",
        tone === "danger" && "border-destructive/30 bg-destructive/5",
        tone === "muted" && "bg-muted/40",
        className,
      )}
      role={tone === "danger" ? "alert" : "status"}
    >
      <div className="flex gap-3">
        <div
          className={cn(
            "mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary",
            tone === "danger" && "bg-destructive/10 text-destructive",
            tone === "muted" && "bg-muted text-muted-foreground",
          )}
        >
          {icon}
        </div>
        <div className="min-w-0">
          <h2 className="text-base font-semibold">{title}</h2>
          {message ? (
            <p className="mt-1 text-sm leading-6 text-muted-foreground">
              {message}
            </p>
          ) : null}
          {action ? <div className="mt-4">{action}</div> : null}
        </div>
      </div>
    </div>
  );
}
