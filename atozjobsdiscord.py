import json
import os
import sys
import time
from pathlib import Path

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = Path(os.environ.get("ATOZ_CONFIG", ROOT / "config.json"))


def load_config():
    if not CONFIG_PATH.is_file():
        sys.exit(
            f"Missing {CONFIG_PATH}. Copy config.example.json to config.json and add your Discord webhooks."
        )
    with CONFIG_PATH.open() as handle:
        config = json.load(handle)
    required = ("url", "zipcode", "default_site", "sites", "shifts")
    missing = [key for key in required if key not in config]
    if missing:
        sys.exit(f"{CONFIG_PATH} is missing: {', '.join(missing)}")
    if config["default_site"] not in config["sites"]:
        sys.exit(f"{CONFIG_PATH} default_site {config['default_site']!r} is not in sites.")
    return config


CONFIG = load_config()
URL = CONFIG["url"]
ZIPCODE = CONFIG["zipcode"]
SITE_MAPPING = CONFIG["sites"]
SHIFT_MAPPING = CONFIG["shifts"]
DEFAULT_SITE = SITE_MAPPING[CONFIG["default_site"]]


def send_to_discord(webhook_url, content_msg, embed_data):
    if not webhook_url:
        print("Skipped Discord alert because the webhook is empty.")
        return
    payload = {
        "content": content_msg,
        "embeds": [embed_data],
        "allowed_mentions": {"parse": ["roles"]}
    }
    try:
        response = requests.post(webhook_url, json=payload)
        if response.status_code in [200, 204]:
            print("Successfully dispatched sorted job embed.")
        else:
            print(f"Webhook failed with status {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Error sending webhook: {e}")


def parse_and_sort_jobs():
    options = webdriver.ChromeOptions()
    # If it still finds nothing, try commenting out options.add_argument("--headless")
    # so you can see the browser open up and watch what it loads.
    options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(options=options)

    print(f"Fetching Amazon hiring portal for ZIP {ZIPCODE}...")
    driver.get(URL)

    # Wait up to 10 seconds for the app container or listings to load
    try:
        WebDriverWait(driver, 10).until(
            lambda d: len(d.find_elements(By.TAG_NAME, "jb-job-card")) > 0 or
                      len(d.find_elements(By.CLASS_NAME, "job-card")) > 0 or
                      len(d.find_elements(By.CSS_SELECTOR, "[class*='job']")) > 0
        )
    except Exception:
        print("Timed out waiting for job elements to render.")

    print(f"Current Page Title: {driver.title}")

    # Broaden selectors to catch React dynamic elements
    listings = driver.find_elements(By.TAG_NAME, "jb-job-card")
    if not listings:
        listings = driver.find_elements(By.CLASS_NAME, "job-card")
    if not listings:
        # Fallback to generic card-like structures if Amazon updated their class names
        listings = driver.find_elements(By.CSS_SELECTOR, "div[class*='Card'], div[class*='listing'], article")

    print(f"Found {len(listings)} raw listing elements.")

    if len(listings) == 0:
        print("Debug snippet of page body text:")
        body_text = driver.find_element(By.TAG_NAME, "body").text[:300]
        print(body_text)

    for item in listings:
        text = item.text.strip()
        if not text:
            continue

        # Detect Site
        matched_site = None
        for code, info in SITE_MAPPING.items():
            if code in text.upper():
                matched_site = info
                break

        # Detect Shift Type
        matched_shift = None
        for shift_name, info in SHIFT_MAPPING.items():
            if shift_name.lower() in text.lower():
                matched_shift = info
                break

        site_name = matched_site["name"] if matched_site else "General Warehouse"
        site_webhook = matched_site["webhook"] if matched_site else DEFAULT_SITE["webhook"]
        site_role_id = matched_site["role_id"] if matched_site else DEFAULT_SITE["role_id"]

        shift_webhook = matched_shift["webhook"] if matched_shift else None
        shift_role_id = matched_shift["role_id"] if matched_shift else None

        embed = {
            "title": f"🚨 New Amazon Job Match ({site_name})",
            "description": f"```text\n{text[:1000]}\n```",
            "color": 16734296,
            "fields": [
                {"name": "Facility", "value": site_name, "inline": True},
                {"name": "ZIP Code", "value": ZIPCODE, "inline": True}
            ],
            "url": URL
        }

        site_ping = f"<@&{site_role_id}>"
        send_to_discord(site_webhook, site_ping, embed)

        if shift_webhook and shift_role_id and shift_webhook != site_webhook:
            shift_ping = f"<@&{shift_role_id}>"
            send_to_discord(shift_webhook, shift_ping, embed)

    driver.quit()
    print("Job check and sorting cycle complete.")


if __name__ == "__main__":
    parse_and_sort_jobs()
