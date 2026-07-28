import json
import time
from pathlib import Path

import requests

API_URL = "https://mm2-market.apineural.com/api/v2/store/items/all"
PAGE_SIZE = 72
ITEM_TYPES = ["weapon", "pet", "misc"]
OUTPUT_FILE = Path(__file__).parent / "docs" / "data.json"
HEADERS = {"accept": "application/json", "content-type": "application/json"}


def fetch_type(item_type):
    items = []
    page = 1
    while True:
        body = {
            "currency": "usd",
            "page": page,
            "amount": PAGE_SIZE,
            "filter": {"types": [{"type": item_type}]},
            "sort": {"popularity": "desc"},
        }
        resp = requests.post(API_URL, json=body, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        page_items = data.get("items", [])
        items.extend(page_items)
        total = data.get("count", 0)
        if page * PAGE_SIZE >= total or not page_items:
            break
        page += 1
    return items


def main():
    payload = {
        "updatedAt": int(time.time() * 1000),
        "items": {item_type: fetch_type(item_type) for item_type in ITEM_TYPES},
    }
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(payload))
    total = sum(len(v) for v in payload["items"].values())
    print(f"dashboard_data: {total} itens salvos em {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
