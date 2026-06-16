"""E-commerce-optimized web scraper.

Knows how to extract price, title, and stock status from
common e-commerce platforms automatically, with custom CSS
selector overrides for tricky sites.
"""

import hashlib
import re
import httpx
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import Optional


@dataclass
class ProductPage:
    url: str
    title: str
    price: Optional[float]
    currency: str
    in_stock: bool
    raw_text_snippet: str
    raw_hash: str


# ── Generic price extraction patterns ──────────────────────────

PRICE_PATTERNS = [
    # $499.99, ¥299, €49.99
    r"([\$\¥\€\£฿₩₽₹₪]\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?))",
    # 299.00元, 49.99 USD, 39,90€
    r"(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)\s*(元|块|美元|usd|eur|gbp|hkd|twd)",
    # Sale: $19.99
    r"(?:sale|price|特价|售价|价格)[:\s]*[\$\¥\€\£฿₩₽₹₪]\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)",
]

STOCK_PATTERNS = {
    "in_stock": [
        r"(?:in\s*stock|available|add\s*to\s*cart|buy\s*now|有货|现货|在售|立即购买|加入购物车)",
        r"stock\s*(?:#|number|no)[:\s]*\d+",
    ],
    "out_of_stock": [
        r"(?:out\s*of\s*stock|sold\s*out|unavailable|discontinued|暂时缺货|已售罄|无货|下架)",
    ],
}

CURRENCY_MAP = {
    "$": "USD", "¥": "CNY", "€": "EUR", "£": "GBP",
    "฿": "THB", "₩": "KRW", "₽": "RUB", "₹": "INR",
    "元": "CNY", "块": "CNY",
}


async def fetch_page(url: str, timeout: int = 30) -> Optional[str]:
    """Fetch HTML from a URL with a browser-like user-agent."""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/134.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.text
    except Exception:
        return None


def _extract_by_selector(soup: BeautifulSoup, selector: str) -> str:
    """Extract text by CSS selector. Returns '' if not found."""
    if not selector:
        return ""
    els = soup.select(selector)
    if not els:
        return ""
    return els[0].get_text(strip=True)


def _extract_price_from_text(text: str) -> Optional[float]:
    """Find first price in text. Returns float or None."""
    for pat in PRICE_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            raw = m.group(1) if pat.startswith(r"[\$") else m.group(0)
            # Clean up the number
            num_str = re.sub(r"[^\d.,]", "", raw)
            # Handle European style 1.234,56
            if "," in num_str and "." not in num_str:
                num_str = num_str.replace(",", ".")
            elif "," in num_str and "." in num_str:
                # Could be 1,234.56 (US) or 1.234,56 (EU)
                if num_str.rindex(",") > num_str.rindex("."):
                    num_str = num_str.replace(".", "").replace(",", ".")
            try:
                return float(num_str)
            except ValueError:
                continue
    return None


def _detect_currency(text: str) -> str:
    for sym, code in CURRENCY_MAP.items():
        if sym in text:
            return code
    return "CNY"


def _check_stock(text: str) -> bool:
    """Heuristic: return True if product appears in stock."""
    text_lower = text.lower()
    for pat in STOCK_PATTERNS["out_of_stock"]:
        if re.search(pat, text_lower):
            return False
    for pat in STOCK_PATTERNS["in_stock"]:
        if re.search(pat, text_lower):
            return True
    # Default: assume in stock
    return True


def _get_meta_title(soup: BeautifulSoup) -> str:
    t = soup.find("title")
    return t.get_text(strip=True)[:200] if t else ""


def extract_product_page(
    html: str,
    url: str,
    selector_price: str = "",
    selector_title: str = "",
    selector_stock: str = "",
) -> ProductPage:
    """Parse a product page and extract structured data."""
    soup = BeautifulSoup(html, "lxml")

    # Title
    title = ""
    if selector_title:
        title = _extract_by_selector(soup, selector_title)
    if not title:
        title = _get_meta_title(soup)

    # Price
    price = None
    price_text = ""
    if selector_price:
        price_text = _extract_by_selector(soup, selector_price)
    if not price_text:
        price_text = soup.get_text(strip=True)[:5000]
    price = _extract_price_from_text(price_text)

    # Stock
    in_stock = True
    if selector_stock:
        stock_text = _extract_by_selector(soup, selector_stock)
        in_stock = _check_stock(stock_text) if stock_text else True
    else:
        in_stock = _check_stock(soup.get_text(strip=True)[:3000])

    # Currency
    currency = _detect_currency(price_text or soup.get_text(strip=True)[:2000])

    # Content hash for change detection
    full_text = soup.get_text(strip=True)[:5000]
    raw_hash = hashlib.md5(full_text.encode("utf-8")).hexdigest()

    return ProductPage(
        url=url,
        title=title,
        price=price,
        currency=currency,
        in_stock=in_stock,
        raw_text_snippet=full_text[:300],
        raw_hash=raw_hash,
    )
