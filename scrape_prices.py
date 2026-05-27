import json
import os
import re
import shutil
import requests
from pathlib import Path
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import chromedriver_autoinstaller


_CHROMEDRIVER_READY = None
_CHROMEDRIVER_ERROR = None
HISTORY_FILE = "price_history.json"
HISTORY_DAYS = 31


def safe_quit(driver):
    """Close the webdriver safely when an exception already occurred."""
    if driver:
        try:
            driver.quit()
        except Exception:
            pass


def parse_price_to_float(price_text):
    """Extract first numeric price token (supports 1.23 / 1,23 / 123 -> 1.23)."""
    if not price_text:
        return None

    match = re.search(r"(\d+[.,]?\d*)", price_text)
    if not match:
        return None

    raw_price = match.group(1)
    value = float(raw_price.replace(",", "."))

    # Handle sources that render cents without decimal separator (e.g. 114 => 1.14).
    if ("." not in raw_price and "," not in raw_price) and 100 <= value < 10000:
        value = value / 100
    if value > 1000:
        value = value / 100

    return value


def ensure_chromedriver():
    """Install the matching ChromeDriver once per process."""
    global _CHROMEDRIVER_READY, _CHROMEDRIVER_ERROR
    if _CHROMEDRIVER_READY is not None:
        return _CHROMEDRIVER_READY
    try:
        chromedriver_autoinstaller.install(path="")
        _CHROMEDRIVER_READY = True
    except Exception as exc:
        _CHROMEDRIVER_ERROR = exc
        _CHROMEDRIVER_READY = False
    return _CHROMEDRIVER_READY


def locate_chrome_binary():
    """Return a Chrome/Chromium executable path if available."""
    # Highest priority: explicit override from environment.
    env_path = os.environ.get("CHROME_BIN")
    if env_path and Path(env_path).exists():
        return env_path

    # Common executable names on Linux/Windows runners and local machines.
    for candidate in [
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
        "chrome",
        "msedge",
        "microsoft-edge",
    ]:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved

    # Playwright browser cache fallback used in CI/local environments.
    playwright_matches = sorted(
        Path.home().glob(".cache/ms-playwright/chromium-*/chrome-linux64/chrome")
    )
    if playwright_matches:
        return str(playwright_matches[-1])

    return None


def _append_history_point(history_list, timestamp, price, extra=None):
    """Append/replace a timeseries point and keep bounded history."""
    point = {"timestamp": timestamp, "price": round(price, 2)}
    if extra:
        point.update(extra)

    if history_list and history_list[-1].get("timestamp") == timestamp:
        history_list[-1] = point
    else:
        history_list.append(point)

def _parse_iso_timestamp(timestamp):
    if not timestamp:
        return None
    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except Exception:
        return None


def _rebuild_total_history(history):
    """Derive average market price using last-known price per store at each timestamp."""
    store_series = []
    all_timestamps = set()

    for store_data in history.get("stores", {}).values():
        if not isinstance(store_data, dict):
            continue
        series = []
        for point in store_data.get("history", []):
            if not isinstance(point, dict):
                continue
            timestamp = point.get("timestamp")
            price = point.get("price")
            point_dt = _parse_iso_timestamp(timestamp)
            if not timestamp or price is None or not point_dt:
                continue
            series.append((point_dt, timestamp, float(price)))
            all_timestamps.add(timestamp)
        if series:
            series.sort(key=lambda item: item[0])
            store_series.append(series)

    total_history = []
    for timestamp in sorted(
        all_timestamps,
        key=lambda ts: _parse_iso_timestamp(ts) or datetime.min,
    ):
        point_dt = _parse_iso_timestamp(timestamp)
        if not point_dt:
            continue

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
        if not isinstance(store_data, dict):
            continue
        for point in store_data.get("history", []):
            timestamp = point.get("timestamp")
            if timestamp:
                timestamps.add(timestamp)
    return sorted(timestamps, key=lambda ts: _parse_iso_timestamp(ts) or datetime.min)


def _backfill_store_history_gaps(history, store_id, fallback_price):
    """Fill missing scrape timestamps so new stores chart like existing ones."""
    scrape_timestamps = _collect_scrape_timestamps(history)
    if not scrape_timestamps or fallback_price is None:
        return

    store_history = history["stores"].get(store_id)
    if not isinstance(store_history, dict):
        return

    entries = store_history.setdefault("history", [])
    existing = {point.get("timestamp") for point in entries if point.get("timestamp")}
    fill_price = round(float(fallback_price), 2)

    for timestamp in scrape_timestamps:
        if timestamp in existing:
            continue
        entries.append({"timestamp": timestamp, "price": fill_price})
        existing.add(timestamp)

    entries.sort(
        key=lambda point: _parse_iso_timestamp(point.get("timestamp")) or datetime.min
    )


