import { lazy } from "react";
import { createBrowserRouter, Navigate } from "react-router-dom";

import { HomePage } from "@/app/pages/HomePage";
import { MembershipPoliciesPage } from "@/app/pages/MembershipPoliciesPage";
import { NotFoundPage } from "@/app/pages/NotFoundPage";
import { PermissionDeniedPage } from "@/app/pages/PermissionDeniedPage";
import { VerificationSuccessPage } from "@/app/pages/VerificationSuccessPage";
import { routePaths } from "@/app/routes";
import { MemberAttendancePage } from "@/features/attendance/pages/MemberAttendancePage";
import { MemberQrPage } from "@/features/attendance/pages/MemberQrPage";
import { AdminBroadcastsPage } from "@/features/admin/pages/AdminBroadcastsPage";
import { AdminDashboardPage } from "@/features/admin/pages/AdminDashboardPage";
import { AdminMemberDetailPage } from "@/features/admin/pages/AdminMemberDetailPage";
import { AdminMembershipApprovalsPage } from "@/features/admin/pages/AdminMembershipApprovalsPage";
import { AdminMembersPage } from "@/features/admin/pages/AdminMembersPage";
import { AdminSettingsPage } from "@/features/admin/pages/AdminSettingsPage";
import { ForgotPasswordPage } from "@/features/auth/pages/ForgotPasswordPage";
import { LoginPage } from "@/features/auth/pages/LoginPage";
import { ChangePasswordPage } from "@/features/auth/pages/ChangePasswordPage";
import { OAuthCallbackPage } from "@/features/auth/pages/OAuthCallbackPage";
import { OAuthLinkAccountPage } from "@/features/auth/pages/OAuthLinkAccountPage";
import { ProtectedRoute } from "@/features/auth/ProtectedRoute";
import { RegisterPage } from "@/features/auth/pages/RegisterPage";
import { ResetPasswordPage } from "@/features/auth/pages/ResetPasswordPage";
import { VerifyEmailPage } from "@/features/auth/pages/VerifyEmailPage";
import { clientRoleGroups } from "@/features/auth/workspace";
import { PaymentHistoryPage } from "@/features/billing/pages/PaymentHistoryPage";
import { PaymentResultPage } from "@/features/billing/pages/PaymentResultPage";
import { AdminClassesPage } from "@/features/classes/pages/AdminClassesPage";
import { AdminTrainersPage } from "@/features/classes/pages/AdminTrainersPage";
import { MemberClassesPage } from "@/features/classes/pages/MemberClassesPage";
import { MyBookingsPage } from "@/features/classes/pages/MyBookingsPage";
import { MemberDashboardPage } from "@/features/member/pages/MemberDashboardPage";
import { MembershipRequestsPage } from "@/features/member/pages/MembershipRequestsPage";
import { NotificationPreferencesPage } from "@/features/member/pages/NotificationPreferencesPage";
import { NotificationsPage } from "@/features/member/pages/NotificationsPage";
import { ProfileSettingsPage } from "@/features/member/pages/ProfileSettingsPage";
import { AccountSecurityPage } from "@/features/member/pages/AccountSecurityPage";
import { AdminEmailDeliveriesPage } from "@/features/admin/pages/AdminEmailDeliveriesPage";
import { PtDashboardPage } from "@/features/member/pages/PtDashboardPage";
import { BuyMembershipPage } from "@/features/memberships/pages/BuyMembershipPage";
import { MembershipPlansPage } from "@/features/memberships/pages/MembershipPlansPage";
import { AdminStaffPage } from "@/features/admin/pages/AdminStaffPage";
import { StaffTimeClockPage } from "@/features/staff/pages/StaffTimeClockPage";

