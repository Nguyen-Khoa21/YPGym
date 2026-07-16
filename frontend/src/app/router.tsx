import { createBrowserRouter, Navigate } from "react-router-dom";

import { HomePage } from "@/app/pages/HomePage";
import { MembershipPoliciesPage } from "@/app/pages/MembershipPoliciesPage";
import { NotFoundPage } from "@/app/pages/NotFoundPage";
import { PermissionDeniedPage } from "@/app/pages/PermissionDeniedPage";
import { PlannedFeaturePage } from "@/app/pages/PlannedFeaturePage";
import { VerificationSuccessPage } from "@/app/pages/VerificationSuccessPage";
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

const adminRoles = ["admin", "manager", "staff"] as const;

export const router = createBrowserRouter([
  { path: "/", element: <HomePage /> },
  { path: "/register", element: <RegisterPage /> },
  { path: "/login", element: <LoginPage /> },
  { path: "/forgot-password", element: <ForgotPasswordPage /> },
  { path: "/reset-password", element: <ResetPasswordPage /> },
  { path: "/verify-email", element: <VerifyEmailPage /> },
  { path: "/verify-email/success", element: <VerificationSuccessPage /> },
  { path: "/policies/membership", element: <MembershipPoliciesPage /> },
  { path: "/memberships", element: <MembershipPlansPage /> },
  {
    path: "/memberships/buy/:planId",
    element: <ProtectedRoute roles={["member"]}><BuyMembershipPage /></ProtectedRoute>,
  },
  {
    path: "/app/dashboard",
    element: <ProtectedRoute roles={["member"]}><MemberDashboardPage /></ProtectedRoute>,
  },
  {
    path: "/app/profile",
    element: <ProtectedRoute><ProfileSettingsPage /></ProtectedRoute>,
  },
  {
    path: "/app/billing",
    element: <ProtectedRoute><PaymentHistoryPage /></ProtectedRoute>,
  },
  {
    path: "/app/qr",
    element: <ProtectedRoute roles={["member"]}><PlannedFeaturePage title="My QR code" description="Attendance QR token generation and scan validation have not been implemented yet." plannedDay="Day 30: QR attendance foundation" scope="member" kind="qr" /></ProtectedRoute>,
  },
  {
    path: "/app/classes",
    element: <ProtectedRoute roles={["member"]}><PlannedFeaturePage title="Class booking" description="Class schedules, booking and waitlists are planned after the current membership and billing work." plannedDay="Day 33: Class booking and schedules" scope="member" kind="classes" /></ProtectedRoute>,
  },
  {
    path: "/admin",
    element: <ProtectedRoute roles={[...adminRoles]}><AdminDashboardPage /></ProtectedRoute>,
  },
  {
    path: "/admin/billing",
    element: <ProtectedRoute roles={[...adminRoles]}><AdminBillingPage /></ProtectedRoute>,
  },
  {
    path: "/admin/members",
    element: <ProtectedRoute roles={[...adminRoles]}><PlannedFeaturePage title="Member CRM" description="Member search, profile records and relationship management need their planned backend APIs before this screen can be connected." plannedDay="Day 26: Member CRM" scope="admin" /></ProtectedRoute>,
  },
  {
    path: "/admin/members/:id",
    element: <ProtectedRoute roles={[...adminRoles]}><PlannedFeaturePage title="Member detail" description="No member detail data is loaded here because the CRM API has not been built yet." plannedDay="Day 26: Member CRM" scope="admin" /></ProtectedRoute>,
  },
  {
    path: "/admin/attendance",
    element: <ProtectedRoute roles={[...adminRoles]}><PlannedFeaturePage title="Attendance operations" description="Attendance dashboards depend on QR scan and occupancy data that does not exist in this release." plannedDay="Day 30: QR attendance foundation" scope="admin" /></ProtectedRoute>,
  },
  {
    path: "/admin/classes",
    element: <ProtectedRoute roles={[...adminRoles]}><PlannedFeaturePage title="Class management" description="Class CRUD and schedule administration are intentionally deferred until class APIs are available." plannedDay="Day 33: Class booking and schedules" scope="admin" kind="classes" /></ProtectedRoute>,
  },
  {
    path: "/admin/pt-assignments",
    element: <ProtectedRoute roles={[...adminRoles]}><PlannedFeaturePage title="PT assignments" description="Trainer assignments are a future admin workflow and no local CRM records are being fabricated for it." plannedDay="Day 35: PT assignment workflows" scope="admin" /></ProtectedRoute>,
  },
  {
    path: "/pt/dashboard",
    element: <ProtectedRoute roles={["pt"]}><PtDashboardPage /></ProtectedRoute>,
  },
  { path: "/permission-denied", element: <PermissionDeniedPage /> },

  // Existing Day 11-20 URLs remain usable as aliases.
  { path: "/member", element: <Navigate to="/app/dashboard" replace /> },
  { path: "/profile", element: <Navigate to="/app/profile" replace /> },
  { path: "/billing", element: <Navigate to="/app/billing" replace /> },
  { path: "/pt", element: <Navigate to="/pt/dashboard" replace /> },
  { path: "*", element: <NotFoundPage /> },
]);
