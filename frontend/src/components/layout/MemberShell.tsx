import type { PropsWithChildren } from "react";
import {
  CalendarDays,
  ChevronRight,
  CircleUserRound,
  LayoutDashboard,
  QrCode,
  ReceiptText,
} from "lucide-react";
import { NavLink } from "react-router-dom";

import { AppFrame } from "@/components/layout/AppFrame";
import { useAuth } from "@/features/auth/AuthContext";

const memberNav = [
  { to: "/app/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/memberships", label: "Membership", icon: ReceiptText },
  { to: "/app/billing", label: "Billing", icon: ReceiptText },
  { to: "/app/qr", label: "My QR code", icon: QrCode, future: true },
  { to: "/app/classes", label: "Classes", icon: CalendarDays, future: true },
  { to: "/app/profile", label: "Profile", icon: CircleUserRound },
];

export function MemberShell({ children }: PropsWithChildren) {
  const { user } = useAuth();

  return (
    <AppFrame>
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
            {memberNav.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `workspace-nav__link ${isActive ? "workspace-nav__link--active" : ""}`
                }
              >
                <item.icon className="size-[18px]" aria-hidden />
                <span>{item.label}</span>
                {item.future ? <small>Day 30+</small> : null}
                <ChevronRight className="workspace-nav__chevron size-4" aria-hidden />
              </NavLink>
            ))}
          </nav>
          <div className="workspace-sidebar__note">
            <strong>Member portal</strong>
            <p>Profile, memberships and billing are connected today.</p>
          </div>
        </aside>
        <main id="main-content" className="workspace-content">
          {children}
        </main>
      </div>
      <nav className="member-bottom-nav" aria-label="Member mobile navigation">
        {memberNav.slice(0, 5).map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `member-bottom-nav__link ${isActive ? "member-bottom-nav__link--active" : ""}`
            }
          >
            <item.icon className="size-5" aria-hidden />
            <span>{item.label === "My QR code" ? "QR" : item.label}</span>
          </NavLink>
        ))}
      </nav>
    </AppFrame>
  );
}
