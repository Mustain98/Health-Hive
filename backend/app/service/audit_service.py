from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from sqlmodel import Session

from app.models.consultant_access import UserHealthChangeAudit, AuditAction, AuditResource


def _utc_now():
    return datetime.now(timezone.utc)


def log_health_change(
    session: Session,
    *,
    user_id: int,
    changed_by_user_id: int,
    resource: AuditResource,
    action: AuditAction,
    before: Optional[Any],
    after: Optional[Any],
    appointment_id: Optional[int] = None,
) -> UserHealthChangeAudit:
    entry = UserHealthChangeAudit(
        user_id=user_id,
        changed_by_user_id=changed_by_user_id,
        resource=resource,
        action=action,
        before_json=None if before is None else json.dumps(before, default=str),
        after_json=None if after is None else json.dumps(after, default=str),
        appointment_id=appointment_id,
        created_at=_utc_now(),
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry
