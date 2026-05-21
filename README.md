# 🛒 White Monster Price Tracker API

Automated price tracking for Monster Energy Zero Ultra 500ml across multiple Greek supermarkets.

## 🌟 Features

- **Automated Updates**: Prices are updated every 6 hours via GitHub Actions
- **Public API**: Access current prices via a simple JSON API
- **Web Interface**: Beautiful dashboard to view prices
- **Multi-Store Coverage**: Tracks prices from 8 different supermarkets

## 🏪 Tracked Stores

- Masoutis
- AB Vassilopoulos
- Sklavenitis
- Kritikos
- MyMarket
- Galaxias
- Bazaar
- Market In

## 📡 API Usage

### API Endpoint

```
https://raw.githubusercontent.com/daglaroglou/white_monster_api/main/prices.json
```

### History Endpoint

```
https://raw.githubusercontent.com/daglaroglou/white_monster_api/main/price_history.json
```

### Web Dashboard

```
https://dag.is-a.dev/white_monster_api/
```

### Response Format

```json
{
  "last_updated": "2025-10-16T12:00:00",
  "product": "Monster Energy Zero Ultra 500ml",
  "currency": "EUR",
  "stores": {
    "masoutis": {
      "name": "Masoutis",
      "price": 1.49,
      "available": true
    },
    ...
  }
}
```

## 💻 Usage Examples

### JavaScript

```javascript
fetch('https://raw.githubusercontent.com/daglaroglou/white_monster_api/main/prices.json')
  .then(response => response.json())
  .then(data => {
    console.log('Latest prices:', data);
    // Find the cheapest price
    const prices = Object.values(data.stores)
      .filter(store => store.available)
      .map(store => store.price);
    const cheapest = Math.min(...prices);
    console.log('Cheapest price:', cheapest);
  });
```

### Python

```python
import requests

response = requests.get('https://raw.githubusercontent.com/daglaroglou/white_monster_api/main/prices.json')
prices = response.json()

# Find the cheapest store
available_stores = {k: v for k, v in prices['stores'].items() if v['available']}
cheapest_store = min(available_stores.items(), key=lambda x: x[1]['price'])

print(f"Cheapest at {cheapest_store[1]['name']}: €{cheapest_store[1]['price']}")
```

### cURL

```bash
curl https://raw.githubusercontent.com/daglaroglou/white_monster_api/main/prices.json
```

## ⏰ Update Schedule

The prices are automatically updated once per day at **08:00 Greece time** (`Europe/Athens`) by GitHub Actions.

You can also manually trigger an update from the Actions tab.

## 📝 License

MIT License - Feel free to use and modify as needed.

## ⚠️ Disclaimer

This project is for educational purposes. Please respect the terms of service of the websites being scraped. Consider implementing rate limiting and caching to minimize server load.

This is not endorsed by Monster Energy.

