"""Test Lizmap dialog form edition."""

from qgis.core import (
    QgsVectorLayer,
    QgsProject,
)
from qgis.testing import unittest

from lizmap.qgis_plugin_tools.tools.resources import plugin_test_data_path
from lizmap.forms.atlas_edition import AtlasEditionDialog
from lizmap.forms.dataviz_edition import DatavizEditionDialog

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


class TestEditionDialog(unittest.TestCase):

    def setUp(self) -> None:
        self.layer = QgsVectorLayer(plugin_test_data_path('lines.geojson'), 'lines', 'ogr')
        QgsProject.instance().addMapLayer(self.layer)
        self.assertTrue(self.layer.isValid())

    def tearDown(self) -> None:
        del self.layer

    def test_load_save_collection_dataviz(self):
        """Test we can load collection."""
        dialog = DatavizEditionDialog()
        self.assertFalse(dialog.error.isVisible())
        self.assertEqual(dialog.validate(), 'The field "x field" is mandatory.')

        data = [
            {
                'color': '#db06b1',
                'colorfield': '',
                'y_field': 'distance',
                'z_field': '',
            }, {
                'color': '',
                'colorfield': 'id',
                'y_field': 'cat_name',
                'z_field': '',
            }
        ]
        self.assertEqual(0, dialog.traces.rowCount())
        dialog.load_collection(data)
        self.assertEqual(2, dialog.traces.rowCount())

        result = dialog.save_collection()
        self.assertCountEqual(result, data)

    def test_atlas_dialog(self):
        """Test atlas dialog."""
        dialog = AtlasEditionDialog()
        self.assertFalse(dialog.error.isVisible())

        self.assertEqual(dialog.validate(), 'The field "primary key" is mandatory.')
        dialog.primary_key.setCurrentIndex(1)
        self.assertEqual(dialog.validate(), 'The field "feature label" is mandatory.')
        dialog.feature_label.setCurrentIndex(1)
        self.assertEqual(dialog.validate(), 'The field "sort field" is mandatory.')
        dialog.sort_field.setCurrentIndex(1)
        self.assertIsNone(dialog.validate())

        data = dialog.save_form()
        self.assertEqual(len(data), len(dialog.config.layer_config.keys()))

        first_field = self.layer.fields().at(0).name()

        for key, value in data.items():

            if key == 'layer':
                self.assertEqual(value, self.layer.id())
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
        self.assertIsNone(dialog.validate())
