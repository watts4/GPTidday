#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen

OUTPUT_PATH = Path('data/products.generated.json')
REJECTED_PATH = Path('data/products.rejected.json')
FALLBACK_PATH = Path('data/fallback_products.json')

NOW = lambda: datetime.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'

# Discovery-first adapters: listing pages are primary, curated backup candidates are fallback.
ADAPTERS: list[dict[str, Any]] = [
    {
        'name': 'vans_kids_listing',
        'retailer_name': 'Vans',
        'retailer_domain': 'vans.com',
        'brand': 'Vans',
        'listing_urls': [
            'https://www.vans.com/en-us/kids-c00003/toddlers-c5011',
            'https://www.vans.com/en-us/search/product?q=toddler',
        ],
        'backup_candidates': [
            'https://www.vans.com/en-us/shoes-c00081/toddler-checkerboard-slip-on-v-shoe-pvn0a4vhrbla',
            'https://www.vans.com/en-us/shoes-c00081/toddler-ward-shoe-pvn000d3ybka',
        ],
        'source_adapter': 'jsonld_product_page',
        'enabled': True,
    },
    {
        'name': 'quiksilver_baby_listing',
        'retailer_name': 'Quiksilver',
        'retailer_domain': 'quiksilver.com',
        'brand': 'Quiksilver',
        'listing_urls': [
            'https://www.quiksilver.com/kids/',
            'https://www.quiksilver.com/search?q=baby',
        ],
        'backup_candidates': [
            'https://www.quiksilver.com/baby-boys-2-7-surfsilk-tijuana-boardshorts-EQKBS03300.html',
        ],
        'source_adapter': 'jsonld_product_page',
        'enabled': True,
    },
    {
        'name': 'oneill_kids_listing',
        'retailer_name': "O'Neill",
        'retailer_domain': 'us.oneill.com',
        'brand': "O'Neill",
        'listing_urls': [
            'https://us.oneill.com/collections/little-boys',
            'https://us.oneill.com/collections/little-girls',
        ],
        'backup_candidates': [
            'https://us.oneill.com/products/fa3106002-boyss-balance-hoodie',
            'https://us.oneill.com/products/sp4106039-girls-saltwater-dreams-tee',
        ],
        'source_adapter': 'jsonld_product_page',
        'enabled': True,
    },
]

# Optional backup metadata (for resilience only, never primary discovery)
FALLBACK_HINTS = {
    'Toddler Checkerboard Slip-On V Shoe': {'age': '2T-6T', 'category': 'shoes', 'tags': ['checkerboard', 'skate']},
    'Toddler Ward Shoe': {'age': '2T-6T', 'category': 'shoes', 'tags': ['skate', 'streetwear']},
    'Baby Boys Surfsilk Tijuana Boardshorts': {'age': '2T-7', 'category': 'boardshorts', 'tags': ['surf', 'beach']},
    'Boys Balance Hoodie': {'age': '2T-7', 'category': 'hoodies', 'tags': ['surf', 'streetwear']},
    'Girls Saltwater Dreams Tee': {'age': '2T-7', 'category': 'tees', 'tags': ['surf', 'graphic']},
}



