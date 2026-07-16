import type { PropsWithChildren } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { LoadingState } from "@/components/common/FeedbackState";
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
    return <Navigate to="/login" replace state={{ from: `${location.pathname}${location.search}` }} />;
  }

  if (roles?.length && !roles.includes(user.role)) {
    return <Navigate to="/permission-denied" replace state={{ from: location.pathname }} />;
  }

  return <>{children}</>;
}
