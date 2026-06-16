"""Monitoring engine: orchestrates scraping, storage, and alerts."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from . import database as db
from .scraper import fetch_page, extract_product_page

logger = logging.getLogger("marketeye.engine")


class CheckResult:
    """Result of one product check."""
    def __init__(self, product_id: int, product_name: str):
        self.product_id = product_id
        self.product_name = product_name
        self.price_changed = False
        self.stock_changed = False
        self.content_changed = False
        self.old_price: Optional[float] = None
        self.new_price: Optional[float] = None
        self.currency = "¥"
        self.in_stock = True
        self.alerts_sent = 0
        self.error: Optional[str] = None

    @property
    def has_changes(self) -> bool:
        return self.price_changed or self.stock_changed or self.content_changed


async def check_product(product_id: int) -> CheckResult:
    """Check one product: fetch, parse, compare, alert."""
    product = db.get_product(product_id)
    if not product:
        result = CheckResult(product_id, "?")
        result.error = "Product not found"
        return result

    result = CheckResult(product_id, product["name"])

    html = await fetch_page(product["product_url"])
    if html is None:
        result.error = "Failed to fetch page"
        return result

    page = extract_product_page(
        html,
        product["product_url"],
        product.get("selector_price", "") or "",
        product.get("selector_title", "") or "",
        product.get("selector_stock", "") or "",
    )

    prev = db.get_latest_snapshot(product_id)
    price_val = page.price if page.price is not None else (prev["price"] if prev else None)

    # Save snapshot regardless
    db.save_snapshot(
        product_id,
        price_val,
        currency=page.currency,
        title=page.title,
        in_stock=page.in_stock,
        raw_hash=page.raw_hash,
    )

    result.new_price = price_val
    result.currency = page.currency
    result.in_stock = page.in_stock

    if prev:
        result.old_price = prev.get("price")

        # Stock change
        if prev.get("in_stock") is not None and prev["in_stock"] != (1 if page.in_stock else 0):
            result.stock_changed = True
            status = "✅ 有货" if page.in_stock else "❌ 缺货"
            msg = f"[{product['name']}] 库存状态变更: {status}"
            db.save_alert(product_id, "stock_change", msg,
                          old_val=str(prev["in_stock"]), new_val=str(1 if page.in_stock else 0))
            logger.info(msg)
            result.alerts_sent += 1

        # Price change (threshold 0.5% to filter noise)
        if (prev.get("price") and price_val is not None
                and abs(price_val - prev["price"]) / max(prev["price"], 0.01) > 0.005):
            result.price_changed = True
            direction = "📈" if price_val > prev["price"] else "📉"
            msg = f"[{product['name']}] 价格变动 {direction}: {prev['price']} → {price_val}"
            db.save_alert(product_id, "price_change", msg,
                          old_val=str(prev["price"]), new_val=str(price_val))
            logger.info(msg)
            result.alerts_sent += 1

        # Content change (title/product page changed significantly)
        if prev.get("raw_hash") and prev["raw_hash"] != page.raw_hash:
            result.content_changed = True

    # Webhook alerts
    if product.get("alert_webhook") and (result.price_changed or result.stock_changed):
        _ = asyncio.create_task(
            _dispatch_webhook(product["alert_webhook"], {
                "type": "price_change" if result.price_changed else "stock_change",
                "product": product["name"],
                "url": product["product_url"],
                "old_price": str(result.old_price or ""),
                "new_price": str(result.new_price or ""),
            })
        )

    # Email alerts
    if product.get("alert_email") and (result.price_changed or result.stock_changed):
        _ = asyncio.create_task(
            _dispatch_email(product["alert_email"], product["name"], result)
        )

    return result


async def check_all_products() -> list[CheckResult]:
    """Check all enabled products."""
    products = db.get_products()
    results = []
    for p in products:
        if not p["enabled"]:
            continue
        try:
            r = await check_product(p["id"])
            results.append(r)
        except Exception as e:
            logger.error(f"[{p['name']}] Error: {e}")
            r = CheckResult(p["id"], p["name"])
            r.error = str(e)
            results.append(r)
    return results


async def _dispatch_webhook(url: str, payload: dict):
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(url, json=payload)
    except Exception:
        pass


async def _dispatch_email(email: str, product_name: str, result: CheckResult):
    """Placeholder for email dispatch. Will implement SMTP support."""
    logger.info(f"[EMAIL] Would send to {email} about {product_name} changes")
