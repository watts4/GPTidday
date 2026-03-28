import unittest

from scripts.refresh_data import (
    feature_score,
    infer_style_tags,
    normalize_category,
    relevance,
)


class ModelTests(unittest.TestCase):
    def test_relevance_positive(self):
        self.assertTrue(relevance('Toddler checkerboard skate shoe'))

    def test_relevance_word_boundary_exclusions(self):
        self.assertFalse(relevance('Adult men gift card'))
        self.assertTrue(relevance('Mini surf tee for tiny riders'))

    def test_category(self):
        self.assertEqual(normalize_category('shoes', 'toddler skate shoe'), 'shoes')
        self.assertEqual(normalize_category('misc', 'baby beanie alt'), 'beanies')

    def test_style_tags(self):
        tags = infer_style_tags('surf beach checkerboard skate', ['graphic'])
        self.assertIn('surf', tags)
        self.assertIn('skate', tags)
        self.assertIn('graphic', tags)

    def test_feature_score(self):
        self.assertGreaterEqual(feature_score(['skate', 'surf'], 'Checkerboard slip on'), 35)


if __name__ == '__main__':
    unittest.main()
