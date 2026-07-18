import json
import os
import re
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from bs4 import BeautifulSoup

try:
    from dotenv import load_dotenv

    SERVER_DIR = Path(__file__).resolve().parents[1]
    # The server-specific file wins locally; hosted environments can omit it and
    # provide the same settings through process variables.
    load_dotenv(SERVER_DIR / ".env", override=True)
except ImportError:
    pass

try:
    from openai import OpenAI
except ImportError:
    # AI extraction is a final fallback, not a runtime requirement.
    OpenAI = None


SCRAPERAPI_ENDPOINT = "https://api.scraperapi.com"
SCRAPERAPI_WALMART_PRODUCT_ENDPOINT = (
    "https://api.scraperapi.com/structured/walmart/product"
)

TARGET_REDSKY_ENDPOINT = (
    "https://redsky.target.com/redsky_aggregations/v1/web/pdp_client_v1"
)

TARGET_REDSKY_KEY = os.getenv(
    "TARGET_REDSKY_KEY",
    "9f36aeafbe60771e321a7cc95a78140772ab3e96"
)

TARGET_STORE_ID = os.getenv("TARGET_STORE_ID", "3991")


class PriceScrapeError(Exception):
    pass


def clean_price_value(value):
    # Normalize the heterogeneous numeric and localized string values returned by
    # retailer APIs, metadata, and embedded page state.
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

    # Reject obvious account/navigation pages early; they frequently contain
    # unrelated dollar amounts that can be mistaken for product prices.
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


def detect_retailer(product_url):
    netloc = urlparse(product_url).netloc.lower()

    if "walmart." in netloc:
        return "walmart"

    if "target." in netloc:
        return "target"

    if "bestbuy." in netloc:
        return "bestbuy"

    if "books.toscrape." in netloc:
        return "books_to_scrape"

    return "generic"


def extract_walmart_product_id(product_url):
    parsed_url = urlparse(product_url)
    path = parsed_url.path

    patterns = [
        r"/ip/(?:[^/]+/)?(\d+)",
        r"/(\d{6,})/?$",
    ]

    for pattern in patterns:
        match = re.search(pattern, path)

        if match:
            return match.group(1)

    return None

def extract_target_tcin(product_url):
    parsed_url = urlparse(product_url)
    path = parsed_url.path

    # Target's canonical product ID is usually the /A-######## ID.
    # Prefer this over preselect because preselect can point at a related
    # variant and cause the wrong price to be pulled.
    path_match = re.search(r"A-(\d+)", path)

    if path_match:
        return path_match.group(1)

    path_number_match = re.search(r"/(\d{6,})/?$", path)

    if path_number_match:
        return path_number_match.group(1)

    query_params = parse_qs(parsed_url.query)
    preselect_values = query_params.get("preselect")

    if preselect_values and preselect_values[0].isdigit():
        return preselect_values[0]

    return None


def build_target_redsky_url(product_url, tcin):
    params = {
        "key": TARGET_REDSKY_KEY,
        "tcin": tcin,
        "is_bot": "false",
        "store_id": TARGET_STORE_ID,
        "pricing_store_id": TARGET_STORE_ID,
        "has_pricing_store_id": "true",
        "has_financing_options": "true",
        "include_obsolete": "true",
        "skip_personalized": "true",
        "skip_variation_hierarchy": "true",
        "channel": "WEB",
        "page": f"/p/A-{tcin}",
        "visitor_id": "0180000000000201A000000000000000",
    }

    return f"{TARGET_REDSKY_ENDPOINT}?{urlencode(params)}"

def get_target_tcin_candidates(product_url):
    parsed_url = urlparse(product_url)
    query_params = parse_qs(parsed_url.query)
    candidates = []

    preselect_values = query_params.get("preselect")

    # Keep every plausible variant ID because Target URLs can carry both a selected
    # variant and a canonical product ID; response matching decides which exists.
    if preselect_values and preselect_values[0].isdigit():
        candidates.append(preselect_values[0])

    path_match = re.search(r"A-(\d+)", parsed_url.path)

    if path_match:
        candidates.append(path_match.group(1))

    path_number_match = re.search(r"/(\d{6,})/?$", parsed_url.path)

    if path_number_match:
        candidates.append(path_number_match.group(1))

    unique_candidates = []

    for candidate in candidates:
        if candidate and candidate not in unique_candidates:
            unique_candidates.append(candidate)

    return unique_candidates


