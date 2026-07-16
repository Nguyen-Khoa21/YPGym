import type { PropsWithChildren } from "react";
import { LogOut, Menu, Sparkles } from "lucide-react";
import { Link, NavLink } from "react-router-dom";

import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";

type AppFrameProps = PropsWithChildren<{
  compact?: boolean;
}>;

const publicLinks = [
  { to: "/", label: "Overview" },
  { to: "/memberships", label: "Memberships" },
  { to: "/policies/membership", label: "Policies" },
];

export function AppFrame({ children, compact = false }: AppFrameProps) {
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
                <Link className="identity-chip" to="/app/profile">
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
            <Menu className="site-header__menu size-5" aria-hidden />
          </div>
        </div>
      </header>
      {children}
    </div>
  );
}
