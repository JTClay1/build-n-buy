import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

try:
    from dotenv import load_dotenv

    SERVER_DIR = Path(__file__).resolve().parents[1]
    load_dotenv(SERVER_DIR / ".env", override=True)
except ImportError:
    pass


SCRAPERAPI_ENDPOINT = "https://api.scraperapi.com"


class PriceScrapeError(Exception):
    pass


def clean_price_value(value):
    if value in [None, ""]:
        return None

    if isinstance(value, (int, float)):
        price = float(value)
        return round(price, 2) if price > 0 else None

    text = str(value).strip()

    text = (
        text
        .replace(",", "")
        .replace("$", "")
        .replace("£", "")
        .replace("€", "")
        .replace("USD", "")
        .replace("usd", "")
        .replace("GBP", "")
        .replace("gbp", "")
        .replace("EUR", "")
        .replace("eur", "")
        .strip()
    )

    match = re.search(r"(\d+(?:\.\d{1,2})?)", text)

    if not match:
        return None

    price = float(match.group(1))

    if price <= 0:
        return None

    return round(price, 2)


def validate_product_url(product_url):
    parsed_url = urlparse(product_url or "")

    if parsed_url.scheme not in ["http", "https"] or not parsed_url.netloc:
        raise PriceScrapeError("Product URL must be a valid http or https URL.")

    path = parsed_url.path.strip("/").lower()

    blocked_path_fragments = [
        "cart",
        "checkout",
        "login",
        "signin",
        "account",
        "help",
        "support",
        "customer-service",
    ]

    if not path:
        raise PriceScrapeError(
            "This looks like a retailer homepage. Use a direct product page URL."
        )

    if any(fragment in path for fragment in blocked_path_fragments):
        raise PriceScrapeError(
            "This URL does not look like a product page. Use a direct product page URL."
        )

    return True


def is_product_json_ld(data):
    item_type = data.get("@type")

    if isinstance(item_type, list):
        return any(str(value).lower() == "product" for value in item_type)

    return str(item_type).lower() == "product"


def find_offer_price(offers):
    if isinstance(offers, list):
        for offer in offers:
            price = find_offer_price(offer)

            if price:
                return price

    if not isinstance(offers, dict):
        return None

    for key in ["price", "lowPrice", "highPrice"]:
        if key in offers:
            price = clean_price_value(offers.get(key))

            if price:
                return price

    price_specification = offers.get("priceSpecification")

    if price_specification:
        price = find_offer_price(price_specification)

        if price:
            return price

    return None


def extract_price_from_json_ld(soup):
    scripts = soup.find_all("script", type="application/ld+json")

    for script in scripts:
        raw_json = script.string or script.get_text()

        if not raw_json:
            continue

        try:
            data = json.loads(raw_json.strip())
        except json.JSONDecodeError:
            continue

        candidates = data if isinstance(data, list) else [data]

        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue

            if is_product_json_ld(candidate):
                price = find_offer_price(candidate.get("offers"))

                if price:
                    return price

            graph_items = candidate.get("@graph", [])

            if isinstance(graph_items, list):
                for graph_item in graph_items:
                    if isinstance(graph_item, dict) and is_product_json_ld(graph_item):
                        price = find_offer_price(graph_item.get("offers"))

                        if price:
                            return price

    return None


def extract_price_from_meta_tags(soup):
    meta_selectors = [
        {"property": "product:price:amount"},
        {"property": "og:price:amount"},
        {"name": "product:price:amount"},
        {"name": "og:price:amount"},
        {"itemprop": "price"},
    ]

    for selector in meta_selectors:
        tag = soup.find("meta", attrs=selector)

        if not tag:
            continue

        price = clean_price_value(tag.get("content"))

        if price:
            return price

    itemprop_price = soup.find(attrs={"itemprop": "price"})

    if itemprop_price:
        price = clean_price_value(
            itemprop_price.get("content") or itemprop_price.get_text(" ", strip=True)
        )

        if price:
            return price

    return None


