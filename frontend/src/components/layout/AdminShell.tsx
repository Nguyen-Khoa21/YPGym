import type { PropsWithChildren } from "react";
import {
  BarChart3,
  CalendarDays,
  ClipboardCheck,
  ClipboardList,
  CreditCard,
  Dumbbell,
  LayoutDashboard,
  Megaphone,
  Settings2,
  ShieldCheck,
  UsersRound,
} from "lucide-react";
import { NavLink } from "react-router-dom";

import { AppFrame } from "@/components/layout/AppFrame";
import { useAuth } from "@/features/auth/AuthContext";

const adminNav = [
  { to: "/admin", label: "Overview", icon: LayoutDashboard, roles: ["staff", "manager", "admin"] },
  { to: "/admin/members", label: "Members", icon: UsersRound, roles: ["admin"] },
  { to: "/admin/billing", label: "Billing", icon: CreditCard, roles: ["admin"] },
  { to: "/admin/attendance", label: "Attendance", icon: ClipboardList, roles: ["staff", "manager", "admin"] },
  { to: "/admin/classes", label: "Classes", icon: CalendarDays, roles: ["admin"] },
  { to: "/admin/approvals", label: "Approvals", icon: ClipboardCheck, roles: ["manager", "admin"] },
  { to: "/admin/broadcasts", label: "Broadcasts", icon: Megaphone, roles: ["manager", "admin"] },
  { to: "/admin/audit", label: "Audit log", icon: ShieldCheck, roles: ["manager", "admin"] },
  { to: "/admin/settings", label: "Settings", icon: Settings2, roles: ["manager", "admin"] },
  { to: "/admin/pt-assignments", label: "PT profiles", icon: Dumbbell, roles: ["manager", "admin"] },
  { to: "/admin/exercises", label: "Exercises", icon: Dumbbell, roles: ["manager", "admin"] },
];

export function AdminShell({ children }: PropsWithChildren) {
  const { user } = useAuth();
  const visibleNav = adminNav.filter((item) => user && item.roles.includes(user.role));
  return (
    <AppFrame navigation={visibleNav}>
      <div className="admin-shell">
        <aside className="admin-sidebar" aria-label="Admin navigation">
          <p className="admin-sidebar__eyebrow">
            <BarChart3 className="size-4" aria-hidden /> Operations
          </p>
          <nav className="admin-nav">
            {visibleNav.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/admin"}
                className={({ isActive }) =>
                  `admin-nav__link ${isActive ? "admin-nav__link--active" : ""}`
                }
              >
                <item.icon className="size-[18px]" aria-hidden />
                <span>{item.label}</span>
              </NavLink>
            ))}
          </nav>
          <p className="admin-sidebar__footnote">
            Navigation is limited to the operations approved for your role.
          </p>
        </aside>
        <main id="main-content" className="admin-content">
          {children}
        </main>
      </div>
    </AppFrame>
  );
}
