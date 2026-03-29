import unittest

from scripts.refresh_data import (
    extract_listing_cards,
    extract_price_numbers,
    infer_style_tags,
    is_probable_product_page,
    normalize_category,
    parse_price,
    pick_image_from_chunk,
    validate_candidate,
    Product,
)


class ModelTests(unittest.TestCase):
    def test_price_parse(self):
        self.assertEqual(parse_price('$49.99'), 49.99)
        self.assertEqual(extract_price_numbers('Now $20.00 was $30.00'), [20.0, 30.0])

    def test_category_and_styles(self):
        self.assertEqual(normalize_category('kids shoes', 'toddler skate shoe'), 'shoes')
        tags = infer_style_tags('surf beach checkerboard skate', ['graphic'])
        self.assertIn('surf', tags)
        self.assertIn('skate', tags)
        self.assertIn('graphic', tags)

    def test_image_extract(self):
        chunk = '<img data-src="/cdn/kids-shirt.jpg" /><source srcset="/cdn/a.jpg 1x, /cdn/b.jpg 2x" />'
        self.assertEqual(pick_image_from_chunk(chunk, 'https://shop.example.com/listing'), 'https://shop.example.com/cdn/kids-shirt.jpg')

    def test_product_page_detection(self):
        self.assertTrue(is_probable_product_page('https://shop.example.com/products/toddler-shoe', '<html>buy now</html>', 'Toddler shoe'))
        self.assertFalse(is_probable_product_page('https://shop.example.com/collections/kids', '<html>collection of items</html>', 'Kids'))

    def test_listing_card_extraction(self):
        html = '''
        <div class="card">
          <a href="/products/punk-kids-tee">Punk Kids Tee</a>
          <img src="/images/tee.jpg" />
          <span>$22.00</span>
        </div>
        '''
        adapter = {
            'source_adapter': 'listing_card_v1',
            'source_type': 'retailer',
            'marketplace': False,
            'retailer_name': 'Example',
            'retailer_domain': 'shop.example.com',
            'brand': 'Example',
            'category_context': 'kids punk',
            'age_range': 'kids',
            'style_tags': ['punk'],
        }
        cards = extract_listing_cards('https://shop.example.com/collections/kids', html, adapter)
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].title, 'Punk Kids Tee')
        self.assertEqual(cards[0].source_product_url, 'https://shop.example.com/products/punk-kids-tee')
        self.assertEqual(cards[0].price_text, '$22.00')

    def test_publish_gating_missing_price(self):
        p = Product(
            id='1', slug='x', title='Test Tee', brand='Test', retailer_name='Shop', retailer_domain='shop.example.com',
            source_listing_url='https://shop.example.com/collections/kids', source_product_url='https://shop.example.com/products/test-tee',
            canonical_product_url='https://shop.example.com/products/test-tee', image_url='https://shop.example.com/img.jpg',
            additional_images=[], current_price=0, original_price=None, currency='USD', availability='in_stock',
            category='tees', subcategory='tees', age_range='kids', sizes=[], gender_target='neutral', style_tags=['punk'],
            source_adapter='listing_card_v1', source_type='retailer', marketplace=False, discovered_at='2026-01-01T00:00:00Z',
            last_checked_at='2026-01-01T00:00:00Z', is_active=False, validation_status='pending', validation_errors=[],
            relevance_score=50, dedupe_key='k'
        )
        out, reason = validate_candidate(p)
        self.assertFalse(out.is_active)
        self.assertIn(reason, {'missing price', 'dead URL', 'broken image'})


if __name__ == '__main__':
    unittest.main()
