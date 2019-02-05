from .test_base import BaseTestCase
from meals import utils


class UtilsTest(BaseTestCase):
    def test_generate_valid_upc(self):
        """Any generated UPC should also be valid"""

        NUM_TESTS = 10
        for _ in range(NUM_TESTS):
            self.assertTrue(utils.is_valid_upc(utils.generate_random_upc()))

    def test_is_valid_upc(self):
        """Tests some real-world UPCs and some made-up ones"""

        # Real-world UPC numbers should be valid
        test_cases = [
            "085239407578",
            "611269991000",
            "742365264450",
            "742365264450",
            "085239616307",
            "048500202753",
        ]
        self.logger.info("%sReal UPCs%s", "=" * 10, "=" * 10)
        for test_case in test_cases:
            self.logger.info("Trying UPC %s", test_case)
            self.assertTrue(utils.is_valid_upc(test_case))

        # Now test some made up ones
        test_cases = [
            "12345",
            "abc123",
            "10293000040",
            "0085239407577",  # invalid check digit
            "0085239616300",
            "1",
            "",
            "0000000000001",
        ]

        self.logger.info("%sFake UPCs%s", "=" * 10, "=" * 10)
        for test_case in test_cases:
            self.logger.info("Trying UPC %s", test_case)
            self.assertFalse(utils.is_valid_upc(test_case))

    def test_next_alphanumeric_str(self):
        test_cases = {
            "123": "124",
            "abc": "abd",
            "ABC": "ABD",
            "zzz": "1aaa",
            "xyz": "xza",
            "0000": "0001",
            "helloworld": "helloworle",
        }

        for test_case, expected in test_cases.items():
            next_str = utils.next_alphanumeric_str(test_case)
            self.assertEqual(next_str, expected)

    def test_next_alphanumeric_str_raises_on_nonalphanumeric_characters(self):
        with self.assertRaisesRegex(RuntimeError, r"'!' is not alphanumeric"):
            utils.next_alphanumeric_str("HelloWorld!")