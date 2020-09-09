"""Test Lizmap dialog form edition."""

from qgis.core import QgsVectorLayer, QgsProject
from qgis.testing import unittest

from lizmap.qgis_plugin_tools.tools.resources import plugin_test_data_path
from lizmap.forms.atlas_edition import AtlasEditionDialog

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


class TestEditionDialog(unittest.TestCase):

    def test_atlas_dialog(self):
        """Test atlas dialog."""
        layer = QgsVectorLayer(plugin_test_data_path('lines.geojson'), 'lines', 'ogr')
        QgsProject.instance().addMapLayer(layer)
        self.assertTrue(layer.isValid())

        dialog = AtlasEditionDialog()
        self.assertFalse(dialog.error.isVisible())

        self.assertEqual(dialog.validate(), 'The field "primary key" is mandatory.')
        dialog.primary_key.setCurrentIndex(1)
        self.assertEqual(dialog.validate(), 'The field "feature label" is mandatory.')
        dialog.feature_label.setCurrentIndex(1)
        self.assertEqual(dialog.validate(), 'The field "sort field" is mandatory.')
        dialog.sort_field.setCurrentIndex(1)
        self.assertEqual(
            'The layers you have chosen for this tool must be checked in the "WFS Capabilities"\n option of the QGIS '
            'Server tab in the "Project Properties" dialog.',
            dialog.validate()
        )
        data = dialog.save_form()
        self.assertEqual(len(data), len(dialog.config.layer_config.keys()))

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
        self.assertEqual(dialog.validate(), 'The field "primary key" is mandatory.')

        dialog.load_form(data)

        self.assertEqual(
            'The layers you have chosen for this tool must be checked in the "WFS Capabilities"\n option of the QGIS '
            'Server tab in the "Project Properties" dialog.',
            dialog.validate()
        )
