import { DEFAULT_FILTERS, applyFilters, getFilterOptions } from './model.js';

const app = document.querySelector('#app');
const PAGE_SIZE = 12;

let filters = { ...DEFAULT_FILTERS };
let favorites = new Set(JSON.parse(localStorage.getItem('ttt-favorites') || '[]'));
let data = { generated_at: '', product_count: 0, products: [], sources: [], warnings: [] };
let visibleCount = PAGE_SIZE;

function escapeHtml(value = '') {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function normalizeAbsoluteUrl(value) {
  const raw = String(value || '').trim();
  if (!raw) return '';
  if (/^https?:\/\//i.test(raw)) return raw;
  if (raw.startsWith('//')) return `https:${raw}`;
  try {
    return new URL(raw, window.location.origin).toString();
  } catch {
    return '';
  }
}

function sanitizeProduct(raw) {
  const styleTags = Array.isArray(raw?.style_tags) ? raw.style_tags.filter(Boolean) : [];
  const sizes = Array.isArray(raw?.sizes) ? raw.sizes.filter(Boolean) : [];
  const price = Number(raw?.current_price ?? raw?.price ?? raw?.amount);
  const title = String(raw?.title || '').trim();
  const image = normalizeAbsoluteUrl(raw?.image_url || raw?.image || raw?.primary_image);
  const sourceUrl = normalizeAbsoluteUrl(raw?.canonical_product_url || raw?.source_product_url || raw?.product_url || raw?.url || raw?.link);
  if (!title || !image || !sourceUrl || !Number.isFinite(price) || price <= 0) return null;
  return {
    ...raw,
    id: String(raw?.id || `${raw?.retailer_name || 'product'}-${raw?.slug || title}`),
    slug: String(raw?.slug || title.toLowerCase().replace(/[^a-z0-9]+/g, '-')),
    title,
    brand: String(raw?.brand || raw?.retailer_name || 'Unknown'),
    retailer_name: String(raw?.retailer_name || 'Unknown retailer'),
    retailer_domain: String(raw?.retailer_domain || 'unknown'),
    source_product_url: String(raw?.source_product_url || sourceUrl),
    canonical_product_url: sourceUrl,
    image_url: image,
    category: String(raw?.category || 'clothing'),
    age_range: String(raw?.age_range || 'kids'),
    style_tags: styleTags,
    sizes,
    description_short: String(raw?.description_short || ''),
    current_price: price,
    currency: String(raw?.currency || 'USD'),
    validation_status: String(raw?.validation_status || 'soft_pass'),
    is_active: raw?.is_active !== false
  };
}

function trackOutbound(product) {
  window.dispatchEvent(
    new CustomEvent('outbound_product_click', {
      detail: {
        product_id: product.id,
        retailer_name: product.retailer_name,
        source_url: product.canonical_product_url || product.source_product_url
      }
    })
  );
}

function safeCurrency(price, currency = 'USD') {
  try {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(price);
  } catch {
    return `$${Number(price || 0).toFixed(2)}`;
  }
}

function saveFavorites() {
  localStorage.setItem('ttt-favorites', JSON.stringify([...favorites]));
}

function nav() {
  return `
    <header>
      <a class="logo" href="#/">Tiny Thrash Threads</a>
      <nav aria-label="Main navigation">
        <a href="#/browse">Browse</a>
        <a href="#/favorites">Favorites</a>
        <a href="#/about">About</a>
      </nav>
    </header>
  `;
}

function productImage(p, cls = '') {
  return `<img class="${cls}" src="${escapeHtml(p.image_url)}" alt="${escapeHtml(p.title)} from ${escapeHtml(p.retailer_name)}" loading="lazy" onerror="this.closest('.img-wrap,.detail-image-wrap')?.classList.add('img-error'); this.remove();" />`;
}

function productCard(p) {
  const saved = favorites.has(p.id);
  const encodedSlug = encodeURIComponent(p.slug);
  const outboundUrl = escapeHtml(p.canonical_product_url || p.source_product_url);
  return `<article class="card">
    <div class="img-wrap">
      ${productImage(p)}
      <span class="pill">${escapeHtml(p.retailer_name)}</span>
      <span class="pill">${p.source_type === 'official_brand' ? 'Official Brand' : p.source_type === 'alt_brand' ? 'Alt Brand' : 'Marketplace'}</span>
      ${p.original_price ? '<span class="sale">Sale</span>' : ''}
    </div>
    <div class="body">
      <p class="brand">${escapeHtml(p.brand)}</p>
      <h3><a href="#/product/${encodedSlug}">${escapeHtml(p.title)}</a></h3>
      <p class="meta">${escapeHtml(p.category)} • ${escapeHtml(p.age_range)}${p.gender_target ? ` • ${escapeHtml(p.gender_target)}` : ''}</p>
      <div class="tags">${p.style_tags.slice(0, 4).map((t) => `<span>${escapeHtml(t)}</span>`).join('')}</div>
      <p class="price"><strong>${safeCurrency(p.current_price, p.currency)}</strong>${p.original_price ? `<s>${safeCurrency(p.original_price, p.currency)}</s>` : ''}</p>
      <div class="actions">
        <button type="button" data-fav="${escapeHtml(p.id)}">${saved ? '★ Saved' : '☆ Save'}</button>
        <a data-out="${escapeHtml(p.id)}" target="_blank" rel="noreferrer" href="${outboundUrl}">View on retailer site ↗</a>
      </div>
    </div>
  </article>`;
}

function freshnessBanner() {
  const generated = data.generated_at ? new Date(data.generated_at).toLocaleString() : 'unknown';
  return `<p class="freshness">Catalog refreshed: <strong>${generated}</strong>. Only products that pass live page + image validation are published.</p>`;
}

function homePage() {
  const collections = ['Tiny Groms', 'Mini Punk', 'Surf Baby', 'Toddler Streetwear', 'Little Rebels', 'Goth Kiddos', 'Checkerboard Classics'];

  return `${nav()}<main>
    <section class="hero">
      <p class="kicker">Curated aggregator • infant + toddler focus</p>
      <h1>Tiny Thrash Threads</h1>
      <p>Punk, surf, and skate-inspired clothing and accessories for tiny humans. We link you directly to trusted retailers for final purchase.</p>
      <a class="cta" href="#/browse">Browse catalog</a>
    </section>
    ${freshnessBanner()}
    <section>
      <h2>Curated collections</h2>
      <div class="collections">${collections.map((c) => `<button type="button" class="collection" data-collection="${c}">${c}</button>`).join('')}</div>
    </section>
    <section>
      <h2>Trending now</h2>
      <div class="grid">${data.products.slice(0, 8).map(productCard).join('')}</div>
    </section>
  </main>${footer()}`;
}

function filterControls(options) {
  const select = (key, values, label) => `
    <label>${label}
      <select data-filter="${key}">
        <option value="all">All ${label.toLowerCase()}</option>
        ${values.map((v) => `<option value="${v}" ${filters[key] === v ? 'selected' : ''}>${v}</option>`).join('')}
      </select>
    </label>`;

  return `<section class="filters" aria-label="Catalog filters">
    <label>Search
      <input data-filter="query" value="${filters.query}" placeholder="checkerboard hoodie beach" aria-label="Search products" />
    </label>
    ${select('category', options.categories, 'Category')}
    ${select('ageRange', options.ages, 'Age')}
    ${select('brand', options.brands, 'Brand')}
    ${select('retailer', options.retailers, 'Retailer')}
    ${select('styleTag', options.styleTags, 'Style')}
    <label>Gender
      <select data-filter="gender">
        <option value="all">All fits</option>
        <option value="neutral" ${filters.gender === 'neutral' ? 'selected' : ''}>Gender-neutral</option>
        <option value="boy" ${filters.gender === 'boy' ? 'selected' : ''}>Boy</option>
        <option value="girl" ${filters.gender === 'girl' ? 'selected' : ''}>Girl</option>
      </select>
    </label>
    <label>Sort
      <select data-filter="sort">
        <option value="featured" ${filters.sort === 'featured' ? 'selected' : ''}>Featured / Curated</option>
        <option value="newest" ${filters.sort === 'newest' ? 'selected' : ''}>Newest</option>
        <option value="price_asc" ${filters.sort === 'price_asc' ? 'selected' : ''}>Price low to high</option>
        <option value="price_desc" ${filters.sort === 'price_desc' ? 'selected' : ''}>Price high to low</option>
        <option value="updated" ${filters.sort === 'updated' ? 'selected' : ''}>Recently updated</option>
      </select>
    </label>
    <label>Min price
      <input type="number" min="0" step="1" data-filter="minPrice" value="${filters.minPrice}" />
    </label>
    <label>Max price
      <input type="number" min="0" step="1" data-filter="maxPrice" value="${filters.maxPrice}" />
    </label>
  </section>`;
}

function browsePage() {
  const options = getFilterOptions(data.products);
  const filtered = applyFilters(data.products, filters);
  const visible = filtered.slice(0, visibleCount);
  const showLoadMore = filtered.length > visible.length;

  return `${nav()}<main>
    <h1>Browse catalog</h1>
    ${freshnessBanner()}
    ${filterControls(options)}
    <p class="small">Showing ${visible.length} of ${filtered.length} products</p>
    <div class="grid">${visible.map(productCard).join('')}</div>
    ${filtered.length === 0 ? '<p class="empty">No active validated items available right now. Try again after the next refresh.</p>' : ''}
    ${showLoadMore ? '<button type="button" class="load-more" data-load-more="true">Load more</button>' : ''}
  </main>${footer()}`;
}

function productPage(slug) {
  const normalizedSlug = decodeURIComponent(slug || '');
  const product = data.products.find((item) => item.slug === normalizedSlug);
  if (!product) {
    return `${nav()}<main><p class="empty">Product not found. It may have been removed after failing active-product validation.</p></main>${footer()}`;
  }

  const related = data.products
    .filter((item) => item.id !== product.id && item.style_tags.some((tag) => product.style_tags.includes(tag)))
    .slice(0, 4);

  return `${nav()}<main class="detail">
    <div class="detail-image-wrap">${productImage(product, 'detail-img')}</div>
    <section>
      <p class="kicker">${escapeHtml(product.brand)} • ${escapeHtml(product.retailer_name)}</p>
      <h1>${escapeHtml(product.title)}</h1>
      <p>${escapeHtml(product.description_short || '')}</p>
      <p class="price"><strong>${safeCurrency(product.current_price, product.currency)}</strong>${product.original_price ? `<s>${safeCurrency(product.original_price, product.currency)}</s>` : ''}</p>
      <p>Age: ${escapeHtml(product.age_range)} • Category: ${escapeHtml(product.category)}</p>
      <p>Sizes: ${product.sizes.length ? escapeHtml(product.sizes.join(', ')) : 'See retailer page for current size availability'}</p>
      <p class="meta">Retailer: ${escapeHtml(product.retailer_name)} (${escapeHtml(product.retailer_domain)})</p>
      <p class="meta">Last checked: ${product.last_checked_at ? new Date(product.last_checked_at).toLocaleString() : 'unknown'}</p>
      <div class="tags">${product.style_tags.map((tag) => `<span>${escapeHtml(tag)}</span>`).join('')}</div>
      <a class="cta" data-out="${escapeHtml(product.id)}" target="_blank" rel="noreferrer" href="${escapeHtml(product.canonical_product_url || product.source_product_url)}">View on retailer site ↗</a>
    </section>
    <section>
      <h2>Related picks</h2>
      <ul>${related.map((item) => `<li><a href="#/product/${encodeURIComponent(item.slug)}">${escapeHtml(item.title)}</a></li>`).join('')}</ul>
    </section>
  </main>${footer()}`;
}

function favoritesPage() {
  const favoritesList = data.products.filter((p) => favorites.has(p.id));
  return `${nav()}<main>
    <h1>Saved favorites</h1>
    ${favoritesList.length ? `<div class="grid">${favoritesList.map(productCard).join('')}</div>` : '<p class="empty">You have no saved favorites yet.</p>'}
  </main>${footer()}`;
}

function aboutPage() {
  const sources = data.sources?.length
    ? `<ul>${data.sources.map((s) => `<li><strong>${s.source_label || s.retailer_name}</strong> • ${s.source_group} • discovered ${s.discovered_count}, published ${s.published_count}, rejected ${s.rejected_count}</li>`).join('')}</ul>`
    : '<p>No source status available for this snapshot.</p>';

  const warnings = data.warnings?.length ? `<ul>${data.warnings.map((w) => `<li>${w}</li>`).join('')}</ul>` : '<p>No refresh warnings recorded.</p>';

  return `${nav()}<main>
    <h1>About & methodology</h1>
    <p>Tiny Thrash Threads is a curated discovery site for infant/toddler punk, surf, skate, and streetwear-adjacent apparel. We do not process payments or checkout.</p>
    <p>Catalog refresh time: <strong>${data.generated_at ? new Date(data.generated_at).toLocaleString() : 'unknown'}</strong>.</p>
    <h2>How validation works</h2>
    <p>Each candidate product is fetched from the retailer source URL, redirected to final URL, validated as a product-detail page, parsed from structured metadata, and verified for live price + working image URL. Failed candidates are excluded from the public catalog.</p>
    <p>Products can disappear when retailers remove listings or when images/prices are no longer valid.</p>
    <h2>Source refresh status</h2>
    ${sources}
    <h2>Refresh warnings</h2>
    ${warnings}
  </main>${footer()}`;
}

function footer() {
  return `<footer><small>Aggregator only • External retailers own checkout • ${data.product_count} validated products indexed</small></footer>`;
}

function attachSharedListeners() {
  app.querySelectorAll('[data-fav]').forEach((button) => {
    button.addEventListener('click', () => {
      const id = button.getAttribute('data-fav');
      if (!id) return;
      favorites.has(id) ? favorites.delete(id) : favorites.add(id);
      saveFavorites();
      render();
    });
  });

  app.querySelectorAll('[data-out]').forEach((link) => {
    link.addEventListener('click', () => {
      const id = link.getAttribute('data-out');
      const product = data.products.find((item) => item.id === id);
      if (product) trackOutbound(product);
    });
  });
}

function attachFilterListeners() {
  app.querySelectorAll('[data-filter]').forEach((el) => {
    const key = el.getAttribute('data-filter');
    const apply = () => {
      if (!key) return;
      const raw = el.value;
      filters[key] = key === 'minPrice' || key === 'maxPrice' ? Number(raw || 0) : raw;
      visibleCount = PAGE_SIZE;
      render();
    };

    el.addEventListener('change', apply);
    if (el.tagName === 'INPUT') el.addEventListener('input', apply);
  });

  const loadMore = app.querySelector('[data-load-more]');
  if (loadMore) {
    loadMore.addEventListener('click', () => {
      visibleCount += PAGE_SIZE;
      render();
    });
  }
}

function attachCollectionListeners() {
  app.querySelectorAll('[data-collection]').forEach((button) => {
    button.addEventListener('click', () => {
      const name = button.getAttribute('data-collection') || '';
      if (name.toLowerCase().includes('checkerboard')) filters.styleTag = 'checkerboard';
      if (name.toLowerCase().includes('surf')) filters.styleTag = 'surf';
      if (name.toLowerCase().includes('punk')) filters.styleTag = 'punk';
      if (name.toLowerCase().includes('streetwear')) filters.styleTag = 'streetwear';
      if (name.toLowerCase().includes('goth')) filters.styleTag = 'goth';
      if (name.toLowerCase().includes('rebel')) filters.styleTag = 'alt';
      window.location.hash = '#/browse';
    });
  });
}

function render() {
  const hash = window.location.hash || '#/';
  const [, route, slug] = hash.match(/^#\/(\w+)?\/?(.*)?$/) || [];

  if (!route) app.innerHTML = homePage();
  else if (route === 'browse') app.innerHTML = browsePage();
  else if (route === 'product') app.innerHTML = productPage(slug);
  else if (route === 'favorites') app.innerHTML = favoritesPage();
  else if (route === 'about') app.innerHTML = aboutPage();
  else app.innerHTML = `${nav()}<main><p class="empty">Page not found.</p></main>${footer()}`;

  attachSharedListeners();
  attachFilterListeners();
  attachCollectionListeners();
}

async function init() {
  app.innerHTML = `${nav()}<main><p>Loading catalog…</p></main>${footer()}`;
  try {
    const candidates = ['public/data/catalog.json', 'data/catalog.json', 'data/products.generated.json'];
    let loaded = null;
    for (const path of candidates) {
      const response = await fetch(path, { cache: 'no-store' });
      if (response.ok) {
        loaded = await response.json();
        break;
      }
    }
    if (!loaded) throw new Error('Failed to load catalog from known paths');
    const incomingProducts = Array.isArray(loaded) ? loaded : loaded.products || [];
    data = Array.isArray(loaded) ? data : loaded;
    data.products = incomingProducts
      .filter((product) => product?.is_active !== false)
      .filter((product) => {
        const status = String(product?.validation_status || 'soft_pass');
        return ['passed', 'soft_pass'].includes(status);
      })
      .map(sanitizeProduct)
      .filter(Boolean);
    data.product_count = data.products.length;
    render();
    window.addEventListener('hashchange', render);
  } catch (error) {
    app.innerHTML = `${nav()}<main><p class="empty">Catalog failed to load. Please retry later.</p><pre>${String(error)}</pre></main>${footer()}`;
  }
}

init();
