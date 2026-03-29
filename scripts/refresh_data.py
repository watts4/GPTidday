#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen

OUTPUT_PATH = Path('data/products.generated.json')
REJECTED_PATH = Path('data/products.rejected.json')
NOW = lambda: datetime.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'

ADAPTERS: list[dict[str, Any]] = [
    {
        'name': 'oneill_kids', 'display_name': "O'Neill", 'group': 'surf_skate_official',
        'retailer_name': "O'Neill", 'retailer_domain': 'us.oneill.com', 'brand': "O'Neill",
        'listing_urls': ['https://us.oneill.com/collections/kids'], 'age_range': 'kids',
        'category_context': 'kids surf beach streetwear boardshorts tees hoodies accessories',
        'style_tags': ['surf', 'beach', 'streetwear'], 'source_type': 'official_brand', 'enabled': True,
    },
    {
        'name': 'vans_little_kids_toddlers', 'display_name': 'Vans', 'group': 'surf_skate_official',
        'retailer_name': 'Vans', 'retailer_domain': 'www.vans.com', 'brand': 'Vans',
        'listing_urls': ['https://www.vans.com/en-us/c/kids/clothing/little-kids-and-toddlers-3202'],
        'age_range': 'little-kids-and-toddlers',
        'category_context': 'kids little kids toddler skate checkerboard shoes streetwear tees hoodies accessories',
        'style_tags': ['skate', 'streetwear', 'checkerboard'], 'source_type': 'official_brand', 'enabled': True,
    },
    {
        'name': 'quiksilver_boys', 'display_name': 'Quiksilver', 'group': 'surf_skate_official',
        'retailer_name': 'Quiksilver', 'retailer_domain': 'www.quiksilver.com', 'brand': 'Quiksilver',
        'listing_urls': ['https://www.quiksilver.com/collections/boys'], 'age_range': 'boys',
        'category_context': 'boys kids surf beach boardshorts tees hoodies accessories streetwear',
        'style_tags': ['surf', 'beach', 'streetwear'], 'source_type': 'official_brand', 'enabled': True,
    },
    {
        'name': 'billabong_kids_boys', 'display_name': 'Billabong', 'group': 'surf_skate_official',
        'retailer_name': 'Billabong', 'retailer_domain': 'www.billabong.com', 'brand': 'Billabong',
        'listing_urls': ['https://www.billabong.com/collections/kids-boys'], 'age_range': 'kids-boys',
        'category_context': 'kids boys surf beach boardshorts tees hoodies accessories',
        'style_tags': ['surf', 'beach'], 'source_type': 'official_brand', 'enabled': True,
    },
    {
        'name': 'hurley_kids', 'display_name': 'Hurley', 'group': 'surf_skate_official',
        'retailer_name': 'Hurley', 'retailer_domain': 'www.hurley.com', 'brand': 'Hurley',
        'listing_urls': ['https://www.hurley.com/collections/kids'], 'age_range': 'kids',
        'category_context': 'kids surf beach streetwear boardshorts tees hoodies accessories',
        'style_tags': ['surf', 'beach', 'streetwear'], 'source_type': 'official_brand', 'enabled': True,
    },
    {
        'name': 'volcom_kids', 'display_name': 'Volcom', 'group': 'surf_skate_official',
        'retailer_name': 'Volcom', 'retailer_domain': 'www.volcom.com', 'brand': 'Volcom',
        'listing_urls': ['https://www.volcom.com/collections/kids'], 'age_range': 'kids',
        'category_context': 'kids skate surf streetwear tees hoodies accessories shoes',
        'style_tags': ['skate', 'surf', 'streetwear'], 'source_type': 'official_brand', 'enabled': True,
    },
    {
        'name': 'red_devil_kids', 'display_name': 'Red Devil Clothing', 'group': 'alt_punk_official',
        'retailer_name': 'Red Devil Clothing', 'retailer_domain': 'reddevilclothing.com', 'brand': 'Red Devil Clothing',
        'listing_urls': ['https://reddevilclothing.com/collections/all-kids'], 'age_range': 'kids',
        'category_context': 'all kids punk goth alternative rockabilly streetwear graphic tees accessories',
        'style_tags': ['punk', 'alt', 'goth', 'rockabilly', 'streetwear', 'graphic'], 'source_type': 'alt_brand', 'enabled': True,
    },
    {
        'name': 'blackcraft_kids', 'display_name': 'Blackcraft', 'group': 'alt_punk_official',
        'retailer_name': 'Blackcraft', 'retailer_domain': 'www.blackcraftcult.com', 'brand': 'Blackcraft',
        'listing_urls': ['https://www.blackcraftcult.com/collections/kids'], 'age_range': 'kids',
        'category_context': 'kids punk goth gothic alternative rock streetwear graphic tees accessories',
        'style_tags': ['punk', 'goth', 'alt', 'streetwear', 'graphic'], 'source_type': 'alt_brand', 'enabled': True,
    },
    {
        'name': 'teepublic_hardcore_punk_kids', 'display_name': 'TeePublic Hardcore Punk', 'group': 'marketplace',
        'retailer_name': 'TeePublic', 'retailer_domain': 'www.teepublic.com', 'brand': 'TeePublic',
        'listing_urls': ['https://www.teepublic.com/kids-t-shirt/hardcore-punk'], 'age_range': 'kids',
        'category_context': 'kids t-shirt hardcore punk rock graphic tee',
        'style_tags': ['punk', 'graphic'], 'source_type': 'marketplace', 'marketplace': True,
        'marketplace_query_context': 'hardcore punk kids t-shirt', 'enabled': True,
    },
    {
        'name': 'teepublic_punk_rock_kids', 'display_name': 'TeePublic Punk Rock', 'group': 'marketplace',
        'retailer_name': 'TeePublic', 'retailer_domain': 'www.teepublic.com', 'brand': 'TeePublic',
        'listing_urls': ['https://www.teepublic.com/kids-t-shirt/punk-rock'], 'age_range': 'kids',
        'category_context': 'kids t-shirt punk rock graphic tee',
        'style_tags': ['punk', 'graphic'], 'source_type': 'marketplace', 'marketplace': True,
        'marketplace_query_context': 'punk rock kids t-shirt', 'enabled': True,
    },
    {
        'name': 'etsy_kids_gothic', 'display_name': 'Etsy Kids Gothic Clothing', 'group': 'marketplace',
        'retailer_name': 'Etsy', 'retailer_domain': 'www.etsy.com', 'brand': 'Etsy',
        'listing_urls': ['https://www.etsy.com/market/kids_gothic_clothing'], 'age_range': 'kids',
        'category_context': 'kids gothic goth alternative punk clothing accessories',
        'style_tags': ['goth', 'alt', 'punk'], 'source_type': 'marketplace', 'marketplace': True,
        'marketplace_query_context': 'kids gothic clothing', 'enabled': True,
    },
]

