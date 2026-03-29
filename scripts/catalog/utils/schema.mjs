import crypto from 'node:crypto';

export const POSITIVE_SIGNALS = [
  'kids', 'toddler', 'infant', 'baby', 'little kids', 'boys', 'girls', 'skate', 'surf', 'checkerboard',
  'boardshorts', 'hoodie', 'slip-on', 'streetwear', 'punk', 'punk rock', 'hardcore', 'goth', 'gothic',
  'rockabilly', 'alt', 'toddler tee', 'youth'
];
export const NEGATIVE_SIGNALS = ['adult-only', 'poster', 'wall art', 'stickers', 'home decor'];

export const slugify = (value = '') => value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');

export function parsePrice(text = '') {
  const m = String(text).match(/\$\s*([0-9]+(?:\.[0-9]{2})?)/);
  return m ? Number(m[1]) : 0;
}

export function extractImage(node = {}) {
  const srcset = node.srcset || node.dataSrcset || '';
  if (srcset) {
    const first = srcset.split(',')[0]?.trim().split(' ')[0];
    if (first) return first;
  }
  return node.src || node.dataSrc || node['data-src'] || '';
}

export function scoreRelevance(title, adapter) {
  const hay = `${title} ${adapter.marketplace_query_context || ''}`.toLowerCase();
  let score = 0;
  for (const word of POSITIVE_SIGNALS) if (hay.includes(word)) score += 8;
  for (const word of NEGATIVE_SIGNALS) if (hay.includes(word)) score -= 20;
  if (adapter.source_type === 'official_brand') score += 20;
  if (adapter.source_type === 'alt_brand') score += 14;
  return Math.max(0, Math.min(100, score));
}

export function normalizeProduct(raw, adapter, now) {
  const title = String(raw.title || '').trim();
  const canonical_product_url = raw.canonical_product_url || raw.source_product_url;
  const current_price = parsePrice(raw.price_text);
  const relevance_score = scoreRelevance(title, adapter);
  const idSeed = `${adapter.id}|${canonical_product_url}|${title}`;
  const id = crypto.createHash('sha1').update(idSeed).digest('hex').slice(0, 14);
  return {
    id,
    slug: slugify(`${adapter.brand}-${title}-${id.slice(0, 6)}`),
    title,
    brand: adapter.brand,
    retailer_name: adapter.retailer_name,
    retailer_domain: adapter.retailer_domain,
    source_type: adapter.source_type,
    source_group: adapter.source_group,
    source_listing_url: adapter.source_listing_url,
    source_product_url: raw.source_product_url,
    canonical_product_url,
    image_url: raw.image_url,
    current_price,
    original_price: null,
    currency: 'USD',
    availability: raw.availability || 'unknown',
    category: 'clothing',
    subcategory: 'clothing',
    age_range: 'kids',
    gender_target: 'neutral',
    style_tags: raw.style_tags || [],
    marketplace_query_context: adapter.marketplace_query_context || null,
    discovered_at: now,
    last_checked_at: now,
    source_adapter: adapter.id,
    is_active: false,
    validation_status: 'pending',
    validation_errors: [],
    relevance_score,
    dedupe_key: `${adapter.retailer_domain}|${slugify(title)}|${current_price}`
  };
}
