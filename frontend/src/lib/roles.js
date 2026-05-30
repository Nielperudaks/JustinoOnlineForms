export const ROLE_OPTIONS = [
  { value: "requestor", label: "Requestor" },
  { value: "approver", label: "Approver" },
  { value: "both", label: "Both" },
  { value: "manager_ops", label: "Manager (OPS)" },
  { value: "manager_sup", label: "Manager (SUP)" },
  { value: "executive_ops", label: "Executive (OPS)" },
  { value: "executive_sup", label: "Executive (SUP)" },
  { value: "super_admin", label: "Super Admin" },
];

export const MANAGER_ROLES = ["manager_ops", "manager_sup"];
export const LEGACY_MANAGER_ROLES = ["manager"];
export const FORM_MANAGER_ROLES = [...MANAGER_ROLES, ...LEGACY_MANAGER_ROLES];
export const APPROVER_ROLES = [
  "approver",
  "both",
  "manager",
  "manager_ops",
  "manager_sup",
  "executive_ops",
  "executive_sup",
  "super_admin",
];
export const REQUESTOR_ROLES = ["requestor", "both", "manager_ops", "manager_sup", "super_admin"];

export function isSuperAdminRole(role) {
  return role === "super_admin";
}

export function isManagerRole(role) {
  return FORM_MANAGER_ROLES.includes(role);
}

export function isApproverRole(role) {
  return APPROVER_ROLES.includes(role);
}

export function isRequestorRole(role) {
  return REQUESTOR_ROLES.includes(role);
}

export function getRoleLabel(role) {
  return ROLE_OPTIONS.find((option) => option.value === role)?.label || role?.replace("_", " ") || "";
}
