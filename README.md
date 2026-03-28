# Tiny Thrash Threads

Tiny Thrash Threads is a curated shopping aggregator focused on infant and toddler punk/surf/skate clothing and accessories. The site does **not** handle checkout; every product links directly to a retailer product detail page.

## Architecture

- `index.html` + `src/main.js`: hash-routed frontend with product cards/detail/filtering.
- `styles/main.css`: visual styles.
- `src/model.js`: filter + sort logic used by browse UI.
- `scripts/refresh_data.py`: discovery → normalization → scoring/curation → publish-validation pipeline.
- `data/products.generated.json`: published catalog snapshot (active products only).
- `data/products.rejected.json`: rejection/debug artifact with stage + reason.
- `data/fallback_products.json`: resilience metadata used only when live source fetch fails.
- `tests/test_model.py`: unit tests for pipeline helpers.

## Product pipeline (4 stages)

### A) Discovery
Adapters discover candidates from retailer listing/category/search pages first. If all listing fetches fail for an adapter, it can temporarily fall back to adapter-specific known product candidates (never guessed URLs).

### B) Normalize
Each candidate is mapped to one schema:

- `id`, `slug`, `title`, `brand`
- `retailer_name`, `retailer_domain`
- `source_listing_url`, `source_product_url`, `canonical_product_url`
- `image_url`, `additional_images`
- `current_price`, `original_price`, `currency`, `availability`
- `category`, `age_range`, `sizes`, `style_tags`, `gender_target`
- `discovered_at`, `last_checked_at`, `source_adapter`
- `is_active`, `validation_status`, `validation_errors`
- `relevance_score`, `dedupe_key`

### C) Curate / score
A transparent niche score combines infant/toddler age signals, surf/skate/punk style signals, category quality, and exclusion penalties. Low-relevance products are filtered out without collapsing the entire catalog.

### D) Publish validation
Validation is the final quality gate.

Hard blockers:

- missing trustworthy source URL
- missing primary price
- missing primary image
- clear 404/410/non-product redirect

Soft uncertainty (publishable as `soft_pass` if relevance is high):

- temporary network failures while checking PDP/image
- fallback-snapshot normalization when source site blocks runtime access

## Adapter health + debug visibility

`products.generated.json` includes `pipeline_debug` with:

- discovered/normalized/validated/published counts
- discovered/accepted/rejected counts by adapter/stage
- top rejection reasons
- missing-price/missing-image counts
- redirected-away-from-PDP count
- dedupe collision count + examples

## Refresh, validation, and reports

```bash
# Full refresh: discover -> normalize -> score -> validate -> publish
python3 scripts/refresh_data.py refresh

# Re-validate a generated catalog
python3 scripts/refresh_data.py validate --path data/products.generated.json

# Summarize rejection reasons
python3 scripts/refresh_data.py report-rejected --path data/products.rejected.json

# Show per-adapter health + pipeline debug block
python3 scripts/refresh_data.py report-health --path data/products.generated.json

# Unit tests
python3 -m unittest tests/test_model.py
```

## Notes on enabled adapters

Current adapters are enabled for:

- Vans kids/toddler listings
- Quiksilver kids/baby listings
- O'Neill little-boys/little-girls listings

An adapter may degrade to backup candidates when listing pages are blocked, but failures are isolated to that adapter so the rest of the catalog can still publish.
