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
  return ["approver", "both", "manager", "super_admin"].includes(user?.role);
}

export function isCustodianUser(user) {
  return user?.is_active !== false;
}
