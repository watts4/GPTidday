# Tiny Thrash Threads

Tiny Thrash Threads is a curated shopping aggregator focused on infant and toddler punk/surf/skate clothing and accessories. The site does **not** handle checkout; every product links directly to the source retailer page.

## Architecture

This repository uses a static, dependency-light stack:

- `index.html` + `src/main.js`: mobile-first hash-routed web app.
- `styles/main.css`: visual system and responsive layout.
- `src/model.js`: search/filter/sort and curation helpers.
- `scripts/refresh_data.py`: source ingestion, normalization, dedupe, and refresh-status reporting.
- `data/products.generated.json`: generated catalog consumed by the frontend.
- `tests/test_model.py`: unit tests for normalization/curation logic.

## UX features

- Homepage with hero, curated collections, and trending products.
- Browse/catalog with:
  - keyword search
  - filters (age, category, brand, retailer, style tags, gender)
  - min/max price filters
  - sorting (featured, newest, price asc/desc, recently updated)
  - incremental “Load more” pagination
- Product detail view with source attribution and outbound retailer link.
- Favorites saved in `localStorage`.
- About/methodology page with source refresh status and warnings.
- Outbound click analytics hook via `CustomEvent('outbound_product_click', ...)`.

## Data model

Generated products include:

- `id`, `slug`, `product_hash`
- `title`, `description_short`, `brand`
- `retailer_name`, `retailer_domain`, `source_product_url`, `source_type`
- `image_url`, `additional_images`
- `current_price`, `original_price`, `currency`
- `age_range`, `sizes`, `gender`
- `category`, `style_tags`
- `availability`, `last_checked_at`
- `featured_score`, `recently_updated`

The generated catalog file also includes refresh metadata:

- `generated_at`
- `sources[]` with per-retailer `live` vs `fallback` status
- `warnings[]` for ingestion failures or fallback conditions

## Ingestion and adapter behavior

Seeded adapters target curated infant/toddler-appropriate URLs from:

- Vans
- Quiksilver
- O'Neill

Refresh pipeline behavior:

1. Fetch public retailer page HTML.
2. Parse Product JSON-LD.
3. Normalize to one schema.
4. Apply curation logic:
   - include/exclude keyword rules
   - style-tag inference
   - category normalization
   - dedupe by product hash
5. If live fetch fails, use curated fallback snapshot (`data/fallback_products.json`).
6. If both live and fallback fail and a previous generated snapshot exists, preserve previous products to avoid an empty catalog.

## Refresh product data

```bash
python3 scripts/refresh_data.py
```

This command is scheduler-friendly (cron/CI).

## Run locally

```bash
python3 -m http.server 8080
# open http://localhost:8080
```

## Test

```bash
python3 -m unittest tests/test_model.py
```

## Freshness and limitations

- Product prices/availability can change at any time on retailer sites.
- Retailer page structures can change and may temporarily break live ingestion.
- In constrained environments (or when blocked by upstream protections), refresh may rely on fallback snapshot data.
- Always treat the outbound retailer page as the final source of truth before purchase.
