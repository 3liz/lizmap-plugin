"""
__copyright__ = 'Copyright 2024, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
"""
from pathlib import Path

import pytest

from pyplugin_installer.version_compare import compareVersions


from .compat import TestCase

""" For testing the core PyPlugin installer 'API'.

As this API is not official, it will allow to detect if the API has changed upstream.
"""


class TestPyPluginInstaller(TestCase):

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