def find_target_objects_by_tcin(data, tcin):
    # RedSky response nesting changes across product categories, so locate exact
    # identifiers recursively instead of depending on one brittle JSON path.
    matches = []

    if isinstance(data, list):
        for item in data:
            matches.extend(find_target_objects_by_tcin(item, tcin))

        return matches

    if not isinstance(data, dict):
        return matches

    item_tcin = data.get("tcin") or data.get("TCIN")

    nested_item = data.get("item")

    if not item_tcin and isinstance(nested_item, dict):
        item_tcin = nested_item.get("tcin") or nested_item.get("TCIN")

    if str(item_tcin) == str(tcin):
        matches.append(data)

    for value in data.values():
        if isinstance(value, (dict, list)):
            matches.extend(find_target_objects_by_tcin(value, tcin))

    return matches


def extract_price_from_target_object(target_object):
    direct_price_keys = [
        "price",
        "price_info",
        "pricing",
        "offer_price",
        "current_price",
        "currentPrice",
        "current_retail",
        "currentRetail",
        "sale_retail",
        "reg_retail",
    ]

    for key in direct_price_keys:
        if key in target_object:
            price = find_price_deep(target_object.get(key))

            if price:
                return price

    for key, value in target_object.items():
        key_lower = str(key).lower()

        if "price" in key_lower or "retail" in key_lower:
            price = find_price_deep(value)

            if price:
                return price

    return None

def extract_target_redsky_price(data, tcin_candidates):
    for tcin in tcin_candidates:
        matching_objects = find_target_objects_by_tcin(data, tcin)

        for target_object in matching_objects:
            price = extract_price_from_target_object(target_object)

            if price:
                return price

    product = (
        data.get("data", {})
        .get("product", {})
    )

    if isinstance(product, dict):
        price_data = (
            product.get("price")
            or product.get("price_info")
            or product.get("pricing")
            or {}
        )

        price = find_price_deep(price_data)

        if price:
            return price

    return None


def scrape_target_redsky(product_url, api_key, country_code, previous_price=None):
    request_tcin = extract_target_tcin(product_url)
    tcin_candidates = get_target_tcin_candidates(product_url)

    if not request_tcin or not tcin_candidates:
        return None

    # Route the retailer API through ScraperAPI to apply the same geographic and
    # anti-bot controls as HTML requests.
    target_api_url = build_target_redsky_url(product_url, request_tcin)

    scraperapi_params = [
        ("api_key", api_key),
        ("country_code", country_code),
        ("device_type", "desktop"),
        ("url", target_api_url),
    ]

    try:
        response = requests.get(
            SCRAPERAPI_ENDPOINT,
            params=scraperapi_params,
            timeout=70
        )
    except requests.RequestException as error:
        raise PriceScrapeError(f"Target product data scrape failed: {error}")

    if response.status_code >= 400:
        return None

    try:
        data = response.json()
    except ValueError:
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            return None

    price = extract_target_redsky_price(data, tcin_candidates)

    if not price:
        return None

    validate_scraped_price(price, previous_price=previous_price)

    return {
        "price": price,
        "render_used": False,
        "country_code": country_code,
        "source_url": product_url,
        "strategy": "target_redsky_product",
        "tcin": tcin_candidates[0],
        "requested_tcin": request_tcin,
        "tcin_candidates": tcin_candidates,
    }


def build_scraperapi_params(api_key, product_url, profile, country_code):
    params = [
        ("api_key", api_key),
        ("country_code", country_code),
        ("device_type", profile.get("device_type", "desktop")),
    ]

    if profile.get("render"):
        params.append(("render", "true"))

    if profile.get("premium"):
        params.append(("premium", "true"))

    if profile.get("ultra_premium"):
        params.append(("ultra_premium", "true"))

    if profile.get("wait_for_selector"):
        params.append(("wait_for_selector", profile["wait_for_selector"]))

    # Keep target url last so ScraperAPI params are clearly separated from
    # product URL query strings.
    params.append(("url", product_url))

    return params


