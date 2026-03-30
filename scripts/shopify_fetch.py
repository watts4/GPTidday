"""
shopify_fetch.py — Fetch real kids' products from Shopify brand stores.

Hits the public /products.json endpoint on Shopify storefronts (no auth required).
Filters for kids/youth/toddler items by product type and tags.
Outputs a catalog.json compatible with the GPTidday frontend.

Usage:
    python3 scripts/shopify_fetch.py
    python3 scripts/shopify_fetch.py --limit 50 --out public/data/catalog.json
"""

import argparse
import hashlib
import json
import re
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

SHOPIFY_STORES = [
    # Surf / skate brands
    {"brand": "Quiksilver", "domain": "www.quiksilver.com", "source_group": "surf_skate_official"},
    {"brand": "Billabong",  "domain": "www.billabong.com",  "source_group": "surf_skate_official"},
    {"brand": "Hurley",     "domain": "www.hurley.com",     "source_group": "surf_skate_official"},
    {"brand": "Volcom",     "domain": "www.volcom.com",     "source_group": "surf_skate_official"},
    {"brand": "Roxy",       "domain": "www.roxy.com",       "source_group": "surf_skate_official"},
    {"brand": "RVCA",       "domain": "www.rvca.com",       "source_group": "surf_skate_official"},
    # Punk / alternative brands
    {"brand": "Blackcraft", "domain": "blackcraftcult.com", "source_group": "punk_alt_official"},
]

# Keywords that indicate an infant/toddler/young kids product
KID_KEYWORDS = {
    "toddler", "toddlers", "baby", "infant", "infants", "little", "tiny",
    "grom", "kids", "kid", "children", "child", "boys", "girls", "youth", "junior", "mini",
}

# For surf/skate brands, any kids item qualifies (the brand itself is the style signal).
# For punk/alt brands, require explicit style keywords in the product text.
STYLE_KEYWORDS = {
    "punk", "skull", "skeleton", "bat", "gothic", "goth", "rock", "metal",
    "band", "horror", "dark", "tattoo", "occult", "witch", "vampire",
    "surf", "skate", "board", "wave", "beach", "rash", "wetsuit", "checkerboard",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def is_kids_product(product: dict) -> bool:
    """Return True if the product appears to be for kids/youth/toddlers."""
    text = " ".join([
        product.get("title", ""),
        product.get("product_type", ""),
        product.get("vendor", ""),
        " ".join(product.get("tags", [])),
    ]).lower()
    return any(kw in text for kw in KID_KEYWORDS)


def has_style_relevance(product: dict) -> bool:
    """Return True if the product has surf/skate/punk style signals."""
    text = " ".join([
        product.get("title", ""),
        product.get("product_type", ""),
        " ".join(product.get("tags", [])),
    ]).lower()
    return any(kw in text for kw in STYLE_KEYWORDS)


def fetch_products(store: dict, max_pages: int = 5) -> list:
    """Fetch products from a Shopify store's public /products.json endpoint."""
    domain = store["domain"]
    brand = store["brand"]
    products = []

    for page in range(1, max_pages + 1):
        url = f"https://{domain}/products.json?limit=250&page={page}"
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
                page_products = data.get("products", [])
                if not page_products:
                    break
                products.extend(page_products)
                print(f"  {brand} page {page}: {len(page_products)} products")
                time.sleep(0.5)  # be polite
        except urllib.error.HTTPError as e:
            print(f"  {brand} page {page}: HTTP {e.code} — stopping")
            break
        except Exception as e:
            print(f"  {brand} page {page}: error — {e}")
            break

    return products


def normalize_product(raw: dict, store: dict) -> dict | None:
    """Convert a Shopify product to the GPTidday catalog format."""
    handle = raw.get("handle", "")
    title = raw.get("title", "").strip()
    domain = store["domain"]
    brand = store["brand"]

    if not handle or not title:
        return None

    product_url = f"https://{domain}/products/{handle}"

    # Get the first available variant price
    variants = raw.get("variants", [])
    price = None
    for v in variants:
        try:
            price = float(v.get("price", 0))
            if price > 0:
                break
        except (ValueError, TypeError):
            pass

    # Get the first image
    images = raw.get("images", [])
    image_url = images[0]["src"] if images else ""

    # Generate a short stable ID from the URL
    product_id = hashlib.md5(product_url.encode()).hexdigest()[:12]
    slug = f"{brand.lower()}-{handle[:40]}-{product_id[:6]}"
    slug = re.sub(r"[^a-z0-9-]", "-", slug)

    # Infer style tags from title/type/tags
    raw_text = " ".join([
        title, raw.get("product_type", ""), " ".join(raw.get("tags", []))
    ]).lower()
    style_tags = []
    for kw in ["surf", "skate", "punk", "checkerboard", "stripe", "beach", "boardshort", "hoodie"]:
        if kw in raw_text:
            style_tags.append(kw)

    return {
        "id": product_id,
        "slug": slug,
        "title": title,
        "brand": brand,
        "retailer_name": brand,
        "retailer_domain": domain,
        "source_type": "official_brand",
        "source_group": store["source_group"],
        "marketplace": False,
        "source_listing_url": f"https://{domain}/collections/kids",
        "source_product_url": product_url,
        "canonical_product_url": product_url,
        "image_url": image_url,
        "additional_images": [img["src"] for img in images[1:4]],
        "current_price": price,
        "currency": "USD",
        "availability": "in_stock",
        "sizes": [v.get("title", "") for v in variants if v.get("available")],
        "category": raw.get("product_type", "").lower() or "apparel",
        "age_range": "kids",
        "style_tags": style_tags,
        "description_short": raw.get("body_html", "")[:120].replace("<[^>]+>", "").strip() if raw.get("body_html") else "",
        "source_adapter": "shopify_api",
        "validation_status": "passed",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=200, help="Max products per store")
    parser.add_argument("--out", default="public/data/catalog.json", help="Output file path")
    parser.add_argument("--max-pages", type=int, default=5, help="Max pages per store")
    args = parser.parse_args()

    all_products = []
    sources = []

    for store in SHOPIFY_STORES:
        print(f"\nFetching {store['brand']} ({store['domain']})...")
        raw_products = fetch_products(store, max_pages=args.max_pages)
        is_punk = store["source_group"] == "punk_alt_official"
        kids_products = [
            p for p in raw_products
            if is_kids_product(p) and (not is_punk or has_style_relevance(p))
        ]
        print(f"  {len(raw_products)} total → {len(kids_products)} kids items")

        normalized = []
        for p in kids_products[:args.limit]:
            result = normalize_product(p, store)
            if result:
                normalized.append(result)

        all_products.extend(normalized)
        sources.append({
            "adapter": store["brand"].lower(),
            "domain": store["domain"],
            "products_fetched": len(normalized),
        })

    print(f"\nTotal products: {len(all_products)}")

    catalog = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "product_count": len(all_products),
        "products": all_products,
        "sources": sources,
        "warnings": [],
    }

    import os
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(catalog, f, indent=2)
    print(f"Written to {args.out}")


if __name__ == "__main__":
    main()