STYLE_SIGNALS = {
    'punk': {'punk', 'punk rock', 'hardcore'}, 'goth': {'goth', 'gothic'}, 'alt': {'alt', 'alternative'},
    'rockabilly': {'rockabilly'}, 'surf': {'surf', 'beach', 'saltwater', 'wave', 'boardshorts', 'boardshort'},
    'skate': {'skate', 'checkerboard', 'slip-on'}, 'streetwear': {'streetwear'},
    'graphic': {'graphic tee', 'graphic', 'logo', 'print'}, 'hoodie': {'hoodie'},
}
POSITIVE_SIGNALS = {
    'kids', 'little kids', 'toddlers', 'toddler', 'infant', 'baby', 'boys', 'girls', 'youth',
    'punk', 'punk rock', 'hardcore', 'goth', 'gothic', 'skate', 'surf', 'checkerboard',
    'boardshorts', 'graphic tee', 'hoodie', 'slip-on', 'streetwear', 'alt', 'rockabilly',
}
NEGATIVE_SIGNALS = {
    'adult-only', 'adult only', 'home decor', 'wall art', 'sticker', 'stickers', 'men', "men's", 'women', "women's",
}
CATEGORY_MAP = [
    ('onesie', 'onesies'), ('bodysuit', 'onesies'), ('romper', 'rompers'), ('tee', 'tees'), ('t-shirt', 'tees'),
    ('hoodie', 'hoodies'), ('short', 'boardshorts'), ('boardshort', 'boardshorts'), ('beanie', 'beanies'),
    ('sock', 'socks'), ('shoe', 'shoes'), ('slip-on', 'shoes'), ('sneaker', 'shoes'), ('jacket', 'jackets'),
    ('hat', 'hats'), ('backpack', 'accessories'), ('bag', 'accessories'), ('accessory', 'accessories'),
]
SOURCE_TYPE_PRIORITY = {'official_brand': 3, 'alt_brand': 2, 'marketplace': 1}


