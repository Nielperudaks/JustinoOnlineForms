export const ADMIN_METADATA_EVENT = "ADMIN_METADATA_CHANGED";

export function shouldRefreshAdminData({ event, payload, user }) {
  if (event !== ADMIN_METADATA_EVENT || !user) {
    return false;
  }

  if (user.role === "super_admin") {
    return true;
  }

  if (user.role !== "manager") {
    return false;
  }

  return !payload?.department_id || payload.department_id === user.department_id;
}
