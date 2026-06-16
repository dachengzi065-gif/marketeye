"""FastAPI web dashboard for MarketEye."""

from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.responses import PlainTextResponse, StreamingResponse

from core import database as db
from core.engine import check_product, check_all_products
from web.export import export_products_csv, export_price_history_json, generate_report

HERE = Path(__file__).parent

app = FastAPI(title="MarketEye", version="1.0.0")


@app.get("/", response_class=HTMLResponse)
async def index():
    products = db.get_products()
    alerts_list = db.get_alerts(limit=20)
    stats = db.get_stats()
    return HTMLResponse(_render_index(products, alerts_list, stats))


@app.post("/products/add")
async def add_product(
    name: str = Form(),
    url: str = Form(),
    store_name: str = Form(default=""),
    sku: str = Form(default=""),
    selector_price: str = Form(default=""),
    selector_title: str = Form(default=""),
    selector_stock: str = Form(default=""),
    interval: int = Form(default=60),
    alert_email: str = Form(default=""),
    alert_webhook: str = Form(default=""),
):
    db.add_product(name, url, store_name, sku,
                   selector_price, selector_title, selector_stock,
                   interval, alert_email, alert_webhook)
    return RedirectResponse("/", status_code=303)


@app.post("/products/{pid}/toggle")
async def toggle_product(pid: int):
    db.toggle_product(pid)
    return RedirectResponse("/", status_code=303)


@app.post("/products/{pid}/check")
async def check_product_now(pid: int):
    await check_product(pid)
    return RedirectResponse("/", status_code=303)


@app.post("/products/{pid}/delete")
async def delete_product(pid: int):
    db.delete_product(pid)
    return RedirectResponse("/", status_code=303)


@app.post("/check-all")
async def check_all():
    await check_all_products()
    return RedirectResponse("/", status_code=303)


@app.get("/products/{pid}", response_class=HTMLResponse)
async def product_detail(pid: int):
    product = db.get_product(pid)
    if not product:
        return HTMLResponse("Product not found", status_code=404)
    snaps = db.get_snapshots(pid, limit=100)
    history = db.get_price_history(pid)
    return HTMLResponse(_render_detail(product, snaps, history))


@app.get("/export/csv")
async def export_csv():
    csv_data = export_products_csv()
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=marketeye_products.csv"},
    )


