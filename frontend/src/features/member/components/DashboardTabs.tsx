import { ArrowRight, Bell } from "lucide-react";
import { useRef, useState, type KeyboardEvent } from "react";
import { Link } from "react-router-dom";

import { EmptyState } from "@/components/common/FeedbackState";
import { StatusBadge } from "@/components/operations/OperationsUi";
import { formatDate } from "@/lib/format";
import type { Broadcast, MemberDashboardPayload, NotificationItem } from "@/types/operations";
import { defaultDashboardTab, formatBadgeCount, importantItems, nextTabIndex, type DashboardTab } from "../memberDashboardLogic";

const tabs: { id: DashboardTab; label: string }[] = [{ id: "important", label: "Important" }, { id: "membership", label: "Membership" }];

/** Two native ARIA tabs: what needs reading now, and the membership summary. No tab library. */
export function DashboardTabs({ broadcasts, notifications, unreadCount, membership }: { broadcasts: Broadcast[]; notifications: NotificationItem[]; unreadCount: number; membership: MemberDashboardPayload["membership"] }) {
  const [selected, setSelected] = useState<DashboardTab>(() => defaultDashboardTab(unreadCount, broadcasts.length));
  const refs = useRef<Record<DashboardTab, HTMLButtonElement | null>>({ important: null, membership: null });
  const items = importantItems(broadcasts, notifications);

  function onKeyDown(event: KeyboardEvent, index: number) {
    const next = nextTabIndex(index, event.key, tabs.length);
    if (next === null) return;
    event.preventDefault();
    setSelected(tabs[next].id);
    refs.current[tabs[next].id]?.focus();
  }

  return <section className="rounded-2xl border border-border bg-card" aria-label="Important notifications and membership">
    <div role="tablist" aria-label="Dashboard details" className="flex gap-1 border-b border-border px-3 pt-3">
      {tabs.map((tab, index) => <button key={tab.id} ref={(node) => { refs.current[tab.id] = node; }} role="tab" type="button" id={`dash-tab-${tab.id}`} aria-selected={selected === tab.id} aria-controls={`dash-panel-${tab.id}`} tabIndex={selected === tab.id ? 0 : -1} onClick={() => setSelected(tab.id)} onKeyDown={(event) => onKeyDown(event, index)} className={`-mb-px inline-flex min-h-11 items-center gap-2 rounded-t-lg border-b-2 px-4 text-sm font-extrabold ${selected === tab.id ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"}`}>
        {tab.label}
        {tab.id === "important" && unreadCount > 0 ? <span className="inline-flex min-w-5 items-center justify-center rounded-full bg-destructive px-1.5 text-[11px] font-black leading-5 text-white" aria-label={`${unreadCount} unread`}>{formatBadgeCount(unreadCount)}</span> : null}
      </button>)}
    </div>
    <div role="tabpanel" id="dash-panel-important" aria-labelledby="dash-tab-important" hidden={selected !== "important"} className="p-4">
      {items.length ? <ul className="grid gap-3">{items.map((item) => <li className="rounded-xl border border-border p-3" key={`${item.kind}-${item.id}`}><div className="flex items-start gap-3"><Bell className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden /><div className="min-w-0"><strong className="text-sm">{item.title}</strong>{item.kind === "broadcast" ? <span className="ml-2 rounded-full bg-secondary px-2 py-0.5 text-[10px] font-extrabold uppercase">Announcement</span> : null}<p className="mt-1 text-xs leading-5 text-muted-foreground">{item.message}</p></div></div></li>)}</ul> : <EmptyState title="Nothing important" message="Announcements and unread updates will appear here." />}
      <Link className="mt-4 inline-flex items-center gap-2 text-sm font-bold text-primary" to="/app/notifications">Open inbox <ArrowRight className="size-4" aria-hidden /></Link>
    </div>
    <div role="tabpanel" id="dash-panel-membership" aria-labelledby="dash-tab-membership" hidden={selected !== "membership"} className="p-4">
      {membership ? <>
        <div className="flex flex-wrap items-center justify-between gap-3"><strong>{membership.plan_name}</strong><StatusBadge value={membership.status} /></div>
        <p className="mt-2 text-sm">{membership.days_remaining} days remaining · expires {formatDate(membership.expiry_date)}</p>
        <p className="mt-1 text-xs text-muted-foreground">{membership.home_gym_name} · {membership.message}</p>
        <Link className="mt-3 inline-flex items-center gap-2 text-sm font-bold text-primary" to="/memberships">Renew membership <ArrowRight className="size-4" aria-hidden /></Link>
      </> : <><p className="text-sm text-muted-foreground">You do not have a membership yet.</p><Link className="mt-3 inline-flex items-center gap-2 text-sm font-bold text-primary" to="/memberships">Buy membership <ArrowRight className="size-4" aria-hidden /></Link></>}
    </div>
  </section>;
}
