#!/usr/bin/env python3
"""MarketEye — E-Commerce Competitor Price Monitoring.

Usage:
    python run.py           # Web dashboard + background scheduler
    python run.py --daemon  # Headless mode (just scheduler)
    python run.py --once    # Check all products once, then exit
    python run.py --setup   # Run setup wizard

First time: python setup.py
"""

import sys
import asyncio
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger("marketeye")


def main():
    # First run detection
    data_dir = Path(__file__).parent / "data"
    config_file = data_dir / "config.json"
    if not config_file.exists() and "--setup" not in sys.argv:
        logger.info("首次运行，请先执行: python setup.py")
        logger.info("或者: python run.py --setup")
        return

    if "--setup" in sys.argv:
        from setup import interactive_setup
        interactive_setup()
        return

    if "--once" in sys.argv:
        asyncio.run(run_once())
        return

    if "--daemon" in sys.argv:
        run_daemon()
        return

    start_web()


async def run_once():
    from core.engine import check_all_products
    logger.info("检查所有商品...")
    results = await check_all_products()
    changed = [r for r in results if r.has_changes]
    logger.info(f"检查完成: {len(results)} 个商品, {len(changed)} 个有变化")
    for r in changed:
        parts = []
        if r.price_changed:
            parts.append(f"价格: {r.old_price} → {r.new_price}")
        if r.stock_changed:
            parts.append(f"库存: {'有货' if r.in_stock else '缺货'}")
        logger.info(f"  [{r.product_name}] {' | '.join(parts)}")


def run_daemon():
    from core.scheduler import start_scheduler
    logger.info("🏪 MarketEye 守护模式启动...")
    sched = start_scheduler()
    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        sched.shutdown()


def start_web():
    import uvicorn
    import webbrowser
    from threading import Timer
    from setup import load_config
    from core.scheduler import start_scheduler

    cfg = load_config()
    port = cfg.get("port", 9199)

    start_scheduler()

    if cfg.get("open_browser", True):
        Timer(1.5, lambda: webbrowser.open(f"http://localhost:{port}")).start()

    logger.info(f"🏪 MarketEye — http://localhost:{port}")
    uvicorn.run(
        "web.dashboard:app",
        host="127.0.0.1",
        port=port,
        log_level="info",
        reload=False,
    )


if __name__ == "__main__":
    main()