@dataclass
class FetchResult:
    status_code: int
    final_url: str
    body: str
    content_type: str


@dataclass
class ListingCandidate:
    source_adapter: str
    source_group: str
    source_type: str
    marketplace: bool
    retailer_name: str
    retailer_domain: str
    brand_hint: str
    source_listing_url: str
    source_product_url: str
    title: str
    price_text: str
    image_url: str
    seller_name: str | None
    badges: list[str]
    category_context: str
    age_range_hint: str
    style_seed_tags: list[str]
    marketplace_query_context: str | None
    discovered_at: str


@dataclass
class Product:
    id: str
    slug: str
    title: str
    brand: str
    retailer_name: str
    retailer_domain: str
    source_type: str
    source_group: str
    marketplace: bool
    source_listing_url: str
    source_product_url: str
    canonical_product_url: str
    image_url: str
    additional_images: list[str]
    current_price: float
    original_price: float | None
    currency: str
    availability: str
    category: str
    subcategory: str
    age_range: str
    sizes: list[str]
    gender_target: str | None
    style_tags: list[str]
    discovered_at: str
    last_checked_at: str
    source_adapter: str
    is_active: bool
    validation_status: str
    validation_errors: list[str]
    relevance_score: int
    dedupe_key: str
    seller_name: str | None = None
    marketplace_confidence: float | None = None
    marketplace_query_context: str | None = None
    description_short: str = ''
    featured_score: int = 0
    recently_updated: bool = True


def slugify(value: str) -> str:
    return re.sub(r'(^-|-$)', '', re.sub(r'[^a-z0-9]+', '-', value.lower()))


def strip_tracking_params(url: str) -> str:
    parsed = urlparse(url)
    clean_query = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if not k.lower().startswith(('utm_', 'gclid', 'fbclid'))]
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, urlencode(clean_query), ''))


def fetch_url(url: str, method: str = 'GET', accept: str = 'text/html,*/*') -> FetchResult:
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0 TinyThrashThreadsBot/5.0', 'Accept': accept}, method=method)
    with urlopen(req, timeout=20) as res:
        status_code = getattr(res, 'status', res.getcode())
        return FetchResult(status_code=status_code, final_url=res.geturl(), body=res.read().decode('utf-8', 'ignore') if method == 'GET' else '', content_type=(res.headers.get('Content-Type') or '').lower())


def text_only(html_fragment: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]*>', ' ', unescape(html_fragment))).strip()


def parse_price(value: Any) -> float:
    if value is None:
        return 0.0
    return float(re.sub(r'[^\d.]', '', str(value)) or 0)


def extract_price_numbers(text: str) -> list[float]:
    vals = [parse_price(m) for m in re.findall(r'\$\s*\d+(?:[\.,]\d{2})?', text)]
    return [v for v in vals if v > 0]