def extract_price_from_common_elements(soup):
    selectors = [
        "[data-testid*='price' i]",
        "[data-test*='price' i]",
        "[data-automation-id*='price' i]",
        "[class*='price' i]",
        "[id*='price' i]",
    ]

    for selector in selectors:
        elements = soup.select(selector)

        for element in elements[:80]:
            text = (
                element.get("content")
                or element.get("aria-label")
                or element.get_text(" ", strip=True)
            )

            if not text:
                continue

            money_matches = re.findall(
                r"[$£€]\s?(\d{1,5}(?:,\d{3})*(?:\.\d{2})?)",
                text
            )

            for match in money_matches:
                price = clean_price_value(match)

                if price and 5 <= price <= 100000:
                    return price

    return None


def extract_price_from_raw_text(html):
    patterns = [
        r'"current_retail"\s*:\s*"?[$£€]?(\d+(?:\.\d{1,2})?)"?',
        r'"current_price"\s*:\s*"?[$£€]?(\d+(?:\.\d{1,2})?)"?',
        r'"currentPrice"\s*:\s*"?[$£€]?(\d+(?:\.\d{1,2})?)"?',
        r'"salePrice"\s*:\s*"?[$£€]?(\d+(?:\.\d{1,2})?)"?',
        r'"price"\s*:\s*"?[$£€]?(\d+(?:\.\d{1,2})?)"?',
        r'"formatted_current_price"\s*:\s*"[$£€](\d{1,5}(?:,\d{3})*(?:\.\d{2})?)"',
        r'"formattedCurrentPrice"\s*:\s*"[$£€](\d{1,5}(?:,\d{3})*(?:\.\d{2})?)"',
    ]

    candidates = []

    for pattern in patterns:
        matches = re.findall(pattern, html)

        for match in matches[:50]:
            price = clean_price_value(match)

            if price and 5 <= price <= 100000:
                candidates.append(price)

    if not candidates:
        return None

    return min(candidates)


def extract_price_from_html(html):
    soup = BeautifulSoup(html, "html.parser")

    extraction_attempts = [
        extract_price_from_json_ld,
        extract_price_from_meta_tags,
        extract_price_from_common_elements,
    ]

    for extractor in extraction_attempts:
        price = extractor(soup)

        if price:
            return price

    return extract_price_from_raw_text(html)


def validate_scraped_price(price, previous_price=None):
    if not price:
        raise PriceScrapeError("Could not find a valid product price on this page.")

    if price < 5:
        raise PriceScrapeError(
            f"Scraped price ${price:,.2f} looks suspiciously low."
        )

    if previous_price and previous_price >= 50:
        low_threshold = previous_price * 0.35
        high_threshold = previous_price * 3

        if price < low_threshold:
            raise PriceScrapeError(
                f"Scraped price ${price:,.2f} is suspiciously lower than the previous price ${previous_price:,.2f}. Use a direct product URL or check the page manually."
            )

        if price > high_threshold:
            raise PriceScrapeError(
                f"Scraped price ${price:,.2f} is suspiciously higher than the previous price ${previous_price:,.2f}. Use a direct product URL or check the page manually."
            )

    return True


def scrape_price_from_url(product_url, render=None, previous_price=None):
    api_key = os.getenv("SCRAPERAPI_KEY")

    if not api_key or api_key == "your_scraperapi_key_here":
        raise PriceScrapeError(
            "SCRAPERAPI_KEY is missing or still set to the placeholder value."
        )

    if not product_url:
        raise PriceScrapeError("Product URL is required for live price refresh.")

    validate_product_url(product_url)

    render_setting = os.getenv("PRICE_SCRAPE_RENDER", "false").lower() == "true"

    if render is not None:
        render_setting = bool(render)

    country_code = os.getenv("PRICE_SCRAPE_COUNTRY", "us")

    params = {
        "api_key": api_key,
        "url": product_url,
        "country_code": country_code,
    }

    if render_setting:
        params["render"] = "true"

    try:
        response = requests.get(
            SCRAPERAPI_ENDPOINT,
            params=params,
            timeout=70
        )
    except requests.RequestException as error:
        raise PriceScrapeError(f"ScraperAPI request failed: {error}")

    if response.status_code >= 400:
        raise PriceScrapeError(
            f"ScraperAPI returned status {response.status_code}. "
            "This retailer page may block scraping or require a different product URL."
        )

    price = extract_price_from_html(response.text)

    validate_scraped_price(price, previous_price=previous_price)

    return {
        "price": price,
        "render_used": render_setting,
        "country_code": country_code,
        "source_url": product_url,
    }