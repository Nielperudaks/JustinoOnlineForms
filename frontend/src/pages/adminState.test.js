import {
  upsertById,
  removeById,
  isApproverUser,
  isCustodianUser,
  getAvailableDepartmentGroupMembers,
  getEditableDepartmentGroups,
  getSpecialApproverLabel,
  mergeServerItemsWithLocalChanges,
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
    expect(isApproverUser({ role: "manager_ops" })).toBe(true);
    expect(isApproverUser({ role: "manager_sup" })).toBe(true);
    expect(isApproverUser({ role: "executive_ops" })).toBe(true);
    expect(isApproverUser({ role: "executive_sup" })).toBe(true);
    expect(isApproverUser({ role: "supervisor" })).toBe(true);
    expect(isApproverUser({ role: "executive" })).toBe(true);
    expect(isApproverUser({ role: "requestor" })).toBe(false);
    expect(isCustodianUser({ is_active: true })).toBe(true);
    expect(isCustodianUser({ is_active: false })).toBe(false);
  });

  test("filters department group members to eligible unassigned users", () => {
    const users = [
      { id: "requestor-a", role: "requestor", department_id: "dept-a" },
      { id: "requestor-b", role: "requestor", department_id: "dept-a" },
      { id: "executive-a", role: "executive", department_id: "dept-a" },
      { id: "supervisor-a", role: "supervisor", department_id: "dept-a" },
      { id: "manager-a", role: "manager_ops", department_id: "dept-a" },
      { id: "requestor-c", role: "requestor", department_id: "dept-b" },
    ];
    const groups = [{ id: "group-1", member_ids: ["requestor-a"] }];

    expect(
      getAvailableDepartmentGroupMembers(users, "dept-a", groups).map((u) => u.id),
    ).toEqual(["requestor-b", "executive-a"]);
  });

  test("normalizes department groups for editing by dropping stale invalid members", () => {
    const users = [
      { id: "requestor-a", role: "requestor", department_id: "dept-a", is_active: true },
      { id: "approver-a", role: "approver", department_id: "dept-a", is_active: true },
      { id: "executive-a", role: "executive", department_id: "dept-a", is_active: true },
      { id: "manager-a", role: "manager_ops", department_id: "dept-a", is_active: true },
      { id: "inactive-a", role: "requestor", department_id: "dept-a", is_active: false },
      { id: "requestor-b", role: "requestor", department_id: "dept-b", is_active: true },
    ];
    const groups = [
      {
        id: "group-a",
        name: "Team A",
        supervisor_id: "supervisor-a",
        member_ids: [
          "requestor-a",
          "approver-a",
          "executive-a",
          "manager-a",
          "inactive-a",
          "requestor-b",
          "missing-user",
        ],
      },
    ];

    expect(getEditableDepartmentGroups(users, "dept-a", groups)[0].member_ids).toEqual([
      "requestor-a",
      "approver-a",
      "executive-a",
    ]);
  });

  test("labels special approver placeholders", () => {
    expect(getSpecialApproverLabel("immediate_manager")).toBe("Immediate Manager");
    expect(getSpecialApproverLabel("immediate_supervisor")).toBe("Immediate Supervisor");
    expect(getSpecialApproverLabel("user-1")).toBe("");
  });

  test("keeps recent local template changes when a stale refresh arrives", () => {
    const staleServerTemplates = [
      {
        id: "template-1",
        approver_chain: [{ step: 1, user_id: "old-approver" }],
        updated_at: "2026-05-21T00:00:00+00:00",
      },
    ];
    const localChanges = [
      {
        id: "template-1",
        item: {
          id: "template-1",
          approver_chain: [{ step: 1, user_id: "new-approver" }],
          updated_at: "2026-05-21T00:01:00+00:00",
        },
        changedAt: 1000,
      },
    ];

    expect(
      mergeServerItemsWithLocalChanges(staleServerTemplates, localChanges, {
        now: 1500,
        ttlMs: 90000,
      }),
    ).toEqual([
      {
        id: "template-1",
        approver_chain: [{ step: 1, user_id: "new-approver" }],
        updated_at: "2026-05-21T00:01:00+00:00",
      },
    ]);
  });

  test("keeps recent local removals when a stale refresh reintroduces an item", () => {
    expect(
      mergeServerItemsWithLocalChanges(
        [{ id: "template-1", name: "Deleted template" }],
        [{ id: "template-1", deleted: true, changedAt: 1000 }],
        { now: 1500, ttlMs: 90000 },
      ),
    ).toEqual([]);
  });
});