def _trim_history_window(history_list, reference_timestamp, days=HISTORY_DAYS):
    """Keep only points in the rolling N-day window."""
    reference_dt = _parse_iso_timestamp(reference_timestamp)
    if not reference_dt:
        return
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
        "total": {
            "name": "Average Market Price",
            "history": []
        },
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
    """Persist per-market and aggregate historical prices for charts."""
    history = _load_or_initialize_history(prices)
    timestamp = prices.get("last_updated")
    if not timestamp:
        return

    for store_id, store_data in prices.get("stores", {}).items():
        price = store_data.get("price")
        if price is None or not store_data.get("available", True):
            continue

        store_history = history["stores"].setdefault(
            store_id,
            {"name": store_data.get("name", store_id), "history": []}
        )
        store_history["name"] = store_data.get("name", store_history.get("name", store_id))
        _append_history_point(store_history["history"], timestamp, price)

    for store_id, store_data in prices.get("stores", {}).items():
        price = store_data.get("price")
        if price is None or not store_data.get("available", True):
            continue
        _backfill_store_history_gaps(history, store_id, price)

    history["last_updated"] = timestamp
    history["product"] = prices.get("product", history.get("product"))
    history["currency"] = prices.get("currency", history.get("currency"))

    for store_data in history["stores"].values():
        if isinstance(store_data, dict):
            _trim_history_window(store_data.get("history", []), timestamp)
    _rebuild_total_history(history)
    _trim_history_window(history["total"]["history"], timestamp)

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def get_driver():
    """Create a new Chrome driver instance with robust options"""
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-software-rasterizer')
    chrome_options.add_argument('--disable-web-security')
    chrome_options.add_argument('--disable-features=IsolateOrigins,site-per-process')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    chrome_binary = locate_chrome_binary()
    if chrome_binary:
        chrome_options.binary_location = chrome_binary

    # Keep chromedriver-autoinstaller as best-effort only. Selenium Manager
    # can still provision a matching driver if this fails.
    ensure_chromedriver()

    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver


def _extract_mymarket_price(soup, page_source):
    """Extract MyMarket product price from schema first, then DOM fallbacks."""
    # Primary strategy: product schema is the most stable source on MyMarket.
    for script_tag in soup.select("script[type='application/ld+json']"):
        raw_json = script_tag.get_text(strip=True)
        if not raw_json:
            continue
        try:
            payload = json.loads(raw_json)
        except Exception:
            continue

        nodes = []
        if isinstance(payload, dict) and isinstance(payload.get("@graph"), list):
            nodes = [node for node in payload["@graph"] if isinstance(node, dict)]
        elif isinstance(payload, dict):
            nodes = [payload]
        elif isinstance(payload, list):
            nodes = [node for node in payload if isinstance(node, dict)]

        for node in nodes:
            if node.get("@type") != "Product":
                continue
            offers = node.get("offers")
            if isinstance(offers, dict):
                schema_price = offers.get("price")
                parsed_schema_price = parse_price_to_float(str(schema_price)) if schema_price is not None else None
                if parsed_schema_price is not None:
                    return parsed_schema_price

    def is_per_unit(text):
        if not text:
            return False
        lower = text.lower()
        return any(x in lower for x in [
            '/l', '€/l', 'ltr', 'lt', 'λίτρο', '/lt', 'lt.',
            'ανά λίτρο', 'ανά lt', 'ανά l', '€/lt', '€/λ', '/λ', 'ανά λ'
        ])

    # Secondary strategy: known selectors
    preferred_selectors = [
        ".product-display-price",
        ".product-summary .selling-unit-row",
        "span.product-full--final-price",
        ".product-full--final-price",
        "span.product-full--price",
        "[data-testid='product-price']",
        "[data-testid='final-price']"
    ]
    for sel in preferred_selectors:
        el = soup.select_one(sel)
        if not el:
            continue
        price_text = el.get_text(strip=True)
        if not price_text or is_per_unit(price_text):
            continue
        split_price_match = re.search(r"€?\s*(\d{1,2})\s+(\d{2})\b", price_text)
        if split_price_match:
            combined_price = f"{split_price_match.group(1)}.{split_price_match.group(2)}"
            return parse_price_to_float(combined_price)
        parsed = parse_price_to_float(price_text)
        if parsed is not None:
            return parsed

    # Final fallback: regex on the page source
    for m in re.finditer(r"(\d+[.,]\d{1,2})\s*€", page_source):
        span_start = max(0, m.start() - 20)
        span_end = min(len(page_source), m.end() + 20)
        context = page_source[span_start:span_end].lower()
        if any(x in context for x in ['/l', '€/l', 'ltr', 'lt', 'λίτρο', 'ανά']):
            continue
        parsed = parse_price_to_float(m.group(1))
        if parsed is not None:
            return parsed

    return None


