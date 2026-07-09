PERMISSION_ORDER = {
    "public": 0,
    "free": 1,
    "paid": 2,
    "internal": 3,
    "restricted": 4,
}

USER_LEVEL = {
    "visitor": "public",
    "free": "free",
    "paid": "paid",
    "internal": "internal",
    "admin": "restricted",
}

INGEST_ROLES = {
    "none": {"can_upload": False, "max_permission": None},
    "contributor": {"can_upload": True, "max_permission": "paid"},
    "internal_uploader": {"can_upload": True, "max_permission": "internal"},
    "admin": {"can_upload": True, "max_permission": "restricted"},
}


def normalize_user_type(user_type: str) -> str:
    return user_type if user_type in USER_LEVEL else "visitor"


def normalize_ingest_role(role: str) -> str:
    return role if role in INGEST_ROLES else "none"


def can_access(user_type: str, permission_level: str) -> bool:
    user_type = normalize_user_type(user_type)
    user_level = USER_LEVEL[user_type]
    return PERMISSION_ORDER[user_level] >= PERMISSION_ORDER.get(permission_level, 0)


def can_ingest(role: str) -> bool:
    role = normalize_ingest_role(role)
    return INGEST_ROLES[role]["can_upload"]


def can_assign_permission(role: str, permission_level: str) -> bool:
    role = normalize_ingest_role(role)
    max_permission = INGEST_ROLES[role]["max_permission"]
    if max_permission is None:
        return False
    return PERMISSION_ORDER.get(permission_level, 0) <= PERMISSION_ORDER[max_permission]


def permission_notice(blocked_count: int) -> str:
    if blocked_count <= 0:
        return ""
    return f"另有 {blocked_count} 条资料因权限不足未展示，可联系管理员开通更高权限。"
