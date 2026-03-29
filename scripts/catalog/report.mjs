import fs from 'node:fs/promises';

const catalog = JSON.parse(await fs.readFile('public/data/catalog.json', 'utf-8'));
const report = JSON.parse(await fs.readFile('public/data/reports/adapter-report.json', 'utf-8'));

const byAdapter = Object.fromEntries(report.adapters.map((a) => [a.adapter, {
  discovered: a.discovered_count,
  published: a.published_count,
  rejected: a.rejected_count
}]));

console.log(JSON.stringify({
  generated_at: catalog.generated_at,
  product_count: catalog.product_count,
  adapters: byAdapter,
  rejection_reasons: report.rejection_reasons
}, null, 2));
