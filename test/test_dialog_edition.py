"""Test Lizmap dialog form edition."""

from qgis.core import QgsVectorLayer, QgsProject, Qgis
from qgis.testing import unittest, start_app

start_app()

from ..qgis_plugin_tools.tools.resources import plugin_test_data_path
from ..forms.atlas_edition import AtlasEditionDialog


__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


class TestEditionDialog(unittest.TestCase):

    @unittest.skipIf(Qgis.QGIS_VERSION_INT >= 31000, 'Segfault')
    def test_atlas_dialog(self):
        """Test atlas dialog."""
        layer = QgsVectorLayer(plugin_test_data_path('lines.geojson'), 'lines', 'ogr')
        QgsProject.instance().addMapLayer(layer)
        self.assertTrue(layer.isValid())

        dialog = AtlasEditionDialog()
        self.assertFalse(dialog.error.isVisible())

        self.assertEqual(dialog.validate(), 'Primary key field is compulsory.')
        dialog.primary_key.setCurrentIndex(1)
        self.assertEqual(dialog.validate(), 'Label field is compulsory.')
        dialog.feature_label.setCurrentIndex(1)
        self.assertEqual(dialog.validate(), 'Sort field is compulsory.')
        dialog.sort_field.setCurrentIndex(1)
        self.assertIsNone(dialog.validate())

        data = dialog.save_form()
        self.assertEqual(len(data), len(dialog.config.layer_config.keys()))

        first_field = layer.fields().at(0).name()

        for key, value in data.items():

            if key == 'layer':
                self.assertEqual(value, layer.id())
            elif key in ['primaryKey', 'featureLabel', 'sortField']:
                pass
                # self.assertEqual(value, first_field)
            elif key in ['atlasDisplayLayerDescription']:
                self.assertTrue(value)
            elif key in ['highlightGeometry', 'displayPopup', 'triggerFilter']:
                self.assertFalse(value)
            elif key == 'duration':
                self.assertEqual(value, 5)

        del dialog
        dialog = AtlasEditionDialog()
        self.assertEqual(dialog.validate(), 'Primary key field is compulsory.')

        dialog.load_form(data)
        self.assertIsNone(dialog.validate())
