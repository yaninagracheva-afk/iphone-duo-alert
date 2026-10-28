
import os
import json
import urllib.request
import urllib.parse

# iPhone Duo 256 GB Night Sky — Singapore
MODEL = "MK2E4X/A"
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

# Only Apple Marina Bay Sands
STORE_NAME = "marina bay"

APPLE_LINK = "https://www.apple.com/sg/shop/buy-iphone/iphone-duo"

params = urllib.parse.urlencode({
    "parts.0": MODEL,
    "location": "Singapore",
    "pl": "true"
})

URL = (
    "https://www.apple.com/sg/shop/retail/pickup-message?"
    + params
)


def request_json(url, payload=None):
    data = None
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(
        url, data=data, headers=headers
    )

    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


def send_telegram(message):
    url = (
        f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    )

    request_json(url, {
        "chat_id": CHAT_ID,
        "text": message
    })


def check_stock():
    result = request_json(URL)
    stores = result.get("body", {}).get("stores")

    if not isinstance(stores, list):
        raise RuntimeError("Apple inventory format changed")

    found = []
    checked = 0

    for store in stores:
        name = store.get("storeName", "")
        name_lower = name.lower()

        # Check ONLY Apple Marina Bay Sands
        if STORE_NAME not in name_lower:
            continue

        checked += 1

        availability = store.get(
            "partsAvailability", {}
        ).get(MODEL, {})

        if availability.get("pickupDisplay") == "available":
            found.append(name)

    if checked == 0:
        raise RuntimeError("Apple Marina Bay Sands not found")

    print(f"Stores checked: {checked}")
    print(f"Available at: {found}")

    if found:
        message = (
            "🚨 iPhone Duo 256GB Night Sky В НАЛИЧИИ!\n\n"
            "📍 Apple Marina Bay Sands, Singapore\n\n"
            "✅ Доступен для самовывоза!\n\n"
            "Купить: " + APPLE_LINK
        )

        send_telegram(message)


if __name__ == "__main__":
    check_stock()
