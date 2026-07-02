import type { PropsWithChildren } from "react";
import { NavLink } from "react-router-dom";

import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";

export function AppFrame({ children }: PropsWithChildren) {
  const { user, logout } = useAuth();
  const navItems = [
    { to: "/", label: "Home", show: true },
    { to: "/memberships", label: "Plans", show: true },
    { to: "/member", label: "Member", show: Boolean(user) },
    { to: "/profile", label: "Profile", show: Boolean(user) },
    { to: "/billing", label: "Billing", show: Boolean(user) },
    {
      to: "/admin",
      label: "Admin",
      show: user ? ["admin", "manager", "staff"].includes(user.role) : false,
    },
    { to: "/login", label: "Login", show: !user },
  ];

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
          <NavLink to="/" className="text-lg font-bold">
            YPGym
          </NavLink>
          <nav className="flex flex-wrap gap-2">
            {navItems.filter((item) => item.show).map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  [
                    "rounded-md px-3 py-2 text-sm font-medium transition",
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground",
                  ].join(" ")
                }
              >
                {item.label}
              </NavLink>
            ))}
            {user ? (
              <Button variant="ghost" className="min-h-9 px-3 py-2" onClick={logout}>
                Logout
              </Button>
            ) : null}
          </nav>
        </div>
      </header>
      {children}
    </div>
  );
}
