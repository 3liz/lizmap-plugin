"""Test code layout."""

import os
import re
import unittest

from .qgis_plugin_tools import resources_path

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


class TestCodeLayout(unittest.TestCase):

    @staticmethod
    def ui_files():
        list_files = []
        for root, _, files in os.walk(resources_path('ui')):
            for file in files:
                if file.lower().endswith('.ui'):
                    file_path = os.path.join(root, file)
                    list_files.append(file_path)
        return list_files

    def test_qgis_widgets(self):
        """Test imports are correct in UI file."""
        list_files = []
        expression = r'<header>qgs[a-z]*\.h<\/header>'
        for ui in self.ui_files():
            with open(ui, 'r') as ui_file:
                matches = re.findall(
                    expression, ui_file.read(), re.MULTILINE)
                if len(matches):
                    list_files.append(ui)
                    print(matches)

        self.assertListEqual(list_files, [], 'Some imports are wrong : {}'.format(', '.join(list_files)))

    def test_no_connection_in_ui(self):
        """Test there is not connection in UI."""
        list_files = []
        expression = r'</connections>'
        for ui in self.ui_files():
            with open(ui, 'r') as ui_file:
                matches = re.findall(
                    expression, ui_file.read(), re.MULTILINE)
                if len(matches):
                    list_files.append(ui)
                    print(matches)

        self.assertListEqual(list_files, [], 'Use PyQt connect in Python files, not UI : {}'.format(', '.join(list_files)))
