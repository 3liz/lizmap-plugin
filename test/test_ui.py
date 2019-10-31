"""Test Lizmap dialog UI."""

from qgis.utils import plugins
from qgis.core import QgsVectorLayer, QgsProject
from qgis.testing import unittest, start_app
from qgis.testing.mocked import get_iface


start_app()

__copyright__ = 'Copyright 2019, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


class TestUiLizmapDialog(unittest.TestCase):

    def test_ui(self):
        layer = QgsVectorLayer('data/lines.geojson', 'lines', 'ogr')
        QgsProject.instance().addMapLayer(layer)

        layer = QgsVectorLayer('data/points.geojson', 'points', 'ogr')
        QgsProject.instance().addMapLayer(layer)

        print(plugins)
        plugins['lizmap'].run()
