
import os
import json
import time
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

# iPhone Duo 256 GB Night Sky
MODEL = "MK2E4X/A"
STORE_NAME = "marina bay"

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

APPLE_LINK = "https://www.apple.com/sg/shop/buy-iphone/iphone-duo"
STATE_FILE = Path("state.json")

MAX_ATTEMPTS = 3
RETRY_DELAYS = [15, 45]
FAILURE_THRESHOLD = 3

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
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    result = request_json(url, {
        "chat_id": CHAT_ID,
        "text": message
    })

    if not result.get("ok"):
        raise RuntimeError("Telegram message failed")

    print("Telegram notification sent", flush=True)


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())

    return {
        "available": False,
        "failures": 0,
        "failure_alert_sent": False
    }


def save_state(state):
    STATE_FILE.write_text(
        json.dumps(state, indent=2) + "\n"
    )


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
            print(f"Apple request failed: {error}", flush=True)

            if attempt == MAX_ATTEMPTS:
                raise RuntimeError(
                    "Apple check failed after all retries"
                ) from error

            time.sleep(RETRY_DELAYS[attempt - 1])


def get_availability():
    result = fetch_apple_stock()
    stores = result.get("body", {}).get("stores")

    if not isinstance(stores, list):
        raise RuntimeError("Unexpected Apple response format")

    for store in stores:
        name = store.get("storeName", "")

        if STORE_NAME not in name.lower():
            continue

        availability = store.get(
            "partsAvailability", {}
        ).get(MODEL)

        if not isinstance(availability, dict):
            raise RuntimeError("Model availability data missing")

        status = availability.get("pickupDisplay")

        print(f"Store: {name}, pickup: {status}", flush=True)

        if status == "available":
            return True

        if status == "unavailable":
            return False

        raise RuntimeError(
            f"Unknown pickup status: {status}"
        )

    raise RuntimeError("Marina Bay Sands store not found")


def main():
    state = load_state()

    try:
        available = get_availability()

    except Exception as error:
        print(f"Stock check unavailable: {error}", flush=True)

        state["failures"] = min(
            state.get("failures", 0) + 1,
            FAILURE_THRESHOLD
        )

        if (
            state["failures"] >= FAILURE_THRESHOLD
            and not state.get("failure_alert_sent", False)
        ):
            send_telegram(
                "⚠️ iPhone Duo Alert\n\n"
                "Не удалось проверить наличие в Apple "
                "Marina Bay Sands 3 запуска подряд.\n\n"
                "Apple может временно блокировать запросы. "
                "Мониторинг требует внимания."
            )

            state["failure_alert_sent"] = True

        save_state(state)
        return

    # Successful Apple response resets failure counter
    if state.get("failure_alert_sent", False):
        print("Apple monitoring recovered", flush=True)

    state["failures"] = 0
    state["failure_alert_sent"] = False

    previously_available = state.get("available", False)

    if available and not previously_available:
        send_telegram(
            "🚨 iPhone Duo 256GB Night Sky В НАЛИЧИИ!\n\n"
            "📍 Apple Marina Bay Sands, Singapore\n\n"
            "✅ Доступен для самовывоза!\n\n"
            "Купить: " + APPLE_LINK
        )

    elif available:
        print(
            "Still available — notification already sent",
            flush=True
        )

    else:
        print("Currently unavailable", flush=True)

    state["available"] = available
    save_state(state)


if __name__ == "__main__":
    main()
