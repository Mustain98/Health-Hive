import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.core.database import get_session
from app.core.auth import get_current_user
from app.modules.user.models import User
from app.modules.plan import service
from app.modules.plan.schemas import PlanCreate, PlanRename

router = APIRouter(prefix="/plans", tags=["Plans"])


@router.get("")
def list_plans(session: Session = Depends(get_session), me: User = Depends(get_current_user)):
    return service.list_plans(session, me.id)


@router.post("")
def create_plan(payload: PlanCreate, session: Session = Depends(get_session), me: User = Depends(get_current_user)):
    p = service.create_plan(session, me.id, payload.name, payload.source)
    return service.get_plan(session, me.id, p.id)


@router.get("/{plan_id}")
def get_plan(plan_id: uuid.UUID, session: Session = Depends(get_session), me: User = Depends(get_current_user)):
    return service.get_plan(session, me.id, plan_id)


@router.put("/{plan_id}")
def rename_plan(plan_id: uuid.UUID, payload: PlanRename, session: Session = Depends(get_session), me: User = Depends(get_current_user)):
    service.rename_plan(session, me.id, plan_id, payload.name)
    return service.get_plan(session, me.id, plan_id)


@router.patch("/{plan_id}/activate")
def activate_plan(plan_id: uuid.UUID, session: Session = Depends(get_session), me: User = Depends(get_current_user)):
    try:
        return service.activate_plan(session, me.id, plan_id)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to activate plan: {str(e)}")


@router.patch("/{plan_id}/deactivate")
def deactivate_plan(plan_id: uuid.UUID, session: Session = Depends(get_session), me: User = Depends(get_current_user)):
    return service.deactivate_plan(session, me.id, plan_id)


@router.delete("/{plan_id}")
def delete_plan(plan_id: uuid.UUID, session: Session = Depends(get_session), me: User = Depends(get_current_user)):
    service.delete_plan(session, me.id, plan_id)
    return {"ok": True}
