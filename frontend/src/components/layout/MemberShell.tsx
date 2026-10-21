import type { PropsWithChildren } from "react";
import { ChevronRight } from "lucide-react";
import { NavLink } from "react-router-dom";

import { memberMobileNavigation, memberNavigation } from "@/app/navigation";
import { AppFrame } from "@/components/layout/AppFrame";
import { useAuth } from "@/features/auth/AuthContext";

export function MemberShell({ children }: PropsWithChildren) {
  const { user } = useAuth();

  return (
    <AppFrame navigation={memberNavigation}>
      <div className="workspace-shell">
        <aside className="workspace-sidebar" aria-label="Member navigation">
          <div className="workspace-profile">
            <span className="workspace-profile__avatar" aria-hidden>
              {user?.name.slice(0, 1).toUpperCase()}
            </span>
            <div>
              <p>{user?.name}</p>
              <span>{user?.tier} member</span>
            </div>
          </div>
          <nav className="workspace-nav">
            {memberNavigation.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `workspace-nav__link ${isActive ? "workspace-nav__link--active" : ""}`
                }
              >
                <item.icon className="size-[18px]" aria-hidden />
                <span>{item.label}</span>
                <ChevronRight className="workspace-nav__chevron size-4" aria-hidden />
              </NavLink>
            ))}
          </nav>
          <div className="workspace-sidebar__note">
            <strong>Member portal</strong>
            <p>Membership, classes, notifications, QR access, attendance and billing are connected.</p>
          </div>
        </aside>
        <main id="main-content" className="workspace-content">
          {children}
        </main>
      </div>
      <nav className="member-bottom-nav" aria-label="Member mobile navigation">
        {memberMobileNavigation.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `member-bottom-nav__link ${isActive ? "member-bottom-nav__link--active" : ""}`
            }
          >
            <item.icon className="size-5" aria-hidden />
            <span>{item.mobileLabel}</span>
          </NavLink>
        ))}
      </nav>
    </AppFrame>
  );
}