const AdminAttendancePage = lazy(() =>
  import("@/features/attendance/pages/AdminAttendancePage").then((module) => ({
    default: module.AdminAttendancePage,
  })),
);
const AdminAuditPage = lazy(() =>
  import("@/features/admin/pages/AdminAuditPage").then((module) => ({
    default: module.AdminAuditPage,
  })),
);
const AdminBillingPage = lazy(() =>
  import("@/features/admin/pages/AdminBillingPage").then((module) => ({
    default: module.AdminBillingPage,
  })),
);
const AdminTrainingPage = lazy(() =>
  import("@/features/training/pages/AdminTrainingPage").then((module) => ({
    default: module.AdminTrainingPage,
  })),
);
const MemberTrainingPage = lazy(() =>
  import("@/features/training/pages/MemberTrainingPage").then((module) => ({
    default: module.MemberTrainingPage,
  })),
);

export const router = createBrowserRouter([
  { path: routePaths.home, element: <HomePage /> },
  { path: routePaths.register, element: <RegisterPage /> },
  { path: routePaths.login, element: <LoginPage /> },
  { path: routePaths.changePassword, element: <ProtectedRoute><ChangePasswordPage /></ProtectedRoute> },
  { path: routePaths.oauthCallback, element: <OAuthCallbackPage /> },
  { path: routePaths.oauthLinkAccount, element: <OAuthLinkAccountPage /> },
  { path: routePaths.forgotPassword, element: <ForgotPasswordPage /> },
  { path: routePaths.resetPassword, element: <ResetPasswordPage /> },
  { path: routePaths.verifyEmail, element: <VerifyEmailPage /> },
  { path: routePaths.verificationSuccess, element: <VerificationSuccessPage /> },
  { path: routePaths.membershipPolicies, element: <MembershipPoliciesPage /> },
  { path: routePaths.membershipPlans, element: <MembershipPlansPage /> },
  {
    path: routePaths.membershipPurchase,
    element: <ProtectedRoute roles={[...clientRoleGroups.member]}><BuyMembershipPage /></ProtectedRoute>,
  },
  {
    path: routePaths.memberDashboard,
    element: <ProtectedRoute roles={[...clientRoleGroups.member]}><MemberDashboardPage /></ProtectedRoute>,
  },
  {
    path: routePaths.memberProfile,
    element: <ProtectedRoute><ProfileSettingsPage /></ProtectedRoute>,
  },
  {
    path: routePaths.memberSecurity,
    element: <ProtectedRoute><AccountSecurityPage /></ProtectedRoute>,
  },
  {
    path: routePaths.memberBilling,
    element: <ProtectedRoute><PaymentHistoryPage /></ProtectedRoute>,
  },
  {
    path: routePaths.paymentResult,
    element: <ProtectedRoute roles={[...clientRoleGroups.member]}><PaymentResultPage /></ProtectedRoute>,
  },
  {
    path: routePaths.memberQr,
    element: <ProtectedRoute roles={[...clientRoleGroups.member]}><MemberQrPage /></ProtectedRoute>,
  },
  {
    path: routePaths.memberAttendance,
    element: <ProtectedRoute roles={[...clientRoleGroups.member]}><MemberAttendancePage /></ProtectedRoute>,
  },
  {
    path: routePaths.membershipRequests,
    element: <ProtectedRoute roles={[...clientRoleGroups.member]}><MembershipRequestsPage /></ProtectedRoute>,
  },
  {
    path: routePaths.memberNotifications,
    element: <ProtectedRoute roles={[...clientRoleGroups.member]}><NotificationsPage /></ProtectedRoute>,
  },
  {
    path: routePaths.notificationPreferences,
    element: <ProtectedRoute roles={[...clientRoleGroups.member]}><NotificationPreferencesPage /></ProtectedRoute>,
  },
  {
    path: routePaths.memberClasses,
    element: <ProtectedRoute roles={[...clientRoleGroups.member]}><MemberClassesPage /></ProtectedRoute>,
  },
  {
    path: routePaths.memberBookings,
    element: <ProtectedRoute roles={[...clientRoleGroups.member]}><MyBookingsPage /></ProtectedRoute>,
  },
  {
    path: routePaths.memberTraining,
    element: <ProtectedRoute roles={[...clientRoleGroups.member]}><MemberTrainingPage /></ProtectedRoute>,
  },
  {
    path: routePaths.memberTrainingDetail,
    element: <ProtectedRoute roles={[...clientRoleGroups.member]}><MemberTrainingPage /></ProtectedRoute>,
  },
  {
    path: routePaths.operationsHome,
    element: <ProtectedRoute roles={[...clientRoleGroups.operations]}><AdminDashboardPage /></ProtectedRoute>,
  },
  {
    path: routePaths.adminBilling,
    element: <ProtectedRoute roles={[...clientRoleGroups.admin]}><AdminBillingPage /></ProtectedRoute>,
  },
  {
    path: routePaths.adminEmailDeliveries,
    element: <ProtectedRoute roles={[...clientRoleGroups.management]}><AdminEmailDeliveriesPage /></ProtectedRoute>,
  },
  {
    path: routePaths.adminMembers,
    element: <ProtectedRoute roles={[...clientRoleGroups.management]}><AdminMembersPage /></ProtectedRoute>,
  },
  {
    path: routePaths.adminMemberDetail,
    element: <ProtectedRoute roles={[...clientRoleGroups.management]}><AdminMemberDetailPage /></ProtectedRoute>,
  },
  {
    path: routePaths.adminAttendance,
    element: <ProtectedRoute roles={[...clientRoleGroups.operations]}><AdminAttendancePage /></ProtectedRoute>,
  },
  {
    path: routePaths.adminClasses,
    element: <ProtectedRoute roles={[...clientRoleGroups.admin]}><AdminClassesPage /></ProtectedRoute>,
  },
  {
    path: routePaths.adminAudit,
    element: <ProtectedRoute roles={[...clientRoleGroups.management]}><AdminAuditPage /></ProtectedRoute>,
  },
  {
    path: routePaths.adminApprovals,
    element: <ProtectedRoute roles={[...clientRoleGroups.management]}><AdminMembershipApprovalsPage /></ProtectedRoute>,
  },
  {
    path: routePaths.adminSettings,
    element: <ProtectedRoute roles={[...clientRoleGroups.management]}><AdminSettingsPage /></ProtectedRoute>,
  },
  {
    path: routePaths.adminBroadcasts,
    element: <ProtectedRoute roles={[...clientRoleGroups.management]}><AdminBroadcastsPage /></ProtectedRoute>,
  },
  {
    path: routePaths.adminPtAssignments,
    element: <ProtectedRoute roles={[...clientRoleGroups.management]}><AdminTrainersPage /></ProtectedRoute>,
  },
  {
    path: routePaths.adminExercises,
    element: <ProtectedRoute roles={[...clientRoleGroups.management]}><AdminTrainingPage /></ProtectedRoute>,
  },
  {
    path: routePaths.adminStaff,
    element: <ProtectedRoute roles={[...clientRoleGroups.management]}><AdminStaffPage /></ProtectedRoute>,
  },
  {
    path: routePaths.staffTimeClock,
    element: <ProtectedRoute roles={[...clientRoleGroups.workforce]}><StaffTimeClockPage /></ProtectedRoute>,
  },
  {
    path: routePaths.ptDashboard,
    element: <ProtectedRoute roles={[...clientRoleGroups.trainer]}><PtDashboardPage /></ProtectedRoute>,
  },
  { path: routePaths.permissionDenied, element: <PermissionDeniedPage /> },

  // Existing Day 11-20 URLs remain usable as aliases.
  { path: routePaths.memberAlias, element: <Navigate to={routePaths.memberDashboard} replace /> },
  { path: routePaths.profileAlias, element: <Navigate to={routePaths.memberProfile} replace /> },
  { path: routePaths.billingAlias, element: <Navigate to={routePaths.memberBilling} replace /> },
  { path: routePaths.ptAlias, element: <Navigate to={routePaths.ptDashboard} replace /> },
  { path: "*", element: <NotFoundPage /> },
]);
