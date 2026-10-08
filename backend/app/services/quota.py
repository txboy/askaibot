from datetime import datetime, time

from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models
from ..common import get_setting


def effective_token_limit(db: Session, user: models.User) -> int | None:
    """对单个用户取有效每日 token 限额：个人 > 部门 > 系统，取第一个正数；全空返回 None。"""
    if user and user.token_limit_daily:
        return user.token_limit_daily
    if user and user.department_id:
        dept = db.get(models.Department, user.department_id)
        if dept and dept.token_limit_daily:
            return dept.token_limit_daily
    setting = get_setting(db)
    if setting and setting.token_limit_daily:
        return setting.token_limit_daily
    return None


def used_tokens_today(db: Session, user_id: int) -> int:
    """统计该用户今日（本地零点起）所有会话消费的 token 总量。"""
    today_start = datetime.combine(datetime.now().date(), time.min)
    total = (
        db.query(func.coalesce(func.sum(models.Message.tokens), 0))
        .join(
            models.Conversation,
            models.Message.conversation_id == models.Conversation.id,
        )
        .filter(
            models.Conversation.user_id == user_id,
            models.Message.created_at >= today_start,
        )
        .scalar()
    )
    return int(total or 0)


def token_limit_status(db: Session, user: models.User) -> dict:
    """返回当前用户额度状态：limit/used/remaining（不限额时 limit=None）。"""
    limit = effective_token_limit(db, user)
    used = used_tokens_today(db, user.id)
    remaining = max(0, limit - used) if limit is not None else None
    return {"limit": limit, "used": used, "remaining": remaining}