@app.get("/export/product/{pid}/json")
async def export_product_json(pid: int):
    data = export_price_history_json(pid)
    return StreamingResponse(
        iter([data]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=product_{pid}_history.json"},
    )


@app.get("/export/report")
async def export_report():
    return PlainTextResponse(generate_report(), media_type="text/plain")


# ── HTML Renderers ──────────────────────────────────────────────

PAGE_STYLE = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f0f2f5;color:#1a1a2e;padding:24px;max-width:1100px;margin:0 auto}
h1{font-size:1.6rem;font-weight:700;margin-bottom:4px;display:flex;align-items:center;gap:8px}
h1 span.sub{font-size:0.9rem;font-weight:400;color:#666}
.card{background:#fff;border-radius:12px;padding:20px;margin-bottom:16px;box-shadow:0 1px 4px rgba(0,0,0,0.06)}
.card h2{font-size:1.1rem;font-weight:600;margin-bottom:12px;color:#1a1a2e}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px}
.stat{text-align:center;padding:12px}
.stat .num{font-size:1.8rem;font-weight:700;color:#2563eb}
.stat .label{font-size:0.8rem;color:#888;margin-top:2px}
table{width:100%;border-collapse:collapse}
th,td{padding:10px 8px;text-align:left;border-bottom:1px solid #eef0f4;font-size:0.88rem}
th{font-weight:600;color:#666;font-size:0.8rem;text-transform:uppercase}
.btn{display:inline-block;padding:5px 14px;border-radius:6px;border:none;cursor:pointer;font-size:0.83rem;text-decoration:none;font-weight:500}
.btn-primary{background:#2563eb;color:#fff}
.btn-danger{background:#ef4444;color:#fff}
.btn-warn{background:#f59e0b;color:#fff}
.btn-sm{padding:3px 10px;font-size:0.78rem}
.btn-outline{background:transparent;border:1px solid #d0d5dd;color:#444}
input,select{padding:7px 10px;border:1px solid #d0d5dd;border-radius:6px;font-size:0.88rem;width:100%}
label{display:block;font-size:0.8rem;color:#666;margin-top:10px;font-weight:500}
.form-row{display:flex;gap:10px}
.form-row>*{flex:1}
.badge{display:inline-block;padding:2px 10px;border-radius:12px;font-size:0.72rem;font-weight:600}
.badge-green{background:#dcfce7;color:#16a34a}
.badge-yellow{background:#fef3c7;color:#d97706}
.badge-gray{background:#f3f4f6;color:#9ca3af}
.price-up{color:#ef4444;font-weight:600}
.price-down{color:#16a34a;font-weight:600}
.mono{font-family:'SF Mono',Consolas,monospace;font-size:0.8rem;color:#666;word-break:break-all}
.alert-item{padding:8px 0;border-bottom:1px solid #f3f4f6;font-size:0.85rem}
.alert-time{color:#999;font-size:0.75rem}
.toolbar{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}
.actions{display:flex;gap:6px}
.form-section{margin-bottom:4px}
.header-bar{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px}
"""


def _render_index(products, alerts, stats):
    prod_rows = "\n".join(_product_row(p) for p in products) if products else _empty_row()
    alert_html = "\n".join(_alert_item(a) for a in alerts) if alerts else '<div style="color:#999;padding:12px;text-align:center">暂无告警</div>'

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MarketEye — 竞品价格监控</title>
<style>{PAGE_STYLE}</style>
</head>
<body>

<div class="header-bar">
<h1>🏪 MarketEye <span class="sub">竞品价格监控 · v1.0</span></h1>
<div class="actions">
<form method="post" action="/check-all" style="margin:0"><button class="btn btn-primary btn-sm">▶ 全部检查</button></form>
</div>
</div>

<!-- Stats -->
<div class="card">
<div class="grid">
<div class="stat"><div class="num">{stats['total_products']}</div><div class="label">监控商品</div></div>
<div class="stat"><div class="num">{stats['enabled']}</div><div class="label">运行中</div></div>
<div class="stat"><div class="num">{stats['total_snapshots']}</div><div class="label">价格快照</div></div>
<div class="stat"><div class="num">{stats['total_alerts']}</div><div class="label">告警记录</div></div>
</div>
</div>

<!-- Add product form -->
<div class="card">
<h2>➕ 添加监控商品</h2>
<form method="post" action="/products/add">
<div class="form-row">
<div><label>商品名称 *</label><input name="name" required placeholder="例如: iPhone 16 Pro"></div>
<div><label>商品URL *</label><input name="url" required placeholder="https://..."></div>
</div>
<div class="form-row">
<div><label>店铺名称</label><input name="store_name" placeholder="京东/淘宝/Amazon"></div>
<div><label>SKU/货号</label><input name="sku" placeholder="可选"></div>
<div><label>检查间隔(分钟)</label><input name="interval" type="number" value="60" min="5"></div>
</div>
<details style="margin-top:8px">
<summary style="cursor:pointer;font-size:0.85rem;color:#2563eb">高级设置 (CSS选择器)</summary>
<div class="form-row" style="margin-top:8px">
<div><label>价格选择器</label><input name="selector_price" placeholder=".price, .sale-price"></div>
<div><label>标题选择器</label><input name="selector_title" placeholder=".product-title h1"></div>
<div><label>库存选择器</label><input name="selector_stock" placeholder=".stock-status"></div>
</div>
</details>
<div class="form-row" style="margin-top:8px">
<div><label>告警邮箱</label><input name="alert_email" type="email" placeholder="your@email.com (可选)"></div>
<div><label>Webhook URL</label><input name="alert_webhook" placeholder="https://hooks.example.com/alert (可选)"></div>
</div>
<p style="margin-top:12px"><button class="btn btn-primary" type="submit">➕ 添加</button></p>
</form>
</div>

<!-- Product list -->
<div class="card">
<div class="toolbar">
<h2>📋 监控列表</h2>
<div class="actions">
<a href="/export/csv" class="btn btn-outline btn-sm">📥 CSV</a>
<a href="/export/report" class="btn btn-outline btn-sm">📄 报告</a>
</div>
</div>
<table>
<thead><tr><th>商品</th><th>店铺</th><th>状态</th><th>最新价格</th><th>间隔</th><th>操作</th></tr></thead>
<tbody>{prod_rows}</tbody>
</table>
</div>

<!-- Recent alerts -->
<div class="card">
<h2>🔔 最近告警</h2>
<div style="max-height:300px;overflow-y:auto">{alert_html}</div>
</div>

</body>
</html>"""


def _product_row(p):
    enabled = p["enabled"]
    status = '<span class="badge badge-green">运行中</span>' if enabled else '<span class="badge badge-gray">已暂停</span>'
    snap = db.get_latest_snapshot(p["id"])
    price_str = ""
    if snap and snap.get("price") is not None:
        cur = snap.get("currency", "¥") or "¥"
        price_str = f'<span style="font-weight:600">{cur}{snap["price"]:.2f}</span>'
        # Show trend
        prev2 = db.get_snapshots(p["id"], limit=2)
        if len(prev2) >= 2:
            if prev2[0].get("price") and prev2[1].get("price"):
                diff = prev2[0]["price"] - prev2[1]["price"]
                if diff > 0.01:
                    price_str += f' <span class="price-up">↑{diff:.2f}</span>'
                elif diff < -0.01:
                    price_str += f' <span class="price-down">↓{abs(diff):.2f}</span>'
    else:
        price_str = '<span class="mono">--</span>'
    store = p.get("store_name") or '-'
    interval = f"{p['check_interval_minutes']}m"

    return f"""<tr>
<td><a href="/products/{p['id']}" style="color:#2563eb;text-decoration:none;font-weight:500">{p['name']}</a></td>
<td>{store}</td>
<td>{status}</td>
<td>{price_str}</td>
<td>{interval}</td>
<td class="actions">
<form method="post" action="/products/{p['id']}/toggle" style="display:inline">
{"<button class='btn btn-warn btn-sm'>暂停</button>" if enabled else "<button class='btn btn-primary btn-sm'>启用</button>"}</form>
<form method="post" action="/products/{p['id']}/check" style="display:inline"><button class="btn btn-sm btn-outline">检查</button></form>
<form method="post" action="/products/{p['id']}/delete" style="display:inline" onsubmit="return confirm('确定删除 {p['name']} 的所有数据？')"><button class="btn btn-danger btn-sm">删除</button></form>
</td>
</tr>"""


def _empty_row():
    return '<tr><td colspan="6" style="text-align:center;padding:30px;color:#999">暂无商品，在上方添加</td></tr>'


def _alert_item(a):
    t = a["created_at"][:19].replace("T", " ")
    badge = ""
    if a["alert_type"] == "price_change":
        badge = '<span class="badge badge-yellow">价格</span>'
    elif a["alert_type"] == "stock_change":
        badge = '<span class="badge badge-green">库存</span>'
    return f'<div class="alert-item">{badge} <span class="alert-time">{t}</span> <strong>{a["product_name"] or "?"}</strong> — {a["message"]}</div>'


def _render_detail(product, snaps, history):
    rows = "\n".join(_snap_row(s) for s in snaps) if snaps else '<tr><td colspan="5" style="text-align:center;padding:20px;color:#999">暂无数据</td></tr>'
    chart = _price_chart(history)
    latest = snaps[0] if snaps else None
    price_cur = f"¥{latest['price']:.2f}" if latest and latest.get("price") else "暂无"
    stock_str = "✅ 有货" if latest and latest.get("in_stock") else ("❌ 缺货" if latest else "未知")
    status_badge = '<span class="badge badge-green">运行中</span>' if product["enabled"] else '<span class="badge badge-gray">已暂停</span>'

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{product['name']} — MarketEye</title>
<style>{PAGE_STYLE}
.price-big{{font-size:2rem;font-weight:700;color:#1a1a2e}}
.grid-2{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
@media(max-width:640px){{.grid-2{{grid-template-columns:1fr}}}}
.info-label{{font-size:0.78rem;color:#888;display:block}}
.info-val{{font-weight:500;margin-top:2px}}
.chart{{display:flex;align-items:end;gap:4px;padding:16px 0;overflow-x:auto;min-height:160px}}
.chart-bar{{border-radius:4px 4px 0 0;min-width:28px;transition:height 0.3s}}
</style>
</head>
<body>

<p style="margin-bottom:12px"><a href="/" style="color:#2563eb;text-decoration:none">← 返回监控列表</a></p>

<div class="card">
<div style="display:flex;justify-content:space-between;align-items:start;flex-wrap:wrap;gap:12px">
<div>
<h1 style="font-size:1.4rem;margin-bottom:4px">🏷️ {product['name']}</h1>
<p class="mono">{product['product_url']}</p>
</div>
<div style="text-align:right">{status_badge}</div>
</div>
</div>

<div class="grid-2">
<div class="card">
<div class="info-label">当前价格</div>
<div class="price-big">{price_cur}</div>
<div class="info-label" style="margin-top:8px">库存状态</div>
<div style="font-size:1rem">{stock_str}</div>
</div>
<div class="card">
<div class="grid">
<div><div class="info-label">店铺</div><div class="info-val">{product.get('store_name') or '-'}</div></div>
<div><div class="info-label">SKU</div><div class="info-val">{product.get('sku') or '-'}</div></div>
<div><div class="info-label">检查间隔</div><div class="info-val">{product['check_interval_minutes']} 分钟</div></div>
<div><div class="info-label">快照数</div><div class="info-val">{len(snaps)}</div></div>
</div>
</div>
</div>

<div class="card">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
<h2>📈 价格走势</h2>
<a href="/export/product/{product['id']}/json" class="btn btn-outline btn-sm">📥 JSON导出</a>
</div>
{chart}
</div>

<div class="card">
<h2>📋 历史快照</h2>
<table>
<thead><tr><th>时间</th><th>价格</th><th>库存</th><th>标题</th><th>Hash</th></tr></thead>
<tbody>{rows}</tbody>
</table>
</div>

</body>
</html>"""


def _snap_row(s):
    t = s["fetched_at"][:19].replace("T", " ")
    price = f'¥{s["price"]:.2f}' if s.get("price") else "-"
    stock = "✅" if s.get("in_stock") else ("❌" if s.get("in_stock") == 0 else "?")
    title = s.get("title", "")[:50] or "-"
    h = s.get("raw_hash", "")[:12] or "-"
    return f'<tr><td class="mono">{t}</td><td style="font-weight:600">{price}</td><td>{stock}</td><td class="mono">{title}</td><td class="mono">{h}</td></tr>'


def _price_chart(history):
    priced = [h for h in history if h.get("price") is not None]
    if len(priced) < 2:
        return '<p style="color:#999;padding:12px">数据不足，至少需要2个价格点才能绘制走势图</p>'

    prices = [h["price"] for h in priced]
    min_p = min(prices)
    max_p = max(prices)
    rng = max_p - min_p if max_p > min_p else 1

    bars = []
    step = max(1, len(priced) // 20)  # max 20 bars
    for i in range(0, len(priced), step):
        h = priced[i]
        pct = ((h["price"] - min_p) / rng) * 120 + 10
        color = "#ef4444" if i > 0 and h["price"] > priced[i - 1]["price"] else "#16a34a"
        bars.append(
            f'<div style="display:flex;flex-direction:column;align-items:center;gap:2px">'
            f'<span style="font-size:0.65rem;color:#888">¥{h["price"]:.1f}</span>'
            f'<div class="chart-bar" style="height:{pct:.0f}px;width:24px;background:{color}" '
            f'title="{h["fetched_at"][:19]} ¥{h["price"]:.2f}"></div>'
            f'<span style="font-size:0.6rem;color:#aaa">{h["fetched_at"][11:16]}</span>'
            f'</div>'
        )

    return f'<div class="chart">{"".join(bars)}</div>'
