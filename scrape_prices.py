import json
import os
import re
import shutil
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

    available_prices = []
    for store_id, store_data in prices.get("stores", {}).items():
        price = store_data.get("price")
        if price is None:
            continue

        store_history = history["stores"].setdefault(
            store_id,
            {"name": store_data.get("name", store_id), "history": []}
        )
        store_history["name"] = store_data.get("name", store_history.get("name", store_id))
        _append_history_point(store_history["history"], timestamp, price)
        available_prices.append(float(price))

    if available_prices:
        market_average = sum(available_prices) / len(available_prices)
        _append_history_point(
            history["total"]["history"],
            timestamp,
            market_average,
            extra={"available_stores": len(available_prices)}
        )

    history["last_updated"] = timestamp
    history["product"] = prices.get("product", history.get("product"))
    history["currency"] = prices.get("currency", history.get("currency"))

    for store_data in history["stores"].values():
        if isinstance(store_data, dict):
            _trim_history_window(store_data.get("history", []), timestamp)
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

        # Try multiple selectors/strategies to locate the price, preferring the final product price
        price_text = None

        def is_per_unit(text):
            if not text:
                return False
            lower = text.lower()
            return any(x in lower for x in [
                '/l', '€/l', 'ltr', 'lt', 'λίτρο', '/lt', 'lt.',
                'ανά λίτρο', 'ανά lt', 'ανά l', '€/lt', '€/λ', '/λ', 'ανά λ'
            ])

        # Preferred known selectors
        preferred_selectors = [
            "span.product-full--final-price",
            ".product-full--final-price",
            "span.product-full--price",
            "[data-testid='product-price']",
            "[data-testid='final-price']"
        ]

        for sel in preferred_selectors:
            el = soup.select_one(sel)
            if el:
                price_text = el.get_text(strip=True)
                if price_text and not is_per_unit(price_text):
                    break
                price_text = None

        # Fallback: look for elements that contain a euro sign and prefer crimson-colored ones
        if not price_text:
            candidates = soup.find_all(lambda tag: tag.name in ['span', 'div', 'p'] and tag.get_text() and '€' in tag.get_text())

            crimson_candidate = None
            generic_candidate = None
            for c in candidates:
                txt = c.get_text(strip=True)
                # skip obvious per-unit labels
                if is_per_unit(txt):
                    continue

                # check style/class for crimson color
                style = (c.get('style') or '').lower()
                classes = ' '.join(c.get('class') or []).lower()
                if 'crimson' in style or 'crimson' in classes or '#dc143c' in style or 'color:red' in style or 'color:#dc143c' in style:
                    crimson_candidate = txt
                    break

                if not generic_candidate:
                    generic_candidate = txt

            price_text = crimson_candidate or generic_candidate

        # Final fallback: regex on the whole page (avoid matching per-unit by checking surrounding text)
        if not price_text:
            # find euro amounts not immediately followed by /L or similar
            for m in re.finditer(r"(\d+[.,]\d{1,2})\s*€", page_source):
                span_start = max(0, m.start()-20)
                span_end = min(len(page_source), m.end()+20)
                context = page_source[span_start:span_end].lower()
                if any(x in context for x in ['/l', '€/l', 'ltr', 'lt', 'λίτρο', 'ανά']):
                    continue
                price_text = m.group(1)
                break

        if price_text:
            return parse_price_to_float(price_text)
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
        ("marketin", "Market In", marketin)
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
