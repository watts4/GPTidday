import fs from 'node:fs/promises';

const path = 'public/data/catalog.json';
const raw = JSON.parse(await fs.readFile(path, 'utf-8'));
const products = raw.products || [];
let passed = 0;
let failed = 0;
for (const p of products) {
  if (p.title && p.image_url && p.canonical_product_url && Number(p.current_price) > 0) passed += 1;
  else failed += 1;
}
console.log(JSON.stringify({ checked: products.length, passed, failed }, null, 2));
if (failed > 0) process.exitCode = 1;
