"""Data export and report generation."""

import csv
import json
import io
from datetime import datetime, timezone

from core import database as db


def export_products_csv() -> str:
    products = db.get_products()
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["ID", "商品名称", "URL", "店铺", "SKU", "最新价格", "货币", "有货", "检查间隔(m)", "状态", "快照数"])
    for p in products:
        snap = db.get_latest_snapshot(p["id"])
        price = f'{snap["price"]:.2f}' if snap and snap.get("price") else ""
        currency = snap.get("currency", "¥") if snap else ""
        in_stock = "是" if snap and snap.get("in_stock") else "否"
        snaps = len(db.get_snapshots(p["id"]))
        status = "运行中" if p["enabled"] else "已暂停"
        w.writerow([p["id"], p["name"], p["product_url"], p.get("store_name", ""),
                     p.get("sku", ""), price, currency, in_stock,
                     p["check_interval_minutes"], status, snaps])
    return out.getvalue()


def export_price_history_json(product_id: int) -> str:
    product = db.get_product(product_id)
    snaps = db.get_snapshots(product_id, limit=200)
    data = {
        "product": {
            "id": product["id"],
            "name": product["name"],
            "url": product["product_url"],
            "store": product.get("store_name", ""),
            "sku": product.get("sku", ""),
        },
        "snapshots": [
            {
                "time": s["fetched_at"],
                "price": s.get("price"),
                "currency": s.get("currency", "¥"),
                "in_stock": bool(s.get("in_stock")),
                "title": s.get("title", ""),
            }
            for s in snaps
        ],
        "total_snapshots": len(snaps),
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def generate_report() -> str:
    products = db.get_products()
    alerts = db.get_alerts(limit=15)
    stats = db.get_stats()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        "=" * 55,
        f"  MarketEye Report — {now}",
        "=" * 55,
        "",
        f"  监控商品: {stats['total_products']}  |  运行中: {stats['enabled']}  |  快照: {stats['total_snapshots']}  |  告警: {stats['total_alerts']}",
        "",
        "─" * 55,
        "  商品概览",
        "─" * 55,
    ]

    for p in products:
        snap = db.get_latest_snapshot(p["id"])
        price = f"¥{snap['price']:.2f}" if snap and snap.get("price") else "N/A"
        stock = "有货" if snap and snap.get("in_stock") else ("缺货" if snap else "未知")
        status = "●" if p["enabled"] else "○"
        store = p.get("store_name", "")
        store_str = f" [{store}]" if store else ""
        lines.append(f"  {status} {p['name']}{store_str}")
        lines.append(f"     价格: {price}  |  库存: {stock}  |  URL: {p['product_url']}")

    lines += ["", "─" * 55, "  最近告警", "─" * 55]
    for a in alerts:
        t = a["created_at"][:19].replace("T", " ")
        lines.append(f"  {t} | {a.get('product_name', '?')} — {a['message']}")

    lines.append("\n" + "=" * 55)
    return "\n".join(lines)
