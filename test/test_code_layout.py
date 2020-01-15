"""Test code layout."""

import os
import re
import unittest

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


class TestCodeLayout(unittest.TestCase):

    def test_qgis_widgets(self):
        """Test imports are correct in UI file."""
        list_files = []
        for root, _, files in os.walk('../'):
            for file in files:
                if file.lower().endswith('.ui'):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r') as ui_file:
                        matches = re.findall(
                            r'<header>qgs[a-z]*\.h<\/header>',
                            ui_file.read(),
                            re.MULTILINE)
                        if len(matches):
                            list_files.append(file)
                            print(matches)

        self.assertEqual(
            len(list_files),
            0,
            'Some imports are wrong : {}'.format(', '.join(list_files))
        )
