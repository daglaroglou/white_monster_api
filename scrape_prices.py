import asyncio
import json
import os
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import requests

HISTORY_FILE = "price_history.json"
HISTORY_DAYS = 31

def parse_price_to_float(price_text):
    if not price_text: return None
    match = re.search(r"(\d+[.,]?\d*)", price_text)
    if not match: return None
    raw_price = match.group(1)
    value = float(raw_price.replace(",", "."))
    if ("." not in raw_price and "," not in raw_price) and 100 <= value < 10000:
        value = value / 100
    if value > 1000:
        value = value / 100
    return value

def _parse_24hr_price(price_text):
    if not price_text: return None
    cleaned = price_text.strip().replace("€", "").strip()
    match = re.search(r"(\d+[.,]\d{2})(?:\D|$)", cleaned)
    if match: return round(float(match.group(1).replace(",", ".")), 2)
    match = re.search(r"(\d+[.,]\d)(?:\D|$)", cleaned)
    if match: return round(float(f"{match.group(1).replace(',', '.')}0"), 2)
    parsed = parse_price_to_float(price_text)
    return round(parsed, 2) if parsed is not None else None

def _write_json_with_price_decimals(path, data):
    rendered = json.dumps(data, indent=2, ensure_ascii=False)
    rendered = re.sub(
        r'("price"\s*:\s*)(-?\d+(?:\.\d+)?)(?=\s*[,}\]])',
        lambda match: f"{match.group(1)}{float(match.group(2)):.2f}",
        rendered,
    )
    with open(path, "w", encoding="utf-8") as file:
        file.write(rendered)
        file.write("\n")

def _append_history_point(history_list, timestamp, price, extra=None):
    point = {"timestamp": timestamp, "price": round(price, 2)}
    if extra: point.update(extra)
    if history_list and history_list[-1].get("timestamp") == timestamp:
        history_list[-1] = point
    else:
        history_list.append(point)

def _parse_iso_timestamp(timestamp):
    if not timestamp: return None
    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except Exception:
        return None

def _rebuild_total_history(history):
    store_series = []
    all_timestamps = set()
    for store_data in history.get("stores", {}).values():
        if not isinstance(store_data, dict): continue
        series = []
        for point in store_data.get("history", []):
            if not isinstance(point, dict): continue
            timestamp = point.get("timestamp")
            price = point.get("price")
            point_dt = _parse_iso_timestamp(timestamp)
            if not timestamp or price is None or not point_dt: continue
            series.append((point_dt, timestamp, float(price)))
            all_timestamps.add(timestamp)
        if series:
            series.sort(key=lambda item: item[0])
            store_series.append(series)

    total_history = []
    for timestamp in sorted(all_timestamps, key=lambda ts: _parse_iso_timestamp(ts) or datetime.min):
        point_dt = _parse_iso_timestamp(timestamp)
        if not point_dt: continue
        prices = []
        for series in store_series:
            last_price = None
            for entry_dt, _, entry_price in series:
                if entry_dt <= point_dt:
                    last_price = entry_price
                else:
                    break
            if last_price is not None:
                prices.append(last_price)
        if prices:
            total_history.append({
                "timestamp": timestamp,
                "price": round(sum(prices) / len(prices), 2),
                "available_stores": len(prices),
            })
    history.setdefault("total", {"name": "Average Market Price", "history": []})
    history["total"]["history"] = total_history

def _collect_scrape_timestamps(history):
    timestamps = set()
    for store_data in history.get("stores", {}).values():
        if not isinstance(store_data, dict): continue
        for point in store_data.get("history", []):
            timestamp = point.get("timestamp")
            if timestamp: timestamps.add(timestamp)
    return sorted(timestamps, key=lambda ts: _parse_iso_timestamp(ts) or datetime.min)

def _backfill_store_history_gaps(history, store_id, fallback_price):
    scrape_timestamps = _collect_scrape_timestamps(history)
    if not scrape_timestamps or fallback_price is None: return
    store_history = history["stores"].get(store_id)
    if not isinstance(store_history, dict): return
    entries = store_history.setdefault("history", [])
    existing = {point.get("timestamp") for point in entries if point.get("timestamp")}
    fill_price = round(float(fallback_price), 2)
    for timestamp in scrape_timestamps:
        if timestamp in existing: continue
        entries.append({"timestamp": timestamp, "price": fill_price})
        existing.add(timestamp)
    entries.sort(key=lambda point: _parse_iso_timestamp(point.get("timestamp")) or datetime.min)