def masoutis(url="https://www.masoutis.gr/categories/item/monster-energy-drink-ultra-zero-500ml?3205614="):
    driver = None
    try:
        driver = get_driver()
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "item-price"))
        )
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        price_element = soup.find('div', class_='item-price')
        
        if price_element:
            price = price_element.get_text(strip=True)
            return float(price.split("€")[0])
    except Exception as e:
        print(f"Error fetching Masoutis price: {e}")
    finally:
        safe_quit(driver)
    return None

def ab(url="https://www.ab.gr/el/eshop/Kava-anapsyktika-nera-xiroi-karpoi/Anapsyktika/Energeiaka-Isotonika/Energeiako-Poto-Energy-Ultra-500ml/p/7289419"):
    driver = None
    try:
        driver = get_driver()
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='product-block-price']"))
        )
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        price_container = soup.find('div', attrs={'data-testid': 'product-block-price'})
        
        if price_container:
            all_divs = price_container.find_all('div', attrs={'aria-hidden': 'true'})
            cents_sup = price_container.find('sup', attrs={'aria-hidden': 'true'})

            if len(all_divs) >= 2 and cents_sup:
                main_price = all_divs[1].get_text(strip=True)
                cents = cents_sup.get_text(strip=True)
                price_str = f"{main_price}.{cents}"
                return float(price_str)
    except Exception as e:
        print(f"Error fetching AB price: {e}")
    finally:
        safe_quit(driver)
    return None

def sklavenitis(url="https://www.sklavenitis.gr/anapsyktika-nera-chymoi/anapsyktika-sodes-energeiaka-pota/energeiaka-isotonika-pota/monster-energy-zero-ultra-energeiako-poto-500ml/"):
    driver = None
    try:
        driver = get_driver()
        driver.set_page_load_timeout(30)
        driver.get(url)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "price"))
        )
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        price_element = soup.find('div', class_='price')
        
        if price_element:
            price_text = price_element.get_text(strip=True)
            return parse_price_to_float(price_text)
    except Exception as e:
        print(f"Error fetching Sklavenitis price: {e}")
    finally:
        safe_quit(driver)
    return None

def kritikos(url="https://kritikos-sm.gr/products/kaba/anapsuktika/energeiaka/monster-energy-zero-ultra-500ml-705294/"):
    driver = None
    try:
        driver = get_driver()
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "span[class*='ProductDetails_price']"))
        )
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        price_element = soup.find('span', class_=lambda x: x and 'ProductDetails_price__' in x and 'grey' not in x.lower())
        
        if price_element:
            price_text = price_element.get_text(strip=True)
            return parse_price_to_float(price_text)
    except Exception as e:
        print(f"Error fetching Kritikos price: {e}")
    finally:
        safe_quit(driver)
    return None

def mymarket(url="https://www.mymarket.gr/monster-energy-zero-ultra-500gr"):
    # Playwright is more reliable for MyMarket (Selenium is often served a stripped page).
    try:
        from playwright.sync_api import sync_playwright  # type: ignore[reportMissingImports]
    except Exception:
        sync_playwright = None

    if sync_playwright is not None:
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(2500)
                page_source = page.content()
                browser.close()
            soup = BeautifulSoup(page_source, 'html.parser')
            extracted = _extract_mymarket_price(soup, page_source)
            if extracted is not None:
                return extracted
        except Exception as e:
            print(f"Warning: Playwright MyMarket fetch failed, falling back to Selenium. ({e})")

    driver = None
    try:
        driver = get_driver()
        driver.get(url)
        # Wait for the page to load (wait for body as a generic fallback)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        def dismiss_mymarket_notification_popup():
            """Close MyMarket push notification popup when it overlays the page."""
            popup_close_locators = [
                (By.XPATH, "//button[contains(normalize-space(.), 'Όχι') and contains(normalize-space(.), 'ευχαριστ')]"),
                (By.XPATH, "//button[contains(normalize-space(.), 'Οχι') and contains(normalize-space(.), 'ευχαριστ')]"),
                (By.XPATH, "//*[@role='button' and contains(normalize-space(.), 'ευχαριστ')]"),
                (By.CSS_SELECTOR, "button[class*='deny'], button[class*='decline'], button[class*='reject']"),
            ]

            def try_close_in_current_context():
                for by, selector in popup_close_locators:
                    try:
                        button = WebDriverWait(driver, 1.5).until(
                            EC.element_to_be_clickable((by, selector))
                        )
                        driver.execute_script("arguments[0].click();", button)
                        return True
                    except TimeoutException:
                        continue
                    except Exception:
                        continue
                return False

            # Try in main page first.
            if try_close_in_current_context():
                return

            # Some popups are rendered inside iframes.
            frames = driver.find_elements(By.TAG_NAME, "iframe")
            for frame in frames:
                try:
                    driver.switch_to.frame(frame)
                    if try_close_in_current_context():
                        break
                except Exception:
                    continue
                finally:
                    driver.switch_to.default_content()

        dismiss_mymarket_notification_popup()

        # Give the product block a chance to render after dismissing overlays.
        try:
            WebDriverWait(driver, 8).until(
                lambda d: d.find_elements(By.CSS_SELECTOR, "span.product-full--final-price, .product-full--final-price, span.product-full--price, [data-testid='product-price'], [data-testid='final-price']")
            )
        except TimeoutException:
            pass

        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')

        return _extract_mymarket_price(soup, page_source)
    except Exception as e:
        print(f"Error fetching MyMarket price: {e}")
    finally:
        safe_quit(driver)
    return None

