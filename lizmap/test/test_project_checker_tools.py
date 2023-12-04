import unittest

from qgis.core import QgsProject, QgsVectorLayer

from lizmap.project_checker_tools import trailing_layer_group_name
from lizmap.widgets.check_project import Error

__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


class TestProjectTable(unittest.TestCase):

    def test_trailing_spaces(self):
        """ Test about trailing spaces in the table. """
        layer = QgsVectorLayer('None?field=field_a:string', ' table', 'memory')
        project = QgsProject()
        project.addMapLayer(layer)

        results = trailing_layer_group_name(project.layerTreeRoot(), project, [])
        self.assertEqual(1, len(results))
        self.assertIsInstance(results[0], Error)
        self.assertEqual(' table', results[0].source)
