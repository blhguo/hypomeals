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
