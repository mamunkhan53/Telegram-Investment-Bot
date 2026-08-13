from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select

from app.admin.auth.security import (
    create_session_cookie,
    read_session_cookie,
    verify_password,
)
from app.config.settings import Settings
from app.database.models import InvestmentPlan, User, Withdrawal
from app.database.models.enums import PlanStatus, WithdrawalStatus
from app.database.session import transaction
from app.utils.logger import get_logger

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/admin/templates")
logger = get_logger(__name__)


def _settings(request: Request) -> Settings:
    return request.app.state.settings


def _authenticated_admin(request: Request) -> str | None:
    return read_session_cookie(_settings(request), request.cookies.get("admin_session"))


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if _authenticated_admin(request):
        return RedirectResponse("/admin", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    settings = _settings(request)
    expected_hash = (
        settings.admin_password_hash.get_secret_value()
        if settings.admin_password_hash
        else ""
    )
    if (
        username != settings.admin_username
        or not expected_hash
        or not verify_password(password, expected_hash)
    ):
        logger.warning("Admin login failed", extra={"username": username})
        return templates.TemplateResponse(
            request, "login.html", {"error": "Invalid credentials."}, status_code=401
        )
    response = RedirectResponse("/admin", status_code=303)
    response.set_cookie(
        "admin_session",
        create_session_cookie(settings, username),
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
        max_age=8 * 60 * 60,
    )
    logger.info("Admin login succeeded", extra={"username": username})
    return response


@router.post("/logout")
async def logout():
    response = RedirectResponse("/admin/login", status_code=303)
    response.delete_cookie("admin_session")
    return response


@router.get("", response_class=HTMLResponse)
async def dashboard(request: Request):
    username = _authenticated_admin(request)
    if not username:
        return RedirectResponse("/admin/login", status_code=303)
    async with transaction() as session:
        user_count = await session.scalar(select(func.count(User.id)))
        plan_count = await session.scalar(
            select(func.count(InvestmentPlan.id)).where(
                InvestmentPlan.status == PlanStatus.ACTIVE
            )
        )
        pending_withdrawals = await session.scalar(
            select(func.count(Withdrawal.id)).where(
                Withdrawal.status.in_(
                    [
                        WithdrawalStatus.REQUESTED,
                        WithdrawalStatus.APPROVED,
                        WithdrawalStatus.PROCESSING,
                    ]
                )
            )
        )
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "admin_username": username,
            "user_count": user_count or 0,
            "plan_count": plan_count or 0,
            "pending_withdrawals": pending_withdrawals or 0,
        },
    )
