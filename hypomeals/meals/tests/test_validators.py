from django.core.exceptions import ValidationError

from meals.validators import validate_alphanumeric
from .test_base import BaseTestCase

import logging


logger = logging.getLogger(__name__)


class ValidatorsTest(BaseTestCase):

    def test_alphanumeric_field(self):
        test_cases = ["test1", "TEST2", "tEsT3", "1234", "abcd"]
        for test_case in test_cases:
            logger.info("Validating %s", test_case)
            validate_alphanumeric(test_case)

        test_cases = ["$(@!@", "123!", "\n", "\t"]
        for test_case in test_cases:
            logger.info("Validating %s", test_case)
            with self.assertRaises(ValidationError):
                validate_alphanumeric(test_case)