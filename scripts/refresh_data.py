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
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen

OUTPUT_PATH = Path('data/products.generated.json')
REJECTED_PATH = Path('data/products.rejected.json')
NOW = lambda: datetime.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'

ADAPTERS: list[dict[str, Any]] = [
    {
        'name': 'vans_kids_listing',
        'retailer_name': 'Vans',
        'retailer_domain': 'www.vans.com',
        'brand': 'Vans',
        'listing_urls': ['https://www.vans.com/en-us/c/kids/clothing/little-kids-and-toddlers-3202'],
        'age_range': 'little-kids-and-toddlers',
        'category_context': 'kids clothing little kids toddlers skate checkerboard',
        'style_tags': ['skate', 'streetwear'],
        'source_adapter': 'listing_card_v1',
        'source_type': 'retailer',
        'marketplace': False,
        'enabled': True,
    },
    {
        'name': 'reddevil_kids_listing',
        'retailer_name': 'Red Devil Clothing',
        'retailer_domain': 'reddevilclothing.com',
        'brand': 'Red Devil Clothing',
        'listing_urls': ['https://reddevilclothing.com/collections/all-kids'],
        'age_range': 'kids',
        'category_context': 'all kids punk rockabilly alt',
        'style_tags': ['punk', 'alt', 'rockabilly'],
        'source_adapter': 'listing_card_v1',
        'source_type': 'retailer',
        'marketplace': False,
        'enabled': True,
    },
    {
        'name': 'teepublic_punk_kids_listing',
        'retailer_name': 'TeePublic',
        'retailer_domain': 'www.teepublic.com',
        'brand': 'TeePublic',
        'listing_urls': ['https://www.teepublic.com/kids-t-shirt/punk'],
        'age_range': 'kids',
        'category_context': 'kids t-shirt punk',
        'style_tags': ['punk', 'graphic'],
        'source_adapter': 'listing_card_v1',
        'source_type': 'marketplace',
        'marketplace': True,
        'enabled': True,
    },
    {
        'name': 'oneill_kids_listing',
        'retailer_name': "O'Neill",
        'retailer_domain': 'us.oneill.com',
        'brand': "O'Neill",
        'listing_urls': ['https://us.oneill.com/collections/kids'],
        'age_range': 'kids',
        'category_context': 'kids surf beach lifestyle',
        'style_tags': ['surf', 'beach', 'lifestyle'],
        'source_adapter': 'listing_card_v1',
        'source_type': 'retailer',
        'marketplace': False,
        'enabled': True,
    },
]

