"""Test Lizmap dialog form edition.

__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
"""

from pathlib import Path

import pytest

from qgis.core import QgsProject, QgsVectorLayer

from lizmap.definitions.definitions import LwcVersions
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

from .compat import TestCase


@pytest.fixture(scope="class", autouse=True)
def layer(data: Path) -> None:
    layer = QgsVectorLayer(str(data.joinpath('lines.geojson')), 'lines', 'ogr')
    QgsProject.instance().addMapLayer(layer)
    assert layer.isValid()
    return layer


class TestEditionDialog(TestCase):

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
            assert not d.error.isVisible()

    def test_load_save_collection_dataviz(self):
        """Test we can load collection."""
        dialog = DatavizEditionDialog()
        assert not dialog.error.isVisible()
        assert 'id' == dialog.x_field.currentField()

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
        assert 0 == dialog.traces.rowCount()
        dialog.load_collection(data)
        assert 2 == dialog.traces.rowCount()

        result = dialog.save_collection()
        self.assertCountEqual(result, data)

    def test_atlas_dialog(self, layer: QgsVectorLayer):
        """Test atlas dialog."""
        dialog = AtlasEditionDialog()
        self.assertFalse(dialog.error.isVisible())

        self.assertEqual(dialog.primary_key.currentField(), 'id')

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
        dialog = TimeManagerEditionDialog(version=LwcVersions.latest())
        self.assertFalse(dialog.error.isVisible())

        self.assertEqual('', dialog.edit_min_value.text())
        self.assertEqual('', dialog.edit_max_value.text())

        dialog.start_field.setCurrentIndex(1)  # Field "name"
        self.assertEqual(dialog.compute_value_min_max(True), '1 Name')
        self.assertEqual(dialog.compute_value_min_max(False), '2 Name')

        dialog.end_field.setCurrentIndex(1)  # Field "id"
        self.assertEqual(dialog.compute_value_min_max(True), '1 Name')
        self.assertEqual(dialog.compute_value_min_max(False), '2')
