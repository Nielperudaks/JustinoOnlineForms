import { shouldRefreshAdminData } from "./adminRealtime";

describe("admin realtime invalidation", () => {
  test("refreshes super admin on metadata changes", () => {
    expect(
      shouldRefreshAdminData({
        event: "ADMIN_METADATA_CHANGED",
        payload: { resource: "templates", department_id: "dept-a" },
        user: { role: "super_admin" },
      }),
    ).toBe(true);
  });

  test("refreshes manager only for their department metadata", () => {
    expect(
      shouldRefreshAdminData({
        event: "ADMIN_METADATA_CHANGED",
        payload: { resource: "templates", department_id: "dept-a" },
        user: { role: "manager", department_id: "dept-a" },
      }),
    ).toBe(true);

    expect(
      shouldRefreshAdminData({
        event: "ADMIN_METADATA_CHANGED",
        payload: { resource: "templates", department_id: "dept-b" },
        user: { role: "manager", department_id: "dept-a" },
      }),
    ).toBe(false);
  });

  test("ignores non-admin realtime events", () => {
    expect(
      shouldRefreshAdminData({
        event: "REQUEST_UPDATED",
        payload: { department_id: "dept-a" },
        user: { role: "super_admin" },
      }),
    ).toBe(false);
  });
});
