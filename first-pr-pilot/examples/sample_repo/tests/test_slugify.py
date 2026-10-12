import unittest
from src.slugify import slugify


class SlugifyTests(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(slugify("Hello World"), "hello-world")
