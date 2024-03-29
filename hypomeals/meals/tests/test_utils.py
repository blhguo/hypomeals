from datetime import datetime

from django.utils import timezone

from meals import utils
from .test_base import BaseTestCase


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

    def test_compute_end_time(self):
        tz = timezone.get_current_timezone()
        test_cases = [
            (
                (tz.localize(datetime(2019, 2, 21, 9, 0, 0)), 1),
                tz.localize(datetime(2019, 2, 21, 10, 0, 0)),
                "9AM, 1 hour, 10AM",
            ),
            (
                (tz.localize(datetime(2019, 2, 21, 9, 0, 0)), 10),
                tz.localize(datetime(2019, 2, 22, 9, 0, 0)),
                "9AM, 10 hours, 9AM next day",
            ),
            (
                (tz.localize(datetime(2019, 2, 21, 9, 0, 0)), 24),
                tz.localize(datetime(2019, 2, 23, 13, 0, 0)),
                "9AM, 24 hours, 1PM two days later",
            ),
            (
                (tz.localize(datetime(2019, 2, 21, 20, 0, 0)), 11),
                tz.localize(datetime(2019, 2, 23, 9, 0, 0)),
                "8PM, 11 hours, 9AM two days later (no work first day)",
            ),
            (
                (tz.localize(datetime(2019, 2, 21, 18, 0, 0)), 10),
                tz.localize(datetime(2019, 2, 22, 18, 0, 0)),
                "6PM, 10 hours, 6PM next day",
            ),
            (
                (tz.localize(datetime(2019, 2, 21, 8, 0, 0)), 10),
                tz.localize(datetime(2019, 2, 21, 18, 0, 0)),
                "8AM, 10 hours, 6PM",
            ),
            (
                (tz.localize(datetime(2019, 2, 21, 8, 0, 0)), 0.5),
                tz.localize(datetime(2019, 2, 21, 8, 30, 0)),
                "8AM, 30 minutes, 8:30AM",
            ),
            (
                (tz.localize(datetime(2019, 2, 21, 8, 0, 0)), 10.5),
                tz.localize(datetime(2019, 2, 22, 8, 30, 0)),
                "8AM, 10.5 hours, 8:30AM next day",
            ),
            (
                (tz.localize(datetime(2019, 2, 21, 1, 0, 0)), 4),
                tz.localize(datetime(2019, 2, 21, 12, 0, 0)),
                "1AM, 4 hours, 12PM same day",
            ),
            (
                (tz.localize(datetime(2019, 3, 9, 16, 0, 0)), 4),
                tz.localize(datetime(2019, 3, 10, 10, 0, 0)),
                "4PM, 4 hours, 10 AM next day, across DST switch"
            )
        ]
        for (start_time, hours), expected, msg in test_cases:
            print(
                "start:   ",
                start_time.strftime("%Y-%m-%d %H:%M:%S %Z%z"),
                "+",
                hours,
                "hours",
            )
            end_time = utils.compute_end_time(start_time, hours)
            print("end:     ", end_time.strftime("%Y-%m-%d %H:%M:%S %Z%z"))
            print("expected:", expected.strftime("%Y-%m-%d %H:%M:%S %Z%z"))
            self.assertEqual(end_time, expected, msg)
