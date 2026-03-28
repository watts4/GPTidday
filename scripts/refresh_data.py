#!/usr/bin/env python3
from __future__ import annotations

import datetime
import hashlib
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

OUTPUT_PATH = Path('data/products.generated.json')
FALLBACK_PATH = Path('data/fallback_products.json')

SEEDS = [
    {
        'url': 'https://www.vans.com/en-us/shoes-c00081/toddler-checkerboard-slip-on-v-shoe-pvn0a4vhrbla',
        'retailer_name': 'Vans',
        'brand': 'Vans',
        'age_hint': '2T-4T',
        'category_hint': 'shoes',
        'tags': ['checkerboard', 'skate', 'classic'],
        'gender': 'neutral'
    },
    {
        'url': 'https://www.vans.com/en-us/shoes-c00081/toddler-ward-shoe-pvn000d3ybka',
        'retailer_name': 'Vans',
        'brand': 'Vans',
        'age_hint': '2T-4T',
        'category_hint': 'shoes',
        'tags': ['skate', 'streetwear'],
        'gender': 'neutral'
    },
    {
        'url': 'https://www.quiksilver.com/baby-boys-2-7-surfsilk-tijuana-boardshorts-EQKBS03300.html',
        'retailer_name': 'Quiksilver',
        'brand': 'Quiksilver',
        'age_hint': '2T-7',
        'category_hint': 'boardshorts',
        'tags': ['surf', 'beach', 'graphic'],
        'gender': 'boy'
    },
    {
        'url': 'https://us.oneill.com/products/fa3106002-boyss-balance-hoodie',
        'retailer_name': "O'Neill",
        'brand': "O'Neill",
        'age_hint': '2T-7',
        'category_hint': 'hoodies',
        'tags': ['surf', 'streetwear', 'vintage wash'],
        'gender': 'boy'
    },
    {
        'url': 'https://us.oneill.com/products/sp4106039-girls-saltwater-dreams-tee',
        'retailer_name': "O'Neill",
        'brand': "O'Neill",
        'age_hint': '2T-7',
        'category_hint': 'tees',
        'tags': ['surf', 'graphic', 'beach'],
        'gender': 'girl'
    }
]

INCLUDE_KEYWORDS = ['toddler', 'baby', 'infant', 'kid', 'romper', 'onesie', 'boardshort', 'skate', 'surf', 'checkerboard', 'hoodie', 'beanie', 'tee', 'shoe']
EXCLUDE_PATTERNS = [r'\badult\b', r'\bgift\s*card\b', r'\bmen(?:\'s)?\b', r'\bwomen(?:\'s)?\b']
STYLE_MAP = {
    'punk': ['punk', 'distressed', 'grunge', 'alt'],
    'surf': ['surf', 'wave', 'beach', 'saltwater', 'boardshort'],
    'skate': ['skate', 'checkerboard', 'streetwear', 'vans'],
    'checkerboard': ['checkerboard'],
    'graphic': ['graphic', 'logo', 'print'],
    'beach': ['beach', 'ocean', 'coast'],
    'vintage wash': ['vintage', 'washed', 'faded']
}


@dataclass
class Product:
    id: str
    slug: str
    title: str
    description_short: str
    brand: str
    retailer_name: str
    retailer_domain: str
    source_product_url: str
    image_url: str
    additional_images: list[str]
    current_price: float
    original_price: float | None
    currency: str
    age_range: str
    sizes: list[str]
    category: str
    style_tags: list[str]
    availability: str
    last_checked_at: str
    source_type: str
    product_hash: str
    gender: str | None
    featured_score: int
    recently_updated: bool


def relevance(text: str) -> bool:
    lowered = text.lower()
    has_include = any(word in lowered for word in INCLUDE_KEYWORDS)
    has_exclude = any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in EXCLUDE_PATTERNS)
    return has_include and not has_exclude


def infer_style_tags(text: str, tags: list[str]) -> list[str]:
    lowered = text.lower()
    output = set(tags)
    for tag, words in STYLE_MAP.items():
        if any(word in lowered for word in words):
            output.add(tag)
    return sorted(output)


def normalize_category(category_hint: str, text: str) -> str:
    options = [
        ('onesie', 'onesies'), ('romper', 'rompers'), ('tee', 'tees'), ('hoodie', 'hoodies'),
        ('short', 'boardshorts'), ('beanie', 'beanies'), ('sock', 'socks'), ('shoe', 'shoes'),
        ('jacket', 'jackets'), ('overall', 'overalls'), ('hat', 'hats'), ('bag', 'accessories')
    ]
    lowered = f'{category_hint} {text}'.lower()
    for needle, category in options:
        if needle in lowered:
            return category
    return 'clothing'


def feature_score(tags: list[str], title: str) -> int:
    score = len(tags) * 10
    if 'checkerboard' in title.lower():
        score += 15
    if 'punk' in tags:
        score += 12
    if 'surf' in tags:
        score += 10
    if 'skate' in tags:
        score += 10
    return min(score, 100)


def slugify(value: str) -> str:
    return re.sub(r'(^-|-$)', '', re.sub(r'[^a-z0-9]+', '-', value.lower()))


def parse_price(value: Any) -> float:
    if value is None:
        return 0.0
    return float(re.sub(r'[^\d.]', '', str(value)) or 0)


def normalize_availability(value: Any) -> str:
    lowered = str(value or '').lower()
    if 'instock' in lowered or 'in stock' in lowered:
        return 'in_stock'
    if 'outofstock' in lowered or 'out of stock' in lowered:
        return 'out_of_stock'
    return 'unknown'