FALLBACK_BY_URL = {
    'https://www.vans.com/en-us/shoes-c00081/toddler-checkerboard-slip-on-v-shoe-pvn0a4vhrbla': 'Toddler Checkerboard Slip-On V Shoe',
    'https://www.vans.com/en-us/shoes-c00081/toddler-ward-shoe-pvn000d3ybka': 'Toddler Ward Shoe',
    'https://www.quiksilver.com/baby-boys-2-7-surfsilk-tijuana-boardshorts-EQKBS03300.html': 'Baby Boys Surfsilk Tijuana Boardshorts',
    'https://us.oneill.com/products/fa3106002-boyss-balance-hoodie': 'Boys Balance Hoodie',
    'https://us.oneill.com/products/sp4106039-girls-saltwater-dreams-tee': 'Girls Saltwater Dreams Tee',
}
INFANT_TERMS = {'baby', 'infant', 'toddler', 'little kids', 'little', '2t', '3t', '4t', '5t', '6t'}
YOUTH_TERMS = {'youth', 'big kids', 'boys', 'girls'}
STYLE_SIGNALS = {
    'punk': {'punk', 'alt', 'grunge', 'distressed'},
    'surf': {'surf', 'beach', 'saltwater', 'wave', 'boardshort'},
    'skate': {'skate', 'checkerboard', 'vans', 'streetwear'},
    'checkerboard': {'checkerboard'},
    'graphic': {'graphic', 'print', 'logo'},
}
EXCLUDE_PATTERNS = [r'\badult\b', r'\bgift\s*card\b', r'\bhome\b', r'\bfurniture\b']
CATEGORY_MAP = [
    ('onesie', 'onesies'), ('bodysuit', 'onesies'), ('romper', 'rompers'), ('tee', 'tees'), ('t-shirt', 'tees'),
    ('hoodie', 'hoodies'), ('short', 'boardshorts'), ('boardshort', 'boardshorts'), ('beanie', 'beanies'),
    ('sock', 'socks'), ('shoe', 'shoes'), ('slip-on', 'shoes'), ('sneaker', 'shoes'), ('jacket', 'jackets'),
    ('hat', 'hats'), ('backpack', 'accessories'), ('bag', 'accessories'),
]


@dataclass
class FetchResult:
    status_code: int
    final_url: str
    body: str
    content_type: str


@dataclass
class Candidate:
    source_adapter: str
    retailer_name: str
    retailer_domain: str
    brand_hint: str
    source_listing_url: str
    source_product_url: str
    discovery_method: str
    discovered_at: str


@dataclass
class Product:
    id: str
    slug: str
    title: str
    brand: str
    retailer_name: str
    retailer_domain: str
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
    age_range: str
    sizes: list[str]
    style_tags: list[str]
    gender_target: str | None
    discovered_at: str
    last_checked_at: str
    source_adapter: str
    is_active: bool
    validation_status: str
    validation_errors: list[str]
    relevance_score: int
    dedupe_key: str
    description_short: str = ''
    featured_score: int = 0
    recently_updated: bool = True


class MetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.canonical: str | None = None
        self.og_url: str | None = None
        self.page_title: str = ''
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {k.lower(): (v or '') for k, v in attrs}
        if tag.lower() == 'link' and attr_map.get('rel', '').lower() == 'canonical':
            self.canonical = attr_map.get('href') or self.canonical
        if tag.lower() == 'meta' and attr_map.get('property', '').lower() == 'og:url':
            self.og_url = attr_map.get('content') or self.og_url
        if tag.lower() == 'title':
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == 'title':
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.page_title += data


def slugify(value: str) -> str:
    return re.sub(r'(^-|-$)', '', re.sub(r'[^a-z0-9]+', '-', value.lower()))


def strip_tracking_params(url: str) -> str:
    parsed = urlparse(url)
    clean_query = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if not k.lower().startswith(('utm_', 'gclid', 'fbclid'))]
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, urlencode(clean_query), ''))


def fetch_url(url: str, method: str = 'GET', accept: str = 'text/html,*/*') -> FetchResult:
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0 TinyThrashThreadsBot/3.0', 'Accept': accept}, method=method)
    with urlopen(req, timeout=20) as res:
        status_code = getattr(res, 'status', res.getcode())
        return FetchResult(
            status_code=status_code,
            final_url=res.geturl(),
            body=res.read().decode('utf-8', 'ignore') if method == 'GET' else '',
            content_type=(res.headers.get('Content-Type') or '').lower(),
        )


def extract_jsonld_nodes(html: str) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for blob in re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.S | re.I):
        text = unescape(blob.strip())
        if not text:
            continue
        try:
            parsed = json.loads(text)
        except Exception:
            continue
        candidates = parsed if isinstance(parsed, list) else [parsed]
        for candidate in candidates:
            if isinstance(candidate, dict):
                if isinstance(candidate.get('@graph'), list):
                    nodes.extend([n for n in candidate['@graph'] if isinstance(n, dict)])
                nodes.append(candidate)
    return nodes


