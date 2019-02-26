from meals.models import Unit
from .test_base import BaseTestCase


class ModelsTest(BaseTestCase):
    fixtures = ["units.json"]

    def test_parse_units(self):
        test_cases = [
            ("1.4oz", (1.4, "oz.")),
            ("0.23lb.", (0.23, "lb.")),
            ("100 kg", (100, "kg")),
            ("12 fl. oz.", (12, "fl. oz.")),
            (".3 L", (0.3, "L")),
            (".25 liters", (0.25, "L")),
            ("10 mL.", (10, "mL")),
            ("1 ton", (1, "ton")),
            (".23               pint", (0.23, "pt.")),
            ("0.12345  gal.lon.", (0.12345, "gal.")),
            ("134 ct", (134, "ct")),
            ("150 c.o.u.n.t.", (150, "ct")),
        ]

        for test_case, (num, unit) in test_cases:
            actual_num, actual_unit = Unit.from_exp(test_case)
            self.assertEqual(num, actual_num, msg="Number part mismatch")
            self.assertEqual(unit, actual_unit.symbol, msg="Unit part mismatch")

    def test_parse_unit_errors(self):
        test_cases = [
            ("123", "missing units"),
            ("ct", "missing number"),
            ("123 unit", "unrecognized unit"),
            ("10 oz.fl.", "unrecognized unit"),
        ]

        for test_case, msg in test_cases:
            with self.assertRaises(RuntimeError, msg=msg):
                Unit.from_exp(test_case)