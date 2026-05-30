import { getSettingsMenuItems } from "./settingsMenu";

describe("settings menu items", () => {
  test("shows password change for requestors", () => {
    expect(getSettingsMenuItems("requestor")).toEqual([
      { key: "change_password", label: "Change password" },
    ]);
  });

  test("shows password change and department form management for manager roles", () => {
    expect(getSettingsMenuItems("manager_ops")).toEqual([
      { key: "change_password", label: "Change password" },
      { key: "manage_forms", label: "Manage department forms" },
    ]);
    expect(getSettingsMenuItems("manager_sup")).toEqual([
      { key: "change_password", label: "Change password" },
      { key: "manage_forms", label: "Manage department forms" },
    ]);
  });

  test("keeps super admins on the admin panel action", () => {
    expect(getSettingsMenuItems("super_admin")).toEqual([
      { key: "admin_panel", label: "Admin Panel" },
    ]);
  });
});
