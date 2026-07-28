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
ITEM_TYPE = "weapon"
PAGE_SIZE = 72
EMBEDS_PER_MESSAGE = 10
DISCORD_MENTION = "<@1443748218843168839>"
STATE_FILE = Path(__file__).parent / "state.json"
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


def fetch_all_items():
    items = []
    page = 1
    while True:
        body = {
            "currency": "usd",
            "page": page,
            "amount": PAGE_SIZE,
            "filter": {"types": [{"type": ITEM_TYPE}]},
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


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state))


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


def main():
    state = load_state()
    items = fetch_all_items()
    seen_ids = set()
    new_alerts = []

    for item in items:
        good_id = item.get("goodId")
        price = item.get("price")
        avg_price = item.get("avgPrice")
        if not good_id or not price or not avg_price or avg_price <= 0:
            continue

        seen_ids.add(good_id)
        if price < MIN_PRICE:
            continue

        discount = (avg_price - price) / avg_price
        if discount < DISCOUNT_THRESHOLD:
            continue

        already_alerted_at = state.get(good_id)
        if already_alerted_at is not None and already_alerted_at <= price:
            continue

        new_alerts.append((item, discount))
        state[good_id] = price

    if new_alerts:
        try:
            embeds = [build_embed(item, discount) for item, discount in new_alerts]
            send_discord_batch(embeds)
        except requests.RequestException as exc:
            print(f"Falha ao notificar Discord: {exc}", file=sys.stderr)
            new_alerts = []

    state = {gid: p for gid, p in state.items() if gid in seen_ids}
    save_state(state)
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {len(items)} itens verificados, {len(new_alerts)} alerta(s) enviado(s)")


if __name__ == "__main__":
    main()