def _trim_history_window(history_list, reference_timestamp, days=HISTORY_DAYS):
    reference_dt = _parse_iso_timestamp(reference_timestamp)
    if not reference_dt: return
    cutoff = reference_dt - timedelta(days=days)
    filtered = []
    for point in history_list:
        point_dt = _parse_iso_timestamp(point.get("timestamp"))
        if point_dt and point_dt >= cutoff:
            filtered.append(point)
    history_list[:] = filtered

def _load_or_initialize_history(prices):
    stores = prices.get("stores", {})
    base_history = {
        "last_updated": prices.get("last_updated"),
        "product": prices.get("product", "Monster Energy Zero Ultra 500ml"),
        "currency": prices.get("currency", "EUR"),
        "total": {"name": "Average Market Price", "history": []},
        "stores": {}
    }
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                base_history.update({
                    "last_updated": loaded.get("last_updated", base_history["last_updated"]),
                    "product": loaded.get("product", base_history["product"]),
                    "currency": loaded.get("currency", base_history["currency"]),
                })
                total_block = loaded.get("total", {})
                if isinstance(total_block, dict):
                    base_history["total"] = {
                        "name": total_block.get("name", "Average Market Price"),
                        "history": total_block.get("history", []),
                    }
                loaded_stores = loaded.get("stores", {})
                if isinstance(loaded_stores, dict):
                    for store_id, store_data in loaded_stores.items():
                        if isinstance(store_data, dict):
                            base_history["stores"][store_id] = {
                                "name": store_data.get("name", store_id),
                                "history": store_data.get("history", []),
                            }
        except Exception as e:
            print(f"Warning: could not parse {HISTORY_FILE}, rebuilding it. ({e})")
    for store_id, store_data in stores.items():
        existing = base_history["stores"].get(store_id, {})
        base_history["stores"][store_id] = {
            "name": store_data.get("name", existing.get("name", store_id)),
            "history": existing.get("history", []),
        }
    return base_history

def update_price_history(prices):
    history = _load_or_initialize_history(prices)
    timestamp = prices.get("last_updated")
    if not timestamp: return
    for store_id, store_data in prices.get("stores", {}).items():
        price = store_data.get("price")
        if price is None or not store_data.get("available", True): continue
        store_history = history["stores"].setdefault(
            store_id, {"name": store_data.get("name", store_id), "history": []}
        )
        store_history["name"] = store_data.get("name", store_history.get("name", store_id))
        _append_history_point(store_history["history"], timestamp, price)
    for store_id, store_data in prices.get("stores", {}).items():
        price = store_data.get("price")
        if price is None or not store_data.get("available", True): continue
        _backfill_store_history_gaps(history, store_id, price)
    history["last_updated"] = timestamp
    history["product"] = prices.get("product", history.get("product"))
    history["currency"] = prices.get("currency", history.get("currency"))
    for store_data in history["stores"].values():
        if isinstance(store_data, dict):
            _trim_history_window(store_data.get("history", []), timestamp)
    _rebuild_total_history(history)
    _trim_history_window(history["total"]["history"], timestamp)
    _write_json_with_price_decimals(HISTORY_FILE, history)

# Scraping Handlers

async def masoutis(page):
    url = "https://www.masoutis.gr/categories/item/monster-energy-drink-ultra-zero-500ml?3205614="
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    el = await page.wait_for_selector(".item-price", timeout=10000)
    text = await el.inner_text()
    return float(text.split("€")[0].replace(',', '.'))

async def ab(page):
    url = "https://www.ab.gr/el/eshop/Kava-anapsyktika-nera-xiroi-karpoi/Anapsyktika/Energeiaka-Isotonika/Energeiako-Poto-Energy-Ultra-500ml/p/7289419"
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    container = await page.wait_for_selector("[data-testid='product-block-price']", timeout=10000)
    html = await container.inner_html()
    soup = BeautifulSoup(html, 'html.parser')
    all_divs = soup.find_all('div', attrs={'aria-hidden': 'true'})
    cents_sup = soup.find('sup', attrs={'aria-hidden': 'true'})
    if len(all_divs) >= 2 and cents_sup:
        main_price = all_divs[1].get_text(strip=True)
        cents = cents_sup.get_text(strip=True)
        return float(f"{main_price}.{cents}")
    return None