def get_scraper_profiles(retailer, render_override=None):
    # Profiles progress from inexpensive static requests to rendered/premium
    # requests; the first successful response controls both cost and latency.
    if render_override is not None:
        return [
            {
                "name": "manual_render" if render_override else "manual_basic",
                "render": bool(render_override),
                "premium": bool(render_override),
                "device_type": "desktop",
                "wait_for_selector": None,
            }
        ]

    if retailer == "target":
        return [
            {
                "name": "target_basic",
                "render": False,
                "premium": False,
                "device_type": "desktop",
                "wait_for_selector": None,
            },
            {
                "name": "target_mobile",
                "render": False,
                "premium": False,
                "device_type": "mobile",
                "wait_for_selector": None,
            },
            {
                "name": "target_render_price",
                "render": True,
                "premium": False,
                "device_type": "desktop",
                "wait_for_selector": "[data-test*='price'], [data-testid*='price'], [class*='price']",
            },
            {
                "name": "target_premium_render",
                "render": True,
                "premium": True,
                "device_type": "desktop",
                "wait_for_selector": "[data-test*='price'], [data-testid*='price'], [class*='price']",
            },
        ]

    if retailer == "walmart":
        return [
            {
                "name": "walmart_basic",
                "render": False,
                "premium": False,
                "device_type": "desktop",
                "wait_for_selector": None,
            },
            {
                "name": "walmart_mobile",
                "render": False,
                "premium": False,
                "device_type": "mobile",
                "wait_for_selector": None,
            },
            {
                "name": "walmart_render_price",
                "render": True,
                "premium": False,
                "device_type": "desktop",
                "wait_for_selector": "[data-testid*='price'], [itemprop='price'], [class*='price']",
            },
        ]

    return [
        {
            "name": "basic",
            "render": False,
            "premium": False,
            "device_type": "desktop",
            "wait_for_selector": None,
        },
        {
            "name": "mobile",
            "render": False,
            "premium": False,
            "device_type": "mobile",
            "wait_for_selector": None,
        },
        {
            "name": "render",
            "render": True,
            "premium": False,
            "device_type": "desktop",
            "wait_for_selector": "[class*='price'], [id*='price'], [itemprop='price']",
        },
    ]


def find_price_deep(data, path=""):
    if isinstance(data, list):
        for index, item in enumerate(data):
            price = find_price_deep(item, f"{path}[{index}]")

            if price:
                return price

    if not isinstance(data, dict):
        return None

    # Prefer semantic current/offer keys before broad formatted or nested matches
    # to reduce false positives from list prices and unrelated amounts.
    high_confidence_keys = [
        "current_retail",
        "currentRetail",
        "current_price",
        "currentPrice",
        "sale_price",
        "salePrice",
        "offerPrice",
        "finalPrice",
        "price",
        "lowPrice",
        "highPrice",
        "value",
    ]

    for key in high_confidence_keys:
        if key in data:
            price = clean_price_value(data.get(key))

            if price:
                return price

    medium_confidence_keys = [
        "formatted_current_price",
        "formattedCurrentPrice",
        "formatted_price",
        "formattedPrice",
        "priceString",
        "displayPrice",
    ]

    for key in medium_confidence_keys:
        if key in data:
            price = clean_price_value(data.get(key))

            if price:
                return price

    nested_keys = [
        "offers",
        "offer",
        "priceSpecification",
        "priceSpecifications",
        "pricing",
        "priceInfo",
        "product",
        "products",
        "item",
        "items",
        "data",
        "props",
        "pageProps",
        "initialData",
        "productDetails",
        "productData",
    ]

    for key in nested_keys:
        if key in data:
            price = find_price_deep(data.get(key), f"{path}.{key}")

            if price:
                return price

    for key, value in data.items():
        key_lower = str(key).lower()

        if "price" in key_lower or "retail" in key_lower or "offer" in key_lower:
            price = find_price_deep(value, f"{path}.{key}")

            if price:
                return price

    return None


def is_product_json_ld(data):
    item_type = data.get("@type")

    if isinstance(item_type, list):
        return any(str(value).lower() == "product" for value in item_type)

    return str(item_type).lower() == "product"


def find_offer_price(offers):
    return find_price_deep(offers)


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


