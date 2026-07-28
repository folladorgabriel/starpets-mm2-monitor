import json
import os
import sys
import time
from pathlib import Path

import requests

API_URL = "https://mm2-market.apineural.com/api/v2/store/items/all"
DISCORD_WEBHOOK = os.environ["DISCORD_WEBHOOK"]
DISCOUNT_THRESHOLD = 0.5
MIN_PRICE = 4.0
ITEM_TYPES = ["weapon", "pet", "misc"]
PAGE_SIZE = 72
EMBEDS_PER_MESSAGE = 10
DISCORD_MENTION = "<@1443748218843168839>"
STATE_FILE = Path(__file__).parent / "state.json"
ALERTS_LOG_FILE = Path(__file__).parent / "docs" / "alerts_log.json"
ALERTS_LOG_MAX = 200
HEADERS = {"accept": "application/json", "content-type": "application/json"}

RARITY_COLORS = {
    "common": 0x95A5A6,
    "uncommon": 0x2ECC71,
    "rare": 0x3498DB,
    "godly": 0xE91E63,
    "ancient": 0xF1C40F,
    "vintage": 0x9B59B6,
    "chroma": 0x1ABC9C,
    "unique": 0xE67E22,
    "exclusive": 0xE74C3C,
    "ultimate": 0x2C3E50,
    "unusual": 0xD35400,
}


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


def fetch_all_items():
    items = []
    for item_type in ITEM_TYPES:
        items.extend(fetch_type(item_type))
    return items


def load_json(path, default):
    if path.exists():
        return json.loads(path.read_text())
    return default


def save_json(path, data):
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(data))


def build_embed(item, discount):
    return {
        "title": item["name"],
        "url": "https://starpets.gg/pt/mm2",
        "description": f"**{discount * 100:.0f}% abaixo do preço médio de mercado**",
        "color": RARITY_COLORS.get(item.get("rare"), 0x7289DA),
        "thumbnail": {"url": item.get("imageUri", "")},
        "fields": [
            {"name": "Preço", "value": f"${item['price']:.2f}", "inline": True},
            {"name": "Média de mercado", "value": f"${item['avgPrice']:.2f}", "inline": True},
            {"name": "Raridade", "value": item.get("rare", "?"), "inline": True},
            {"name": "Categoria", "value": item.get("type", "?"), "inline": True},
        ],
    }


def send_discord_batch(embeds):
    for i in range(0, len(embeds), EMBEDS_PER_MESSAGE):
        chunk = embeds[i:i + EMBEDS_PER_MESSAGE]
        payload = {"embeds": chunk}
        if i == 0:
            payload["content"] = DISCORD_MENTION
        for attempt in range(3):
            resp = requests.post(DISCORD_WEBHOOK, json=payload, timeout=15)
            if resp.status_code == 429:
                retry_after = resp.json().get("retry_after", 1)
                time.sleep(retry_after + 0.5)
                continue
            resp.raise_for_status()
            break
        else:
            raise requests.HTTPError(f"Discord seguiu retornando 429 após 3 tentativas para lote {i // EMBEDS_PER_MESSAGE}")
        time.sleep(1)


def log_alerts(new_alerts):
    log = load_json(ALERTS_LOG_FILE, [])
    now = int(time.time() * 1000)
    for item, discount in new_alerts:
        log.append({
            "t": now,
            "name": item["name"],
            "type": item.get("type", "?"),
            "rare": item.get("rare", "?"),
            "price": item["price"],
            "avgPrice": item["avgPrice"],
            "discount": round(discount, 4),
            "imageUri": item.get("imageUri", ""),
        })
    log = log[-ALERTS_LOG_MAX:]
    save_json(ALERTS_LOG_FILE, log)


def main():
    state = load_json(STATE_FILE, {})
    items = fetch_all_items()
    seen_ids = set()
    new_alerts = []

    for item in items:
        good_id = item.get("goodId")
        price = item.get("price")
        avg_price = item.get("avgPrice")
        if not good_id or not price or not avg_price or avg_price <= 0:
            continue

        key = f"{item.get('type', '?')}:{good_id}"
        seen_ids.add(key)
        if price < MIN_PRICE:
            continue

        discount = (avg_price - price) / avg_price
        if discount < DISCOUNT_THRESHOLD:
            continue

        already_alerted_at = state.get(key)
        if already_alerted_at is not None and already_alerted_at <= price:
            continue

        new_alerts.append((item, discount))
        state[key] = price

    if new_alerts:
        try:
            embeds = [build_embed(item, discount) for item, discount in new_alerts]
            send_discord_batch(embeds)
            log_alerts(new_alerts)
        except requests.RequestException as exc:
            print(f"Falha ao notificar Discord: {exc}", file=sys.stderr)
            new_alerts = []

    state = {k: p for k, p in state.items() if k in seen_ids}
    save_json(STATE_FILE, state)
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {len(items)} itens verificados, {len(new_alerts)} alerta(s) enviado(s)")


if __name__ == "__main__":
    main()