async def sklavenitis(page):
    url = "https://www.sklavenitis.gr/anapsyktika-nera-chymoi/energeiaka-pota-ice-tea-ice-coffee/energeiaka-isotonika-pota/monster-energy-zero-ultra-energeiako-poto-500ml/"
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    el = await page.wait_for_selector(".price", timeout=10000, state="attached")
    html = await page.content()
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    # Sklavenitis sometimes hides the price or has multiple. Find the one that matches 'price' exactly
    price_div = soup.find('div', class_='price')
    if price_div:
        return parse_price_to_float(price_div.get_text(strip=True))
    return None

async def kritikos(page):
    url = "https://kritikos-sm.gr/products/kaba/anapsuktika/energeiaka/monster-energy-zero-ultra-500ml-705294/"
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    # The selector requires matching 'ProductDetails_price__'
    html = await page.content()
    soup = BeautifulSoup(html, 'html.parser')
    price_element = soup.find('span', class_=lambda x: x and 'ProductDetails_price__' in x and 'grey' not in x.lower())
    if price_element:
        return parse_price_to_float(price_element.get_text(strip=True))
    return None

def _extract_mymarket_price(soup, page_source):
    for script_tag in soup.select("script[type='application/ld+json']"):
        raw_json = script_tag.get_text(strip=True)
        if not raw_json: continue
        try:
            payload = json.loads(raw_json)
        except Exception: continue
        nodes = []
        if isinstance(payload, dict) and isinstance(payload.get("@graph"), list):
            nodes = [node for node in payload["@graph"] if isinstance(node, dict)]
        elif isinstance(payload, dict): nodes = [payload]
        elif isinstance(payload, list): nodes = [node for node in payload if isinstance(node, dict)]
        for node in nodes:
            if node.get("@type") != "Product": continue
            offers = node.get("offers")
            if isinstance(offers, dict):
                schema_price = offers.get("price")
                parsed = parse_price_to_float(str(schema_price)) if schema_price is not None else None
                if parsed is not None: return parsed

    def is_per_unit(text):
        if not text: return False
        lower = text.lower()
        return any(x in lower for x in ['/l', '€/l', 'ltr', 'lt', 'λίτρο', '/lt', 'lt.', 'ανά λίτρο', 'ανά lt', 'ανά l', '€/lt', '€/λ', '/λ', 'ανά λ'])
    
    preferred_selectors = [".product-display-price", ".product-summary .selling-unit-row", "span.product-full--final-price", ".product-full--final-price", "span.product-full--price", "[data-testid='product-price']", "[data-testid='final-price']"]
    for sel in preferred_selectors:
        el = soup.select_one(sel)
        if not el: continue
        price_text = el.get_text(strip=True)
        if not price_text or is_per_unit(price_text): continue
        split_price_match = re.search(r"€?\s*(\d{1,2})\s+(\d{2})\b", price_text)
        if split_price_match:
            combined_price = f"{split_price_match.group(1)}.{split_price_match.group(2)}"
            return parse_price_to_float(combined_price)
        parsed = parse_price_to_float(price_text)
        if parsed is not None: return parsed

    for m in re.finditer(r"(\d+[.,]\d{1,2})\s*€", page_source):
        span_start = max(0, m.start() - 20)
        span_end = min(len(page_source), m.end() + 20)
        context = page_source[span_start:span_end].lower()
        if any(x in context for x in ['/l', '€/l', 'ltr', 'lt', 'λίτρο', 'ανά']): continue
        parsed = parse_price_to_float(m.group(1))
        if parsed is not None: return parsed
    return None

async def mymarket(page):
    url = "https://www.mymarket.gr/monster-energy-zero-ultra-500gr"
    await page.goto(url, wait_until="networkidle", timeout=60000)
    await page.wait_for_timeout(2500)
    
    # Dismiss popup if it exists
    locators = [
        "//button[contains(normalize-space(.), 'Όχι') and contains(normalize-space(.), 'ευχαριστ')]",
        "//button[contains(normalize-space(.), 'Οχι') and contains(normalize-space(.), 'ευχαριστ')]",
        "//*[@role='button' and contains(normalize-space(.), 'ευχαριστ')]",
        "button[class*='deny']", "button[class*='decline']", "button[class*='reject']"
    ]
    for locator in locators:
        try:
            el = await page.wait_for_selector(locator, timeout=500)
            if el:
                await el.click()
                break
        except Exception:
            pass

    page_source = await page.content()
    soup = BeautifulSoup(page_source, 'html.parser')
    return _extract_mymarket_price(soup, page_source)