def extract_json_from_script_text(raw_text):
    if not raw_text:
        return None

    stripped_text = raw_text.strip()

    if not stripped_text:
        return None

    try:
        return json.loads(stripped_text)
    except json.JSONDecodeError:
        pass

    assignment_patterns = [
        r"window\.__PRELOADED_STATE__\s*=\s*({.*?});",
        r"window\.__INITIAL_STATE__\s*=\s*({.*?});",
        r"window\.__TARGET_INITIAL_STATE__\s*=\s*({.*?});",
        r"__NEXT_DATA__\s*=\s*({.*?});",
    ]

    for pattern in assignment_patterns:
        match = re.search(pattern, stripped_text, flags=re.DOTALL)

        if not match:
            continue

        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            continue

    return None


def extract_price_from_json_scripts(soup):
    script_selectors = [
        "script#__NEXT_DATA__",
        "script#serverApp-state",
        "script[type='application/json']",
        "script",
    ]

    for selector in script_selectors:
        scripts = soup.select(selector)

        # Bound scanning on script-heavy storefronts and skip payloads that cannot
        # contain a price before attempting JSON parsing.
        for script in scripts[:80]:
            raw_text = script.string or script.get_text()

            if not raw_text:
                continue

            if (
                "price" not in raw_text.lower()
                and "retail" not in raw_text.lower()
                and "current_retail" not in raw_text.lower()
            ):
                continue

            data = extract_json_from_script_text(raw_text)

            if data is None:
                continue

            price = find_price_deep(data)

            if price:
                return price

    return None


def extract_price_from_common_elements(soup):
    selectors = [
        "[data-test='product-price']",
        "[data-test*='price' i]",
        "[data-testid*='price' i]",
        "[data-automation-id*='price' i]",
        "[itemprop='price']",
        "[class*='price' i]",
        "[id*='price' i]",
    ]

    for selector in selectors:
        elements = soup.select(selector)

        for element in elements[:100]:
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


def extract_price_from_target_text(html):
    patterns = [
        r'"current_retail"\s*:\s*(\d+(?:\.\d{1,2})?)',
        r'"currentRetail"\s*:\s*(\d+(?:\.\d{1,2})?)',
        r'"formatted_current_price"\s*:\s*"\$(\d{1,5}(?:,\d{3})*(?:\.\d{2})?)"',
        r'"formattedCurrentPrice"\s*:\s*"\$(\d{1,5}(?:,\d{3})*(?:\.\d{2})?)"',
        r'"reg_retail"\s*:\s*(\d+(?:\.\d{1,2})?)',
        r'"sale_retail"\s*:\s*(\d+(?:\.\d{1,2})?)',
        r'"price"\s*:\s*{\s*"current_retail"\s*:\s*(\d+(?:\.\d{1,2})?)',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, html)

        for match in matches[:20]:
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
        r'"offerPrice"\s*:\s*"?[$£€]?(\d+(?:\.\d{1,2})?)"?',
        r'"finalPrice"\s*:\s*"?[$£€]?(\d+(?:\.\d{1,2})?)"?',
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

    # When raw text is the only signal, the lowest current-looking candidate is
    # more likely to be the sale price than the crossed-out list price.
    return min(candidates)


def build_ai_price_snippets(html):
    lowered_html = html.lower()
    keywords = [
        "current_retail",
        "formatted_current_price",
        "currentprice",
        "saleprice",
        "offerprice",
        "product-price",
        "price",
        "$",
    ]

    snippets = []

    for keyword in keywords:
        start = 0

        while len(snippets) < 40:
            index = lowered_html.find(keyword, start)

            if index == -1:
                break

            snippet_start = max(0, index - 700)
            snippet_end = min(len(html), index + 900)
            snippets.append(html[snippet_start:snippet_end])
            start = index + len(keyword)

    unique_snippets = []
    seen = set()

    for snippet in snippets:
        normalized = snippet[:200]

        if normalized in seen:
            continue

        seen.add(normalized)
        unique_snippets.append(snippet)

    # Send small, deduplicated neighborhoods rather than an entire page to reduce
    # token use and keep the model focused on price-bearing content.
    return "\n\n---SNIPPET---\n\n".join(unique_snippets[:25])


