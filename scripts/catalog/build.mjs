import fs from 'node:fs/promises';
import path from 'node:path';
import { chromium } from 'playwright';
import { ADAPTERS } from './adapters/index.mjs';
import { extractImage, normalizeProduct } from './utils/schema.mjs';

const OUT = path.resolve('public/data/catalog.json');
const REPORT = path.resolve('public/data/reports/adapter-report.json');

const now = new Date().toISOString();

function absolutize(base, maybeRelative) {
  try {
    return new URL(maybeRelative, base).toString();
  } catch {
    return '';
  }
}

function dedupe(products) {
  const byKey = new Map();
  for (const p of products) {
    const key = p.canonical_product_url || p.dedupe_key;
    if (!byKey.has(key)) byKey.set(key, p);
  }
  return [...byKey.values()];
}

async function validateProduct(product) {
  const errors = [];
  try {
    const resp = await fetch(product.source_product_url, { redirect: 'follow' });
    if (!resp.ok) errors.push('dead_url');
    const finalUrl = resp.url;
    product.canonical_product_url = finalUrl;
    if (/\/collections\/|\/search|\/market\//i.test(new URL(finalUrl).pathname)) errors.push('non_product_redirect');
  } catch {
    errors.push('dead_url');
  }

  if (!product.title) errors.push('missing_title');
  if (!product.current_price || Number.isNaN(product.current_price)) errors.push('missing_price');

  try {
    const img = await fetch(product.image_url, { method: 'HEAD', redirect: 'follow' });
    if (!img.ok) errors.push('missing_image');
    const type = img.headers.get('content-type') || '';
    if (!type.includes('image/')) errors.push('missing_image');
  } catch {
    errors.push('missing_image');
  }

  product.validation_errors = [...new Set(errors)];
  product.validation_status = errors.some((e) => ['dead_url', 'non_product_redirect', 'missing_title', 'missing_price', 'missing_image'].includes(e))
    ? 'failed'
    : 'passed';
  product.is_active = product.validation_status === 'passed';
  return product;
}

async function extractAdapter(page, adapter) {
  await page.goto(adapter.source_listing_url, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(2500);

  const cards = await page.$$eval(adapter.listing_card_selector, (anchors, cfg) => {
    const textOf = (el) => (el?.textContent || '').replace(/\s+/g, ' ').trim();
    return anchors
      .slice(0, 240)
      .map((a) => {
        const href = a.getAttribute('href') || '';
        const title = a.getAttribute('title') || textOf(a);
        const card = a.closest('article, li, div, section') || a.parentElement;
        const img = card?.querySelector(cfg.image_selectors.join(',')) || a.querySelector('img');
        const priceEl = card?.querySelector(cfg.price_selectors.join(','));
        const badgeEl = card?.querySelector('[class*="badge"],[class*="tag"],[data-badge]');
        return {
          source_product_url: href,
          title,
          price_text: textOf(priceEl),
          image: {
            src: img?.getAttribute('src') || '',
            dataSrc: img?.getAttribute('data-src') || '',
            srcset: img?.getAttribute('srcset') || '',
            dataSrcset: img?.getAttribute('data-srcset') || ''
          },
          availability: textOf(badgeEl)
        };
      })
      .filter((row) => row.source_product_url && row.title);
  }, { image_selectors: adapter.image_selectors, price_selectors: adapter.price_selectors });

  return cards.map((card) => ({
    ...card,
    source_product_url: absolutize(adapter.source_listing_url, card.source_product_url),
    image_url: absolutize(adapter.source_listing_url, extractImage(card.image)),
    style_tags: [adapter.source_group.includes('surf') ? 'surf' : 'punk'].filter(Boolean)
  }));
}

async function main() {
  await fs.mkdir(path.dirname(OUT), { recursive: true });
  await fs.mkdir(path.dirname(REPORT), { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  const all = [];
  const report = { generated_at: now, adapters: [], rejection_reasons: {} };

  for (const adapter of ADAPTERS) {
    let discovered = [];
    let error = null;
    try {
      discovered = await extractAdapter(page, adapter);
    } catch (e) {
      error = String(e);
    }

    const normalized = discovered.map((row) => normalizeProduct({ ...row, canonical_product_url: row.source_product_url }, adapter, now));
    const validated = [];
    for (const n of normalized) validated.push(await validateProduct(n));

    const accepted = validated.filter((p) => p.validation_status === 'passed');
    const rejected = validated.filter((p) => p.validation_status === 'failed');
    for (const r of rejected) {
      for (const reason of r.validation_errors) report.rejection_reasons[reason] = (report.rejection_reasons[reason] || 0) + 1;
    }

    all.push(...accepted);
    report.adapters.push({
      adapter: adapter.id,
      source_listing_url: adapter.source_listing_url,
      discovered_count: discovered.length,
      published_count: accepted.length,
      rejected_count: rejected.length,
      sample_accepted: accepted.slice(0, 3).map((p) => ({ title: p.title, url: p.canonical_product_url, price: p.current_price })),
      error
    });
  }

  await browser.close();

  const published = dedupe(all);
  const catalog = {
    generated_at: now,
    product_count: published.length,
    products: published,
    sources: report.adapters.map((a) => ({
      adapter: a.adapter,
      source_label: a.adapter,
      source_group: ADAPTERS.find((x) => x.id === a.adapter)?.source_group || 'unknown',
      discovered_count: a.discovered_count,
      published_count: a.published_count,
      rejected_count: a.rejected_count
    })),
    pipeline_debug: {
      discovered_candidates: report.adapters.reduce((n, a) => n + a.discovered_count, 0),
      published_products: published.length,
      top_rejection_reasons: Object.entries(report.rejection_reasons).sort((a, b) => b[1] - a[1]).slice(0, 20)
    },
    source_groups: {
      surf_skate_official: ADAPTERS.filter((a) => a.source_group === 'surf_skate_official').map((a) => a.retailer_name),
      alt_punk_official: ADAPTERS.filter((a) => a.source_group === 'alt_punk_official').map((a) => a.retailer_name),
      marketplace: ADAPTERS.filter((a) => a.source_group === 'marketplace').map((a) => a.retailer_name)
    }
  };

  await fs.writeFile(OUT, JSON.stringify(catalog, null, 2));
  await fs.writeFile(REPORT, JSON.stringify(report, null, 2));
  console.log(`Catalog build complete: ${published.length} products -> ${OUT}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
