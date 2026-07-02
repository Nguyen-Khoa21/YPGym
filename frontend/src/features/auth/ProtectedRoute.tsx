import type { PropsWithChildren } from "react";
import { Link, Navigate, useLocation } from "react-router-dom";

import {
  LoadingState,
  PermissionState,
} from "@/components/common/FeedbackState";
import { ButtonLink } from "@/components/ui/Button";
import { AppFrame } from "@/components/layout/AppFrame";
import { useAuth } from "@/features/auth/AuthContext";
import type { UserRole } from "@/types/api";

type ProtectedRouteProps = PropsWithChildren<{
  roles?: UserRole[];
}>;

export function ProtectedRoute({ children, roles }: ProtectedRouteProps) {
  const location = useLocation();
  const { token, user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <AppFrame>
        <main className="mx-auto max-w-3xl px-5 py-10">
          <LoadingState title="Checking access" />
        </main>
      </AppFrame>
    );
  }

  if (!token || !user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (roles?.length && !roles.includes(user.role)) {
    return (
      <AppFrame>
        <main className="mx-auto max-w-3xl px-5 py-10">
          <PermissionState
            title="This area is restricted"
            message="Your current role does not allow access to this page."
            action={
              <ButtonLink asChild>
                <Link to="/member">Go to member dashboard</Link>
              </ButtonLink>
            }
          />
        </main>
      </AppFrame>
    );
  }

  return <>{children}</>;
}
