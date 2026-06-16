# MarketEye 🏪 — Self-Hosted Competitor Price Monitor

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-green)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)]()

**MarketEye** monitors e-commerce product prices automatically and alerts you when things change.  
Self-hosted, unlimited products, no monthly fees.

> 💡 I built this because Prisync costs $99/month and I'm too cheap to pay that.  
> Now it's open source. If you want the easy packaged version → [Gumroad ($49)](https://gumroad.com/l/kvnkhb)

---

## ✨ What It Does

- Drop any product URL → **auto price tracking**
- Email & webhook alerts on price drops / stock changes
- Price history charts 📈
- CSV / JSON data export
- Works with **Amazon, JD.com, Taobao, Shopify** — any HTML product page
- Built-in Chinese e-commerce support (¥ prices auto-detected)

## 🧰 Tech Stack

| Component | What |
|-----------|------|
| Language | Python 3.8+ |
| Web Framework | FastAPI + Jinja2 |
| Database | SQLite |
| Scraping | httpx + BeautifulSoup |
| Scheduler | APScheduler |
| Alerts | SMTP email + Webhooks |

## 🚀 Quick Start

```bash
git clone https://github.com/dachengzi065-gif/marketeye.git
cd marketeye
pip install -r requirements.txt
python setup.py
python run.py
```

Then open **http://localhost:9199** in your browser.

### Docker (coming soon)

```bash
docker pull dachengzi065-gif/marketeye
docker run -p 9199:9199 marketeye
```

## 📸 Screenshots

![Dashboard](https://via.placeholder.com/800x450?text=Dashboard+Preview)
![Price Chart](https://via.placeholder.com/800x450?text=Price+History+Chart)

## 🏗️ Project Structure

```
marketeye/
├── run.py              # Entry point
├── setup.py            # Initial setup wizard
├── requirements.txt    # Python dependencies
├── core/
│   ├── scraper.py      # Web scraping engine
│   ├── engine.py       # Monitoring engine
│   ├── scheduler.py    # Background scheduler
│   └── database.py     # SQLite data layer
├── web/
│   ├── dashboard.py    # FastAPI web dashboard
│   └── export.py       # CSV/JSON/report export
├── alerts/
│   └── email_sender.py # SMTP email alerts
└── tools/              # Utility scripts
```

## ⚙️ Configuration

Edit `data/config.json` (auto-created after first `python setup.py`):

```json
{
  "port": 9199,
  "check_interval_minutes": 60,
  "smtp_host": "",
  "smtp_port": 587,
  "smtp_user": "",
  "smtp_password": ""
}
```

## 🌍 Supported Sites

Any HTML-based product page works, including:
- **Amazon** (.com, .co.jp, .de, .co.uk...)
- **JD.com** / **JD Global**
- **Taobao** / **Tmall**
- **Shopify** stores
- **eBay**, **Walmart**, **Best Buy**
- Any site with visible price text in HTML

### Custom CSS Selectors

If the auto-detection doesn't work, you can specify custom CSS selectors for price, title, and stock status when adding a product.

## 🤝 Contributing

PRs welcome! Ideas:

- Dockerfile
- More site-specific scrapers (plugins)
- Prometheus / Grafana integration
- Telegram / Discord bot alerts
- Price prediction (ML-based)

## 📜 License

MIT — use it, modify it, sell it. Attribution appreciated but not required.

## ☕ Support

- [GitHub Issues](https://github.com/dachengzi065-gif/marketeye/issues) — bug reports & feature requests
- [Gumroad ($49)](https://gumroad.com/l/kvnkhb) — packaged download + email support
