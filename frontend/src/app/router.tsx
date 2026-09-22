import { createBrowserRouter, Navigate } from "react-router-dom";

import { HomePage } from "@/app/pages/HomePage";
import { MembershipPoliciesPage } from "@/app/pages/MembershipPoliciesPage";
import { NotFoundPage } from "@/app/pages/NotFoundPage";
import { PermissionDeniedPage } from "@/app/pages/PermissionDeniedPage";
import { VerificationSuccessPage } from "@/app/pages/VerificationSuccessPage";
import { AdminAttendancePage } from "@/features/attendance/pages/AdminAttendancePage";
import { MemberAttendancePage } from "@/features/attendance/pages/MemberAttendancePage";
import { MemberQrPage } from "@/features/attendance/pages/MemberQrPage";
import { AdminAuditPage } from "@/features/admin/pages/AdminAuditPage";
import { AdminBillingPage } from "@/features/admin/pages/AdminBillingPage";
import { AdminBroadcastsPage } from "@/features/admin/pages/AdminBroadcastsPage";
import { AdminDashboardPage } from "@/features/admin/pages/AdminDashboardPage";
import { AdminMemberDetailPage } from "@/features/admin/pages/AdminMemberDetailPage";
import { AdminMembershipApprovalsPage } from "@/features/admin/pages/AdminMembershipApprovalsPage";
import { AdminMembersPage } from "@/features/admin/pages/AdminMembersPage";
import { AdminSettingsPage } from "@/features/admin/pages/AdminSettingsPage";
import { ForgotPasswordPage } from "@/features/auth/pages/ForgotPasswordPage";
import { LoginPage } from "@/features/auth/pages/LoginPage";
import { ProtectedRoute } from "@/features/auth/ProtectedRoute";
import { RegisterPage } from "@/features/auth/pages/RegisterPage";
import { ResetPasswordPage } from "@/features/auth/pages/ResetPasswordPage";
import { VerifyEmailPage } from "@/features/auth/pages/VerifyEmailPage";
import { PaymentHistoryPage } from "@/features/billing/pages/PaymentHistoryPage";
import { AdminClassesPage } from "@/features/classes/pages/AdminClassesPage";
import { AdminTrainersPage } from "@/features/classes/pages/AdminTrainersPage";
import { MemberClassesPage } from "@/features/classes/pages/MemberClassesPage";
import { MyBookingsPage } from "@/features/classes/pages/MyBookingsPage";
import { MemberDashboardPage } from "@/features/member/pages/MemberDashboardPage";
import { MembershipRequestsPage } from "@/features/member/pages/MembershipRequestsPage";
import { NotificationPreferencesPage } from "@/features/member/pages/NotificationPreferencesPage";
import { NotificationsPage } from "@/features/member/pages/NotificationsPage";
import { ProfileSettingsPage } from "@/features/member/pages/ProfileSettingsPage";
import { PtDashboardPage } from "@/features/member/pages/PtDashboardPage";
import { BuyMembershipPage } from "@/features/memberships/pages/BuyMembershipPage";
import { MembershipPlansPage } from "@/features/memberships/pages/MembershipPlansPage";
import { AdminTrainingPage } from "@/features/training/pages/AdminTrainingPage";
import { MemberTrainingPage } from "@/features/training/pages/MemberTrainingPage";

const operationsRoles = ["admin", "manager", "staff"] as const;
const managerRoles = ["admin", "manager"] as const;

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
    element: <ProtectedRoute roles={["member"]}><MemberQrPage /></ProtectedRoute>,
  },
  {
    path: "/app/attendance",
    element: <ProtectedRoute roles={["member"]}><MemberAttendancePage /></ProtectedRoute>,
  },
  {
    path: "/app/membership-requests",
    element: <ProtectedRoute roles={["member"]}><MembershipRequestsPage /></ProtectedRoute>,
  },
  {
    path: "/app/notifications",
    element: <ProtectedRoute roles={["member"]}><NotificationsPage /></ProtectedRoute>,
  },
  {
    path: "/app/notifications/preferences",
    element: <ProtectedRoute roles={["member"]}><NotificationPreferencesPage /></ProtectedRoute>,
  },
  {
    path: "/app/classes",
    element: <ProtectedRoute roles={["member"]}><MemberClassesPage /></ProtectedRoute>,
  },
  {
    path: "/app/bookings",
    element: <ProtectedRoute roles={["member"]}><MyBookingsPage /></ProtectedRoute>,
  },
  {
    path: "/app/train",
    element: <ProtectedRoute roles={["member"]}><MemberTrainingPage /></ProtectedRoute>,
  },
  {
    path: "/app/train/:id",
    element: <ProtectedRoute roles={["member"]}><MemberTrainingPage /></ProtectedRoute>,
  },
  {
    path: "/admin",
    element: <ProtectedRoute roles={[...operationsRoles]}><AdminDashboardPage /></ProtectedRoute>,
  },
  {
    path: "/admin/billing",
    element: <ProtectedRoute roles={["admin"]}><AdminBillingPage /></ProtectedRoute>,
  },
  {
    path: "/admin/members",
    element: <ProtectedRoute roles={["admin"]}><AdminMembersPage /></ProtectedRoute>,
  },
  {
    path: "/admin/members/:id",
    element: <ProtectedRoute roles={["admin"]}><AdminMemberDetailPage /></ProtectedRoute>,
  },
  {
    path: "/admin/attendance",
    element: <ProtectedRoute roles={[...operationsRoles]}><AdminAttendancePage /></ProtectedRoute>,
  },
  {
    path: "/admin/classes",
    element: <ProtectedRoute roles={["admin"]}><AdminClassesPage /></ProtectedRoute>,
  },
  {
    path: "/admin/audit",
    element: <ProtectedRoute roles={[...managerRoles]}><AdminAuditPage /></ProtectedRoute>,
  },
  {
    path: "/admin/approvals",
    element: <ProtectedRoute roles={[...managerRoles]}><AdminMembershipApprovalsPage /></ProtectedRoute>,
  },
  {
    path: "/admin/settings",
    element: <ProtectedRoute roles={[...managerRoles]}><AdminSettingsPage /></ProtectedRoute>,
  },
  {
    path: "/admin/broadcasts",
    element: <ProtectedRoute roles={[...managerRoles]}><AdminBroadcastsPage /></ProtectedRoute>,
  },
  {
    path: "/admin/pt-assignments",
    element: <ProtectedRoute roles={[...managerRoles]}><AdminTrainersPage /></ProtectedRoute>,
  },
  {
    path: "/admin/exercises",
    element: <ProtectedRoute roles={[...managerRoles]}><AdminTrainingPage /></ProtectedRoute>,
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
