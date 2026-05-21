import {
  upsertById,
  removeById,
  isApproverUser,
  isCustodianUser,
} from "./adminState";

describe("admin state helpers", () => {
  test("upserts API results without waiting for a full refetch", () => {
    const users = [
      { id: "user-1", name: "Old Name" },
      { id: "user-2", name: "Another User" },
    ];

    expect(upsertById(users, { id: "user-1", name: "New Name" })).toEqual([
      { id: "user-1", name: "New Name" },
      { id: "user-2", name: "Another User" },
    ]);
    expect(upsertById(users, { id: "user-3", name: "Created User" })).toEqual([
      { id: "user-3", name: "Created User" },
      { id: "user-1", name: "Old Name" },
      { id: "user-2", name: "Another User" },
    ]);
  });

  test("removes deleted records from the current list", () => {
    expect(
      removeById(
        [
          { id: "dept-1", name: "Accounting" },
          { id: "dept-2", name: "IT" },
        ],
        "dept-1",
      ),
    ).toEqual([{ id: "dept-2", name: "IT" }]);
  });

  test("keeps derived user pickers in sync with updated roles and status", () => {
    expect(isApproverUser({ role: "manager" })).toBe(true);
    expect(isApproverUser({ role: "requestor" })).toBe(false);
    expect(isCustodianUser({ is_active: true })).toBe(true);
    expect(isCustodianUser({ is_active: false })).toBe(false);
  });
});
