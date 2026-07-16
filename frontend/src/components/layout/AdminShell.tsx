import type { PropsWithChildren } from "react";
import {
  BarChart3,
  CalendarDays,
  ClipboardList,
  CreditCard,
  Dumbbell,
  LayoutDashboard,
  UsersRound,
} from "lucide-react";
import { NavLink } from "react-router-dom";

import { AppFrame } from "@/components/layout/AppFrame";

const adminNav = [
  { to: "/admin", label: "Overview", icon: LayoutDashboard },
  { to: "/admin/billing", label: "Billing", icon: CreditCard },
  { to: "/admin/members", label: "Members", icon: UsersRound, future: true },
  { to: "/admin/attendance", label: "Attendance", icon: ClipboardList, future: true },
  { to: "/admin/classes", label: "Classes", icon: CalendarDays, future: true },
  { to: "/admin/pt-assignments", label: "PT assignments", icon: Dumbbell, future: true },
];

export function AdminShell({ children }: PropsWithChildren) {
  return (
    <AppFrame>
      <div className="admin-shell">
        <aside className="admin-sidebar" aria-label="Admin navigation">
          <p className="admin-sidebar__eyebrow">
            <BarChart3 className="size-4" aria-hidden /> Operations
          </p>
          <nav className="admin-nav">
            {adminNav.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `admin-nav__link ${isActive ? "admin-nav__link--active" : ""}`
                }
              >
                <item.icon className="size-[18px]" aria-hidden />
                <span>{item.label}</span>
                {item.future ? <small>Planned</small> : null}
              </NavLink>
            ))}
          </nav>
          <p className="admin-sidebar__footnote">
            Only the billing ledger is connected in the current release.
          </p>
        </aside>
        <main id="main-content" className="admin-content">
          {children}
        </main>
      </div>
    </AppFrame>
  );
}
