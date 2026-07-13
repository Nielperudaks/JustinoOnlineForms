// Core roles form a fixed departmental hierarchy: Requestor -> Supervisor ->
// Manager -> Executive. Approval routing is resolved from per-department
// assignments (executive/manager/supervisor groups), not from role names.
export const ROLE_OPTIONS = [
  { value: "requestor", label: "Requestor" },
  { value: "both", label: "Requestor and Approver" },
  { value: "supervisor", label: "Supervisor" },
  { value: "manager", label: "Manager" },
  { value: "executive", label: "Executive" },
  { value: "super_admin", label: "Super Admin" },
];

// Legacy role values that may still exist on older user records. They behave
// as aliases of the core manager/executive roles.
const LEGACY_ROLE_LABELS = {
  approver: "Approver (Legacy)",
  manager_ops: "Manager (OPS) (Legacy)",
  manager_sup: "Manager (SUP) (Legacy)",
  executive_ops: "Executive (OPS) (Legacy)",
  executive_sup: "Executive (SUP) (Legacy)",
};

export const LEGACY_MANAGER_ROLES = ["manager_ops", "manager_sup"];
export const LEGACY_EXECUTIVE_ROLES = ["executive_ops", "executive_sup"];
export const MANAGER_ROLES = ["manager", ...LEGACY_MANAGER_ROLES];
export const EXECUTIVE_ROLES = ["executive", ...LEGACY_EXECUTIVE_ROLES];
export const FORM_MANAGER_ROLES = MANAGER_ROLES;
export const APPROVER_ROLES = [
  "approver",
  "both",
  "supervisor",
  "super_admin",
  ...MANAGER_ROLES,
  ...EXECUTIVE_ROLES,
];
export const REQUESTOR_ROLES = [
  "requestor",
  "both",
  "supervisor",
  "super_admin",
  ...MANAGER_ROLES,
  ...EXECUTIVE_ROLES,
];

export function isSuperAdminRole(role) {
  return role === "super_admin";
}

export function isManagerRole(role) {
  return MANAGER_ROLES.includes(role);
}

export function isExecutiveRole(role) {
  return EXECUTIVE_ROLES.includes(role);
}

export function isSupervisorRole(role) {
  return role === "supervisor";
}

export function isApproverRole(role) {
  return APPROVER_ROLES.includes(role);
}

export function isRequestorRole(role) {
  return REQUESTOR_ROLES.includes(role);
}

export function getRoleLabel(role) {
  return (
    ROLE_OPTIONS.find((option) => option.value === role)?.label ||
    LEGACY_ROLE_LABELS[role] ||
    role?.replace("_", " ") ||
    ""
  );
}