def extract_product_node(html: str) -> dict[str, Any] | None:
    for node in extract_jsonld_nodes(html):
        types = node.get('@type')
        type_values = [types] if isinstance(types, str) else (types or [])
        if any(str(t).lower() == 'product' for t in type_values):
            return node
    return None


def parse_metadata(html: str, base_url: str) -> tuple[str, str]:
    parser = MetadataParser()
    parser.feed(html)
    canonical = parser.canonical or parser.og_url or base_url
    return (strip_tracking_params(urljoin(base_url, canonical)), parser.page_title.strip())


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
    if 'preorder' in lowered:
        return 'preorder'
    return 'unknown'


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


def extract_listing_links(base_url: str, html: str) -> set[str]:
    links = set()
    for href in re.findall(r'href=["\']([^"\']+)["\']', html, flags=re.I):
        abs_url = strip_tracking_params(urljoin(base_url, href))
        parsed = urlparse(abs_url)
        if parsed.scheme not in {'http', 'https'}:
            continue
        path = parsed.path.lower()
        if any(token in path for token in ['/products/', '/product/', '-p', '.html']):
            links.add(abs_url)
    return links


def check_image_url(image_url: str) -> tuple[bool, str | None]:
    if not image_url:
        return False, 'missing image url'
    try:
        head = fetch_url(image_url, method='HEAD', accept='image/*,*/*')
        if head.status_code >= 400:
            return False, f'image status {head.status_code}'
        if head.content_type and 'image/' not in head.content_type:
            return False, f'non-image content type ({head.content_type})'
        return True, None
    except Exception as error:
        return False, str(error)


def is_probable_product_page(final_url: str, html: str, title: str | None = None) -> bool:
    path = urlparse(final_url).path.lower()
    if path in {'', '/'}:
        return False
    if any(token in path for token in ['/search', '/collections', '/category']):
        return False
    content = f"{title or ''} {html[:1400]}".lower()
    if any(bad in content for bad in ['search results', 'no results', '404', 'page not found']):
        return False
    return True


def score_candidate(title: str, description: str, category: str, style_tags: list[str], age_range: str, source_url: str) -> tuple[int, list[str]]:
    text = f'{title} {description} {category} {age_range} {source_url}'.lower()
    reasons = []
    score = 0

    if any(re.search(pattern, text, flags=re.I) for pattern in EXCLUDE_PATTERNS):
        return 0, ['excluded keyword pattern matched']

    infant_hits = sum(1 for term in INFANT_TERMS if term in text)
    youth_hits = sum(1 for term in YOUTH_TERMS if term in text)
    style_hits = len(style_tags)

    score += min(infant_hits * 14, 42)
    score += min(style_hits * 12, 36)
    if category in {'shoes', 'tees', 'hoodies', 'boardshorts', 'onesies', 'rompers', 'accessories'}:
        score += 14
    if 'checkerboard' in text:
        score += 12
    if youth_hits and not infant_hits:
        score -= 18

    if infant_hits:
        reasons.append(f'infant/toddler signals={infant_hits}')
    if style_hits:
        reasons.append(f'style signals={style_hits}')
    if youth_hits and not infant_hits:
        reasons.append('youth-only penalty')

    return max(0, min(score, 100)), reasons




def relevance(text: str) -> bool:
    lowered = text.lower()
    if any(re.search(pattern, lowered, flags=re.I) for pattern in EXCLUDE_PATTERNS):
        return False
    include_terms = {'toddler', 'baby', 'infant', 'kid', 'tiny', 'mini', 'tee', 'shoe', 'hoodie', 'surf', 'skate', 'checkerboard'}
    return any(term in lowered for term in include_terms)


def feature_score(tags: list[str], title: str) -> int:
    score, _ = score_candidate(title, '', normalize_category('', title), tags, 'unknown', '')
    return score

