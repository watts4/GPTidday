# Tiny Thrash Threads

Tiny Thrash Threads is a curated shopping aggregator focused on infant/toddler/little-kids punk/surf/skate/alt apparel. The site does **not** handle checkout; every product links directly to a live retailer product page.

## Architecture

- `index.html` + `src/main.js`: hash-routed frontend with product cards/detail/filtering.
- `styles/main.css`: visual styles.
- `src/model.js`: browse/filter/sort logic.
- `scripts/refresh_data.py`: **listing-card-first** discovery → normalization → validation → publish pipeline.
- `data/products.generated.json`: published catalog snapshot (active products only).
- `data/products.rejected.json`: rejection/debug artifact with stage + reason.
- `tests/test_model.py`: unit tests for parser + validation helpers.

## Listing-card-first catalog pipeline

### 1) Fetch live listing pages
Each enabled adapter fetches its retailer category/search page(s):

- Vans little kids & toddlers
- Red Devil all-kids collection
- TeePublic punk kids t-shirt listing
- O'Neill kids collection

### 2) Extract listing cards
Extraction reads only what is present on listing cards:

- card anchor (`href`) for `source_product_url`
- title text
- visible price text
- card image (`src`, `data-src`, `srcset`)
- badges (sale/new/out-of-stock)

No guessed slugs, guessed PDP URLs, guessed image URLs, or synthetic title generation is allowed.

### 3) Normalize
Candidates are normalized to a single schema including:

- `source_listing_url`, `source_product_url`, `canonical_product_url`
- `title`, `image_url`, `current_price`, `original_price`
- `retailer_name`, `retailer_domain`, `source_adapter`
- `source_type` and `marketplace` (for TeePublic)
- `category`, `subcategory`, `age_range`, `style_tags`
- validation + relevance metadata

### 4) Validate and publish
Hard publish blockers:

- dead product URL / 404 / failed resolution
- redirect to non-product page
- missing/broken primary image
- missing/unparseable primary price
- empty title

Only products passing those checks are published.

## Commands

```bash
# fetch live listings -> extract cards -> normalize -> validate -> publish
python3 scripts/refresh_data.py refresh

# re-check URLs and images in a generated catalog
python3 scripts/refresh_data.py validate --path data/products.generated.json

# rejection summary + reason counts
python3 scripts/refresh_data.py report-rejected --path data/products.rejected.json

# adapter health + discovered/published/rejected counts
python3 scripts/refresh_data.py report-health --path data/products.generated.json

# unit tests
python3 -m unittest tests/test_model.py
```

## Adapter health / debug outputs

`data/products.generated.json` includes:

- discovered / normalized / validated / published counts
- per-adapter discovered / published / rejected counts
- top rejection reasons (`dead URL`, `non-product redirect`, `missing price`, `missing image`, `broken image`, etc.)
- duplicate collision count
- sample accepted products per adapter