def fetch_jsonld(url: str) -> dict[str, Any] | None:
    request = Request(url, headers={'User-Agent': 'Mozilla/5.0 TinyThrashThreadsBot/1.0'})
    html = urlopen(request, timeout=20).read().decode('utf-8', 'ignore')

    blobs = re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.S | re.I)
    for blob in blobs:
        try:
            parsed = json.loads(blob.strip())
        except Exception:
            continue

        nodes = parsed if isinstance(parsed, list) else [parsed]
        for node in nodes:
            if isinstance(node, dict) and node.get('@type') == 'Product':
                return node

    return None


def normalize_product(seed: dict[str, Any], node: dict[str, Any], now: str) -> Product | None:
    title = str(node.get('name') or '').strip()
    image = node.get('image')
    if isinstance(image, list):
        image = image[0] if image else ''

    if not title or not image:
        return None

    description = re.sub('<[^>]*>', ' ', str(node.get('description') or '')).strip()
    relevance_text = f"{title} {description} {seed['category_hint']} {seed['age_hint']}"
    if not relevance(relevance_text):
        return None

    offers = node.get('offers')
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    if not isinstance(offers, dict):
        offers = {}

    sizes = node.get('size')
    if isinstance(sizes, list):
        normalized_sizes = [str(s) for s in sizes]
    elif sizes:
        normalized_sizes = [str(sizes)]
    else:
        normalized_sizes = []

    tags = infer_style_tags(relevance_text, list(seed['tags']))
    category = normalize_category(seed['category_hint'], relevance_text)
    price = parse_price(offers.get('price') or node.get('price'))
    url = seed['url']

    return Product(
        id=hashlib.sha1(url.encode()).hexdigest()[:12],
        slug=slugify(f"{seed['brand']}-{title}"),
        title=title,
        description_short=description[:180],
        brand=seed['brand'],
        retailer_name=seed['retailer_name'],
        retailer_domain=urlparse(url).hostname or '',
        source_product_url=url,
        image_url=str(image),
        additional_images=[item for item in node.get('image', []) if isinstance(item, str)][1:6] if isinstance(node.get('image'), list) else [],
        current_price=price,
        original_price=None,
        currency=str(offers.get('priceCurrency', 'USD')),
        age_range=seed['age_hint'],
        sizes=normalized_sizes,
        category=category,
        style_tags=tags,
        availability=normalize_availability(offers.get('availability')),
        last_checked_at=now,
        source_type='json_ld',
        product_hash=hashlib.sha1(f"{seed['brand']}:{title}:{price}".encode()).hexdigest(),
        gender=seed.get('gender'),
        featured_score=feature_score(tags, title),
        recently_updated=True
    )


def load_previous_products() -> list[dict[str, Any]]:
    if not OUTPUT_PATH.exists():
        return []

    try:
        payload = json.loads(OUTPUT_PATH.read_text(encoding='utf-8'))
        if isinstance(payload, dict) and isinstance(payload.get('products'), list):
            return payload['products']
    except Exception:
        pass

    return []


def build_payload() -> dict[str, Any]:
    now = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'
    fallback = json.loads(FALLBACK_PATH.read_text(encoding='utf-8'))

    source_statuses: list[dict[str, str]] = []
    warnings: list[str] = []
    products: list[Product] = []

    for index, seed in enumerate(SEEDS):
        retailer_label = f"{seed['retailer_name']} ({seed['url']})"
        try:
            node = fetch_jsonld(seed['url'])
            if not node:
                raise RuntimeError('Product JSON-LD not found')
            normalized = normalize_product(seed, node, now)
            if not normalized:
                raise RuntimeError('Source product failed relevance/normalization')
            products.append(normalized)
            source_statuses.append({'retailer_name': seed['retailer_name'], 'status': 'live'})
        except Exception as error:
            source_statuses.append({'retailer_name': seed['retailer_name'], 'status': 'fallback', 'error': str(error)})
            warnings.append(f'Live ingestion failed for {retailer_label}: {error}')
            fallback_node = fallback[index] if index < len(fallback) else None
            if fallback_node:
                normalized_fallback = normalize_product(seed, fallback_node, now)
                if normalized_fallback:
                    products.append(normalized_fallback)
                else:
                    warnings.append(f'Fallback record for {retailer_label} did not pass normalization.')
            else:
                warnings.append(f'No fallback record available for {retailer_label}.')

    dedup: dict[str, Product] = {}
    for product in products:
        existing = dedup.get(product.product_hash)
        if not existing or product.featured_score > existing.featured_score:
            dedup[product.product_hash] = product

    normalized_products = sorted((asdict(p) for p in dedup.values()), key=lambda item: item['featured_score'], reverse=True)

    if not normalized_products:
        previous = load_previous_products()
        if previous:
            warnings.append('No products were refreshed. Preserving previous generated product snapshot.')
            normalized_products = previous

    return {
        'generated_at': now,
        'product_count': len(normalized_products),
        'products': normalized_products,
        'sources': source_statuses,
        'warnings': warnings
    }


def main() -> None:
    payload = build_payload()
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print(f"Wrote {payload['product_count']} products to {OUTPUT_PATH}")
    live = sum(1 for source in payload['sources'] if source.get('status') == 'live')
    fallback = sum(1 for source in payload['sources'] if source.get('status') == 'fallback')
    print(f'Sources: {live} live, {fallback} fallback')


if __name__ == '__main__':
    main()
