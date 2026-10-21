import { routePaths } from "../../app/routes.ts";
import type { UserRole } from "../../types/api.ts";

export const clientRoleGroups = {
  member: ["member"],
  staff: ["staff"],
  workforce: ["staff", "pt"],
  operations: ["staff", "manager", "admin"],
  management: ["manager", "admin"],
  admin: ["admin"],
  trainer: ["pt"],
} as const satisfies Record<string, readonly UserRole[]>;

const workspacePaths: Record<UserRole, string> = {
  admin: routePaths.operationsHome,
  manager: routePaths.operationsHome,
  staff: routePaths.staffTimeClock,
  pt: routePaths.ptDashboard,
  member: routePaths.memberDashboard,
};

export function workspacePathForRole(role: UserRole) {
  return workspacePaths[role];
}
