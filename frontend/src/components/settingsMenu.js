export function getSettingsMenuItems(role) {
  if (role === "super_admin") {
    return [{ key: "admin_panel", label: "Admin Panel" }];
  }

  // if (role === "manager") {
  //   return [
  //     { key: "change_password", label: "Change password" },
  //     { key: "manage_forms", label: "Manage department forms" },
  //   ];
  // }

  return [{ key: "change_password", label: "Change password" }];
}