async def galaxias(page):
    url = "https://galaxias.shop/product/5060337501125"
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    el = await page.wait_for_selector("span.fs-1.mr-2", timeout=10000)
    text = await el.inner_text()
    return parse_price_to_float(text)

async def bazaar(page):
    url = "https://www.bazaar-online.gr/monster-500ml-energy-zero-ultra?search=monster"
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    # Use locator.first to handle multiple matches where the first might be hidden or we just want the text
    el = page.locator(".new_price").first
    await el.wait_for(timeout=10000)
    text = await el.inner_text()
    return parse_price_to_float(text)

async def marketin(page):
    url = "https://www.market-in.gr/el-gr/kava-anapsuktika-xumoi-md-energeiaka-pota/monster-energy-zero-ultra-kouti-500ml"
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    el = await page.wait_for_selector(".p-price", timeout=10000)
    text = await el.inner_text()
    return parse_price_to_float(text)

async def hr24(page=None):
    url = "https://www.24hr.gr/el/%CF%80%CF%81%CE%BF%CF%8A%CF%8C%CE%BD%CF%84%CE%B1/energy/energy/monster-energy-%CE%B5%CE%BD%CE%B5%CF%81%CE%B3%CE%B5%CE%B9%CE%B1%CE%BA%CF%8C-%CF%80%CE%BF%CF%84%CF%8C-ultra-white-zero-sugar-500ml"
    try:
        response = await asyncio.to_thread(
            requests.get, url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}, timeout=30
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        price_element = soup.select_one("#das-product-details-price, .das-product-details-price-value")
        if price_element:
            parsed = _parse_24hr_price(price_element.get_text(strip=True))
            if parsed is not None: return parsed
        final_price_input = soup.select_one('input[name="final_price"][das-cart-key="final_price"]')
        if final_price_input and final_price_input.get("value"):
            return _parse_24hr_price(final_price_input["value"])
    except Exception as e:
        print(f"Error fetching 24hr.gr price: {e}")
    return None

async def fetch_store(context, store_id, store_name, scraper_func):
    page = await context.new_page()
    price = None
    try:
        price = await scraper_func(page)
    except Exception as e:
        print(f"Error fetching {store_name} price: {e}")
    finally:
        await page.close()
    
    if price is not None:
        print(f"{store_name}: €{price:.2f}")
    else:
        print(f"{store_name}: N/A")
        
    return store_id, store_name, price

async def main_async():
    print("Starting async price scraping...")
    
    prices = {
        "last_updated": datetime.now().isoformat(),
        "product": "Monster Energy Zero Ultra 500ml",
        "currency": "EUR",
        "stores": {}
    }
    
    stores = [
        ("masoutis", "Masoutis", masoutis),
        ("ab", "AB Vassilopoulos", ab),
        ("sklavenitis", "Sklavenitis", sklavenitis),
        ("kritikos", "Kritikos", kritikos),
        ("mymarket", "MyMarket", mymarket),
        ("galaxias", "Galaxias", galaxias),
        ("bazaar", "Bazaar", bazaar),
        ("marketin", "Market In", marketin),
    ]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # Schedule all playright tasks + 1 requests task
        tasks = [fetch_store(context, s_id, s_name, func) for s_id, s_name, func in stores]
        # Run 24hr without a page
        hr24_task = asyncio.create_task(hr24())
        
        results = await asyncio.gather(*tasks)
        hr24_price = await hr24_task
        
        results.append(("24hr", "24hr Stores", hr24_price))
        
        for store_id, store_name, price in results:
            prices["stores"][store_id] = {
                "name": store_name,
                "price": price,
                "available": price is not None
            }
            
        await browser.close()
        
    _write_json_with_price_decimals("prices.json", prices)
    update_price_history(prices)
    print("\nPrices saved to prices.json")
    print(f"Price history saved to {HISTORY_FILE}")

if __name__ == "__main__":
    asyncio.run(main_async())