def get_openai_text(openai_response):
    if hasattr(openai_response, "output_text") and openai_response.output_text:
        return openai_response.output_text

    try:
        response_dict = openai_response.model_dump()
    except AttributeError:
        return ""

    output_items = response_dict.get("output", [])

    for output_item in output_items:
        for content_item in output_item.get("content", []):
            if content_item.get("type") in ["output_text", "text"]:
                return content_item.get("text", "")

    return ""


def extract_price_with_ai(html, product_url, retailer):
    # Deterministic structured/HTML extractors run first; this path is only for
    # storefronts whose price is buried in unfamiliar page state.
    if OpenAI is None:
        return None

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return None

    snippets = build_ai_price_snippets(html)

    if not snippets:
        return None

    model = os.getenv(
        "OPENAI_SCRAPER_MODEL",
        os.getenv("OPENAI_ADVISOR_MODEL", "gpt-5.6-luna")
    )

    client = OpenAI(api_key=api_key, timeout=30)

    system_prompt = """
You extract a single current product price from retailer HTML snippets.

Rules:
- Return JSON only.
- Only return a price if it clearly belongs to the product page.
- Prefer current/sale/offer price over list price.
- Ignore ratings, quantities, discounts, shipping minimums, reward points, dates, review counts, and unrelated numbers.
- If no reliable current product price is visible, return null.
"""

    user_payload = {
        "retailer": retailer,
        "product_url": product_url,
        "html_snippets": snippets,
        "required_json_shape": {
            "price": "number or null",
            "confidence": "high | medium | low",
            "reason": "short string"
        }
    }

    try:
        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": json.dumps(user_payload),
                },
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "price_extraction",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["price", "confidence", "reason"],
                        "properties": {
                            "price": {
                                "type": ["number", "null"]
                            },
                            "confidence": {
                                "type": "string",
                                "enum": ["high", "medium", "low"]
                            },
                            "reason": {
                                "type": "string"
                            },
                        },
                    },
                }
            },
            max_output_tokens=300,
        )

        text = get_openai_text(response)

        if not text:
            return None

        parsed = json.loads(text)
        price = clean_price_value(parsed.get("price"))

        if not price:
            return None

        # Reject low-confidence values rather than polluting trusted price history.
        if parsed.get("confidence") == "low":
            return None

        return price

    except Exception as error:
        print(f"AI price extraction skipped: {error}")
        return None


def extract_price_from_html(html, retailer="generic", product_url=None):
    soup = BeautifulSoup(html, "html.parser")

    if retailer == "target":
        price = extract_price_from_target_text(html)

        if price:
            return price

    # Order extractors from standardized, product-scoped signals to increasingly
    # permissive DOM and text heuristics.
    extraction_attempts = [
        extract_price_from_json_ld,
        extract_price_from_meta_tags,
        extract_price_from_json_scripts,
        extract_price_from_common_elements,
    ]

    for extractor in extraction_attempts:
        price = extractor(soup)

        if price:
            return price

    price = extract_price_from_raw_text(html)

    if price:
        return price

    if product_url:
        return extract_price_with_ai(html, product_url, retailer)

    return None


def validate_scraped_price(price, previous_price=None):
    if not price:
        raise PriceScrapeError("Could not find a valid product price on this page.")

    if price < 5:
        raise PriceScrapeError(
            f"Scraped price ${price:,.2f} looks suspiciously low."
        )

    # Compare mature prices against generous bounds to catch variant IDs, payment
    # amounts, and parsing errors without rejecting ordinary promotions.
    if previous_price and previous_price >= 50:
        low_threshold = previous_price * 0.35
        high_threshold = previous_price * 3

        if price < low_threshold:
            raise PriceScrapeError(
                f"Scraped price ${price:,.2f} is suspiciously lower than the previous price ${previous_price:,.2f}."
            )

        if price > high_threshold:
            raise PriceScrapeError(
                f"Scraped price ${price:,.2f} is suspiciously higher than the previous price ${previous_price:,.2f}."
            )

    return True


