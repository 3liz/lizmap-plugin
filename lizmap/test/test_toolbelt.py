"""Test toolbelt."""

import unittest

from lizmap.toolbelt.strings import human_size

__copyright__ = 'Copyright 2024, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


class TestToolBelt(unittest.TestCase):

    def test_human_size(self):
        """ Test human size. """
        self.assertEqual("53 KB", human_size(54512))
        self.assertEqual("53 KB", human_size("54512"))
        self.assertEqual("14 KB", human_size(15145))
        self.assertEqual("14 KB", human_size("15145"))
