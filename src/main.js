import { DEFAULT_FILTERS, applyFilters, getFilterOptions } from './model.js';

const app = document.querySelector('#app');
const PAGE_SIZE = 12;

let filters = { ...DEFAULT_FILTERS };
let favorites = new Set(JSON.parse(localStorage.getItem('ttt-favorites') || '[]'));
let data = { generated_at: '', product_count: 0, products: [], sources: [], warnings: [] };
let visibleCount = PAGE_SIZE;

function trackOutbound(product) {
  window.dispatchEvent(
    new CustomEvent('outbound_product_click', {
      detail: {
        product_id: product.id,
        retailer_name: product.retailer_name,
        source_url: product.source_product_url
      }
    })
  );
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

function productCard(p) {
  const saved = favorites.has(p.id);
  return `<article class="card">
    <div class="img-wrap">
      <img src="${p.image_url}" alt="${p.title} from ${p.retailer_name}" loading="lazy" />
      <span class="pill">${p.retailer_name}</span>
      ${p.original_price ? '<span class="sale">Sale</span>' : ''}
    </div>
    <div class="body">
      <p class="brand">${p.brand}</p>
      <h3><a href="#/product/${p.slug}">${p.title}</a></h3>
      <p class="meta">${p.category} • ${p.age_range}${p.gender ? ` • ${p.gender}` : ''}</p>
      <div class="tags">${p.style_tags.slice(0, 4).map((t) => `<span>${t}</span>`).join('')}</div>
      <p class="price"><strong>$${p.current_price.toFixed(2)}</strong>${p.original_price ? `<s>$${p.original_price.toFixed(2)}</s>` : ''}</p>
      <div class="actions">
        <button type="button" data-fav="${p.id}">${saved ? '★ Saved' : '☆ Save'}</button>
        <a data-out="${p.id}" target="_blank" rel="noreferrer" href="${p.source_product_url}">View on retailer site ↗</a>
      </div>
    </div>
  </article>`;
}

function freshnessBanner() {
  const generated = data.generated_at ? new Date(data.generated_at).toLocaleString() : 'unknown';
  return `<p class="freshness">Catalog refreshed: <strong>${generated}</strong>. Pricing/availability are sourced from retailers and can change at any time.</p>`;
}

function homePage() {
  const collections = ['Tiny Groms', 'Mini Punk', 'Surf Baby', 'Toddler Streetwear', 'Checkerboard Classics'];

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
    ${filtered.length === 0 ? '<p class="empty">No matching items found. Try fewer filters.</p>' : ''}
    ${showLoadMore ? '<button type="button" class="load-more" data-load-more="true">Load more</button>' : ''}
  </main>${footer()}`;
}

function productPage(slug) {
  const product = data.products.find((item) => item.slug === slug);
  if (!product) {
    return `${nav()}<main><p class="empty">Product not found. It may have been removed by the source retailer.</p></main>${footer()}`;
  }

  const related = data.products
    .filter((item) => item.id !== product.id && item.style_tags.some((tag) => product.style_tags.includes(tag)))
    .slice(0, 4);

  return `${nav()}<main class="detail">
    <img class="detail-img" src="${product.image_url}" alt="${product.title}" />
    <section>
      <p class="kicker">${product.brand} • ${product.retailer_name}</p>
      <h1>${product.title}</h1>
      <p>${product.description_short || ''}</p>
      <p class="price"><strong>$${product.current_price.toFixed(2)}</strong>${product.original_price ? `<s>$${product.original_price.toFixed(2)}</s>` : ''}</p>
      <p>Age: ${product.age_range} • Category: ${product.category}</p>
      <p>Sizes: ${product.sizes.length ? product.sizes.join(', ') : 'See retailer page for current size availability'}</p>
      <p class="meta">Retailer: ${product.retailer_name} (${product.retailer_domain})</p>
      <div class="tags">${product.style_tags.map((tag) => `<span>${tag}</span>`).join('')}</div>
      <a class="cta" data-out="${product.id}" target="_blank" rel="noreferrer" href="${product.source_product_url}">View on retailer site ↗</a>
    </section>
    <section>
      <h2>Related picks</h2>
      <ul>${related.map((item) => `<li><a href="#/product/${item.slug}">${item.title}</a></li>`).join('')}</ul>
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
    ? `<ul>${data.sources.map((s) => `<li><strong>${s.retailer_name}</strong>: ${s.status}${s.error ? ` (${s.error})` : ''}</li>`).join('')}</ul>`
    : '<p>No source status available for this snapshot.</p>';

  const warnings = data.warnings?.length ? `<ul>${data.warnings.map((w) => `<li>${w}</li>`).join('')}</ul>` : '<p>No refresh warnings recorded.</p>';

  return `${nav()}<main>
    <h1>About & methodology</h1>
    <p>Tiny Thrash Threads is a curated discovery site for infant/toddler punk, surf, skate, and streetwear-adjacent apparel. We do not process payments or checkout.</p>
    <p>Catalog refresh time: <strong>${data.generated_at ? new Date(data.generated_at).toLocaleString() : 'unknown'}</strong>.</p>
    <h2>How curation works</h2>
    <p>Products are normalized from retailer metadata into one schema, filtered by age/style relevance, tagged by style keywords, category-normalized, and deduplicated by content hash.</p>
    <h2>Source refresh status</h2>
    ${sources}
    <h2>Refresh warnings</h2>
    ${warnings}
  </main>${footer()}`;
}

function footer() {
  return `<footer><small>Aggregator only • External retailers own checkout • ${data.product_count} products indexed</small></footer>`;
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
    const response = await fetch('data/products.generated.json', { cache: 'no-store' });
    if (!response.ok) throw new Error(`Failed to load catalog (${response.status})`);
    data = await response.json();
    render();
    window.addEventListener('hashchange', render);
  } catch (error) {
    app.innerHTML = `${nav()}<main><p class="empty">Catalog failed to load. Please retry later.</p><pre>${String(error)}</pre></main>${footer()}`;
  }
}

init();