def scrape_walmart_structured(product_url, api_key, country_code, previous_price=None):
    product_id = extract_walmart_product_id(product_url)

    if not product_id:
        return None

    params = {
        "api_key": api_key,
        "product_id": product_id,
        "country_code": country_code,
        "tld": "com",
    }

    try:
        response = requests.get(
            SCRAPERAPI_WALMART_PRODUCT_ENDPOINT,
            params=params,
            timeout=70
        )
    except requests.RequestException as error:
        raise PriceScrapeError(f"Walmart structured scrape failed: {error}")

    if response.status_code >= 400:
        return None

    try:
        data = response.json()
    except ValueError:
        return None

    price = find_price_deep(data)

    if not price:
        return None

    validate_scraped_price(price, previous_price=previous_price)

    return {
        "price": price,
        "render_used": False,
        "country_code": country_code,
        "source_url": product_url,
        "strategy": "walmart_structured_product",
        "product_id": product_id,
    }


def fetch_html_with_scraperapi(product_url, api_key, country_code, retailer, render=None):
    profiles = get_scraper_profiles(retailer, render_override=render)
    failures = []

    # Retry with progressively stronger profiles and retain compact failure context
    # for an actionable final error.
    for profile in profiles:
        params = build_scraperapi_params(
            api_key=api_key,
            product_url=product_url,
            profile=profile,
            country_code=country_code,
        )

        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            response = requests.get(
                SCRAPERAPI_ENDPOINT,
                params=params,
                headers=headers,
                timeout=70
            )
        except requests.RequestException as error:
            failures.append(f"{profile['name']}: request failed: {error}")
            continue

        if response.status_code >= 400:
            failures.append(
                f"{profile['name']}: ScraperAPI status {response.status_code}"
            )
            continue

        if not response.text or len(response.text) < 500:
            failures.append(f"{profile['name']}: empty or tiny response")
            continue

        return response.text, profile, failures

    raise PriceScrapeError(
        "All scraper profiles failed. "
        + " | ".join(failures[-5:])
    )


def scrape_price_from_url(product_url, render=None, previous_price=None):
    api_key = os.getenv("SCRAPERAPI_KEY")

    if not api_key or api_key == "your_scraperapi_key_here":
        raise PriceScrapeError(
            "SCRAPERAPI_KEY is missing or still set to the placeholder value."
        )

    if not product_url:
        raise PriceScrapeError("Product URL is required for live price refresh.")

    validate_product_url(product_url)

    country_code = os.getenv("PRICE_SCRAPE_COUNTRY", "us")
    retailer = detect_retailer(product_url)

    retailer_specific_errors = []

    # Retailer APIs are more precise than page scraping, so use them first and
    # fall back to the shared HTML pipeline when they are unavailable.
    if retailer == "walmart":
        try:
            structured_result = scrape_walmart_structured(
                product_url=product_url,
                api_key=api_key,
                country_code=country_code,
                previous_price=previous_price
            )

            if structured_result:
                return structured_result
        except PriceScrapeError as error:
            retailer_specific_errors.append(f"Walmart structured: {error}")

    if retailer == "target":
        try:
            target_result = scrape_target_redsky(
                product_url=product_url,
                api_key=api_key,
                country_code=country_code,
                previous_price=previous_price
            )

            if target_result:
                return target_result
        except PriceScrapeError as error:
            retailer_specific_errors.append(f"Target product data: {error}")

    html, profile, profile_failures = fetch_html_with_scraperapi(
        product_url=product_url,
        api_key=api_key,
        country_code=country_code,
        retailer=retailer,
        render=render
    )

    price = extract_price_from_html(
        html,
        retailer=retailer,
        product_url=product_url
    )

    if not price:
        extra_context = ""

        if retailer_specific_errors:
            extra_context += " Retailer-specific adapter errors: "
            extra_context += " | ".join(retailer_specific_errors)

        if profile_failures:
            extra_context += " Scraper profile failures: "
            extra_context += " | ".join(profile_failures[-5:])

        raise PriceScrapeError(
            f"Could not find a valid product price on this page using strategy {profile['name']}."
            f"{extra_context}"
        )

    validate_scraped_price(price, previous_price=previous_price)

    return {
        "price": price,
        "render_used": bool(profile.get("render")),
        "country_code": country_code,
        "source_url": product_url,
        "strategy": profile["name"],
        "retailer": retailer,
        "profile_failures": profile_failures,
    }
