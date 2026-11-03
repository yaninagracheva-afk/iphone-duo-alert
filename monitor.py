
import os
import json
import time
import urllib.request
import urllib.parse
import urllib.error

# iPhone Duo 256 GB Night Sky — Singapore
MODEL = "MK2E4X/A"

# Telegram settings
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

# Check ONLY Apple Marina Bay Sands
STORE_NAME = "marina bay"

APPLE_LINK = (
    "https://www.apple.com/sg/shop/buy-iphone/iphone-duo"
)

# Retry settings
MAX_ATTEMPTS = 3
RETRY_DELAYS = [15, 45]

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
        url,
        data=data,
        headers=headers
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


def fetch_apple_stock():
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            print(
                f"Checking Apple: attempt {attempt}/{MAX_ATTEMPTS}",
                flush=True
            )

            result = request_json(URL)

            print("Apple responded successfully", flush=True)
            return result

        except (
            urllib.error.HTTPError,
            urllib.error.URLError,
            TimeoutError,
            json.JSONDecodeError
        ) as error:

            print(
                f"Apple request failed: {error}",
                flush=True
            )

            if attempt == MAX_ATTEMPTS:
                raise RuntimeError(
                    "Apple stock check failed after "
                    f"{MAX_ATTEMPTS} attempts"
                ) from error

            delay = RETRY_DELAYS[attempt - 1]

            print(
                f"Retrying in {delay} seconds...",
                flush=True
            )

            time.sleep(delay)


def check_stock():
    result = fetch_apple_stock()

    stores = result.get("body", {}).get("stores")

    if not isinstance(stores, list):
        raise RuntimeError(
            "Apple inventory response format changed"
        )

    found = []
    checked = 0

    for store in stores:
        name = store.get("storeName", "")
        name_lower = name.lower()

        # Only Apple Marina Bay Sands
        if STORE_NAME not in name_lower:
            continue

        checked += 1

        availability = store.get(
            "partsAvailability", {}
        ).get(MODEL, {})

        pickup_status = availability.get(
            "pickupDisplay", "unknown"
        )

        print(
            f"Store: {name}, pickup: {pickup_status}",
            flush=True
        )

        if pickup_status == "available":
            found.append(name)

    if checked == 0:
        raise RuntimeError(
            "Apple Marina Bay Sands not found in response"
        )

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

        print("Telegram stock alert sent", flush=True)

    else:
        print(
            "iPhone not confirmed available for pickup",
            flush=True
        )


if __name__ == "__main__":
    check_stock()
