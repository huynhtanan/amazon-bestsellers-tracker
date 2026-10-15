"""Compare the Amazon Best Sellers top 10 of one category across many marketplaces.

Prints a one-row-per-marketplace table showing the leader title, local price, rating
and review count — useful for finding brands that top the chart in one country but
nowhere else, or for a buyer who wants to see pricing in GBP, EUR and USD side by side.

    pip install "apify-client>=3"
    export APIFY_TOKEN=...
    python compare_markets.py
"""
import os

from apify_client import ApifyClient

MARKETS = ["com", "co.uk", "fr", "it", "co.jp"]
CATEGORY = "electronics"
TOP_N = 5


def _attr(obj, snake, camel):
    if isinstance(obj, dict):
        return obj.get(camel) or obj.get(snake)
    return getattr(obj, snake, None) or getattr(obj, camel, None)


def main():
    client = ApifyClient(os.environ["APIFY_TOKEN"])
    run = client.actor("zet46/amazon-best-sellers-scraper").call(run_input={
        "listType": "bestsellers",
        "categoryUrls": [f"https://www.amazon.{tld}/gp/bestsellers/{CATEGORY}" for tld in MARKETS],
        "maxItemsPerCategory": TOP_N,
    })
    dataset_id = _attr(run, "default_dataset_id", "defaultDatasetId")
    items = list(client.dataset(dataset_id).iterate_items())

    print(f"\nAmazon best sellers / {CATEGORY} — top {TOP_N} per marketplace\n")
    for mp in MARKETS:
        print(f"  amazon.{mp}:")
        rows = sorted((it for it in items if it["marketplace"] == mp), key=lambda it: it["rank"])
        for it in rows:
            price = it.get("priceText") or "    --"
            if it.get("rating"):
                reviews = f' ({it["reviewsCount"]:,})' if it.get("reviewsCount") else ""
                rating = f'{it["rating"]}{reviews}'
            else:
                rating = ""
            print(f'    #{it["rank"]}  {it["title"][:52]:52}  {price:>10}  {rating}')
        print()


if __name__ == "__main__":
    main()
