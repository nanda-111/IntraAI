"""关键操作审计日志写入。"""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.user import User


def _dump(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        return str(value)


def log_action(
    db: Session,
    operator: User | None,
    action: str,
    target_type: str | None = None,
    target_id: str | int | None = None,
    before: object | None = None,
    after: object | None = None,
    reason: str | None = None,
    commit: bool = True,
) -> AuditLog:
    """写入审计记录。默认立即提交，确保关键操作留痕。"""
    record = AuditLog(
        operator_id=operator.id if operator else None,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        before_value=_dump(before),
        after_value=_dump(after),
        reason=reason,
    )
    db.add(record)
    if commit:
        db.commit()
    return record
