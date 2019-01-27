from django.test import TestCase

from meals import utils


class UtilsTest(TestCase):

    def test_generate_valid_upc(self):
        NUM_TESTS = 10
        for i in range(NUM_TESTS):
            self.assertTrue(utils.is_valid_upc(utils.generate_random_upc()))