# White Monster Price Scraper

Automated Python scraper that fetches Monster Energy Zero Ultra 500ml prices from Greek supermarkets using Playwright and BeautifulSoup.

## Setup

```bash
# Recommended: using uv
uv pip install -r requirements.txt
playwright install chromium

# Or using standard pip
pip install -r requirements.txt
playwright install chromium
```

## Running

Run from this directory or repository root:

```bash
python scrape_prices.py
```

Scraped data is saved to `../data/prices.json` and historical price points are appended to `../data/price_history.json`.

