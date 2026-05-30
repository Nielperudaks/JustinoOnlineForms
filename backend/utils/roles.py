MANAGER_OPS = "manager_ops"
MANAGER_SUP = "manager_sup"
EXECUTIVE_OPS = "executive_ops"
EXECUTIVE_SUP = "executive_sup"
LEGACY_MANAGER = "manager"
SUPER_ADMIN = "super_admin"

REQUESTOR_ROLES = {"requestor", "both", MANAGER_OPS, MANAGER_SUP, SUPER_ADMIN}
MANAGER_ROLES = {MANAGER_OPS, MANAGER_SUP}
FORM_MANAGER_ROLES = MANAGER_ROLES | {LEGACY_MANAGER}
EXECUTIVE_ROLES = {EXECUTIVE_OPS, EXECUTIVE_SUP}
APPROVER_ROLES = {"approver", "both", SUPER_ADMIN} | FORM_MANAGER_ROLES | EXECUTIVE_ROLES

EXECUTIVE_BY_MANAGER_ROLE = {
    MANAGER_OPS: EXECUTIVE_OPS,
    MANAGER_SUP: EXECUTIVE_SUP,
}


def role_of(user):
    return (user or {}).get("role", "")


def is_super_admin(user):
    return role_of(user) == SUPER_ADMIN


def is_manager_role(role):
    return role in FORM_MANAGER_ROLES


def is_manager(user):
    return is_manager_role(role_of(user))


def is_approval_capable(user):
    return role_of(user) in APPROVER_ROLES


def is_requestor_capable(user):
    return role_of(user) in REQUESTOR_ROLES


def executive_role_for_manager(user):
    return EXECUTIVE_BY_MANAGER_ROLE.get(role_of(user))
