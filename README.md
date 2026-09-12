<div align="center">

# 🥤 White Monster Price Tracker

**Live price tracking for Monster Energy Zero Ultra 500ml across Greek supermarkets.**

[![Live Site](https://img.shields.io/badge/Live_Site-dag.is--a.dev-0070F3?style=for-the-badge&logo=github)](https://dag.is-a.dev/white_monster_api/)
[![License](https://img.shields.io/badge/License-MIT-111111?style=for-the-badge)](LICENSE)
[![Prices Updated](https://img.shields.io/badge/Prices-Updated_Daily-4ade80?style=for-the-badge&logo=clockify&logoColor=white)](https://daglaroglou.github.io/white_monster_api/prices.json)

[**View Live →**](https://dag.is-a.dev/white_monster_api/)

</div>

---

## What is this?

A fully automated price tracker that scrapes **Monster Energy Zero Ultra 500ml** prices from **9 major Greek supermarkets** every day, stores the data as JSON, and presents it through a polished, interactive dashboard — complete with an interactive 3D can model, per-store sparkline charts, and a free public API.

Prices update automatically at **11:00 AM Greek time** via GitHub Actions. The scraper runs, commits fresh data, and triggers a rebuild — zero manual intervention.

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 📊 Live Dashboard
A bento-grid layout with animated cards showing each store's current price and 30-day price history sparkline — at a glance, you know where the cheapest can is.

### 🧊 Interactive 3D Can
A WebGL-rendered Monster Energy can you can grab and spin, floating with particle effects. Built with Three.js and React Three Fiber.

### 🌗 Light / Dark Mode
Theme toggle with a custom fizzy bubble transition — 220 animated circles rise and cover the screen like carbonation bubbles while the palette swaps underneath.

</td>
<td width="50%">

### 🔌 Free Public API
A static JSON endpoint anyone can hit — no auth, no rate limits, no API keys. Fetch the latest prices from JavaScript, Python, cURL, or anything that speaks HTTP.

### 📈 30-Day Price History
Per-store and market-average history with interactive Recharts line graphs. Hover any point to see the exact date and price.

### ⚡ Fully Automated
A GitHub Actions cron job scrapes all 9 stores daily using Playwright, commits the data, and deploys a fresh static build to GitHub Pages — hands-off.

</td>
</tr>
</table>

---

## 🏪 Tracked Supermarkets

| Store | Website |
|:------|:--------|
| **Masoutis** | [masoutis.gr](https://www.masoutis.gr) |
| **AB Vassilopoulos** | [ab.gr](https://www.ab.gr) |
| **Sklavenitis** | [sklavenitis.gr](https://www.sklavenitis.gr) |
| **Kritikos** | [kritikos-sm.gr](https://kritikos-sm.gr) |
| **MyMarket** | [mymarket.gr](https://www.mymarket.gr) |
| **Galaxias** | [galaxias.shop](https://galaxias.shop) |
| **Bazaar** | [bazaar-online.gr](https://www.bazaar-online.gr) |
| **Market In** | [market-in.gr](https://www.market-in.gr) |
| **24hr Stores** | [24hr.gr](https://www.24hr.gr) |

---

## 🔌 API

The price data is served as a static JSON file — no backend needed.

### Endpoint

```
GET  https://dag.is-a.dev/white_monster_api/prices.json
```

### Response

```json
{
  "last_updated": "2026-09-11T09:25:20.879285",
  "product": "Monster Energy Zero Ultra 500ml",
  "currency": "EUR",
  "stores": {
    "masoutis": { "name": "Masoutis", "price": 1.14, "available": true },
    "ab": { "name": "AB Vassilopoulos", "price": 1.09, "available": true },
    "sklavenitis": { "name": "Sklavenitis", "price": null, "available": false },
    "kritikos": { "name": "Kritikos", "price": 1.14, "available": true },
    "mymarket": { "name": "MyMarket", "price": 1.52, "available": true },
    "galaxias": { "name": "Galaxias", "price": null, "available": false },
    "bazaar": { "name": "Bazaar", "price": 1.10, "available": true },
    "marketin": { "name": "Market In", "price": 1.55, "available": true },
    "24hr": { "name": "24hr Stores", "price": 1.70, "available": true }
  }
}
```

### Quick Start

<details>
<summary><strong>JavaScript</strong></summary>

```js
fetch('https://daglaroglou.github.io/white_monster_api/prices.json')
  .then(res => res.json())
  .then(data => console.log(data));
```
</details>

<details>
<summary><strong>Python</strong></summary>

```python
import requests

response = requests.get('https://dag.is-a.dev/white_monster_api/prices.json')
prices = response.json()
```
</details>

<details>
<summary><strong>cURL</strong></summary>

```bash
curl https://dag.is-a.dev/white_monster_api/prices.json
```
</details>

---

## 🧰 Tech Stack

| Layer | Technology |
|:------|:-----------|
| **Frontend** | [Next.js 16](https://nextjs.org/) · [React 19](https://react.dev/) · [TypeScript](https://www.typescriptlang.org/) |
| **3D** | [Three.js](https://threejs.org/) · [React Three Fiber](https://r3f.docs.pmnd.rs/) · [Drei](https://drei.docs.pmnd.rs/) |
| **Charts** | [Recharts](https://recharts.org/) |
| **Motion** | [Motion](https://motion.dev/) (Framer Motion) |
| **Icons** | [Phosphor Icons](https://phosphoricons.com/) |
| **Scraping** | [Playwright](https://playwright.dev/) · [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) · Python |
| **CI/CD** | [GitHub Actions](https://github.com/features/actions) · [GitHub Pages](https://pages.github.com/) |
| **Fonts** | [Geist Sans & Mono](https://vercel.com/font) |

---

## 📄 License

[MIT](LICENSE) © [Christos Daglaroglou](https://dag.is-a.dev)
