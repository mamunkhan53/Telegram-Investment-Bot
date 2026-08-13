from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.admin.auth.security import read_session_cookie
from app.config.settings import Settings
from app.database.models import InvestmentPlan, User, Withdrawal
from app.database.models.enums import PlanStatus, WithdrawalStatus
from app.database.session import transaction
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/v1/admin", tags=["admin-resources"])


class PlanCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str = Field(pattern=r"^[a-z0-9-]{2,140}$")
    description: str | None = None
    minimum_amount: Decimal = Field(gt=0)
    maximum_amount: Decimal | None = Field(default=None, gt=0)
    duration_days: int = Field(gt=0, le=3650)
    profit_rate: Decimal = Field(ge=0, le=1000)
    auto_reinvest_allowed: bool = False


def _require_admin(request: Request) -> str:
    settings: Settings = request.app.state.settings
    username = read_session_cookie(settings, request.cookies.get("admin_session"))
    if not username:
        raise HTTPException(status_code=401, detail="Admin authentication required")
    return username


@router.get("/users")
async def list_users(request: Request, limit: int = 50, offset: int = 0) -> list[dict]:
    _require_admin(request)
    limit = max(1, min(limit, 200))
    async with transaction() as session:
        result = await session.execute(
            select(User)
            .order_by(User.created_at.desc())
            .limit(limit)
            .offset(max(offset, 0))
        )
        users = result.scalars().all()
    return [
        {
            "id": str(user.id),
            "telegram_user_id": user.telegram_user_id,
            "username": user.username,
            "status": user.status.value,
            "created_at": user.created_at.isoformat(),
        }
        for user in users
    ]


@router.get("/plans")
async def list_plans(request: Request) -> list[dict]:
    _require_admin(request)
    async with transaction() as session:
        result = await session.execute(
            select(InvestmentPlan).order_by(
                InvestmentPlan.sort_order, InvestmentPlan.name
            )
        )
        plans = result.scalars().all()
    return [
        {
            "id": str(plan.id),
            "name": plan.name,
            "slug": plan.slug,
            "status": plan.status.value,
            "minimum_amount": str(plan.minimum_amount),
            "maximum_amount": str(plan.maximum_amount)
            if plan.maximum_amount is not None
            else None,
            "duration_days": plan.duration_days,
            "profit_rate": str(plan.profit_rate),
        }
        for plan in plans
    ]


@router.post("/plans", status_code=201)
async def create_plan(request: Request, payload: PlanCreateRequest) -> dict:
    username = _require_admin(request)
    if (
        payload.maximum_amount is not None
        and payload.maximum_amount < payload.minimum_amount
    ):
        raise HTTPException(
            status_code=422, detail="maximum_amount must be at least minimum_amount"
        )
    async with transaction() as session:
        plan = InvestmentPlan(
            name=payload.name,
            slug=payload.slug,
            description=payload.description,
            minimum_amount=payload.minimum_amount,
            maximum_amount=payload.maximum_amount,
            duration_days=payload.duration_days,
            profit_rate=payload.profit_rate,
            auto_reinvest_allowed=payload.auto_reinvest_allowed,
            status=PlanStatus.DRAFT,
        )
        session.add(plan)
        await session.flush()
        await AuditService(session).record(
            action="admin.plan.created",
            entity_type="investment_plan",
            entity_id=str(plan.id),
            payload={"admin_username": username, "slug": plan.slug},
        )
    return {"id": str(plan.id), "status": plan.status.value}


@router.get("/withdrawals")
async def list_withdrawals(request: Request, limit: int = 50) -> list[dict]:
    _require_admin(request)
    async with transaction() as session:
        result = await session.execute(
            select(Withdrawal)
            .where(
                Withdrawal.status.in_(
                    [
                        WithdrawalStatus.REQUESTED,
                        WithdrawalStatus.APPROVED,
                        WithdrawalStatus.PROCESSING,
                        WithdrawalStatus.FAILED,
                    ]
                )
            )
            .order_by(Withdrawal.requested_at.desc())
            .limit(max(1, min(limit, 200)))
        )
        withdrawals = result.scalars().all()
    return [
        {
            "id": str(item.id),
            "user_id": str(item.user_id),
            "amount": str(item.amount),
            "fee": str(item.fee),
            "destination_address": item.destination_address,
            "status": item.status.value,
            "requested_at": item.requested_at.isoformat(),
        }
        for item in withdrawals
    ]
