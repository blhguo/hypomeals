import sys

from django.test import TestCase

import logging


class BaseTestCase(TestCase):

    def setUp(self):
        self.logger = logging.getLogger(__name__)
        self._log_handler = logging.StreamHandler(sys.stdout)
        self.logger.addHandler(self._log_handler)

    def tearDown(self):
        self.logger.removeHandler(self._log_handler)