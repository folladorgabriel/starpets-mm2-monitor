import json
import time
from pathlib import Path

import requests

API_URL = "https://mm2-market.apineural.com/api/v2/store/items/all"
PAGE_SIZE = 72
ITEM_TYPES = ["weapon", "pet", "misc"]
DOCS_DIR = Path(__file__).parent / "docs"
OUTPUT_FILE = DOCS_DIR / "data.json"
HISTORY_FILE = DOCS_DIR / "history.json"
HISTORY_MAX = 1000
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


def category_stats(items):
    valid = [it for it in items if (it.get("price") or 0) > 0 and (it.get("avgPrice") or 0) > 0]
    if not valid:
        return {"avgPrice": 0, "deals": 0, "count": len(items)}
    avg_price = sum(it["price"] for it in valid) / len(valid)
    deals = sum(1 for it in valid if (it["avgPrice"] - it["price"]) / it["avgPrice"] >= 0.35)
    return {"avgPrice": round(avg_price, 4), "deals": deals, "count": len(items)}


def load_json(path, default):
    if path.exists():
        return json.loads(path.read_text())
    return default


def main():
    DOCS_DIR.mkdir(exist_ok=True)
    items_by_type = {item_type: fetch_type(item_type) for item_type in ITEM_TYPES}
    updated_at = int(time.time() * 1000)

    payload = {"updatedAt": updated_at, "items": items_by_type}
    OUTPUT_FILE.write_text(json.dumps(payload))

    history = load_json(HISTORY_FILE, [])
    history.append({
        "t": updated_at,
        **{item_type: category_stats(items) for item_type, items in items_by_type.items()},
    })
    history = history[-HISTORY_MAX:]
    HISTORY_FILE.write_text(json.dumps(history))

    total = sum(len(v) for v in items_by_type.values())
    print(f"dashboard_data: {total} itens salvos em {OUTPUT_FILE}, {len(history)} pontos de histórico")


if __name__ == "__main__":
    main()
