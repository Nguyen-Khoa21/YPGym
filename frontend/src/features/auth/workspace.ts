import type { UserRole } from "@/types/api";

const workspacePaths: Record<UserRole, string> = {
  admin: "/admin",
  manager: "/admin",
  staff: "/admin",
  pt: "/pt/dashboard",
  member: "/app/dashboard",
};

export function workspacePathForRole(role: UserRole) {
  return workspacePaths[role];
}
