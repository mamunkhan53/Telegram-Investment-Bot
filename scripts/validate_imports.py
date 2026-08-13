from app.admin.admin import build_admin_router
from app.api.api import app
from app.blockchain.bsc import BSCUSDTAdapter
from app.bot.bot import build_dispatcher
from app.scheduler.runner import build_scheduler


def main() -> None:
    assert app.title == "Telegram Investment Platform API"
    assert build_admin_router().routes
    assert len(build_dispatcher().sub_routers) == 2
    assert build_scheduler
    assert BSCUSDTAdapter
    print("application imports: ok")


if __name__ == "__main__":
    main()
