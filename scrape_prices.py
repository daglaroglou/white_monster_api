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
        "description": prices.get("description", ""),
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
                    "description": loaded.get("description", base_history.get("description", "")),
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
        store_history["is_discount"] = store_data.get("is_discount", False)
        _append_history_point(store_history["history"], timestamp, price)
    for store_id, store_data in prices.get("stores", {}).items():
        price = store_data.get("price")
        if price is None or not store_data.get("available", True): continue
        _backfill_store_history_gaps(history, store_id, price)
    history["last_updated"] = timestamp
    history["product"] = prices.get("product", history.get("product"))
    history["currency"] = prices.get("currency", history.get("currency"))
    if "description" in prices:
        history["description"] = prices["description"]
    for store_data in history["stores"].values():
        if isinstance(store_data, dict):
            _trim_history_window(store_data.get("history", []), timestamp)
    _rebuild_total_history(history)
    _trim_history_window(history["total"]["history"], timestamp)
    _write_json_with_price_decimals(HISTORY_FILE, history)

# Scraping Handlers

async def fetch_api_prices():
    url = "https://api.posokanei.gov.gr/products/92482dbc21c54e08b76320730929c0a9"
    try:
        import requests
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = await asyncio.to_thread(requests.get, url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        api_mapping = {
            "ab_vasilopoulos": ("ab", "AB Vassilopoulos"),
            "galaxias": ("galaxias", "Galaxias"),
            "halkiadakis": ("halkiadakis", "Halkiadakis"),
            "kritikos": ("kritikos", "Kritikos"),
            "market_in": ("marketin", "Market In"),
            "masoutis": ("masoutis", "Masoutis"),
            "mymarket": ("mymarket", "MyMarket"),
            "sklavenitis": ("sklavenitis", "Sklavenitis"),
            "bazaar": ("bazaar", "Bazaar"),
            "synka": ("synka", "Synka"),
        }
        
        extracted = {}
        for item in data.get("retailer_prices", []):
            ret = item.get("retailer")
            if ret in api_mapping:
                store_id, store_name = api_mapping[ret]
                extracted[store_id] = {
                    "name": store_name,
                    "price": item.get("price"),
                    "available": item.get("price") is not None,
                    "is_discount": item.get("is_discount", False)
                }
        return extracted, data.get("description", "")
    except Exception as e:
        print(f"Error fetching API prices: {e}")
        return {}, ""

async def bazaar(page):
    url = "https://www.bazaar-online.gr/monster-500ml-energy-zero-ultra?search=monster"
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    el = page.locator(".new_price").first
    try:
        await el.wait_for(state="attached", timeout=15000)
        text = await el.evaluate("el => el.textContent")
        return parse_price_to_float(text)
    except Exception:
        pass
    return None

async def hr24(page=None):
    url = "https://www.24hr.gr/el/%CF%80%CF%81%CE%BF%CF%8A%CF%8C%CE%BD%CF%84%CE%B1/energy/energy/monster-energy-%CE%B5%CE%BD%CE%B5%CF%81%CE%B3%CE%B5%CE%B9%CE%B1%CE%BA%CF%8C-%CF%80%CE%BF%CF%84%CF%8C-ultra-white-zero-sugar-500ml"
    try:
        import requests
        from bs4 import BeautifulSoup
        import asyncio
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

async def main_async():
    print("Starting async price scraping...")
    
    from datetime import datetime
    prices = {
        "last_updated": datetime.now().isoformat(),
        "product": "Monster Energy Zero Ultra 500ml",
        "currency": "EUR",
        "stores": {}
    }
    
    import asyncio
    from playwright.async_api import async_playwright
    
    # Fetch from new API
    api_task = asyncio.create_task(fetch_api_prices())
    
    # Fetch Bazaar using Playwright
    async def fetch_bazaar():
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            try:
                page = await context.new_page()
                bazaar_price = await bazaar(page)
                return bazaar_price
            except Exception as e:
                print(f"Error fetching Bazaar price: {e}")
                return None
            finally:
                await browser.close()
                
    bazaar_task = asyncio.create_task(fetch_bazaar())
    hr24_task = asyncio.create_task(hr24())
    (api_prices, description), bazaar_price, hr24_price = await asyncio.gather(api_task, bazaar_task, hr24_task)
    
    # Add description to root of prices dict
    if description:
        prices["description"] = description
    
    # Combine results
    prices["stores"].update(api_prices)
    
    # Keep the API's discount status for Bazaar if it exists
    bazaar_discount = prices["stores"].get("bazaar", {}).get("is_discount", False)
    prices["stores"]["bazaar"] = {
        "name": "Bazaar",
        "price": bazaar_price,
        "available": bazaar_price is not None,
        "is_discount": bazaar_discount
    }
    
    prices["stores"]["24hr"] = {
        "name": "24hr Stores",
        "price": hr24_price,
        "available": hr24_price is not None,
        "is_discount": False
    }
    
    # Print results to stdout for logging
    for s_id, s_data in prices["stores"].items():
        pr = s_data.get("price")
        print(f"{s_data['name']}: €{pr:.2f}" if pr else f"{s_data['name']}: N/A")

    _write_json_with_price_decimals("prices.json", prices)
    update_price_history(prices)
    print("\nPrices saved to prices.json")
    print(f"Price history saved to {HISTORY_FILE}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main_async())
