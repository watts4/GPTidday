# Tiny Thrash Threads

Tiny Thrash Threads is a static catalog discovery site for kids surf/skate + punk/alt clothing.

## New static build-time catalog architecture

The catalog is generated **before** site build using Playwright (headless browser):

1. Load each source listing/search URL with a real browser.
2. Extract only visible listing cards.
3. Normalize into a shared schema.
4. Validate product URLs, redirects, images, title, and parseable price.
5. Publish static JSON files for GitHub Pages/static hosting.

Generated files:
- `public/data/catalog.json`
- `public/data/reports/adapter-report.json`

No runtime retailer scraping is required for page render.

## Commands

```bash
npm install
npx playwright install chromium
npm run catalog:build
npm run catalog:validate
npm run catalog:report
```

## Adapter coverage

- surf_skate_official: O’Neill, Vans, Quiksilver, Billabong, Hurley, Volcom
- alt_punk_official: Red Devil Clothing, Blackcraft
- marketplace: TeePublic Hardcore Punk, TeePublic Punk Rock, Etsy Kids Gothic Clothing