STYLE_SIGNALS = {
    'punk': {'punk', 'alt', 'grunge', 'distressed'},
    'surf': {'surf', 'beach', 'saltwater', 'wave', 'boardshort'},
    'skate': {'skate', 'checkerboard', 'vans', 'streetwear'},
    'rockabilly': {'rockabilly'},
    'graphic': {'graphic', 'print', 'logo'},
    'lifestyle': {'lifestyle'},
}
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
class ListingCandidate:
    source_adapter: str
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
    badges: list[str]
    category_context: str
    age_range_hint: str
    style_seed_tags: list[str]
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
    subcategory: str
    age_range: str
    sizes: list[str]
    gender_target: str | None
    style_tags: list[str]
    source_adapter: str
    source_type: str
    marketplace: bool
    discovered_at: str
    last_checked_at: str
    is_active: bool
    validation_status: str
    validation_errors: list[str]
    relevance_score: int
    dedupe_key: str
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
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0 TinyThrashThreadsBot/4.0', 'Accept': accept}, method=method)
    with urlopen(req, timeout=20) as res:
        status_code = getattr(res, 'status', res.getcode())
        return FetchResult(
            status_code=status_code,
            final_url=res.geturl(),
            body=res.read().decode('utf-8', 'ignore') if method == 'GET' else '',
            content_type=(res.headers.get('Content-Type') or '').lower(),
        )


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
    parsed = urlparse(url)
    path = parsed.path.lower()
    if any(x in path for x in ['/search', '/collections', '/collection', '/category', '/c/']):
        return False
    return any(x in path for x in ['/product', '/products/', '.html', '-p']) or path.count('/') >= 2


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

        start = max(0, match.start() - 1000)
        end = min(len(html), match.end() + 1200)
        chunk = html[start:end]
        price_text = ' '.join(re.findall(r'\$\s*\d+(?:[\.,]\d{2})?', chunk))
        image_url = pick_image_from_chunk(chunk, listing_url)
        badges = [b.lower() for b in re.findall(r'\b(sale|new|best seller|out of stock)\b', chunk, flags=re.I)]

        cards.append(ListingCandidate(
            source_adapter=adapter['source_adapter'],
            source_type=adapter['source_type'],
            marketplace=bool(adapter.get('marketplace')),
            retailer_name=adapter['retailer_name'],
            retailer_domain=adapter['retailer_domain'],
            brand_hint=adapter['brand'],
            source_listing_url=listing_url,
            source_product_url=href,
            title=title,
            price_text=price_text,
            image_url=image_url,
            badges=badges,
            category_context=adapter['category_context'],
            age_range_hint=adapter['age_range'],
            style_seed_tags=list(adapter.get('style_tags', [])),
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
            'retailer_name': adapter['retailer_name'],
            'enabled': bool(adapter.get('enabled', True)),
            'listing_fetch_ok': 0,
            'listing_fetch_failed': 0,
            'discovered_count': 0,
            'published_count': 0,
            'rejected_count': 0,
            'notes': [],
            'sample_accepted': [],
        }
        if not adapter.get('enabled', True):
            continue

        adapter_cards: list[ListingCandidate] = []
        for final_url, page in fetch_listing_pages(adapter, health[name]):
            adapter_cards.extend(extract_listing_cards(final_url, page.body, adapter))

        # listing-card-first hard rule: no synthetic fallback candidates.
        if not adapter_cards:
            health[name]['notes'].append('no listing cards extracted')

        candidates.extend(adapter_cards)
        health[name]['discovered_count'] = len(adapter_cards)

    return candidates, rejected, health


def score_candidate(title: str, category: str, style_tags: list[str], age_range: str) -> int:
    text = f'{title} {category} {age_range}'.lower()
    score = 0
    if any(w in text for w in ['infant', 'baby', 'toddler', 'little kid', 'kids']):
        score += 35
    score += min(30, len(style_tags) * 8)
    if category in {'shoes', 'tees', 'hoodies', 'boardshorts', 'onesies', 'rompers'}:
        score += 25
    if any(w in text for w in ['adult', 'home goods', 'furniture']):
        score -= 60
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
    relevance_score = score_candidate(candidate.title, category, style_tags, candidate.age_range_hint)

    canonical_url = strip_tracking_params(candidate.source_product_url)
    id_seed = f"{candidate.retailer_name}:{canonical_url}:{candidate.title}"
    pid = hashlib.sha1(id_seed.encode()).hexdigest()[:12]

    errs: list[str] = []
    if not candidate.title:
        errs.append('missing title')
    if not candidate.image_url:
        errs.append('missing image')
    if current_price <= 0:
        errs.append('missing price')
    if not candidate.source_product_url:
        errs.append('missing source_product_url')

    return Product(
        id=pid,
        slug=slugify(f"{candidate.brand_hint}-{candidate.title}-{pid[:6]}"),
        title=candidate.title,
        brand=candidate.brand_hint,
        retailer_name=candidate.retailer_name,
        retailer_domain=candidate.retailer_domain,
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
        source_adapter=candidate.source_adapter,
        source_type=candidate.source_type,
        marketplace=candidate.marketplace,
        discovered_at=candidate.discovered_at,
        last_checked_at=now,
        is_active=False,
        validation_status='pending',
        validation_errors=errs,
        relevance_score=relevance_score,
        dedupe_key=hashlib.sha1(f"{candidate.retailer_name}:{canonical_url}".encode()).hexdigest(),
        description_short='',
        featured_score=relevance_score,
        recently_updated=True,
    )


def check_image_url(image_url: str) -> tuple[bool, str | None]:
    if not image_url:
        return False, 'missing image'
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
    if any(token in path for token in ['/search', '/collections', '/collection', '/category']):
        return False
    content = f"{title or ''} {html[:2000]}".lower()
    if any(bad in content for bad in ['search results', 'page not found', '404', 'collection of']):
        return False
    return True


def validate_candidate(product: Product) -> tuple[Product, str | None]:
    reasons = list(product.validation_errors)

    if product.relevance_score < 25:
        reasons.append('low relevance')

    try:
        page = fetch_url(product.source_product_url)
        if page.status_code >= 400:
            reasons.append('dead URL')
        if not is_probable_product_page(page.final_url, page.body, product.title):
            reasons.append('non-product redirect')
        product.canonical_product_url = strip_tracking_params(page.final_url)
    except Exception:
        reasons.append('dead URL')

    img_ok, img_error = check_image_url(product.image_url)
    if not img_ok:
        reasons.append('missing image' if img_error == 'missing image' else 'broken image')

    if product.current_price <= 0:
        reasons.append('missing price')
    if not product.title:
        reasons.append('parse failure')

    reasons = sorted(set(reasons))
    product.validation_errors = reasons

    hard_blockers = {'dead URL', 'non-product redirect', 'missing price', 'missing image', 'broken image', 'parse failure'}
    if any(r in hard_blockers for r in reasons):
        product.validation_status = 'failed'
        product.is_active = False
        return product, (next((r for r in reasons if r in hard_blockers), 'parse failure'))

    product.validation_status = 'passed'
    product.is_active = True
    return product, None


def dedupe_products(products: list[Product]) -> tuple[list[Product], int]:
    out: dict[str, Product] = {}
    collisions = 0
    for p in products:
        existing = out.get(p.dedupe_key)
        if not existing:
            out[p.dedupe_key] = p
            continue
        collisions += 1
        winner = p if (p.relevance_score, p.last_checked_at) > (existing.relevance_score, existing.last_checked_at) else existing
        out[p.dedupe_key] = winner
    return sorted(out.values(), key=lambda x: (-x.relevance_score, x.title)), collisions


def build_payload() -> tuple[dict[str, Any], dict[str, Any]]:
    now = NOW()
    candidates, rejected_rows, health = discover_candidates(now)

    normalized = [normalize_candidate(c, now) for c in candidates]

    validated: list[Product] = []
    reason_counts: Counter[str] = Counter()
    adapter_rejected: Counter[str] = Counter()
    for p in normalized:
        vp, reject_reason = validate_candidate(p)
        validated.append(vp)
        if reject_reason:
            adapter_rejected[p.retailer_name] += 1
            reason_counts[reject_reason] += 1
            rejected_rows.append({
                'id': p.id,
                'title': p.title,
                'retailer_name': p.retailer_name,
                'source_listing_url': p.source_listing_url,
                'source_product_url': p.source_product_url,
                'errors': p.validation_errors,
                'stage': 'publish_validation',
            })

    deduped, collisions = dedupe_products(validated)
    published = [p for p in deduped if p.is_active and p.validation_status == 'passed']

    by_adapter: dict[str, dict[str, int]] = defaultdict(lambda: {'discovered': 0, 'published': 0, 'rejected': 0})
    for c in candidates:
        by_adapter[c.retailer_name]['discovered'] += 1
    for p in published:
        by_adapter[p.retailer_name]['published'] += 1
    for r in rejected_rows:
        by_adapter[r.get('retailer_name', 'unknown')]['rejected'] += 1

    for source in health.values():
        retailer = source['retailer_name']
        source['published_count'] = by_adapter[retailer]['published']
        source['rejected_count'] = by_adapter[retailer]['rejected']
        source['sample_accepted'] = [
            {'title': p.title, 'price': p.current_price, 'url': p.canonical_product_url}
            for p in published if p.retailer_name == retailer
        ][:3]

    payload = {
        'generated_at': now,
        'product_count': len(published),
        'products': [asdict(p) for p in published],
        'sources': list(health.values()),
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
        by_adapter[row.get('retailer_name', 'unknown')] += 1
        for err in row.get('errors', []):
            counts[err] += 1
    return {'generated_at': payload.get('generated_at'), 'rejected_count': len(rejected), 'by_adapter': by_adapter, 'top_reasons': counts.most_common(20)}


def report_adapter_health(path: Path = OUTPUT_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding='utf-8'))
    return {'generated_at': payload.get('generated_at'), 'sources': payload.get('sources', []), 'pipeline_debug': payload.get('pipeline_debug', {})}


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
