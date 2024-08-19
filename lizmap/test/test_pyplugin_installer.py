__copyright__ = 'Copyright 2024, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import unittest

from pyplugin_installer.version_compare import chopString, compareVersions

""" For testing the core PyPlugin installer 'API'.

As this API is not official, it will allow to detect if the API has changed upstream.
"""


class TestPyPluginInstaller(unittest.TestCase):

    def test_version_compare(self):
        """ Test version compare. """
        self.assertEqual(2, compareVersions("1.0.0", "2.0.1"))
        self.assertEqual(0, compareVersions("1.0.0", "1.0.0"))
        self.assertEqual(1, compareVersions("2.0.0", "1.0.0"))

        self.assertEqual(2, compareVersions("3.10.2-alpha", "3.10.2-alpha.3"))
        self.assertEqual(1, compareVersions("3.10.2-alpha.4", "3.10.2-alpha.3"))

        # Ok, weird
        self.assertEqual(1, compareVersions("master", "1.0.0"))
        self.assertEqual(2, compareVersions("1.0.0", "master"))

    def test_chop_strings(self):
        """ Test chop strings. """
        self.assertListEqual(['1', '0', '0'], chopString("1.0.0"))
        self.assertListEqual(['1', '0', '0', 'pre'], chopString("1.0.0-pre"))
        self.assertListEqual(['1', '0', '0', 'rc', '4'], chopString("1.0.0-rc.4"))
        self.assertListEqual(['1', '0', '0', 'rc', '4', '1'], chopString("1.0.0-rc.4.1"))
