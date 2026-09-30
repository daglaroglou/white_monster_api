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

def robust_price_extract(html):
    soup = BeautifulSoup(html, "html.parser")
    
    semantic_prices = []
    
    # Next.js Data Extraction (Kritikos fallback)
    next_data = soup.find("script", id="__NEXT_DATA__")
    if next_data and next_data.string:
        try:
            prices = re.findall(r'"price"\s*:\s*(\d+\.\d{2})', next_data.string)
            for p in prices:
                semantic_prices.append(float(p))
        except: pass
        
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            if isinstance(data, dict): data = [data]
            for item in data:
                if isinstance(item, dict):
                    if item.get("@type") == "Product" or item.get("@type") == "ItemPage":
                        offers = item.get("offers", {})
                        if isinstance(offers, list): offers = offers[0] if offers else {}
                        if "price" in offers:
                            try: semantic_prices.append(float(offers["price"]))
                            except: pass
        except: pass

    meta_price = soup.find("meta", property="product:price:amount")
    if meta_price and meta_price.get("content"):
        try: semantic_prices.append(float(meta_price["content"]))
        except: pass
            
    for el in soup.find_all(attrs={"itemprop": "price"}):
        if el.get("content"):
            try: semantic_prices.append(float(el["content"]))
            except: pass
        text = el.get_text(strip=True)
        if text:
            parsed = parse_price_to_float(text)
            if parsed is not None: semantic_prices.append(parsed)

    valid_semantic = [p for p in semantic_prices if 0.8 <= p <= 2.0]
    if valid_semantic:
        return min(valid_semantic)

    text = soup.get_text(separator=" ", strip=True)
    matches = re.findall(r'(\d+)[.,\s](\d{2})\s*€|€\s*(\d+)[.,\s](\d{2})', text)
    
    text_prices = []
    for m1, m2, m3, m4 in matches:
        if m1 and m2:
            parsed = parse_price_to_float(f"{m1}.{m2}")
        else:
            parsed = parse_price_to_float(f"{m3}.{m4}")
        if parsed is not None:
            text_prices.append(parsed)
            
    for p in text_prices:
        if 0.8 <= p <= 2.0:
            return p
            
    for p in text_prices[:5]:
        if 0.8 <= p <= 3.0:
            return p
            
    return None

async def _fetch_and_extract(page, url):
    price = None
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        try:
            await page.wait_for_timeout(5000)
        except: pass
        html = await page.content()
        price = robust_price_extract(html)
    except Exception as e:
        print(f"Error fetching {url} with Playwright: {e}")
        
    if price is not None:
        return price
        
    print(f"Playwright returned None for {url}, falling back to requests...")
    try:
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
        resp = await asyncio.to_thread(
            requests.get, url, headers={"User-Agent": user_agent, "Accept-Language": "el-GR,el;q=0.9,en;q=0.8"}, timeout=30
        )
        if resp.status_code == 200:
            return robust_price_extract(resp.text)
    except Exception as e:
        print(f"Requests fallback failed for {url}: {e}")
        
    return None

async def ab_vasilopoulos(page):
    url = "https://www.ab.gr/eshop/Kava-anapsyktika-nera-xiroi-karpoi/Anapsyktika/Energeiaka-Isotonika/Energeiako-Poto-Energy-Ultra-500ml/p/7289419"
    return await _fetch_and_extract(page, url)

async def galaxias(page):
    url = "https://galaxias.shop/product/5060337501125"
    return await _fetch_and_extract(page, url)

async def halkiadakis(page):
    url = "https://xalkiadakis.gr/product/monster-energy-energheiako-poto-ultra-xoris-zakhari-500-ml"
    return await _fetch_and_extract(page, url)

async def kritikos(page):
    url = "https://kritikos-sm.gr/products/kaba/anapsuktika/energeiaka/monster-energy-zero-ultra-500ml-705294/"
    return await _fetch_and_extract(page, url)

async def market_in(page):
    url = "https://www.market-in.gr/el-gr/kava-anapsuktika-xumoi-md-energeiaka-pota/monster-energy-zero-ultra-kouti-500ml"
    return await _fetch_and_extract(page, url)

async def masoutis(page):
    url = "https://www.masoutis.gr/categories/item/monster-energy-drink-ultra-zero-500ml?3205614="
    return await _fetch_and_extract(page, url)

async def mymarket(page):
    url = "https://www.mymarket.gr/monster-energy-zero-ultra-500gr"
    return await _fetch_and_extract(page, url)

async def sklavenitis(page):
    url = "https://www.sklavenitis.gr/anapsyktika-nera-chymoi/energeiaka-pota-ice-tea-ice-coffee/energeiaka-isotonika-pota/monster-energy-zero-ultra-energeiako-poto-500ml/"
    return await _fetch_and_extract(page, url)

async def bazaar(page):
    url = "https://www.bazaar-online.gr/monster-energeiako-poto-zero-ultra-500ml"
    return await _fetch_and_extract(page, url)

async def hr24(page=None):
    url = "https://www.24hr.gr/el/%CF%80%CF%81%CE%BF%CF%8A%CF%8C%CE%BD%CF%84%CE%B1/energy/energy/monster-energy-%CE%B5%CE%BD%CE%B5%CF%81%CE%B3%CE%B5%CE%B9%CE%B1%CE%BA%CF%8C-%CF%80%CE%BF%CF%84%CF%8C-ultra-white-zero-sugar-500ml"
    try:
        import requests
        from bs4 import BeautifulSoup
        import asyncio
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
            
        response = await asyncio.to_thread(
            requests.get, url, headers={"User-Agent": user_agent}, timeout=30
        )
        response.raise_for_status()
        price = robust_price_extract(response.text)
        if price is not None:
            return price
            
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
    
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=user_agent)
        
        async def scrape_with_page(func):
            page = await context.new_page()
            try:
                return await func(page)
            finally:
                await page.close()
                
        tasks = {
            "ab_vasilopoulos": asyncio.create_task(scrape_with_page(ab_vasilopoulos)),
            "galaxias": asyncio.create_task(scrape_with_page(galaxias)),
            "halkiadakis": asyncio.create_task(scrape_with_page(halkiadakis)),
            "kritikos": asyncio.create_task(scrape_with_page(kritikos)),
            "market_in": asyncio.create_task(scrape_with_page(market_in)),
            "masoutis": asyncio.create_task(scrape_with_page(masoutis)),
            "mymarket": asyncio.create_task(scrape_with_page(mymarket)),
            "sklavenitis": asyncio.create_task(scrape_with_page(sklavenitis)),
            "bazaar": asyncio.create_task(scrape_with_page(bazaar)),
            "24hr": asyncio.create_task(hr24())
        }
        
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        
        names = {
            "ab_vasilopoulos": "AB Vassilopoulos",
            "galaxias": "Galaxias",
            "halkiadakis": "Halkiadakis",
            "kritikos": "Kritikos",
            "market_in": "Market In",
            "masoutis": "Masoutis",
            "mymarket": "MyMarket",
            "sklavenitis": "Sklavenitis",
            "bazaar": "Bazaar",
            "24hr": "24hr Stores"
        }
        
        for key, result in zip(tasks.keys(), results):
            price = result if not isinstance(result, Exception) else None
            prices["stores"][key] = {
                "name": names[key],
                "price": price,
                "available": price is not None,
                "is_discount": False
            }
            
        await browser.close()
    
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
