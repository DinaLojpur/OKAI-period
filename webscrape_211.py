"""
Scraper for 211central.ca shelter results.
Requires: pip install playwright beautifulsoup4 pandas
          playwright install chromium
"""
import csv
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

URL = (
    "https://211central.ca/results/"
    "?searchLocation=Toronto&topicPath=502"
    "&latitude=43.6596&longitude=-79.35657"
)

OUTPUT = "shelters_211.csv"


def load_all_results(page):
    """Click 'Load More' until it disappears or stops loading new results."""
    while True:
        try:
            btn = page.locator("a:has-text('Load More'), button:has-text('Load More')")
            if btn.count() == 0:
                break
            prev_count = page.locator("[class*='result'], [class*='listing'], li.views-row").count()
            btn.first.click()
            time.sleep(2)
            new_count = page.locator("[class*='result'], [class*='listing'], li.views-row").count()
            if new_count == prev_count:
                break
        except Exception:
            break


def parse_results(html):
    soup = BeautifulSoup(html, "html.parser")
    records = []

    # 211central uses li elements with class containing 'views-row' or similar
    # Try several common selectors
    items = (
        soup.select("li.views-row")
        or soup.select("div.views-row")
        or soup.select(".search-result")
        or soup.select("article")
    )

    if not items:
        # Fallback: find all links to /record/ pages and work outward
        for link in soup.select("a[href*='/record/']"):
            container = link.find_parent("li") or link.find_parent("div") or link.find_parent("article")
            if container and container not in items:
                items.append(container)

    for item in items:
        # Name
        name_tag = item.find("a", href=lambda h: h and "/record/" in h)
        name = name_tag.get_text(strip=True) if name_tag else ""
        record_url = name_tag["href"] if name_tag else ""

        # Phone numbers
        phones = {}
        for phone_link in item.select("a[href^='tel:']"):
            number = phone_link.get_text(strip=True)
            raw = phone_link.parent.get_text(" ", strip=True) if phone_link.parent else ""
            phones[number] = raw

        phones_str = "; ".join(f"{v}" for v in phones.values())

        # Address — look for text near a postal code pattern
        import re
        address = ""
        full_text = item.get_text(" ", strip=True)
        postal_match = re.search(r"[A-Z]\d[A-Z]\s?\d[A-Z]\d", full_text)
        if postal_match:
            chunk = full_text[: postal_match.end()]
            address = chunk[-120:].strip()

        # Skip non-Toronto locations
        if "Toronto" not in address:
            continue

        # Distance
        dist_match = re.search(r"\((\d+(?:\.\d+)?)\s*km\)", full_text)
        distance_km = dist_match.group(1) if dist_match else ""

        # Website
        website = ""
        for a in item.select("a[href^='http']"):
            href = a["href"]
            if "211central" not in href:
                website = href
                break

        if name:
            records.append({
                "name": name,
                "record_url": record_url,
                "address": address,
                "distance_km": distance_km,
                "phones": phones_str,
                "website": website,
            })

    return records


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print(f"Loading {URL} ...")
        page.goto(URL, wait_until="networkidle", timeout=30000)

        print("Clicking 'Load More' until all results are loaded...")
        load_all_results(page)

        html = page.content()
        browser.close()

    print("Parsing results...")
    records = parse_results(html)
    print(f"Found {len(records)} records.")

    if not records:
        print("No records parsed — printing a snippet of the HTML for debugging:")
        soup = BeautifulSoup(html, "html.parser")
        # Print first 3000 chars of body text to help identify selectors
        print(soup.body.get_text(" ", strip=True)[:3000] if soup.body else html[:3000])
        return

    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)

    print(f"Saved to {OUTPUT}")
    for r in records[:3]:
        print(r)


if __name__ == "__main__":
    main()