def pick_image_from_chunk(chunk: str, base_url: str) -> str:
    for pattern in [r'(?:data-src|data-original|src)=["\']([^"\']+)["\']', r'srcset=["\']([^"\']+)["\']']:
        for raw in re.findall(pattern, chunk, flags=re.I):
            candidate = raw.split(',')[0].strip().split(' ')[0]
            if not candidate or candidate.startswith('data:'):
                continue
            return strip_tracking_params(urljoin(base_url, candidate))
    return ''


def normalize_category(category_hint: str, text: str) -> str:
    lowered = f'{category_hint} {text}'.lower()
    for needle, category in CATEGORY_MAP:
        if needle in lowered:
            return category
    return 'clothing'


def infer_style_tags(text: str, seed_tags: list[str] | None = None) -> list[str]:
    lowered = text.lower()
    out = set(seed_tags or [])
    for tag, words in STYLE_SIGNALS.items():
        if any(word in lowered for word in words):
            out.add(tag)
    return sorted(out)


def is_product_like_url(url: str) -> bool:
    path = urlparse(url).path.lower()
    if any(x in path for x in ['/search', '/collections', '/collection', '/category', '/c/', '/market/']):
        return False
    return any(x in path for x in ['/product', '/products/', '/listing/', '.html', '-p']) or path.count('/') >= 2


def extract_seller_name(chunk: str) -> str | None:
    byline_patterns = [r'by\s+<[^>]*>([^<]+)<', r'\bSeller\s*:\s*([^<\n]+)', r'\bby\s+([A-Za-z0-9_\- ]{3,40})']
    for pattern in byline_patterns:
        m = re.search(pattern, chunk, flags=re.I)
        if m:
            return text_only(m.group(1))[:80]
    return None


def extract_listing_cards(listing_url: str, html: str, adapter: dict[str, Any]) -> list[ListingCandidate]:
    cards: list[ListingCandidate] = []
    seen: set[str] = set()
    domain = adapter['retailer_domain'].lower().replace('www.', '')

    for match in re.finditer(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, flags=re.I | re.S):
        href = strip_tracking_params(urljoin(listing_url, match.group(1).strip()))
        parsed = urlparse(href)
        if parsed.scheme not in {'http', 'https'}:
            continue
        if domain not in parsed.netloc.lower().replace('www.', ''):
            continue
        if href in seen or not is_product_like_url(href):
            continue

        title = text_only(match.group(2))
        if len(title) < 4:
            continue

        start = max(0, match.start() - 1400)
        end = min(len(html), match.end() + 1600)
        chunk = html[start:end]
        price_text = ' '.join(re.findall(r'\$\s*\d+(?:[\.,]\d{2})?', chunk))
        image_url = pick_image_from_chunk(chunk, listing_url)
        badges = [b.lower() for b in re.findall(r'\b(sale|new|best seller|out of stock)\b', chunk, flags=re.I)]

        cards.append(ListingCandidate(
            source_adapter=adapter.get('name', adapter.get('source_adapter', 'listing_card_v1')),
            source_group=adapter.get('group', 'surf_skate_official'),
            source_type=adapter.get('source_type', 'official_brand' if not adapter.get('marketplace') else 'marketplace'),
            marketplace=bool(adapter.get('marketplace')),
            retailer_name=adapter['retailer_name'],
            retailer_domain=adapter['retailer_domain'],
            brand_hint=adapter['brand'],
            source_listing_url=listing_url,
            source_product_url=href,
            title=title,
            price_text=price_text,
            image_url=image_url,
            seller_name=extract_seller_name(chunk) if adapter.get('marketplace') else None,
            badges=badges,
            category_context=adapter['category_context'],
            age_range_hint=adapter['age_range'],
            style_seed_tags=list(adapter.get('style_tags', [])),
            marketplace_query_context=adapter.get('marketplace_query_context'),
            discovered_at=NOW(),
        ))
        seen.add(href)

    return cards


