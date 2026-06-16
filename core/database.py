"""SQLite storage with product-aware schema."""

import sqlite_utils
from pathlib import Path
from datetime import datetime, timezone

DATA_DIR = Path(__file__).parent.parent / "data"


def get_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db = sqlite_utils.Database(str(DATA_DIR / "marketeye.db"))
    _ensure_tables(db)
    return db


def _ensure_tables(db):
    if "products" not in db.table_names():
        db["products"].create(
            {
                "id": int,
                "name": str,
                "product_url": str,
                "store_name": str,
                "sku": str,
                "selector_price": str,
                "selector_title": str,
                "selector_stock": str,
                "check_interval_minutes": int,
                "alert_email": str,
                "alert_webhook": str,
                "enabled": int,
                "created_at": str,
            },
            pk="id",
        )
    if "price_snapshots" not in db.table_names():
        db["price_snapshots"].create(
            {
                "id": int,
                "product_id": int,
                "price": float,
                "currency": str,
                "title": str,
                "in_stock": int,
                "raw_hash": str,
                "fetched_at": str,
            },
            pk="id",
            foreign_keys=[("product_id", "products", "id")],
        )
    if "alerts" not in db.table_names():
        db["alerts"].create(
            {
                "id": int,
                "product_id": int,
                "alert_type": str,
                "message": str,
                "old_value": str,
                "new_value": str,
                "created_at": str,
            },
            pk="id",
            foreign_keys=[("product_id", "products", "id")],
        )
    db.conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_snap_pid_time "
        "ON price_snapshots(product_id, fetched_at)"
    )
    db.conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_alerts_pid "
        "ON alerts(product_id)"
    )


def add_product(name, url, store_name="", sku="",
                selector_price="", selector_title="", selector_stock="",
                interval=60, alert_email="", alert_webhook=""):
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    return db["products"].insert({
        "name": name,
        "product_url": url,
        "store_name": store_name,
        "sku": sku,
        "selector_price": selector_price,
        "selector_title": selector_title,
        "selector_stock": selector_stock,
        "check_interval_minutes": interval,
        "alert_email": alert_email,
        "alert_webhook": alert_webhook,
        "enabled": 1,
        "created_at": now,
    })


def get_products():
    return list(get_db()["products"].rows)


def get_product(product_id):
    return get_db()["products"].get(product_id)


def toggle_product(product_id, enabled=None):
    db = get_db()
    p = db["products"].get(product_id)
    if enabled is None:
        enabled = 0 if p["enabled"] else 1
    db["products"].update(product_id, {"enabled": enabled})
    return enabled


def delete_product(product_id):
    db = get_db()
    db["price_snapshots"].delete_where("product_id = ?", [product_id])
    db["alerts"].delete_where("product_id = ?", [product_id])
    db["products"].delete(product_id)


def save_snapshot(product_id, price, currency="¥", title="", in_stock=None, raw_hash=""):
    db = get_db()
    return db["price_snapshots"].insert({
        "product_id": product_id,
        "price": price,
        "currency": currency,
        "title": title,
        "in_stock": 1 if in_stock else 0,
        "raw_hash": raw_hash,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    })


def get_snapshots(product_id, limit=50):
    return list(get_db().query(
        "SELECT * FROM price_snapshots WHERE product_id=? ORDER BY fetched_at DESC LIMIT ?",
        [product_id, limit],
    ))


def get_latest_snapshot(product_id):
    rows = list(get_db().query(
        "SELECT * FROM price_snapshots WHERE product_id=? ORDER BY fetched_at DESC LIMIT 1",
        [product_id],
    ))
    return rows[0] if rows else None


def get_price_history(product_id, limit=100):
    """Get price snapshots oldest-first for charting."""
    return list(get_db().query(
        "SELECT * FROM price_snapshots WHERE product_id=? ORDER BY fetched_at ASC LIMIT ?",
        [product_id, limit],
    ))


def save_alert(product_id, alert_type, message, old_val="", new_val=""):
    db = get_db()
    return db["alerts"].insert({
        "product_id": product_id,
        "alert_type": alert_type,
        "message": message,
        "old_value": old_val,
        "new_value": new_val,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


def get_alerts(limit=50):
    return list(get_db().query(
        """SELECT a.*, p.name as product_name
           FROM alerts a LEFT JOIN products p ON a.product_id = p.id
           ORDER BY a.created_at DESC LIMIT ?""",
        [limit],
    ))


def get_stats():
    db = get_db()
    products = list(db["products"].rows)
    total = len(products)
    enabled = sum(1 for p in products if p["enabled"])
    snapshots = list(db.query("SELECT COUNT(*) as c FROM price_snapshots"))[0]["c"]
    alerts_count = list(db.query("SELECT COUNT(*) as c FROM alerts"))[0]["c"]
    return {
        "total_products": total,
        "enabled": enabled,
        "total_snapshots": snapshots,
        "total_alerts": alerts_count,
    }
