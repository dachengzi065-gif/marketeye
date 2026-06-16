#!/usr/bin/env python3
"""MarketEye Setup Wizard — first-run configuration.

Usage:
    python setup.py        # Interactive setup
    python setup.py --auto # Quick setup with defaults
"""

import sys
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")

DATA_DIR = Path(__file__).parent / "data"


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    if "--auto" in sys.argv:
        auto_setup()
    else:
        interactive_setup()


def auto_setup():
    """Quick setup with minimal prompts."""
    port = 9199
    config = {
        "port": port,
        "scheduler_interval": 30,
        "dashboard": True,
    }
    _write_config(config)
    print(f"\n✅ MarketEye 已配置完毕")
    print(f"   Dashboard: http://localhost:{port}")
    print(f"   启动命令: python run.py\n")


def interactive_setup():
    """Interactive setup wizard."""
    print("\n" + "=" * 50)
    print("  🏪 MarketEye 设置向导")
    print("=" * 50)
    print()
    print("  本向导将帮你配置 MarketEye 的基本设置。")
    print("  你可以随时通过修改 data/config.json 来调整。\n")

    # Port
    port_input = input("  Dashboard端口 [9199]: ").strip()
    port = int(port_input) if port_input.isdigit() else 9199

    # Scheduler
    sched_input = input("  调度检查间隔(秒) [30]: ").strip()
    sched = int(sched_input) if sched_input.isdigit() else 30

    # Auto-start browser
    browser = input("  启动时自动打开浏览器? [Y/n]: ").strip().lower()
    open_browser = browser != "n"

    config = {
        "port": port,
        "scheduler_interval": sched,
        "open_browser": open_browser,
        "dashboard": True,
    }

    _write_config(config)
    print("\n" + "=" * 50)
    print(f"  ✅ MarketEye 配置完成!")
    print(f"  🌐 Dashboard: http://localhost:{port}")
    print(f"  ⏱  检查间隔: {sched}s")
    print(f"  🚀 启动命令: python run.py")
    print("=" * 50 + "\n")


def _write_config(config):
    with open(DATA_DIR / "config.json", "w") as f:
        json.dump(config, f, indent=2)


def load_config() -> dict:
    cfg_path = DATA_DIR / "config.json"
    defaults = {"port": 9199, "scheduler_interval": 30, "open_browser": True, "dashboard": True}
    if cfg_path.exists():
        try:
            with open(cfg_path) as f:
                return {**defaults, **json.load(f)}
        except Exception:
            pass
    return defaults


if __name__ == "__main__":
    main()
