"""Test Lizmap dialog form edition."""

from qgis.core import QgsProject, QgsVectorLayer
from qgis.testing import unittest

from lizmap.forms.atlas_edition import AtlasEditionDialog
from lizmap.forms.attribute_table_edition import AttributeTableEditionDialog
from lizmap.forms.dataviz_edition import DatavizEditionDialog
from lizmap.forms.edition_edition import EditionLayerDialog
from lizmap.forms.filter_by_form_edition import FilterByFormEditionDialog
from lizmap.forms.filter_by_login import FilterByLoginEditionDialog
from lizmap.forms.filter_by_polygon import FilterByPolygonEditionDialog
from lizmap.forms.layout_edition import LayoutEditionDialog
from lizmap.forms.locate_layer_edition import LocateLayerEditionDialog
from lizmap.forms.time_manager_edition import TimeManagerEditionDialog
from lizmap.forms.tooltip_edition import ToolTipEditionDialog
from lizmap.qgis_plugin_tools.tools.resources import plugin_test_data_path
from lizmap.tools import qgis_version

__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

# Crashing in QGIS_VERSION_INT 3.16
# from qgis.testing import start_app
# start_app()


class TestEditionDialog(unittest.TestCase):

    def setUp(self) -> None:
        self.layer = QgsVectorLayer(plugin_test_data_path('lines.geojson'), 'lines', 'ogr')
        QgsProject.instance().addMapLayer(self.layer)
        self.assertTrue(self.layer.isValid())

    def tearDown(self) -> None:
        del self.layer

    def test_batch_loading_dialogs(self):
        """Open all dialogs to check that definitions are correct."""
        # It would be better to have a proper test for each dialog, checking form validation.
        dialogs = [
            AtlasEditionDialog,
            AttributeTableEditionDialog,
            DatavizEditionDialog,
            EditionLayerDialog,
            FilterByFormEditionDialog,
            FilterByLoginEditionDialog,
            FilterByPolygonEditionDialog,
            LayoutEditionDialog,
            LocateLayerEditionDialog,
            TimeManagerEditionDialog,
            ToolTipEditionDialog,
        ]
        for dialog in dialogs:
            d = dialog()
            self.assertFalse(d.error.isVisible())

    def test_load_save_collection_dataviz(self):
        """Test we can load collection."""
        dialog = DatavizEditionDialog()
        self.assertFalse(dialog.error.isVisible())
        if qgis_version() < 32200:
            self.assertEqual('', dialog.x_field.currentField())
            self.assertEqual(dialog.validate(), 'The field "x field" is mandatory.')
        else:
            self.assertEqual('id', dialog.x_field.currentField())

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

        if qgis_version() >= 32200:
            self.assertEqual(dialog.primary_key.currentField(), 'id')
        else:
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
        if qgis_version() < 32200:
            self.assertEqual(dialog.validate(), 'The field "primary key" is mandatory.')
        else:
            self.assertEqual(
                dialog.validate(),
                'The layers you have chosen for this tool must be checked in the "WFS Capabilities"\n option of the '
                'QGIS Server tab in the "Project Properties" dialog.'
            )

        dialog.load_form(data)

        self.assertEqual(
            'The layers you have chosen for this tool must be checked in the "WFS Capabilities"\n option of the QGIS '
            'Server tab in the "Project Properties" dialog.',
            dialog.validate()
        )

    def test_time_manager_dialog(self):
        """Test time manager dialog."""
        dialog = TimeManagerEditionDialog()
        self.assertFalse(dialog.error.isVisible())

        self.assertEqual('', dialog.edit_min_value.text())
        self.assertEqual('', dialog.edit_max_value.text())

        dialog.start_field.setCurrentIndex(1)  # Field "name"
        self.assertEqual(dialog.compute_value_min_max(True), '1 Name')
        self.assertEqual(dialog.compute_value_min_max(False), '2 Name')

        dialog.end_field.setCurrentIndex(1)  # Field "id"
        self.assertEqual(dialog.compute_value_min_max(True), '1 Name')
        self.assertEqual(dialog.compute_value_min_max(False), '2')