def galaxias(url="https://galaxias.shop/product/5060337501125"):
    driver = None
    try:
        driver = get_driver()
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "span.fs-1.mr-2"))
        )
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        price_element = soup.find('span', class_='fs-1 mr-2')
        
        if price_element:
            price_text = price_element.get_text(strip=True)
            return parse_price_to_float(price_text)
    except Exception as e:
        print(f"Error fetching Galaxias price: {e}")
    finally:
        safe_quit(driver)
    return None

def bazaar(url="https://www.bazaar-online.gr/monster-500ml-energy-zero-ultra?search=monster"):
    driver = None
    try:
        driver = get_driver()
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "new_price"))
        )
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        price_element = soup.find('div', class_='new_price')
        
        if price_element:
            price_text = price_element.get_text(strip=True)
            return parse_price_to_float(price_text)
    except Exception as e:
        print(f"Error fetching Bazaar price: {e}")
    finally:
        safe_quit(driver)
    return None

def hr24(url="https://www.24hr.gr/el/%CF%80%CF%81%CE%BF%CF%8A%CF%8C%CE%BD%CF%84%CE%B1/energy/energy/monster-energy-%CE%B5%CE%BD%CE%B5%CF%81%CE%B3%CE%B5%CE%B9%CE%B1%CE%BA%CF%8C-%CF%80%CE%BF%CF%84%CF%8C-ultra-white-zero-sugar-500ml"):
    """Fetch 24hr.gr product price (server-rendered HTML, no browser needed)."""
    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            },
            timeout=30,
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        price_element = soup.select_one(
            "#das-product-details-price, .das-product-details-price-value"
        )
        if price_element:
            parsed = parse_price_to_float(price_element.get_text(strip=True))
            if parsed is not None:
                return parsed

        final_price_input = soup.select_one(
            'input[name="final_price"][das-cart-key="final_price"]'
        )
        if final_price_input and final_price_input.get("value"):
            return parse_price_to_float(final_price_input["value"])
    except Exception as e:
        print(f"Error fetching 24hr.gr price: {e}")
    return None


def marketin(url="https://www.market-in.gr/el-gr/kava-anapsuktika-xumoi-md-energeiaka-pota/monster-energy-zero-ultra-kouti-500ml"):
    driver = None
    try:
        driver = get_driver()
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "p-price"))
        )
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        price_element = soup.find('span', class_='p-price')
        
        if price_element:
            price_text = price_element.get_text(strip=True)
            return parse_price_to_float(price_text)
    except Exception as e:
        print(f"Error fetching Market In price: {e}")
    finally:
        safe_quit(driver)
    return None

def main():
    print("Starting price scraping...")
    
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
        ("24hr", "24hr Stores", hr24),
    ]
    
    for store_id, store_name, scraper_func in stores:
        print(f"Fetching {store_name} price...")
        price = scraper_func()
        prices["stores"][store_id] = {
            "name": store_name,
            "price": price,
            "available": price is not None
        }
        if price is not None:
            print(f"{store_name}: €{price}")
        else:
            print(f"{store_name}: N/A")
    
    # Save to JSON file
    with open('prices.json', 'w', encoding='utf-8') as f:
        json.dump(prices, f, indent=2, ensure_ascii=False)

    update_price_history(prices)
    
    print("\nPrices saved to prices.json")
    print(f"Price history saved to {HISTORY_FILE}")

if __name__ == "__main__":
    main()
