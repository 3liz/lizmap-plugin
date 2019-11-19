"""Test Lizmap Table Form edition."""

from qgis.PyQt.QtWidgets import QDialog
from qgis.PyQt import uic
from qgis.core import QgsVectorLayer, QgsProject

from qgis.testing import unittest, start_app

from ..table_form import TableForm
from ..qgis_plugin_tools.tools.resources import plugin_test_data_path


start_app()

__copyright__ = 'Copyright 2019, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'

UI, _ = uic.loadUiType(plugin_test_data_path('table_form.ui'))


class TableFormDialog(QDialog, UI):
    def __init__(self, parent=None):
        super(TableFormDialog, self).__init__(parent)
        self.setupUi(self)


class TestTableForm(unittest.TestCase):

    def test_table_form_ui(self):
        """Test for the UI and save/restore from JSON."""
        layer = QgsVectorLayer(plugin_test_data_path('lines.geojson'), 'lines', 'ogr')
        QgsProject.instance().addMapLayer(layer)

        dialog = TableFormDialog()
        json_config = {
            'tableWidget': dialog.table_widget,
            'removeButton': dialog.button_remove,
            'addButton': dialog.button_add,
            'form': dialog.form_group,
            'fields': [
                dialog.combo_layer,
                dialog.check_box,
                dialog.combo_box,
            ],
            'cols': ['layerTest', 'checkbox', 'comboBox'],
            'useSingleRowIfPossible': True,
        }
        table_form = TableForm('test', json_config)
        table_form.set_connections()

        # We have 0 row for now.
        self.assertEqual(0, dialog.table_widget.rowCount())
        self.assertListEqual(table_form.to_dict(), list())
        self.assertFalse(dialog.form_group.isEnabled())
        self.assertListEqual(table_form.to_dict(), [])

        # Add the first row
        table_form.add_button.click()

        self.assertEqual(1, dialog.table_widget.rowCount())
        self.assertTrue(dialog.form_group.isEnabled())
        expected_1_layer = {
            'testEnabled': 'True', 'testCheckbox': 'False', 'testComboBox': '', 'testLayerTest': layer.id()}
        # noinspection PyTypeChecker
        self.assertDictEqual(table_form.to_dict(), expected_1_layer)

        dialog.check_box.setChecked(True)
        expected = {
            'testEnabled': 'True', 'testCheckbox': 'True', 'testComboBox': '', 'testLayerTest': layer.id()
        }
        # noinspection PyTypeChecker
        self.assertDictEqual(table_form.to_dict(), expected)

        # Second row
        table_form.add_button.click()
        self.assertEqual(2, dialog.table_widget.rowCount())
        dialog.check_box.setChecked(False)
        expected_2_layers = [
            {'checkbox': True, 'comboBox': '', 'layerTest': layer.id()},
            {'checkbox': False, 'comboBox': '', 'layerTest': layer.id()}
        ]
        self.assertListEqual(table_form.to_dict(), expected_2_layers)

        # Nothing is selected
        table_form.remove_button.click()
        self.assertEqual(2, dialog.table_widget.rowCount())

        table_form.table.selectRow(0)
        table_form.remove_button.click()
        # self.assertEqual(1, dialog.table_widget.rowCount())

        # noinspection PyTypeChecker
        # self.assertDictEqual(table_form.to_dict(), expected_1_layer)
