# Amazon Best Sellers tracker (Python)

Pull the **Amazon Best Sellers** and **Hot New Releases** charts for any category, in **17 marketplaces** (US, UK, DE, FR, ES, IT, NL, PL, SE, MX, BR, CA, AU, IN, JP, SG, AE, TR), with ranks, ASINs, titles, prices in local currency, ratings and review counts. For books you also get the author (byline) and format (Hardcover, Paperback, Kindle Edition).

Code uses a ready-made Apify scraper that costs **$1 per 1,000 products** (pay-per-result, with free monthly credit on new Apify accounts).

Scraper: **[apify.com/zet46/amazon-best-sellers-scraper](https://apify.com/zet46/amazon-best-sellers-scraper)**.

## Setup

```bash
pip install "apify-client>=3"
export APIFY_TOKEN=...   # https://console.apify.com/settings/integrations (free account)
```

## 1. Today's top sellers in one category ([python/top_sellers.py](python/top_sellers.py))

```bash
python python/top_sellers.py
```
```
Amazon co.uk top bestsellers in electronics:
  #  1  Amazon Basics 20-Pack AA Alkaline High-Performance Batteries     £6.32  4.6 (930,935)
  #  2  DURACELL Plus 9V Alkaline Batteries (2 Pack) 6LR61 | 100% Li     £5.42  4.7 (15,730)
  #  3  Amazon Basics 40-Pack AA Alkaline Industrial Batteries, 1.5      £6.62  4.5 (101,364)
  #  4  DURACELL 2032 Lithium Coin Batteries (4 Pack) 3V, CR2032 | U        --  4.7 (144,677)
  #  5  DURACELL Plus AA Alkaline Batteries (30 Pack) 1.5V, LR06 | D    £15.41  4.8 (1,115)
  #  6  Ring Battery Video Doorbell 2K (newest gen), DIY Wireless Do        --  4.2 (3,919)
  #  7  Amazon Fire TV Stick HD (newest gen), free & live TV, Alexa         --  4.1 (5,055)
  ...
```

Change `MARKETPLACE`, `CATEGORY` and `LIST_TYPE` at the top of the script. Set `LIST_TYPE` to `"new-releases"` for the Hot New Releases chart.

## 2. Compare one category across many marketplaces ([python/compare_markets.py](python/compare_markets.py))

```bash
python python/compare_markets.py
```
```
Amazon best sellers / electronics — top 5 per marketplace

  amazon.com:
    #1  blink plus plan with monthly auto-renewal                 $11.99  4.4 (281,100)
    #2  Apple EarPods Headphones with USB-C Plug, Wired Ear       $19.00  4.5 (19,026)
    #3  Apple AirTag (2nd Generation): Tracker for Keychain,      $24.00  4.6 (11,866)
    #4  Apple AirPods Pro 3 Wireless Earbuds with Active Noi     $199.00  4.4 (16,462)
    #5  Apple AirPods 5 Wireless Earbuds with Active Noise C     $129.00  4.3 (220)

  amazon.co.uk:
    #1  Amazon Basics 20-Pack AA Alkaline High-Performance B       £7.58  4.6 (930,935)
    #2  DURACELL Plus 9V Alkaline Batteries (2 Pack) 6LR61 |       £6.50  4.7 (15,730)
    #3  Amazon Basics 40-Pack AA Alkaline Industrial Batteri       £7.94  4.5 (101,364)

  amazon.fr:
    #1  DURACELL 2032 Piles Boutons au Lithium (Lot de 8) 3V          --  4.7 (979)
    #2  TOCOL Coque pour iPhone 15, Compatible avec MagSafe,          --  4.6 (417)
    #3  Amazon Basics Lot de 20 piles alcalines AA haute per      7,32 €  4.6 (554)

  amazon.it:
    #1  NEW'C Pellicola Vetro per iPhone 17/17 Pro/16 Pro, i      8,19 €  4.4 (306,728)

  amazon.co.jp:
    #4  Amazonベーシック 単3形 アルカリ乾電池 20本 1.5V 保存期限10年 液漏れ防止              ￥759  4.3
    #5  Amazonベーシック 単4形 アルカリ乾電池 20本 1.5V 保存期限10年 液漏れ防止              ￥757  4.3
```

The script passes `categoryUrls` so each marketplace returns prices in the local currency with the correct decimal format (`,` vs `.`).

## 3. Daily rank + price tracking ([python/track_rank.py](python/track_rank.py))

Run this file every day (cron, Windows Task Scheduler, or Apify Scheduler). Each run writes one row per ASIN to a local SQLite database and prints what moved versus the previous observation.

First run:
```
Amazon.com bestsellers / electronics on 2026-10-15
(60 products tracked)

  #  1  blink plus plan with monthly auto-renewal                        11.99 USD
  #  2  Apple EarPods Headphones with USB-C Plug, Wired Ear Buds with    19.00 USD
  #  3  Apple AirTag (2nd Generation): Tracker for Keychain, Wallet, a   24.00 USD
  ...
  (first run — rerun tomorrow to see rank/price changes)
```

Next-day output looks like this:
```
  New in the chart:
    #  3  Apple AirPods Pro 3 Wireless Earbuds with Active Noise    199.00 USD

  Climbers (3+ positions up):
    # 11 (was # 18)  Energizer Advanced - AAA Batteries (24 Pack)        price +1.2%
    #  7 (was # 12)  Roku TV Remote Control (Official)                   price -5.0%

  Fallers (3+ positions down):
    # 25 (was #  8)  Roku Streaming Stick HD with Voice Remote           price +0.0%

  Dropped out:
    (was # 19)  B0BXYZ1234
```

Because the data lives in SQLite, you can query the whole history, plot it, or alert yourself with one SQL line — for example, "which ASINs lost 10+ ranks since last week":

```sql
WITH last_two AS (
  SELECT asin, title, rank,
         LAG(rank) OVER (PARTITION BY asin ORDER BY run_date) AS prev_rank
  FROM ranks WHERE marketplace='com' AND category='electronics')
SELECT asin, title, prev_rank, rank, rank - prev_rank AS delta
FROM last_two
WHERE prev_rank IS NOT NULL AND rank - prev_rank >= 10
ORDER BY delta DESC;
```

## Pricing

$1 per 1,000 products. Tracking the top 100 of one chart daily for a month is **~3,000 products = $3**.

Skipped items (via `minRating`, `minReviews`, or dedup) are not charged.

## Fields you get back

For each product: `marketplace`, `listType`, `rank`, `asin`, `title`, `url`, `image`, `rating`, `reviewsCount`, `price` (float, locale-aware), `priceText` (raw), `currency` (ISO code), `byline` (books), `format` (books/media), `categorySlug`, `categoryName`, `scrapedAt` (UTC).

Full input/output schema and examples: **[apify.com/zet46/amazon-best-sellers-scraper](https://apify.com/zet46/amazon-best-sellers-scraper)**.

## Use it from AI agents (MCP)

Give Claude, Cursor or any MCP client live Amazon chart data:

```json
{"mcpServers": {"apify": {"url": "https://mcp.apify.com?tools=zet46/amazon-best-sellers-scraper"}}}
```

Then ask things like *"What's the #1 book on amazon.de this week, and who's the author?"*

## No-code

The scraper can also be run from the Apify web console: schedule it daily, export to CSV or Excel, or send results to Google Sheets, Slack, Zapier, Make or n8n.

---
Output above is from real runs. Prices and rankings change constantly. MIT licensed.


## Tutorials

Deep-dive write-up on dev.to:

- [Track Amazon Best Sellers in 17 country stores with Python and SQLite](https://dev.to/huynhtanan/track-amazon-best-sellers-in-17-country-stores-with-python-odm)

Full series (all four actors): [Apify + Python: scrapers, trackers, and Claude Desktop](https://dev.to/huynhtanan/series/45271).

## See also

More repos from this account:

- [google-hotels-api](https://github.com/huynhtanan/google-hotels-api) - Python and Node.js examples for Google Hotels and Vacation Rentals
- [walmart-deals-tracker](https://github.com/huynhtanan/walmart-deals-tracker) - Daily Walmart Rollback deal tracking with Python and SQLite
- [google-hotels-mcp](https://github.com/huynhtanan/google-hotels-mcp) - MCP server for Claude Desktop: Google Hotels search, price calendar, and vacation rentals
