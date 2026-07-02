import { createBrowserRouter } from "react-router-dom";

import { HomePage } from "@/app/pages/HomePage";
import { NotFoundPage } from "@/app/pages/NotFoundPage";
import { AdminBillingPage } from "@/features/admin/pages/AdminBillingPage";
import { AdminDashboardPage } from "@/features/admin/pages/AdminDashboardPage";
import { ForgotPasswordPage } from "@/features/auth/pages/ForgotPasswordPage";
import { LoginPage } from "@/features/auth/pages/LoginPage";
import { ProtectedRoute } from "@/features/auth/ProtectedRoute";
import { RegisterPage } from "@/features/auth/pages/RegisterPage";
import { ResetPasswordPage } from "@/features/auth/pages/ResetPasswordPage";
import { VerifyEmailPage } from "@/features/auth/pages/VerifyEmailPage";
import { PaymentHistoryPage } from "@/features/billing/pages/PaymentHistoryPage";
import { MemberDashboardPage } from "@/features/member/pages/MemberDashboardPage";
import { ProfileSettingsPage } from "@/features/member/pages/ProfileSettingsPage";
import { PtDashboardPage } from "@/features/member/pages/PtDashboardPage";
import { BuyMembershipPage } from "@/features/memberships/pages/BuyMembershipPage";
import { MembershipPlansPage } from "@/features/memberships/pages/MembershipPlansPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <HomePage />,
  },
  {
    path: "/register",
    element: <RegisterPage />,
  },
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/forgot-password",
    element: <ForgotPasswordPage />,
  },
  {
    path: "/reset-password",
    element: <ResetPasswordPage />,
  },
  {
    path: "/verify-email",
    element: <VerifyEmailPage />,
  },
  {
    path: "/verify-email/success",
    element: <VerifyEmailPage />,
  },
  {
    path: "/memberships",
    element: <MembershipPlansPage />,
  },
  {
    path: "/member",
    element: (
      <ProtectedRoute roles={["member", "pt", "admin", "manager", "staff"]}>
        <MemberDashboardPage />
      </ProtectedRoute>
    ),
  },
  {
    path: "/profile",
    element: (
      <ProtectedRoute>
        <ProfileSettingsPage />
      </ProtectedRoute>
    ),
  },
  {
    path: "/billing",
    element: (
      <ProtectedRoute>
        <PaymentHistoryPage />
      </ProtectedRoute>
    ),
  },
  {
    path: "/memberships/buy/:planId",
    element: (
      <ProtectedRoute roles={["member"]}>
        <BuyMembershipPage />
      </ProtectedRoute>
    ),
  },
  {
    path: "/admin",
    element: (
      <ProtectedRoute roles={["admin", "manager", "staff"]}>
        <AdminDashboardPage />
      </ProtectedRoute>
    ),
  },
  {
    path: "/admin/billing",
    element: (
      <ProtectedRoute roles={["admin", "manager", "staff"]}>
        <AdminBillingPage />
      </ProtectedRoute>
    ),
  },
  {
    path: "/pt",
    element: (
      <ProtectedRoute roles={["pt"]}>
        <PtDashboardPage />
      </ProtectedRoute>
    ),
  },
  {
    path: "*",
    element: <NotFoundPage />,
  },
]);
