# Core roles form a fixed departmental hierarchy. Who actually approves a
# request is resolved at request time from per-department assignments
# (department executive/manager/supervisor groups), not from role names.
REQUESTOR = "requestor"
BOTH = "both"  # Requestor and Approver
SUPERVISOR = "supervisor"
MANAGER = "manager"
EXECUTIVE = "executive"
SUPER_ADMIN = "super_admin"

# Legacy role values that may still exist on user documents. They keep
# working as aliases of the core manager/executive roles.
LEGACY_MANAGER_ROLES = {"manager_ops", "manager_sup"}
LEGACY_EXECUTIVE_ROLES = {"executive_ops", "executive_sup"}

MANAGER_ROLES = {MANAGER} | LEGACY_MANAGER_ROLES
EXECUTIVE_ROLES = {EXECUTIVE} | LEGACY_EXECUTIVE_ROLES

# Roles allowed to manage forms for their department.
FORM_MANAGER_ROLES = MANAGER_ROLES

REQUESTOR_ROLES = {REQUESTOR, BOTH, SUPERVISOR, SUPER_ADMIN} | MANAGER_ROLES | EXECUTIVE_ROLES
APPROVER_ROLES = {"approver", BOTH, SUPERVISOR, SUPER_ADMIN} | MANAGER_ROLES | EXECUTIVE_ROLES

# Managerial hierarchy levels used to resolve role-based approval steps.
# A head at level N approves requestors below level N.
SUPERVISOR_LEVEL = 1
MANAGER_LEVEL = 2
EXECUTIVE_LEVEL = 3


def hierarchy_level(role):
    """Managerial level of a role: 0 for non-managerial requestors/approvers."""
    if role == SUPERVISOR:
        return SUPERVISOR_LEVEL
    if role in MANAGER_ROLES:
        return MANAGER_LEVEL
    if role in EXECUTIVE_ROLES:
        return EXECUTIVE_LEVEL
    return 0


def role_of(user):
    return (user or {}).get("role", "")


def user_hierarchy_level(user):
    return hierarchy_level(role_of(user))


def is_super_admin(user):
    return role_of(user) == SUPER_ADMIN


def is_manager_role(role):
    return role in MANAGER_ROLES


def is_manager(user):
    return is_manager_role(role_of(user))


def is_executive_role(role):
    return role in EXECUTIVE_ROLES


def is_supervisor_role(role):
    return role == SUPERVISOR


def is_approval_capable(user):
    return role_of(user) in APPROVER_ROLES


def is_requestor_capable(user):
    return role_of(user) in REQUESTOR_ROLES
