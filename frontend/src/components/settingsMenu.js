import { isManagerRole, isSuperAdminRole } from "../lib/roles";

export function getSettingsMenuItems(role) {
  if (isSuperAdminRole(role)) {
    return [{ key: "admin_panel", label: "Admin Panel" }];
  }

  // if (isManagerRole(role)) {
  //   return [
  //     { key: "change_password", label: "Change password" },
  //     { key: "manage_forms", label: "Manage department forms" },
  //   ];
  // }

  return [{ key: "change_password", label: "Change password" }];
}
