import {
  Bell,
  CalendarDays,
  CircleUserRound,
  ClipboardCheck,
  ClipboardList,
  CreditCard,
  Dumbbell,
  LayoutDashboard,
  MailCheck,
  Megaphone,
  PauseCircle,
  QrCode,
  ReceiptText,
  Settings2,
  ShieldCheck,
  UserRoundCog,
  UsersRound,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { clientRoleGroups } from "../features/auth/workspace.ts";
import type { UserRole } from "../types/api.ts";
import { routePaths } from "./routes.ts";

export type NavigationItem = {
  to: string;
  label: string;
};

type IconNavigationItem = NavigationItem & {
  icon: LucideIcon;
};

type MemberNavigationItem = IconNavigationItem & {
  mobileLabel?: string;
};

export type OperationsNavigationItem = IconNavigationItem & {
  roles: readonly UserRole[];
  dashboard?: {
    title: string;
    detail: string;
  };
};

export const publicNavigation = [
  { to: routePaths.home, label: "Overview" },
  { to: routePaths.membershipPlans, label: "Memberships" },
  { to: routePaths.membershipPolicies, label: "Policies" },
] satisfies readonly NavigationItem[];

export const memberNavigation = [
  { to: routePaths.memberDashboard, label: "Dashboard", icon: LayoutDashboard, mobileLabel: "Dashboard" },
  { to: routePaths.membershipPlans, label: "Membership", icon: ReceiptText },
  { to: routePaths.memberBilling, label: "Billing", icon: ReceiptText },
  { to: routePaths.memberQr, label: "My QR code", icon: QrCode, mobileLabel: "QR" },
  { to: routePaths.memberAttendance, label: "Attendance", icon: ClipboardList },
  { to: routePaths.membershipRequests, label: "Freeze / cancel", icon: PauseCircle },
  { to: routePaths.memberNotifications, label: "Notifications", icon: Bell },
  { to: routePaths.memberClasses, label: "Classes", icon: CalendarDays, mobileLabel: "Classes" },
  { to: routePaths.memberTraining, label: "YPTrain", icon: Dumbbell, mobileLabel: "YPTrain" },
  { to: routePaths.memberBookings, label: "My bookings", icon: CalendarDays },
  { to: routePaths.memberProfile, label: "Profile", icon: CircleUserRound, mobileLabel: "Profile" },
] satisfies readonly MemberNavigationItem[];

export const memberMobileNavigation = memberNavigation.filter((item) => item.mobileLabel !== undefined);

export const operationsNavigation = [
  { to: routePaths.operationsHome, label: "Overview", icon: LayoutDashboard, roles: clientRoleGroups.operations },
  { to: routePaths.adminMembers, label: "Members", icon: UsersRound, roles: clientRoleGroups.management, dashboard: { title: "Member CRM", detail: "Search, filter, review complete member records, and manage memberships." } },
  { to: routePaths.adminBilling, label: "Billing", icon: CreditCard, roles: clientRoleGroups.admin, dashboard: { title: "Billing ledger", detail: "Filtered payments, invoices, audited exports, and totals." } },
  { to: routePaths.adminEmailDeliveries, label: "Email delivery", icon: MailCheck, roles: clientRoleGroups.management },
  { to: routePaths.adminAttendance, label: "Attendance", icon: ClipboardList, roles: clientRoleGroups.operations, dashboard: { title: "Attendance ops", detail: "Live capacity, session controls, event sources, and peak-hours analytics." } },
  { to: routePaths.adminClasses, label: "Classes", icon: CalendarDays, roles: clientRoleGroups.admin, dashboard: { title: "Class schedule", detail: "Create, edit, filter, and cancel trainer-linked classes." } },
  { to: routePaths.adminApprovals, label: "Approvals", icon: ClipboardCheck, roles: clientRoleGroups.management, dashboard: { title: "Membership approvals", detail: "Review freeze and cancellation requests with required reasons and outcomes." } },
  { to: routePaths.adminBroadcasts, label: "Broadcasts", icon: Megaphone, roles: clientRoleGroups.management, dashboard: { title: "Broadcasts", detail: "Publish preference-aware announcements with active periods." } },
  { to: routePaths.adminAudit, label: "Audit log", icon: ShieldCheck, roles: clientRoleGroups.management, dashboard: { title: "Audit log", detail: "Review sensitive actions, actors, targets, reasons, and outcomes." } },
  { to: routePaths.adminSettings, label: "Settings", icon: Settings2, roles: clientRoleGroups.management, dashboard: { title: "Configuration", detail: "Manage validated runtime values with Redis cache invalidation." } },
  { to: routePaths.adminPtAssignments, label: "PT profiles", icon: Dumbbell, roles: clientRoleGroups.management, dashboard: { title: "PT profiles", detail: "Maintain member-facing coach profiles and future class assignments." } },
  { to: routePaths.adminExercises, label: "Exercises", icon: Dumbbell, roles: clientRoleGroups.management, dashboard: { title: "YPTrain exercises", detail: "Maintain the shared member exercise guide, muscle tags and images." } },
  { to: routePaths.adminStaff, label: "Staff & shifts", icon: UserRoundCog, roles: clientRoleGroups.management, dashboard: { title: "Staff & shifts", detail: "Provision individual staff/PT sign-ins and review auditable shift records." } },
  { to: routePaths.staffTimeClock, label: "My time clock", icon: UserRoundCog, roles: clientRoleGroups.staff, dashboard: { title: "My time clock", detail: "Clock in or out and review your own recent shifts." } },
] satisfies readonly OperationsNavigationItem[];

export function navigationForRole<T extends { roles: readonly UserRole[] }>(items: readonly T[], role?: UserRole) {
  return role ? items.filter((item) => item.roles.includes(role)) : [];
}

const staffNavigation = [
  { to: routePaths.staffTimeClock, label: "Time clock" },
  { to: routePaths.adminAttendance, label: "Attendance operations" },
  { to: routePaths.memberProfile, label: "Account" },
] satisfies readonly NavigationItem[];

const trainerNavigation = [
  { to: routePaths.ptDashboard, label: "Trainer workspace" },
  { to: routePaths.staffTimeClock, label: "Time clock" },
  { to: routePaths.memberProfile, label: "Account" },
] satisfies readonly NavigationItem[];

export function workforceNavigationForRole(role?: UserRole) {
  return role === "pt" ? trainerNavigation : staffNavigation;
}