def fetch_listing_pages(adapter: dict[str, Any], health: dict[str, Any]) -> list[tuple[str, FetchResult]]:
    pages: list[tuple[str, FetchResult]] = []
    for listing_url in adapter['listing_urls']:
        try:
            page = fetch_url(listing_url)
            if page.status_code >= 400:
                raise ValueError(f'listing status {page.status_code}')
            pages.append((page.final_url, page))
            health['listing_fetch_ok'] += 1
        except Exception as error:
            health['listing_fetch_failed'] += 1
            health['notes'].append(f'listing failed {listing_url}: {error}')
    return pages


def discover_candidates(now: str) -> tuple[list[ListingCandidate], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    candidates: list[ListingCandidate] = []
    rejected: list[dict[str, Any]] = []
    health: dict[str, dict[str, Any]] = {}

    for adapter in ADAPTERS:
        name = adapter['name']
        health[name] = {
            'adapter': name,
            'source_label': adapter.get('display_name', adapter['retailer_name']),
            'source_group': adapter['group'],
            'source_type': adapter['source_type'],
            'retailer_name': adapter['retailer_name'],
            'enabled': bool(adapter.get('enabled', True)),
            'listing_fetch_ok': 0,
            'listing_fetch_failed': 0,
            'discovered_count': 0,
            'published_count': 0,
            'rejected_count': 0,
            'top_rejection_reasons': [],
            'notes': [],
            'sample_accepted': [],
        }
        if not adapter.get('enabled', True):
            continue

        adapter_cards: list[ListingCandidate] = []
        for final_url, page in fetch_listing_pages(adapter, health[name]):
            adapter_cards.extend(extract_listing_cards(final_url, page.body, adapter))

        if not adapter_cards:
            health[name]['notes'].append('no listing cards extracted')

        candidates.extend(adapter_cards)
        health[name]['discovered_count'] = len(adapter_cards)

    return candidates, rejected, health


def score_candidate(product: Product) -> int:
    text = f"{product.title} {product.category} {product.age_range} {' '.join(product.style_tags)} {product.marketplace_query_context or ''}".lower()
    score = 0
    score += sum(6 for w in POSITIVE_SIGNALS if w in text)
    score -= sum(12 for w in NEGATIVE_SIGNALS if w in text)
    if product.source_type == 'official_brand':
        score += 20
    elif product.source_type == 'alt_brand':
        score += 12
    else:
        score += 4
    if product.category in {'shoes', 'tees', 'hoodies', 'boardshorts', 'onesies', 'rompers', 'accessories'}:
        score += 15
    if product.marketplace and not any(w in text for w in {'kids', 'toddler', 'baby', 'boys', 'girls'}):
        score -= 25
    return max(0, min(100, score))


def normalize_candidate(candidate: ListingCandidate, now: str) -> Product:
    price_values = extract_price_numbers(candidate.price_text)
    current_price = price_values[0] if price_values else 0.0
    original_price = None
    if len(price_values) >= 2:
        a, b = price_values[0], price_values[1]
        current_price, original_price = (min(a, b), max(a, b))

    text = f"{candidate.title} {candidate.category_context} {' '.join(candidate.badges)}"
    style_tags = infer_style_tags(text, candidate.style_seed_tags)
    category = normalize_category(candidate.category_context, candidate.title)

    canonical_url = strip_tracking_params(candidate.source_product_url)
    id_seed = f"{candidate.retailer_name}:{canonical_url}:{candidate.title}"
    pid = hashlib.sha1(id_seed.encode()).hexdigest()[:12]
    norm_title = slugify(candidate.title)
    image_sig = hashlib.sha1(candidate.image_url.encode()).hexdigest()[:10] if candidate.image_url else 'noimg'
    dedupe_key = hashlib.sha1(f"{norm_title}|{candidate.brand_hint.lower()}|{canonical_url}|{image_sig}|{current_price}|{candidate.retailer_domain}".encode()).hexdigest()

    errs: list[str] = []
    if not candidate.title:
        errs.append('title missing')
    if not candidate.image_url:
        errs.append('no usable primary image')
    if current_price <= 0:
        errs.append('no parseable price')
    if not candidate.source_product_url:
        errs.append('missing source_product_url')

    product = Product(
        id=pid,
        slug=slugify(f"{candidate.brand_hint}-{candidate.title}-{pid[:6]}"),
        title=candidate.title,
        brand=candidate.brand_hint,
        retailer_name=candidate.retailer_name,
        retailer_domain=candidate.retailer_domain,
        source_type=candidate.source_type,
        source_group=candidate.source_group,
        marketplace=candidate.marketplace,
        source_listing_url=candidate.source_listing_url,
        source_product_url=candidate.source_product_url,
        canonical_product_url=canonical_url,
        image_url=candidate.image_url,
        additional_images=[],
        current_price=current_price,
        original_price=original_price,
        currency='USD',
        availability='out_of_stock' if 'out of stock' in candidate.badges else 'in_stock',
        category=category,
        subcategory=category,
        age_range=candidate.age_range_hint,
        sizes=[],
        gender_target='neutral',
        style_tags=style_tags,
        discovered_at=candidate.discovered_at,
        last_checked_at=now,
        source_adapter=candidate.source_adapter,
        is_active=False,
        validation_status='pending',
        validation_errors=errs,
        relevance_score=0,
        dedupe_key=dedupe_key,
        seller_name=candidate.seller_name,
        marketplace_confidence=None,
        marketplace_query_context=candidate.marketplace_query_context,
        description_short='',
        featured_score=0,
        recently_updated=True,
    )
    product.relevance_score = score_candidate(product)
    if candidate.marketplace:
        product.marketplace_confidence = round(product.relevance_score / 100.0, 2)
    product.featured_score = product.relevance_score + (SOURCE_TYPE_PRIORITY.get(product.source_type, 0) * 10)
    return product


def check_image_url(image_url: str) -> tuple[bool, str | None]:
    if not image_url:
        return False, 'no usable primary image'
    try:
        res = fetch_url(image_url, method='HEAD', accept='image/*,*/*')
        if res.status_code >= 400:
            return False, f'image status {res.status_code}'
        if res.content_type and 'image/' not in res.content_type:
            return False, f'non-image content type ({res.content_type})'
        return True, None
    except Exception as error:
        return False, str(error)


def is_probable_product_page(final_url: str, html: str, title: str | None = None) -> bool:
    path = urlparse(final_url).path.lower()
    if path in {'', '/'}:
        return False
    if any(token in path for token in ['/search', '/collections', '/collection', '/category', '/market/']):
        return False
    content = f"{title or ''} {html[:2500]}".lower()
    if any(bad in content for bad in ['search results', 'page not found', '404', 'collection of', 'results for']):
        return False
    return True


def validate_candidate(product: Product) -> tuple[Product, str | None]:
    reasons = list(product.validation_errors)

    if product.relevance_score < 20:
        reasons.append('low relevance')

    try:
        page = fetch_url(product.source_product_url)
        if page.status_code >= 400:
            reasons.append('source product URL 404s')
        if not is_probable_product_page(page.final_url, page.body, product.title):
            reasons.append('URL redirects to a non-product page')
        product.canonical_product_url = strip_tracking_params(page.final_url)
    except Exception:
        reasons.append('source product URL 404s')

    img_ok, _ = check_image_url(product.image_url)
    if not img_ok:
        reasons.append('no usable primary image')

    if product.current_price <= 0:
        reasons.append('no parseable price')
    if not product.title:
        reasons.append('title missing')

    if product.source_type == 'marketplace' and product.relevance_score < 35:
        reasons.append('marketplace confidence too low')

    reasons = sorted(set(reasons))
    product.validation_errors = reasons
    hard_blockers = {
        'source product URL 404s', 'URL redirects to a non-product page', 'no usable primary image', 'no parseable price', 'title missing'
    }
    if any(r in hard_blockers for r in reasons):
        product.validation_status = 'failed'
        product.is_active = False
        return product, (next((r for r in reasons if r in hard_blockers), 'title missing'))

    product.validation_status = 'passed'
    product.is_active = True
    return product, None


def dedupe_products(products: list[Product]) -> tuple[list[Product], int]:
    out: dict[str, Product] = {}
    collisions = 0
    for p in products:
        key_variants = {
            p.dedupe_key,
            hashlib.sha1(f"{slugify(p.title)}|{p.brand.lower()}|{p.canonical_product_url}".encode()).hexdigest(),
            hashlib.sha1(f"{slugify(p.title)}|{p.brand.lower()}|{p.current_price}|{p.retailer_domain}".encode()).hexdigest(),
        }
        existing_key = next((k for k in key_variants if k in out), None)
        if existing_key is None:
            out[p.dedupe_key] = p
            continue
        collisions += 1
        existing = out[existing_key]
        lhs = (SOURCE_TYPE_PRIORITY.get(p.source_type, 0), p.relevance_score, p.last_checked_at)
        rhs = (SOURCE_TYPE_PRIORITY.get(existing.source_type, 0), existing.relevance_score, existing.last_checked_at)
        out[existing_key] = p if lhs > rhs else existing
    return sorted(out.values(), key=lambda x: (-SOURCE_TYPE_PRIORITY.get(x.source_type, 0), -x.featured_score, x.title)), collisions


def build_payload() -> tuple[dict[str, Any], dict[str, Any]]:
    now = NOW()
    candidates, rejected_rows, health = discover_candidates(now)
    normalized = [normalize_candidate(c, now) for c in candidates]

    validated: list[Product] = []
    reason_counts: Counter[str] = Counter()
    source_reason_counts: dict[str, Counter[str]] = defaultdict(Counter)

    for p in normalized:
        vp, reject_reason = validate_candidate(p)
        validated.append(vp)
        if reject_reason:
            reason_counts[reject_reason] += 1
            source_reason_counts[p.source_adapter][reject_reason] += 1
            rejected_rows.append({'id': p.id, 'title': p.title, 'retailer_name': p.retailer_name, 'source_adapter': p.source_adapter, 'source_listing_url': p.source_listing_url, 'source_product_url': p.source_product_url, 'errors': p.validation_errors, 'stage': 'publish_validation'})

    deduped, collisions = dedupe_products(validated)
    published = [p for p in deduped if p.is_active and p.validation_status == 'passed']

    by_adapter: dict[str, dict[str, int]] = defaultdict(lambda: {'discovered': 0, 'published': 0, 'rejected': 0})
    for c in candidates:
        by_adapter[c.source_adapter]['discovered'] += 1
    for p in published:
        by_adapter[p.source_adapter]['published'] += 1
    for r in rejected_rows:
        by_adapter[r.get('source_adapter', 'unknown')]['rejected'] += 1

    for source in health.values():
        name = source['adapter']
        source['published_count'] = by_adapter[name]['published']
        source['rejected_count'] = by_adapter[name]['rejected']
        source['top_rejection_reasons'] = source_reason_counts[name].most_common(5)
        source['sample_accepted'] = [{'title': p.title, 'price': p.current_price, 'url': p.canonical_product_url} for p in published if p.source_adapter == name][:3]

    payload = {
        'generated_at': now,
        'product_count': len(published),
        'products': [asdict(p) for p in published],
        'sources': list(health.values()),
        'source_groups': {
            'surf_skate_official': [a['display_name'] for a in ADAPTERS if a['group'] == 'surf_skate_official'],
            'alt_punk_official': [a['display_name'] for a in ADAPTERS if a['group'] == 'alt_punk_official'],
            'marketplace': [a['display_name'] for a in ADAPTERS if a['group'] == 'marketplace'],
        },
        'publish_rules': {
            'listing_card_first': True,
            'requires_real_source_product_url': True,
            'requires_image': True,
            'requires_price': True,
            'requires_dead_link_check': True,
        },
        'pipeline_debug': {
            'discovered_candidates': len(candidates),
            'normalized_candidates': len(normalized),
            'validated_candidates': len(validated),
            'published_products': len(published),
            'adapter_counts': by_adapter,
            'top_rejection_reasons': reason_counts.most_common(20),
            'duplicate_collisions': collisions,
        },
    }

    rejected_payload = {'generated_at': now, 'rejected_count': len(rejected_rows), 'rejected': rejected_rows}
    return payload, rejected_payload


def validate_existing_catalog(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding='utf-8'))
    products = payload.get('products', []) if isinstance(payload, dict) else []
    checked = []
    for product in products:
        errors: list[str] = []
        try:
            res = fetch_url(product['canonical_product_url'])
            if res.status_code >= 400 or not is_probable_product_page(res.final_url, res.body, product.get('title')):
                errors.append('URL not healthy or not PDP')
        except Exception as error:
            errors.append(f'url check failed: {error}')
        img_ok, img_error = check_image_url(product.get('image_url', ''))
        if not img_ok:
            errors.append(f'image validation: {img_error}')
        checked.append({'id': product.get('id'), 'title': product.get('title'), 'errors': errors, 'validation_status': 'passed' if not errors else 'failed'})
    return {'checked_at': NOW(), 'product_count': len(checked), 'passed': sum(1 for c in checked if c['validation_status'] == 'passed'), 'failed': sum(1 for c in checked if c['validation_status'] == 'failed'), 'products': checked}


