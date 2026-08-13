from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config.settings import Settings
from app.scheduler.deposit_checker import run_deposit_cycle
from app.scheduler.investment_scheduler import run_investment_cycle
from app.scheduler.notification_scheduler import run_notification_cycle
from app.scheduler.withdrawal_scheduler import run_withdrawal_cycle
from app.utils.logger import get_logger

logger = get_logger(__name__)


def build_scheduler(settings: Settings) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    if not settings.scheduler_enabled:
        return scheduler

    scheduler.add_job(
        run_deposit_cycle,
        "interval",
        seconds=settings.deposit_check_interval_seconds,
        args=[settings],
        id="deposit-monitor",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        run_investment_cycle,
        "interval",
        seconds=settings.investment_tick_interval_seconds,
        args=[settings],
        id="investment-accrual",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        run_withdrawal_cycle,
        "interval",
        seconds=settings.withdrawal_check_interval_seconds,
        args=[settings],
        id="withdrawal-queue",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        run_notification_cycle,
        "interval",
        seconds=settings.notification_check_interval_seconds,
        args=[settings],
        id="notification-queue",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    return scheduler


def start_scheduler(scheduler: AsyncIOScheduler) -> None:
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started", extra={"jobs": len(scheduler.get_jobs())})


def stop_scheduler(scheduler: AsyncIOScheduler) -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
