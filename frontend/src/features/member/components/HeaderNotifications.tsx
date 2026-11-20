import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Bell } from "lucide-react";
import { useRef, type FocusEvent, type KeyboardEvent } from "react";
import { Link } from "react-router-dom";

import { routePaths } from "@/app/routes";
import { useAuth } from "@/features/auth/AuthContext";
import { apiRequest } from "@/lib/apiClient";
import type { Broadcast, NotificationPage } from "@/types/operations";
import { formatBadgeCount, importantItems } from "../memberDashboardLogic";

/**
 * Header bell for members: unread count on the button, and the important items (active
 * announcements, then unread notifications) in a native <details> dropdown.
 */
export function HeaderNotifications() {
  const { token } = useAuth();
  const detailsRef = useRef<HTMLDetailsElement>(null);
  const inbox = useQuery({
    queryKey: ["notifications", "header"],
    queryFn: ({ signal }) =>
      apiRequest<NotificationPage>("/notifications/me?page=1&page_size=10", { token, signal }),
    enabled: Boolean(token),
    refetchInterval: 30_000,
  });
  const broadcasts = useQuery({
    queryKey: ["notifications", "broadcasts", "active"],
    queryFn: ({ signal }) =>
      apiRequest<Broadcast[]>("/notifications/broadcasts/active", { token, signal }),
    enabled: Boolean(token),
    staleTime: 60_000,
  });
  const unread = inbox.data?.unread_count ?? 0;
  const items = importantItems(broadcasts.data ?? [], inbox.data?.items ?? []);

  function close() {
    if (detailsRef.current) detailsRef.current.open = false;
  }

  function onBlur(event: FocusEvent<HTMLDetailsElement>) {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) close();
  }

  function onKeyDown(event: KeyboardEvent<HTMLDetailsElement>) {
    if (event.key !== "Escape" || !detailsRef.current?.open) return;
    close();
    detailsRef.current.querySelector("summary")?.focus();
  }

  return (
    <details
      ref={detailsRef}
      className="header-notifications"
      onBlur={onBlur}
      onKeyDown={onKeyDown}
    >
      <summary
        className="header-notifications__button"
        aria-label={unread > 0 ? `Notifications, ${unread} unread` : "Notifications"}
      >
        <Bell className="size-4" aria-hidden />
        <span className="header-notifications__label">Notifications</span>
        {unread > 0 ? (
          <span className="header-notifications__count" aria-hidden>
            {formatBadgeCount(unread)}
          </span>
        ) : null}
      </summary>
      <div
        className="header-notifications__panel rounded-xl border border-border bg-card p-3 shadow-lg outline-none"
        tabIndex={-1}
      >
        <p className="px-1 text-xs font-black uppercase tracking-wider text-muted-foreground">
          Important
        </p>
        {inbox.isLoading ? (
          <p className="px-1 py-3 text-sm text-muted-foreground">Loading notifications…</p>
        ) : inbox.isError ? (
          <p className="px-1 py-3 text-sm text-muted-foreground">
            Notifications could not be loaded right now.
          </p>
        ) : items.length ? (
          <ul className="mt-2 grid max-h-[60dvh] gap-2 overflow-y-auto">
            {items.map((item) => (
              <li className="rounded-lg border border-border p-3" key={`${item.kind}-${item.id}`}>
                <div className="flex items-start gap-3">
                  <Bell className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden />
                  <div className="min-w-0">
                    <strong className="text-sm">{item.title}</strong>
                    {item.kind === "broadcast" ? (
                      <span className="ml-2 rounded-full bg-secondary px-2 py-0.5 text-[10px] font-extrabold uppercase">
                        Announcement
                      </span>
                    ) : null}
                    <p className="mt-1 text-xs leading-5 text-muted-foreground">{item.message}</p>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="px-1 py-3 text-sm text-muted-foreground">
            Nothing important. Announcements and unread updates will appear here.
          </p>
        )}
        <Link
          className="mt-3 inline-flex items-center gap-2 px-1 text-sm font-bold text-primary"
          to={routePaths.memberNotifications}
          onClick={close}
        >
          Open inbox <ArrowRight className="size-4" aria-hidden />
        </Link>
      </div>
    </details>
  );
}