def report_rejected(path: Path = REJECTED_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding='utf-8'))
    rejected = payload.get('rejected', [])
    counts = Counter()
    by_adapter = Counter()
    for row in rejected:
        by_adapter[row.get('source_adapter', row.get('retailer_name', 'unknown'))] += 1
        for err in row.get('errors', []):
            counts[err] += 1
    return {'generated_at': payload.get('generated_at'), 'rejected_count': len(rejected), 'by_adapter': by_adapter, 'top_reasons': counts.most_common(20)}


def report_adapter_health(path: Path = OUTPUT_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding='utf-8'))
    return {'generated_at': payload.get('generated_at'), 'sources': payload.get('sources', []), 'pipeline_debug': payload.get('pipeline_debug', {}), 'source_groups': payload.get('source_groups', {})}


def main() -> None:
    parser = argparse.ArgumentParser(description='Refresh, validate, and report Tiny Thrash Threads catalog pipeline.')
    sub = parser.add_subparsers(dest='command')
    sub.add_parser('refresh', help='fetch live listings -> extract cards -> normalize -> validate -> publish')
    validate_parser = sub.add_parser('validate', help='validate an existing generated catalog file')
    validate_parser.add_argument('--path', default=str(OUTPUT_PATH))
    reject_parser = sub.add_parser('report-rejected', help='summarize rejected items')
    reject_parser.add_argument('--path', default=str(REJECTED_PATH))
    health_parser = sub.add_parser('report-health', help='show adapter health report')
    health_parser.add_argument('--path', default=str(OUTPUT_PATH))

    args = parser.parse_args()
    cmd = args.command or 'refresh'

    if cmd == 'validate':
        print(json.dumps(validate_existing_catalog(Path(args.path)), indent=2))
        return
    if cmd == 'report-rejected':
        print(json.dumps(report_rejected(Path(args.path)), indent=2))
        return
    if cmd == 'report-health':
        print(json.dumps(report_adapter_health(Path(args.path)), indent=2))
        return

    payload, rejected_payload = build_payload()
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    REJECTED_PATH.write_text(json.dumps(rejected_payload, indent=2), encoding='utf-8')
    print(f"Discovered {payload['pipeline_debug']['discovered_candidates']} candidates")
    print(f"Published {payload['product_count']} products to {OUTPUT_PATH}")
    print(f"Rejected {rejected_payload['rejected_count']} candidates to {REJECTED_PATH}")


if __name__ == '__main__':
    main()
