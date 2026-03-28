export const DEFAULT_FILTERS = {
  query: '',
  ageRange: 'all',
  category: 'all',
  brand: 'all',
  retailer: 'all',
  styleTag: 'all',
  gender: 'all',
  sort: 'featured',
  minPrice: 0,
  maxPrice: 500
};

const includeKeywords = ['toddler', 'baby', 'infant', 'kid', 'romper', 'onesie', 'boardshort', 'skate', 'surf', 'checkerboard', 'hoodie', 'beanie', 'tee', 'shoe'];
const excludePatterns = [/\badult\b/i, /\bgift\s*card\b/i, /\bmen(?:'s)?\b/i, /\bwomen(?:'s)?\b/i];

const styleKeywordMap = {
  punk: ['punk', 'distressed', 'grunge', 'alt'],
  surf: ['surf', 'wave', 'beach', 'saltwater', 'boardshort'],
  skate: ['skate', 'checkerboard', 'streetwear', 'vans'],
  checkerboard: ['checkerboard'],
  graphic: ['graphic', 'logo', 'print'],
  beach: ['beach', 'ocean', 'coast'],
  'vintage wash': ['vintage', 'washed', 'faded']
};

export function relevancePass(text) {
  const lowered = text.toLowerCase();
  const include = includeKeywords.some((word) => lowered.includes(word));
  const excluded = excludePatterns.some((pattern) => pattern.test(text));
  return include && !excluded;
}

export function inferStyleTags(text, seedTags = []) {
  const lowered = text.toLowerCase();
  const inferred = Object.entries(styleKeywordMap)
    .filter(([, words]) => words.some((w) => lowered.includes(w)))
    .map(([tag]) => tag);
  return [...new Set([...seedTags, ...inferred])];
}

export function normalizeCategory(categoryHint, text) {
  const options = [
    ['onesie', 'onesies'],
    ['romper', 'rompers'],
    ['tee', 'tees'],
    ['hoodie', 'hoodies'],
    ['short', 'boardshorts'],
    ['beanie', 'beanies'],
    ['sock', 'socks'],
    ['shoe', 'shoes'],
    ['jacket', 'jackets'],
    ['overall', 'overalls'],
    ['hat', 'hats'],
    ['bag', 'accessories']
  ];

  const lowered = `${categoryHint} ${text}`.toLowerCase();
  const match = options.find(([needle]) => lowered.includes(needle));
  return match ? match[1] : 'clothing';
}

export function styleScore(styleTags, title) {
  let score = styleTags.length * 10;
  if (title.toLowerCase().includes('checkerboard')) score += 15;
  if (styleTags.includes('punk')) score += 12;
  if (styleTags.includes('surf')) score += 10;
  if (styleTags.includes('skate')) score += 10;
  return Math.min(score, 100);
}

export function applyFilters(products, f) {
  const filtered = products.filter((p) => {
    const text = `${p.title} ${p.description_short} ${p.style_tags.join(' ')}`.toLowerCase();
    if (f.query && !text.includes(f.query.toLowerCase())) return false;
    if (f.ageRange !== 'all' && p.age_range !== f.ageRange) return false;
    if (f.category !== 'all' && p.category !== f.category) return false;
    if (f.brand !== 'all' && p.brand !== f.brand) return false;
    if (f.retailer !== 'all' && p.retailer_name !== f.retailer) return false;
    if (f.styleTag !== 'all' && !p.style_tags.includes(f.styleTag)) return false;
    if (f.gender !== 'all' && (p.gender_target || p.gender) !== f.gender) return false;
    if (p.current_price < f.minPrice || p.current_price > f.maxPrice) return false;
    return true;
  });

  return filtered.sort((a, b) => {
    if (f.sort === 'newest') return b.last_checked_at.localeCompare(a.last_checked_at);
    if (f.sort === 'updated') return Number(b.recently_updated) - Number(a.recently_updated);
    if (f.sort === 'price_asc') return a.current_price - b.current_price;
    if (f.sort === 'price_desc') return b.current_price - a.current_price;
    return b.featured_score - a.featured_score;
  });
}

export function getFilterOptions(products) {
  return {
    ages: [...new Set(products.map((p) => p.age_range))],
    categories: [...new Set(products.map((p) => p.category))],
    brands: [...new Set(products.map((p) => p.brand))],
    retailers: [...new Set(products.map((p) => p.retailer_name))],
    styleTags: [...new Set(products.flatMap((p) => p.style_tags))]
  };
}
