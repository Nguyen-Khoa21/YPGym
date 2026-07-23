import type { PropsWithChildren } from "react";
import {
  Bell,
  CalendarDays,
  ChevronRight,
  CircleUserRound,
  ClipboardList,
  LayoutDashboard,
  PauseCircle,
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
  { to: "/app/qr", label: "My QR code", icon: QrCode },
  { to: "/app/attendance", label: "Attendance", icon: ClipboardList },
  { to: "/app/membership-requests", label: "Freeze / cancel", icon: PauseCircle },
  { to: "/app/notifications", label: "Notifications", icon: Bell },
  { to: "/app/classes", label: "Classes", icon: CalendarDays },
  { to: "/app/bookings", label: "My bookings", icon: CalendarDays },
  { to: "/app/profile", label: "Profile", icon: CircleUserRound },
];

const mobileNav = [memberNav[0], memberNav[3], memberNav[7], memberNav[8], memberNav[9]];

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
        {mobileNav.map((item) => (
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
