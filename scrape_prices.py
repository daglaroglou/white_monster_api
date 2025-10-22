import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import chromedriver_autoinstaller

# Automatically install the correct ChromeDriver version
chromedriver_autoinstaller.install(path="")

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
        if driver:
            driver.quit()
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
        if driver:
            try:
                driver.quit()
            except:
                pass
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
            price = price_text.split('€')[0].strip().replace(',', '.')
            return float(price)
    except Exception as e:
        print(f"Error fetching Sklavenitis price: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass
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
            price = price_text.replace('€', '').strip().replace(',', '.')
            return float(price)
    except Exception as e:
        print(f"Error fetching Kritikos price: {e}")
    finally:
        if driver:
            driver.quit()
    return None

def mymarket(url="https://www.mymarket.gr/monster-energy-zero-ultra-500gr"):
    driver = None
    try:
        driver = get_driver()
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "span.product-full--final-price"))
        )
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        price_element = soup.find('span', class_='product-full--final-price')
        
        if price_element:
            price_text = price_element.get_text(strip=True)
            price = price_text.replace('€', '').strip().replace(',', '.')
            return float(price)
    except Exception as e:
        print(f"Error fetching MyMarket price: {e}")
    finally:
        if driver:
            driver.quit()
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
            price = price_text.replace('€', '').strip().replace(',', '.')
            return float(price)
    except Exception as e:
        print(f"Error fetching Galaxias price: {e}")
    finally:
        if driver:
            driver.quit()
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
            price = price_text.replace('€', '').strip().replace(',', '.')
            return float(price)
    except Exception as e:
        print(f"Error fetching Bazaar price: {e}")
    finally:
        if driver:
            driver.quit()
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
            price = price_text.replace('€', '').strip().replace(',', '.')
            return float(price)
    except Exception as e:
        print(f"Error fetching Market In price: {e}")
    finally:
        if driver:
            driver.quit()
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
        if price:
            print(f"{store_name}: €{price}")
        else:
            print(f"{store_name}: N/A")
    
    # Save to JSON file
    with open('prices.json', 'w', encoding='utf-8') as f:
        json.dump(prices, f, indent=2, ensure_ascii=False)
    
    print("\nPrices saved to prices.json")

if __name__ == "__main__":
    main()
