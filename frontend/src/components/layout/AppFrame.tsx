import type { PropsWithChildren } from "react";
import { LayoutDashboard, LogOut, Menu, Sparkles } from "lucide-react";
import { Link, NavLink } from "react-router-dom";

import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { workspacePathForRole } from "@/features/auth/workspace";

type AppFrameProps = PropsWithChildren<{
  compact?: boolean;
  navigation?: { to: string; label: string }[];
}>;

const publicLinks = [
  { to: "/", label: "Overview" },
  { to: "/memberships", label: "Memberships" },
  { to: "/policies/membership", label: "Policies" },
];

export function AppFrame({ children, compact = false, navigation }: AppFrameProps) {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-[hsl(var(--background))] text-foreground">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <header className="site-header">
        <div className="site-header__inner">
          <Link to="/" className="brand" aria-label="YPGym home">
            <span className="brand__mark" aria-hidden>
              YP
            </span>
            <span>YPGYM</span>
          </Link>

          {!compact ? (
            <nav className="site-nav" aria-label="Main navigation">
              {publicLinks.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    `site-nav__link ${isActive ? "site-nav__link--active" : ""}`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>
          ) : null}

          <div className="site-header__actions">
            {user ? (
              <>
                <Link className="header-join" to={workspacePathForRole(user.role)}>
                  <LayoutDashboard className="size-4" aria-hidden />
                  Workspace
                </Link>
                <Link className="identity-chip" to="/app/profile" aria-label="Your profile">
                  <span className="identity-chip__avatar" aria-hidden>
                    {user.name.slice(0, 1).toUpperCase()}
                  </span>
                  <span className="identity-chip__copy">
                    <strong>{user.name.split(" ")[0]}</strong>
                    <small>{user.role}</small>
                  </span>
                </Link>
                <Button
                  aria-label="Log out"
                  className="site-header__logout"
                  variant="ghost"
                  onClick={logout}
                >
                  <LogOut className="size-4" aria-hidden />
                  <span>Log out</span>
                </Button>
              </>
            ) : (
              <>
                <Link className="header-login" to="/login">
                  Log in
                </Link>
                <Link className="header-join" to="/register">
                  <Sparkles className="size-4" aria-hidden />
                  Join YPGym
                </Link>
              </>
            )}
            <details className="site-header__menu relative">
              <summary className="grid size-9 cursor-pointer list-none place-items-center rounded-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary" aria-label="Navigation menu"><Menu className="size-5" aria-hidden /></summary>
              <nav aria-label="Mobile main navigation" className="absolute right-0 top-11 z-50 grid max-h-[75dvh] min-w-48 gap-1 overflow-y-auto rounded-xl border border-border bg-card p-2 shadow-lg">
                {(navigation ?? publicLinks).map((item) => <Link key={item.to} to={item.to} className="rounded-md px-3 py-2 text-sm font-semibold hover:bg-muted">{item.label}</Link>)}
                {user ? <Button variant="ghost" className="justify-start" onClick={logout}><LogOut className="size-4" aria-hidden />Log out</Button> : <Link className="rounded-md px-3 py-2 text-sm font-semibold hover:bg-muted" to="/login">Log in</Link>}
              </nav>
            </details>
          </div>
        </div>
      </header>
      {children}
    </div>
  );
}