def discover_candidates(now: str) -> tuple[list[Candidate], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    candidates: list[Candidate] = []
    rejects: list[dict[str, Any]] = []
    health: dict[str, dict[str, Any]] = {}

    for adapter in ADAPTERS:
        name = adapter['name']
        discovered_links: set[str] = set()
        health[name] = {
            'adapter': name,
            'retailer_name': adapter['retailer_name'],
            'enabled': bool(adapter.get('enabled', True)),
            'listing_fetch_ok': 0,
            'listing_fetch_failed': 0,
            'discovered_count': 0,
            'backup_used': False,
            'notes': [],
        }
        if not adapter.get('enabled', True):
            health[name]['notes'].append('adapter disabled')
            continue

        for listing_url in adapter['listing_urls']:
            try:
                page = fetch_url(listing_url)
                if page.status_code >= 400:
                    raise ValueError(f'listing status {page.status_code}')
                discovered_links |= extract_listing_links(page.final_url, page.body)
                health[name]['listing_fetch_ok'] += 1
            except Exception as error:
                health[name]['listing_fetch_failed'] += 1
                health[name]['notes'].append(f'listing failed {listing_url}: {error}')

        if not discovered_links:
            discovered_links |= set(adapter.get('backup_candidates', []))
            health[name]['backup_used'] = True
            health[name]['notes'].append('no listing links; using backup candidates')

        for link in sorted(discovered_links):
            candidates.append(Candidate(
                source_adapter=adapter['source_adapter'],
                retailer_name=adapter['retailer_name'],
                retailer_domain=adapter['retailer_domain'],
                brand_hint=adapter['brand'],
                source_listing_url=adapter['listing_urls'][0],
                source_product_url=link,
                discovery_method='listing' if link not in adapter.get('backup_candidates', []) else 'backup_candidates',
                discovered_at=now,
            ))

        health[name]['discovered_count'] = len(discovered_links)

    # Optional enrichment: fallback metadata entries become candidates only when URL matching exists in adapters.
    if FALLBACK_PATH.exists():
        fallback = json.loads(FALLBACK_PATH.read_text(encoding='utf-8'))
        known = {c.source_product_url for c in candidates}
        for item in fallback:
            name = item.get('name', '')
            hint = FALLBACK_HINTS.get(name)
            if not hint:
                continue
            # keep only known products; no guessed URLs introduced
            for adapter in ADAPTERS:
                for url in adapter.get('backup_candidates', []):
                    if slugify(name.split()[0]) in url and url not in known:
                        candidates.append(Candidate(
                            source_adapter='fallback_snapshot',
                            retailer_name=adapter['retailer_name'],
                            retailer_domain=adapter['retailer_domain'],
                            brand_hint=adapter['brand'],
                            source_listing_url='data/fallback_products.json',
                            source_product_url=url,
                            discovery_method='fallback_snapshot',
                            discovered_at=now,
                        ))
                        known.add(url)

    return candidates, rejects, health


def normalize_candidate(candidate: Candidate, now: str) -> tuple[Product | None, dict[str, Any] | None]:
    errors: list[str] = []
    page: FetchResult | None = None
    node: dict[str, Any] | None = None
    canonical = candidate.source_product_url
    page_title = ''

    try:
        page = fetch_url(candidate.source_product_url)
        canonical, page_title = parse_metadata(page.body, page.final_url)
        node = extract_product_node(page.body)
    except (HTTPError, URLError) as error:
        errors.append(f'fetch failed: {error}')
    except Exception as error:
        errors.append(f'fetch failed: {error}')

    fallback_row = None
    if FALLBACK_PATH.exists():
        rows = json.loads(FALLBACK_PATH.read_text(encoding='utf-8'))
        by_name = {row.get('name'): row for row in rows if row.get('name')}
        fallback_name = FALLBACK_BY_URL.get(candidate.source_product_url)
        if fallback_name:
            fallback_row = by_name.get(fallback_name)

    if node:
        title = str(node.get('name') or '').strip()
        description = re.sub('<[^>]*>', ' ', str(node.get('description') or '')).strip()
        brand = str((node.get('brand') or {}).get('name') if isinstance(node.get('brand'), dict) else node.get('brand') or candidate.brand_hint)
        offers = node.get('offers')
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        offers = offers if isinstance(offers, dict) else {}
        price = parse_price(offers.get('price') or node.get('price'))
        currency = str(offers.get('priceCurrency') or node.get('priceCurrency') or 'USD')
        availability = normalize_availability(offers.get('availability') or node.get('availability'))
        image = node.get('image')
        image_list = [i for i in image if isinstance(i, str)] if isinstance(image, list) else ([image] if isinstance(image, str) else [])
        sizes_raw = node.get('size')
        sizes = [str(s) for s in sizes_raw] if isinstance(sizes_raw, list) else ([str(sizes_raw)] if sizes_raw else [])
        product_url = str(node.get('url') or '').strip()
        canonical_product_url = strip_tracking_params(urljoin(canonical, product_url)) if product_url else strip_tracking_params(canonical)
    elif fallback_row:
        title = str(fallback_row.get('name') or '').strip()
        description = str(fallback_row.get('description') or '').strip()
        hint = FALLBACK_HINTS.get(title, {})
        brand = candidate.brand_hint
        price = parse_price(fallback_row.get('price'))
        currency = str(fallback_row.get('currency') or 'USD')
        availability = normalize_availability(fallback_row.get('availability'))
        image_list = [fallback_row.get('image')] if fallback_row.get('image') else []
        sizes = [str(s) for s in (fallback_row.get('sizes') or [])]
        canonical_product_url = strip_tracking_params(candidate.source_product_url)
        errors.append('normalized from fallback snapshot; live page unavailable')
    else:
        return None, {'source_product_url': candidate.source_product_url, 'retailer_name': candidate.retailer_name, 'errors': errors + ['missing metadata for normalization'], 'stage': 'normalize'}

    text = f'{title} {description} {page_title}'
    hint = FALLBACK_HINTS.get(title, {})
    category = normalize_category(str(hint.get('category', '')), text)
    style_tags = infer_style_tags(text, list(hint.get('tags', [])))
    age_range = str(hint.get('age') or ('2T-7' if any(term in text.lower() for term in {'2t', '3t', '4t', 'toddler', 'baby', 'infant'}) else 'unknown'))
    relevance_score, score_reasons = score_candidate(title, description, category, style_tags, age_range, candidate.source_product_url)

    image_url = (image_list[0] if image_list else '')
    if not title:
        errors.append('missing title')
    if not candidate.source_product_url:
        errors.append('missing trustworthy source product URL')
    if not canonical_product_url:
        errors.append('missing canonical product URL')
    if price <= 0:
        errors.append('missing primary price')
    if not image_url:
        errors.append('missing primary image')

    dedupe_key = hashlib.sha1(f'{candidate.retailer_name}:{canonical_product_url}:{title}'.encode()).hexdigest()

    product = Product(
        id=hashlib.sha1(canonical_product_url.encode()).hexdigest()[:12],
        slug=slugify(f'{brand}-{title}'),
        title=title,
        brand=brand or candidate.brand_hint,
        retailer_name=candidate.retailer_name,
        retailer_domain=candidate.retailer_domain,
        source_listing_url=candidate.source_listing_url,
        source_product_url=candidate.source_product_url,
        canonical_product_url=canonical_product_url,
        image_url=image_url,
        additional_images=[img for img in image_list[1:6] if img],
        current_price=price,
        original_price=None,
        currency=currency,
        availability=availability,
        category=category,
        age_range=age_range,
        sizes=sizes,
        style_tags=style_tags,
        gender_target='neutral',
        discovered_at=candidate.discovered_at,
        last_checked_at=now,
        source_adapter=candidate.source_adapter,
        is_active=False,
        validation_status='pending',
        validation_errors=errors,
        relevance_score=relevance_score,
        dedupe_key=dedupe_key,
        description_short=description[:180],
        featured_score=relevance_score,
        recently_updated=True,
    )

    return product, ({'source_product_url': candidate.source_product_url, 'retailer_name': candidate.retailer_name, 'errors': errors, 'score_reasons': score_reasons, 'stage': 'normalize'} if errors else None)


def validate_for_publish(product: Product) -> tuple[Product, dict[str, Any] | None]:
    errors = list(product.validation_errors)
    hard_fail = False

    if product.relevance_score < 25:
        errors.append('relevance score too low for niche')
        hard_fail = True

    try:
        page = fetch_url(product.canonical_product_url)
        if page.status_code in {404, 410} or page.status_code >= 500:
            errors.append(f'product URL hard failure: {page.status_code}')
            hard_fail = True
        elif page.status_code >= 400:
            errors.append(f'product URL not healthy: {page.status_code}')
        if not is_probable_product_page(page.final_url, page.body):
            errors.append('redirected away from probable PDP')
            hard_fail = True
        product.canonical_product_url = strip_tracking_params(page.final_url)
    except Exception as error:
        errors.append(f'product URL validation uncertain: {error}')

    img_ok, img_err = check_image_url(product.image_url)
    if not img_ok:
        # image is a hard blocker only if missing, otherwise uncertain unless explicit 404
        if 'missing image' in (img_err or '') or '404' in (img_err or ''):
            hard_fail = True
        errors.append(f'image check: {img_err}')

    has_blockers = any(msg.startswith('missing primary price') or msg.startswith('missing trustworthy source product URL') or msg.startswith('missing primary image') for msg in errors)
    if has_blockers:
        hard_fail = True

    product.validation_errors = sorted(set(errors))
    if hard_fail:
        product.validation_status = 'failed'
        product.is_active = False
        return product, {'id': product.id, 'title': product.title, 'source_product_url': product.source_product_url, 'errors': product.validation_errors, 'stage': 'publish_validation'}

    # Soft-uncertain publish path to avoid all-or-nothing collapse.
    if any('uncertain' in e or 'fallback snapshot' in e for e in product.validation_errors):
        product.validation_status = 'soft_pass'
    else:
        product.validation_status = 'passed'
    product.is_active = product.relevance_score >= 35 and product.current_price > 0 and bool(product.image_url)
    if not product.is_active:
        product.validation_status = 'failed'
        return product, {'id': product.id, 'title': product.title, 'source_product_url': product.source_product_url, 'errors': product.validation_errors + ['inactive after gating'], 'stage': 'publish_validation'}

    return product, None


def dedupe_products(products: list[Product]) -> tuple[list[Product], list[dict[str, Any]]]:
    by_key: dict[str, Product] = {}
    collisions: list[dict[str, Any]] = []
    for p in products:
        existing = by_key.get(p.dedupe_key)
        if not existing:
            by_key[p.dedupe_key] = p
            continue
        winner = p if (p.relevance_score, p.validation_status == 'passed') > (existing.relevance_score, existing.validation_status == 'passed') else existing
        loser = existing if winner is p else p
        by_key[p.dedupe_key] = winner
        collisions.append({'winner_id': winner.id, 'loser_id': loser.id, 'dedupe_key': p.dedupe_key})
    return sorted(by_key.values(), key=lambda x: (x.validation_status != 'passed', -x.relevance_score, x.title)), collisions


def build_payload() -> tuple[dict[str, Any], dict[str, Any]]:
    now = NOW()
    candidates, rejected, health = discover_candidates(now)
    normalized: list[Product] = []

    for c in candidates:
        p, reject = normalize_candidate(c, now)
        if p:
            normalized.append(p)
        if reject:
            rejected.append(reject)

    validated: list[Product] = []
    for p in normalized:
        vp, reject = validate_for_publish(p)
        validated.append(vp)
        if reject:
            rejected.append(reject)

    deduped, collisions = dedupe_products(validated)
    published = [p for p in deduped if p.is_active and p.validation_status in {'passed', 'soft_pass'}]

    rejected_counts = Counter()
    missing_price = 0
    missing_image = 0
    redirected_non_pdp = 0
    for row in rejected:
        for err in row.get('errors', []):
            rejected_counts[err] += 1
            if 'missing primary price' in err:
                missing_price += 1
            if 'missing primary image' in err:
                missing_image += 1
            if 'redirected away from probable PDP' in err:
                redirected_non_pdp += 1

    adapter_counts = defaultdict(lambda: {'discovered': 0, 'accepted': 0, 'rejected': 0})
    for c in candidates:
        adapter_counts[c.source_adapter]['discovered'] += 1
    for p in published:
        adapter_counts[p.source_adapter]['accepted'] += 1
    for r in rejected:
        stage = r.get('stage', 'unknown')
        adapter_counts[stage]['rejected'] += 1

    payload = {
        'generated_at': now,
        'product_count': len(published),
        'products': [asdict(p) for p in published],
        'sources': [
            {
                'adapter': k,
                'retailer_name': v['retailer_name'],
                'enabled': v['enabled'],
                'listing_fetch_ok': v['listing_fetch_ok'],
                'listing_fetch_failed': v['listing_fetch_failed'],
                'discovered_count': v['discovered_count'],
                'backup_used': v['backup_used'],
                'notes': v['notes'],
            }
            for k, v in health.items()
        ],
        'publish_rules': {
            'requires_is_active': True,
            'allowed_validation_statuses': ['passed', 'soft_pass'],
            'minimum_relevance_score': 35,
        },
        'pipeline_debug': {
            'discovered_candidates': len(candidates),
            'normalized_candidates': len(normalized),
            'validated_candidates': len(validated),
            'published_products': len(published),
            'adapter_counts': adapter_counts,
            'top_rejection_reasons': rejected_counts.most_common(12),
            'products_missing_price': missing_price,
            'products_missing_image': missing_image,
            'products_redirected_away_from_pdp': redirected_non_pdp,
            'duplicate_collisions': len(collisions),
            'duplicate_examples': collisions[:10],
        },
    }

    rejected_payload = {'generated_at': now, 'rejected_count': len(rejected), 'rejected': rejected}
    return payload, rejected_payload


def validate_existing_catalog(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding='utf-8'))
    products = payload.get('products', []) if isinstance(payload, dict) else []
    checked = []
    for product in products:
        url_ok = False
        image_ok = False
        errors: list[str] = []
        try:
            res = fetch_url(product['canonical_product_url'])
            url_ok = res.status_code < 400 and is_probable_product_page(res.final_url, res.body)
            if not url_ok:
                errors.append('URL not healthy or not PDP')
        except Exception as error:
            errors.append(f'url validation uncertain: {error}')
        image_ok, image_error = check_image_url(product.get('image_url', ''))
        if not image_ok:
            errors.append(f'image validation: {image_error}')

        checked.append({
            'id': product.get('id'),
            'title': product.get('title'),
            'url_ok': url_ok,
            'image_ok': image_ok,
            'validation_status': 'passed' if (url_ok and image_ok) else 'soft_fail',
            'errors': errors,
        })

    return {
        'checked_at': NOW(),
        'product_count': len(checked),
        'passed': sum(1 for row in checked if row['validation_status'] == 'passed'),
        'soft_fail': sum(1 for row in checked if row['validation_status'] != 'passed'),
        'products': checked,
    }


def report_rejected(path: Path = REJECTED_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding='utf-8'))
    rejected = payload.get('rejected', [])
    counts = Counter()
    for row in rejected:
        for err in row.get('errors', []):
            counts[err] += 1
    return {
        'generated_at': payload.get('generated_at'),
        'rejected_count': len(rejected),
        'top_reasons': counts.most_common(20),
    }


def report_adapter_health(path: Path = OUTPUT_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding='utf-8'))
    return {
        'generated_at': payload.get('generated_at'),
        'sources': payload.get('sources', []),
        'pipeline_debug': payload.get('pipeline_debug', {}),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Refresh, validate, and report Tiny Thrash Threads catalog pipeline.')
    sub = parser.add_subparsers(dest='command')
    sub.add_parser('refresh', help='Discover -> normalize -> score -> validate -> publish catalog.')

    validate_parser = sub.add_parser('validate', help='Validate an existing generated catalog file.')
    validate_parser.add_argument('--path', default=str(OUTPUT_PATH))

    reject_parser = sub.add_parser('report-rejected', help='Generate rejected products summary report.')
    reject_parser.add_argument('--path', default=str(REJECTED_PATH))

    health_parser = sub.add_parser('report-health', help='Generate adapter health report.')
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
