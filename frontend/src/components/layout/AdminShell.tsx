import type { PropsWithChildren } from "react";
import {
  BarChart3,
} from "lucide-react";
import { NavLink } from "react-router-dom";

import { navigationForRole, operationsNavigation } from "@/app/navigation";
import { routePaths } from "@/app/routes";
import { AppFrame } from "@/components/layout/AppFrame";
import { useAuth } from "@/features/auth/AuthContext";

export function AdminShell({ children }: PropsWithChildren) {
  const { user } = useAuth();
  const visibleNav = navigationForRole(operationsNavigation, user?.role);
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
                end={item.to === routePaths.operationsHome}
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
