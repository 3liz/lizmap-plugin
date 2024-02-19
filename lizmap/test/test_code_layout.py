"""Test code layout."""

import re
import unittest

from pathlib import Path

from lizmap.toolbelt.resources import resources_path

__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


class TestCodeLayout(unittest.TestCase):

    @staticmethod
    def ui_files():
        """ List of UI files in the plugin. """
        return [x for x in Path(resources_path('ui')).iterdir() if x.suffix == '.ui']

    def test_qgis_widgets(self):
        """Test imports are correct in UI file."""
        list_files = []
        expression = r'<header>qgs[a-z]*\.h<\/header>'
        for ui in self.ui_files():
            with open(ui) as ui_file:
                matches = re.findall(
                    expression, ui_file.read(), re.MULTILINE)
                if len(matches):
                    list_files.append(str(ui))

        self.assertListEqual(list_files, [], 'Some imports are wrong : {}'.format(', '.join(list_files)))

    def test_no_connection_in_ui(self):
        """Test there is not connection in UI."""
        list_files = []
        expression = r'</connections>'
        for ui in self.ui_files():
            with open(ui) as ui_file:
                matches = re.findall(
                    expression, ui_file.read(), re.MULTILINE)
                if len(matches):
                    list_files.append(str(ui))

        self.assertListEqual(list_files, [], 'Use PyQt connect in Python files, not UI : {}'.format(', '.join(list_files)))
