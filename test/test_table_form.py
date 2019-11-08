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


class TestTableForm(unittest.TestCase):

    def test_ui(self):
        """Test for the UI and save/restore from JSON."""

        ui_class, _ = uic.loadUiType(plugin_test_data_path('table_form.ui'))

        class TableFormDialog(QDialog, ui_class):
            def __init__(self, parent=None):
                super(TableFormDialog, self).__init__(parent)
                self.setupUi(self)

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
            'cols': ['layer', 'checkbox', 'combo'],
            'jsonConfig': {}
        }
        table_form = TableForm('test', json_config)
        table_form.set_connections()

        self.assertEqual(0, dialog.table_widget.rowCount())
        self.assertListEqual(table_form.to_dict(), list())
        self.assertFalse(dialog.form_group.isEnabled())

        table_form.add_button.click()

        self.assertEqual(1, dialog.table_widget.rowCount())
        self.assertTrue(dialog.form_group.isEnabled())
        expected = [{'checkbox': False, 'combo': '', 'layer': None}]
        self.assertListEqual(table_form.to_dict(), expected)

        dialog.check_box.setChecked(True)
        expected = [{'checkbox': True, 'combo': '', 'layer': None}]
        self.assertListEqual(table_form.to_dict(), expected)

        table_form.add_button.click()

        dialog.check_box.setChecked(False)
        expected = [
            {'checkbox': True, 'combo': '', 'layer': None},
            {'checkbox': False, 'combo': '', 'layer': None}
        ]
        self.assertListEqual(table_form.to_dict(), expected)

        layer = QgsVectorLayer(plugin_test_data_path('lines.geojson'), 'lines', 'ogr')
        QgsProject.instance().addMapLayer(layer)

        def assert_with_layer(result, expected_result):
            """Helper to check layer ID."""
            for r, e in zip(result, expected_result):
                for i in r.keys():
                    if i != 'layer':
                        self.assertEqual(r[i], e[i])
                    else:
                        if e[i] is None:
                            self.assertIsNone(r[i])
                        else:
                            self.assertIsInstance(r[i], str)
                            self.assertTrue(r[i].startswith(e[i]))

        expected = [
            {'checkbox': True, 'combo': '', 'layer': None},
            {'checkbox': False, 'combo': '', 'layer': 'lines'}
        ]
        assert_with_layer(table_form.to_dict(), expected)
