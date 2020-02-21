"""Test table manager."""

import copy

from qgis.PyQt.QtWidgets import QTableWidget
from qgis.core import QgsVectorLayer, QgsProject, Qgis
from qgis.testing import unittest, start_app


start_app()

from ..definitions.atlas import AtlasDefinitions
from ..definitions.attribute_table import AttributeTableDefinitions
from ..definitions.edition import EditionDefinitions
from ..definitions.filter_by_form import FilterByFormDefinitions
from ..definitions.filter_by_login import FilterByLoginDefinitions
from ..definitions.locate_by_layer import LocateByLayerDefinitions
from ..definitions.tooltip import ToolTipDefinitions
from ..definitions.time_manager import TimeManagerDefinitions
from ..forms.table_manager import TableManager
from ..forms.atlas_edition import AtlasEditionDialog
from ..qgis_plugin_tools.tools.resources import plugin_test_data_path


__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


@unittest.skipIf(Qgis.QGIS_VERSION_INT >= 31000, 'Segfault')
class TestTableManager(unittest.TestCase):

    def setUp(self) -> None:
        self.maxDiff = None

    def test_form_filter(self):
        """Test table manager with filter by form."""
        layer = QgsVectorLayer(plugin_test_data_path('lines.geojson'), 'lines', 'ogr')
        QgsProject.instance().addMapLayer(layer)
        self.assertTrue(layer.isValid())

        table = QTableWidget()
        definitions = FilterByFormDefinitions()

        table_manager = TableManager(
            None, definitions, None, table, None, None, None, None)

        json = {
            '0': {
                'title': 'Line filtering',
                'type': 'text',
                'field': 'name',
                'min_date': '',
                'max_date': '',
                'format': 'checkboxes',
                'splitter': '',
                'provider': 'ogr',
                'layerId': layer.id(),
                'order': 0
            },
            '1': {
                'title': 'Line filtering',
                'type': 'numeric',
                'field': 'id',
                'min_date': '',
                'max_date': '',
                'format': 'checkboxes',
                'splitter': '',
                'provider': 'ogr',
                'layerId': layer.id(),
                'order': 1
            }
        }

        self.assertEqual(table_manager.table.rowCount(), 0)
        table_manager.from_json(json)
        self.assertEqual(table_manager.table.rowCount(), 2)
        data = table_manager.to_json()

        expected = {
            '0': {
                'layerId': layer.id(),
                'provider': 'ogr',  # Added automatically on the fly
                'title': 'Line filtering',
                'type': 'text',
                'field': 'name',
                'format': 'checkboxes',
                'order': 0
            },
            '1': {
                'layerId': layer.id(),
                'provider': 'ogr',  # Added automatically on the fly
                'title': 'Line filtering',
                'type': 'numeric',
                'field': 'id',
                'format': 'checkboxes',
                'order': 1
            }
        }
        self.assertDictEqual(data, expected)

    def test_filter_by_login(self):
        """Test table manager with filter by login."""
        layer = QgsVectorLayer(plugin_test_data_path('lines.geojson'), 'lines', 'ogr')
        QgsProject.instance().addMapLayer(layer)
        self.assertTrue(layer.isValid())

        table = QTableWidget()
        definitions = FilterByLoginDefinitions()

        table_manager = TableManager(
            None, definitions, None, table, None, None, None, None)

        json = {
            'lines': {
                'filterAttribute': 'name',
                'filterPrivate': 'False',
                'layerId': layer.id(),
                'order': 0
            }
        }
        self.assertEqual(table_manager.table.rowCount(), 0)
        table_manager.from_json(json)
        self.assertEqual(table_manager.table.rowCount(), 1)
        data = table_manager.to_json()

        expected = {
            'lines': {
                'filterAttribute': 'name',
                'filterPrivate': 'False',
                'layerId': layer.id(),
                'order': 0
            }
        }
        self.assertDictEqual(data, expected)

    def test_tool_tip(self):
        """Test table manager with tooltip layer."""
        layer = QgsVectorLayer(plugin_test_data_path('lines.geojson'), 'lines', 'ogr')

        QgsProject.instance().addMapLayer(layer)
        self.assertTrue(layer.isValid())

        table = QTableWidget()
        definitions = ToolTipDefinitions()

        table_manager = TableManager(
            None, definitions, None, table, None, None, None, None)

        json = {
            'lines': {
                'fields': 'id,name',
                'displayGeom': 'False',
                'colorGeom': '',
                'layerId': layer.id(),
                'order': 0
            }
        }
        self.assertEqual(table_manager.table.rowCount(), 0)
        table_manager.from_json(json)
        self.assertEqual(table_manager.table.rowCount(), 1)
        data = table_manager.to_json()
        json['lines'].pop('colorGeom')
        self.assertDictEqual(data, json)

    def test_attribute_table(self):
        """Test table manager with attribute table."""
        layer = QgsVectorLayer(plugin_test_data_path('lines.geojson'), 'lines', 'ogr')

        QgsProject.instance().addMapLayer(layer)
        self.assertTrue(layer.isValid())

        table = QTableWidget()
        definitions = AttributeTableDefinitions()

        table_manager = TableManager(
            None, definitions, None, table, None, None, None, None)

        json = {
            'lines': {
                'primaryKey': 'id',
                'hiddenFields': 'id,name',
                'pivot': 'False',
                'hideAsChild': 'False',
                'hideLayer': 'False',
                'layerId': layer.id(),
                'order': 0
            }
        }
        self.assertEqual(table_manager.table.rowCount(), 0)
        table_manager.from_json(json)
        self.assertEqual(table_manager.table.rowCount(), 1)
        data = table_manager.to_json()
        self.assertDictEqual(data, json)

    def test_time_manager_table(self):
        """Test table manager with time manager."""
        layer = QgsVectorLayer(plugin_test_data_path('lines.geojson'), 'lines', 'ogr')

        QgsProject.instance().addMapLayer(layer)
        self.assertTrue(layer.isValid())

        table = QTableWidget()
        definitions = TimeManagerDefinitions()

        table_manager = TableManager(
            None, definitions, None, table, None, None, None, None)

        json = {
            'lines': {
                'startAttribute': 'id',
                'label': 'name',
                'group': 'fake',
                'groupTitle': 'fake',
                'layerId': layer.id(),
                'order': 0
            }
        }
        self.assertEqual(table_manager.table.rowCount(), 0)
        table_manager.from_json(json)
        self.assertEqual(table_manager.table.rowCount(), 1)
        data = table_manager.to_json()
        self.assertDictEqual(data, json)

        table_manager.truncate()

        # Minimum fields
        json = {
            'lines': {
                'startAttribute': 'id',
                'layerId': layer.id(),
                'order': 0
            }
        }
        self.assertEqual(table_manager.table.rowCount(), 0)
        table_manager.from_json(json)
        self.assertEqual(table_manager.table.rowCount(), 1)
        data = table_manager.to_json()
        self.assertDictEqual(data, json)

    def test_edition_layer(self):
        """Test table manager with edition layer."""
        layer = QgsVectorLayer(plugin_test_data_path('lines.geojson'), 'lines', 'ogr')
        QgsProject.instance().addMapLayer(layer)
        self.assertTrue(layer.isValid())

        table = QTableWidget()
        definitions = EditionDefinitions()

        table_manager = TableManager(
            None, definitions, None, table, None, None, None, None)

        json = {
            'lines': {
                'layerId': layer.id(),
                'geometryType': 'line',
                'capabilities': {
                    'createFeature': 'True',
                    'modifyAttribute': 'True',
                    'modifyGeometry': 'True',
                    'deleteFeature': 'True'
                },
                'acl': 'edition_group',
                'order': 0
            }
        }
        json_legacy = table_manager._from_json_legacy_order(copy.deepcopy(json))
        json_legacy = table_manager._from_json_legacy_capabilities(json_legacy)
        expected = {
            'layers': [
                {
                    'layerId': layer.id(),
                    'createFeature': 'True',
                    'modifyAttribute': 'True',
                    'modifyGeometry': 'True',
                    'deleteFeature': 'True',
                    'acl': 'edition_group',
                    'order': 0
                },
            ]
        }
        self.assertDictEqual(json_legacy, expected)

        self.assertEqual(table_manager.table.rowCount(), 0)
        table_manager.from_json(copy.deepcopy(json))
        self.assertEqual(table_manager.table.rowCount(), 1)
        data = table_manager.to_json()
        self.assertDictEqual(data, json)

    def test_locate_by_layer(self):
        """Test table manager with locate by layer."""
        layer = QgsVectorLayer(plugin_test_data_path('lines.geojson'), 'lines', 'ogr')
        layer_2 = QgsVectorLayer(plugin_test_data_path('lines.geojson'), 'lines_2', 'ogr')

        QgsProject.instance().addMapLayer(layer)
        QgsProject.instance().addMapLayer(layer_2)
        self.assertTrue(layer.isValid())
        self.assertTrue(layer_2.isValid())

        table = QTableWidget()
        definitions = LocateByLayerDefinitions()

        table_manager = TableManager(
            None, definitions, None, table, None, None, None, None)

        json = {
            'lines': {
                'fieldName': 'name',
                'filterFieldName': 'id',
                'displayGeom': 'True',
                'minLength': 0,
                'filterOnLocate': 'False',
                'layerId': layer.id(),
                'order': 1
            },
            'lines_2': {
                'fieldName': 'name',
                # 'filterFieldName': 'id', DISABLED on purpose. This field is not mandatory.
                'displayGeom': 'False',
                'minLength': 0,
                'filterOnLocate': 'True',
                'layerId': layer_2.id(),
                'order': 0
            }
        }

        # noinspection PyProtectedMember
        data = table_manager._from_json_legacy_order(json)
        expected = {
            'layers': [
                {
                    'fieldName': 'name',
                    # 'filterFieldName': '', DISABLED
                    'displayGeom': 'False',
                    'minLength': 0,
                    'filterOnLocate': 'True',
                    'layerId': layer_2.id(),
                    'order': 0
                },
                {
                    'fieldName': 'name',
                    'filterFieldName': 'id',
                    'displayGeom': 'True',
                    'minLength': 0,
                    'filterOnLocate': 'False',
                    'layerId': layer.id(),
                    'order': 1
                },
            ]
        }
        self.assertDictEqual(data, expected)

        self.assertEqual(table_manager.table.rowCount(), 0)
        table_manager.from_json(json)
        self.assertEqual(table_manager.table.rowCount(), 2)
        data = table_manager.to_json()

        expected = {
            'lines_2': {
                'fieldName': 'name',
                'displayGeom': 'False',
                'minLength': 0,
                'filterOnLocate': 'True',
                'layerId': layer_2.id(),
                'order': 0
            },
            'lines': {
                'fieldName': 'name',
                'filterFieldName': 'id',
                'displayGeom': 'True',
                'minLength': 0,
                'filterOnLocate': 'False',
                'layerId': layer.id(),
                'order': 1
            },
        }
        self.assertDictEqual(data, expected)

    def test_fake_layer_id_table_manager(self):
        """Test we can skip a wrong layer id."""
        table = QTableWidget()
        definitions = AtlasDefinitions()

        table_manager = TableManager(
            None, definitions, AtlasEditionDialog, table, None, None, None, None)

        self.assertEqual(table.columnCount(), len(definitions.layer_config.keys()))

        # JSON from LWC 3.4 and above
        layer_1 = {
            "layer": "ID_WHICH_DOES_NOT_EXIST",
            "primaryKey": "id",
            "displayLayerDescription": "False",
            "featureLabel": "name",
            "sortField": "name",
            "highlightGeometry": "True",
            "zoom": "center",
            "duration": 5,
            "displayPopup": "True",
            "triggerFilter": "True"
        }
        json = {
            'layers': [
                layer_1
            ]
        }
        self.assertEqual(table_manager.table.rowCount(), 0)
        table_manager.from_json(json)
        self.assertEqual(table_manager.table.rowCount(), 0)

    def test_table_manager(self):
        """Test about the table manager.

        Add new row
        Edit existing new row
        are not tested
        """
        layer = QgsVectorLayer(plugin_test_data_path('lines.geojson'), 'lines', 'ogr')
        field = 'id'
        QgsProject.instance().addMapLayer(layer)
        self.assertTrue(layer.isValid())

        table = QTableWidget()
        definitions = AtlasDefinitions()
        definitions._use_single_row = False

        table_manager = TableManager(
            None, definitions, AtlasEditionDialog, table, None, None, None, None)

        self.assertEqual(table.columnCount(), len(definitions.layer_config.keys()))

        # JSON from LWC 3.4 and above
        layer_1 = {
            'layer': layer.id(),
            'primaryKey': field,
            'displayLayerDescription': 'False',
            'featureLabel': 'name',
            'sortField': 'name',
            'highlightGeometry': 'True',
            'zoom': 'center',
            'duration': 5,
            'displayPopup': 'True',
            'triggerFilter': 'True'
        }
        json = {
            'layers': [
                layer_1
            ]
        }
        self.assertEqual(table_manager.table.rowCount(), 0)
        table_manager.from_json(json)
        self.assertEqual(table_manager.table.rowCount(), 1)
        data = table_manager.to_json()
        self.assertDictEqual(data, json)

        # QGIS notify layer has been deleted
        table_manager.layers_has_been_deleted(['another_layer_ID_in_canvas'])
        self.assertEqual(table_manager.table.rowCount(), 1)
        table_manager.layers_has_been_deleted([layer.id()])
        self.assertEqual(table_manager.table.rowCount(), 0)

        data = table_manager.to_json()
        self.assertDictEqual(data, {'layers': []})

        # We add 2 layers
        layer_2 = dict(layer_1)
        layer_2['sortField'] = 'id'
        self.assertNotEqual(layer_1['sortField'], layer_2['sortField'])
        json = {
            'layers': [
                layer_1,
                layer_2,
            ]
        }
        table_manager.from_json(json)
        self.assertEqual(table_manager.table.rowCount(), 2)

        # noinspection PyProtectedMember
        self.assertDictEqual(
            table_manager._primary_keys(),
            {'layer': [layer.id(), layer.id()]}
        )

        data = table_manager.to_json()
        self.assertDictEqual(data, {'layers': [layer_1, layer_2]})

        # We select second row and we move up
        table.setCurrentCell(1, 0)
        table_manager.move_layer_up()

        # Export and check order
        data = table_manager.to_json()
        self.assertDictEqual(data, {'layers': [layer_2, layer_1]})

        # We select first row and we move up
        table.setCurrentCell(0, 0)
        table_manager.move_layer_up()
        # Nothing happen, we are on top
        data = table_manager.to_json()
        self.assertDictEqual(data, {'layers': [layer_2, layer_1]})

        table_manager.move_layer_down()
        data = table_manager.to_json()
        self.assertDictEqual(data, {'layers': [layer_1, layer_2]})

        # We select first row and we remove it
        table.setCurrentCell(0, 0)
        table_manager.remove_selection()
        data = table_manager.to_json()
        self.assertDictEqual(data, {'layers': [layer_2]})

        table_manager.truncate()
        self.assertEqual(table_manager.table.rowCount(), 0)

        # We select first row and we edit it
        # table.selectRow(0)
        # self.assertEqual(table_manager.edit_existing_row(), QDialog.Accepted)

    def test_atlas_missing_json_parameter(self):
        """Test if we can load CFG file with missing parameter."""
        layer = QgsVectorLayer(plugin_test_data_path('lines.geojson'), 'lines', 'ogr')
        QgsProject.instance().addMapLayer(layer)

        table = QTableWidget()

        definitions = AtlasDefinitions()
        definitions._use_single_row = False
        table_manager = TableManager(
            None, definitions, AtlasEditionDialog, table, None, None, None, None)

        json = {
            'layers': [
                {
                    'layer': layer.id(),
                    'primaryKey': 'id',
                    'displayLayerDescription': 'False',
                    'featureLabel': 'name',
                    'sortField': 'name',
                    'highlightGeometry': 'True',
                    'zoom': 'center',
                    'duration': 5,
                    'displayPopup': 'True',
                    'triggerFilter': 'True'
                }
            ]
        }

        self.assertEqual(table_manager.table.rowCount(), 0)
        table_manager.from_json(json)
        self.assertEqual(table_manager.table.rowCount(), 1)
        table_manager.truncate()
        new_json = copy.deepcopy(json)
        del new_json['layers'][0]['layer']
        table_manager.from_json(new_json)
        # Layer is mandatory
        self.assertEqual(table_manager.table.rowCount(), 0)

        new_json = copy.deepcopy(json)
        # Trigger filter will take the default value from definitions
        del new_json['layers'][0]['triggerFilter']
        table_manager.from_json(new_json)
        self.assertEqual(table_manager.table.rowCount(), 1)
        table_manager.truncate()

    def test_table_manager_3_3(self):
        """Test we can read/write to LWC 3.3 format."""
        layer = QgsVectorLayer(plugin_test_data_path('lines.geojson'), 'lines', 'ogr')
        field = 'id'
        QgsProject.instance().addMapLayer(layer)
        self.assertTrue(layer.isValid())

        table = QTableWidget()
        definitions = AtlasDefinitions()
        definitions._use_single_row = False

        json = {
            'atlasEnabled': 'True',  # Will not be used
            'atlasLayer': layer.id(),
            'atlasPrimaryKey': field,
            'atlasDisplayLayerDescription': 'True',
            'atlasFeatureLabel': 'inf3_o_t',
            'atlasSortField': 'inf3_o_t',
            'atlasZoom': 'zoom',
            'atlasShowAtStartup': 'True',  # will not be used
            'atlasMaxWidth': 25,  # will not be used
            'atlasDuration': 5
        }

        table_manager = TableManager(
            None, definitions, AtlasEditionDialog, table, None, None, None, None)

        self.assertEqual(table_manager.table.rowCount(), 0)
        table_manager.from_json(json)
        self.assertEqual(table_manager.table.rowCount(), 1)

        data = table_manager.to_json()
        expected = {
            'layers': [
                {
                    'layer': layer.id(),
                    'primaryKey': field,
                    'displayLayerDescription': 'True',
                    'featureLabel': 'inf3_o_t',
                    'sortField': 'inf3_o_t',
                    'zoom': 'zoom',
                    'duration': 5,
                    'displayPopup': 'False',  # auto added by the tool
                    'highlightGeometry': 'False',  # auto added by the tool
                    'triggerFilter': 'False',  # auto added by the tool
                }
            ]
        }
        self.assertDictEqual(data, expected)

        definitions._use_single_row = True
        data = table_manager.to_json()

        expected = {
            'atlasEnabled': 'True',  # Hard coded for Lizmap 3.3
            'atlasMaxWidth': 25,  # will not be used
            'atlasLayer': layer.id(),
            'atlasPrimaryKey': 'id',
            'atlasDisplayLayerDescription': 'True',
            'atlasFeatureLabel': 'inf3_o_t',
            'atlasSortField': 'inf3_o_t',
            'atlasHighlightGeometry': 'False',
            'atlasZoom': 'zoom',
            'atlasDisplayPopup': 'False',
            'atlasTriggerFilter': 'False',
            'atlasDuration': 5
        }
        self.assertDictEqual(data, expected)
