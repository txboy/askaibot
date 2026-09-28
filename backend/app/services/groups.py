"""用户组与按组授权工具：组成员查询、资源可见性过滤、组授权读写。

资源类型(resource_type)取值：endpoint / knowledge_base / mcp / search / skill。
- 资源可见规则：scope=global 对所有人可见；scope=group 仅对所在组被授权的用户可见。
- 搜索为单例资源（resource_type=search, resource_id=0），开关式授权。
"""

from sqlalchemy.orm import Session

from app import models

RESOURCE_TYPES = {"endpoint", "knowledge_base", "mcp", "search", "skill"}


def user_group_ids(db: Session, user_id: int | None) -> list[int]:
    """返回用户所属的所有组 id（支持一个用户多个组）。"""
    if not user_id:
        return []
    return [
        m.group_id
        for m in db.query(models.UserGroupMember)
        .filter(models.UserGroupMember.user_id == user_id)
        .all()
    ]


def _granted_ids(db: Session, group_ids: list[int], resource_type: str) -> set[int]:
    if not group_ids:
        return set()
    return {
        g.resource_id
        for g in db.query(models.GroupGrant)
        .filter(
            models.GroupGrant.group_id.in_(group_ids),
            models.GroupGrant.resource_type == resource_type,
        )
        .all()
    }


def accessible_ids(db: Session, user_id: int | None, resource_type: str) -> set[int]:
    """返回用户可用的 'group' 范围资源 id 集合（不含 global 项）。"""
    return _granted_ids(db, user_group_ids(db, user_id), resource_type)


def filter_accessible(
    db: Session, user_id: int | None, resource_type: str, rows
) -> list:
    """过滤出当前用户可见的资源：scope=global 全部可见，或所在组已授权。"""
    granted = accessible_ids(db, user_id, resource_type)
    out = []
    for r in rows:
        scope = getattr(r, "scope", "global")
        if scope == "global" or getattr(r, "id", None) in granted:
            out.append(r)
    return out


def is_accessible(
    db: Session,
    user_id: int | None,
    resource_type: str,
    resource_id: int,
    scope: str,
) -> bool:
    """判断单个资源对用户是否可见。"""
    if scope == "global":
        return True
    return resource_id in accessible_ids(db, user_id, resource_type)


def group_ids_for_resource(
    db: Session | None, resource_type: str, resource_id: int
) -> list[int]:
    """读取某资源被授权给哪些组。"""
    if not db:
        return []
    return [
        g.group_id
        for g in db.query(models.GroupGrant)
        .filter(
            models.GroupGrant.resource_type == resource_type,
            models.GroupGrant.resource_id == resource_id,
        )
        .all()
    ]


def set_resource_grants(db: Session, resource_type: str, resource_id: int, group_ids) -> None:
    """写入某资源授权的组集合（先删后插）。"""
    db.query(models.GroupGrant).filter(
        models.GroupGrant.resource_type == resource_type,
        models.GroupGrant.resource_id == resource_id,
    ).delete(synchronize_session=False)
    for gid in group_ids or []:
        db.add(
            models.GroupGrant(
                group_id=int(gid),
                resource_type=resource_type,
                resource_id=int(resource_id),
            )
        )


def can_search(db: Session, user_id: int | None, setting: models.Setting) -> bool:
    """判断用户是否可用联网搜索：provider 已配置，且 scope 非 group 或所在组被授予搜索。"""
    if not setting.search_provider:
        return False
    scope = getattr(setting, "search_scope", "global") or "global"
    if scope == "global":
        return True
    return bool(_granted_ids(db, user_group_ids(db, user_id), "search"))
