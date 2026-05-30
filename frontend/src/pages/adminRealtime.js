import { isManagerRole, isSuperAdminRole } from "../lib/roles";

export const ADMIN_METADATA_EVENT = "ADMIN_METADATA_CHANGED";

export function shouldRefreshAdminData({ event, payload, user }) {
  if (event !== ADMIN_METADATA_EVENT || !user) {
    return false;
  }

  if (isSuperAdminRole(user.role)) {
    return true;
  }

  if (!isManagerRole(user.role)) {
    return false;
  }

  return !payload?.department_id || payload.department_id === user.department_id;
}
