import { isApproverRole } from "../lib/roles";

export function upsertById(items, item) {
  if (!item?.id) {
    return items;
  }

  const index = items.findIndex((existing) => existing.id === item.id);
  if (index === -1) {
    return [item, ...items];
  }

  return items.map((existing) => (existing.id === item.id ? item : existing));
}

export function removeById(items, id) {
  return items.filter((item) => item.id !== id);
}

export function isApproverUser(user) {
  return isApproverRole(user?.role);
}

export function isCustodianUser(user) {
  return user?.is_active !== false;
}

const GROUP_MEMBER_EXCLUDED_ROLES = new Set([
  "supervisor",
  "manager",
  "manager_ops",
  "manager_sup",
  "executive_ops",
  "executive_sup",
  "super_admin",
]);

export function getAvailableDepartmentGroupMembers(
  users,
  departmentId,
  groups,
  currentGroupId = null,
) {
  const assignedMemberIds = new Set();

  for (const group of groups || []) {
    if (currentGroupId && group.id === currentGroupId) {
      continue;
    }
    for (const memberId of group.member_ids || []) {
      assignedMemberIds.add(memberId);
    }
  }

  return (users || []).filter(
    (user) =>
      user.department_id === departmentId &&
      user.is_active !== false &&
      !GROUP_MEMBER_EXCLUDED_ROLES.has(user.role) &&
      !assignedMemberIds.has(user.id),
  );
}

export function getEditableDepartmentGroups(users, departmentId, groups) {
  return (groups || []).map((group) => {
    const eligibleMemberIds = new Set(
      getAvailableDepartmentGroupMembers(
        users,
        departmentId,
        groups,
        group.id,
      ).map((user) => user.id),
    );

    return {
      ...group,
      member_ids: (group.member_ids || []).filter((memberId) =>
        eligibleMemberIds.has(memberId),
      ),
    };
  });
}

export function getSpecialApproverLabel(userId) {
  if (userId === "immediate_manager") return "Immediate Manager";
  if (userId === "immediate_supervisor") return "Immediate Supervisor";
  return "";
}

function itemVersion(item) {
  const value = item?.updated_at || item?.created_at || "";
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? 0 : parsed;
}

export function mergeServerItemsWithLocalChanges(
  serverItems,
  localChanges,
  { now = Date.now(), ttlMs = 90000 } = {},
) {
  const activeChanges = (localChanges || []).filter(
    (change) => change?.id && now - change.changedAt <= ttlMs,
  );
  if (!activeChanges.length) {
    return serverItems;
  }

  const changesById = new Map(activeChanges.map((change) => [change.id, change]));
  const seenIds = new Set();
  const merged = [];

  for (const serverItem of serverItems) {
    const change = changesById.get(serverItem.id);
    seenIds.add(serverItem.id);

    if (change?.deleted) {
      continue;
    }

    if (
      change?.item &&
      (itemVersion(serverItem) < itemVersion(change.item) || itemVersion(change.item) === 0)
    ) {
      merged.push(change.item);
      continue;
    }

    merged.push(serverItem);
  }

  for (const change of activeChanges) {
    if (!change.deleted && change.item && !seenIds.has(change.id)) {
      merged.unshift(change.item);
    }
  }

  return merged;
}
