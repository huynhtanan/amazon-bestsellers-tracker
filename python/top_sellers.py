"""Pull today's Amazon Best Sellers for one category and marketplace.

    pip install "apify-client>=3"
    export APIFY_TOKEN=...        # https://console.apify.com/settings/integrations
    python top_sellers.py
"""
import os

from apify_client import ApifyClient

MARKETPLACE = "co.uk"
CATEGORY = "electronics"
LIST_TYPE = "bestsellers"


def _attr(obj, snake, camel):
    if isinstance(obj, dict):
        return obj.get(camel) or obj.get(snake)
    return getattr(obj, snake, None) or getattr(obj, camel, None)


def main():
    client = ApifyClient(os.environ["APIFY_TOKEN"])
    run = client.actor("zet46/amazon-best-sellers-scraper").call(run_input={
        "marketplace": MARKETPLACE,
        "listType": LIST_TYPE,
        "categorySlugs": [CATEGORY],
        "maxItemsPerCategory": 20,
    })
    dataset_id = _attr(run, "default_dataset_id", "defaultDatasetId")
    print(f"Amazon {MARKETPLACE} top {LIST_TYPE} in {CATEGORY}:")
    for it in client.dataset(dataset_id).iterate_items():
        price = it.get("priceText") or "    --"
        rating = f'{it["rating"]} ({it["reviewsCount"]:,})' if it.get("rating") else ""
        print(f'  #{it["rank"]:>3}  {it["title"][:60]:60}  {price:>8}  {rating}')


if __name__ == "__main__":
    main()
