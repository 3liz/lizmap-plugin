"""Test table manager."""

import copy

from qgis.core import QgsProject, QgsVectorLayer
from qgis.PyQt.QtWidgets import QTableWidget
from qgis.testing import unittest

from lizmap.definitions.atlas import AtlasDefinitions
from lizmap.definitions.attribute_table import AttributeTableDefinitions
from lizmap.definitions.dataviz import DatavizDefinitions
from lizmap.definitions.definitions import LwcVersions
from lizmap.definitions.edition import EditionDefinitions
from lizmap.definitions.filter_by_form import FilterByFormDefinitions
from lizmap.definitions.filter_by_login import FilterByLoginDefinitions
from lizmap.definitions.filter_by_polygon import FilterByPolygonDefinitions
from lizmap.definitions.locate_by_layer import LocateByLayerDefinitions
from lizmap.definitions.time_manager import TimeManagerDefinitions
from lizmap.definitions.tooltip import ToolTipDefinitions
from lizmap.forms.atlas_edition import AtlasEditionDialog
from lizmap.forms.table_manager import TableManager
from lizmap.qgis_plugin_tools.tools.resources import plugin_test_data_path

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


class TestTableManager(unittest.TestCase):

    def setUp(self) -> None:
        self.maxDiff = None
        self.layer = QgsVectorLayer(plugin_test_data_path('lines.geojson'), 'lines', 'ogr')
        QgsProject.instance().addMapLayer(self.layer)
        self.assertTrue(self.layer.isValid())

    def tearDown(self) -> None:
        QgsProject.instance().removeMapLayer(self.layer)
        del self.layer

    def test_form_filter(self):
        """Test table manager with filter by form."""
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
                'layerId': self.layer.id(),
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
                'layerId': self.layer.id(),
                'order': 1
            }
        }

        self.assertEqual(table_manager.table.rowCount(), 0)
        table_manager.from_json(json)
        self.assertEqual(table_manager.table.rowCount(), 2)
        data = table_manager.to_json()

        expected = {
            '0': {
                'layerId': self.layer.id(),
                'provider': 'ogr',  # Added automatically on the fly
                'title': 'Line filtering',
                'type': 'text',
                'field': 'name',
                'format': 'checkboxes',
                'order': 0
            },
            '1': {
                'layerId': self.layer.id(),
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
        table = QTableWidget()
        definitions = FilterByLoginDefinitions()

        table_manager = TableManager(
            None, definitions, None, table, None, None, None, None)

        json = {
            'lines': {
                'filterAttribute': 'name',
                'filterPrivate': 'False',
                'layerId': self.layer.id(),
                'order': 0
            }
        }
        self.assertEqual(table_manager.table.rowCount(), 0)
        table_manager.from_json(json)
        self.assertEqual(table_manager.table.rowCount(), 1)
        data = table_manager.to_json()

        expected = {
            'lines': {
                'edition_only': 'False',
                'filterAttribute': 'name',
                'filterPrivate': 'False',
                'layerId': self.layer.id(),
                'order': 0
            }
        }
        self.assertDictEqual(data, expected)

    def test_dataviz_definitions(self):
        """Test dataviz collections keys."""
        table_manager = TableManager(
            None, DatavizDefinitions(), None, QTableWidget(), None, None, None, None)
        expected = [
            'type', 'title', 'description', 'layerId', 'x_field', 'aggregation',
            'traces', 'html_template', 'layout', 'popup_display_child_plot', 'stacked',
            'horizontal', 'only_show_child', 'display_legend', 'display_when_layer_visible',
        ]
        self.assertListEqual(expected, table_manager.keys)

    def test_remove_extra_field_dataviz(self):
        """Test we can remove an empty field from a trace."""
        table = QTableWidget()
        definitions = DatavizDefinitions()

        table_manager = TableManager(
            None, definitions, None, table, None, None, None, None)

        # Lizmap 3.3
        json = {
            '0': {
                'title': 'My graph',
                'type': 'scatter',
                'x_field': 'id',
                'aggregation': '',
                'y_field': 'name',
                'color': '#00aaff',
                'colorfield': '',
                'has_y2_field': 'True',
                # 'y2_field': 'name', Not this one in the test
                'color2': '#ffaa00',  # Even if we have this line and the next one
                'colorfield2': '',
                'popup_display_child_plot': 'False',
                'only_show_child': 'True',
                'layerId': self.layer.id(),
                'order': 0
            }
        }
        data = table_manager._from_json_legacy_order(copy.deepcopy(json))
        data = table_manager._from_json_legacy_dataviz(data)
        expected = {
            'layers': [
                {
                    'title': 'My graph',
                    'type': 'scatter',
                    'x_field': 'id',
                    'aggregation': '',
                    'popup_display_child_plot': 'False',
                    'only_show_child': 'True',
                    'layerId': self.layer.id(),
                    'order': 0,
                    'traces': [
                        {
                            'y_field': 'name',
                            'color': '#00aaff',
                            'colorfield': '',
                        }
                    ]
                }
            ]
        }
        self.assertDictEqual(expected, data)

    def test_dataviz_legacy_3_3_with_1_trace(self):
        """Test table manager with dataviz format 3.3 with only 1 trace"""
        table = QTableWidget()
        definitions = DatavizDefinitions()

        table_manager = TableManager(
            None, definitions, None, table, None, None, None, None)

        # Lizmap 3.3
        json = {
            '0': {
                'title': 'My graph',
                'type': 'scatter',
                'x_field': 'id',
                'aggregation': '',
                'y_field': 'name',
                'color': '#00aaff',
                'colorfield': '',
                'has_y2_field': 'True',  # Wrong but let's trt
                'y2_field': '',  # Empty
                'color2': '#ffaa00',
                'colorfield2': '',
                'popup_display_child_plot': 'False',
                'only_show_child': 'True',
                'layerId': self.layer.id(),
                'order': 0
            }
        }
        data = table_manager._from_json_legacy_order(copy.deepcopy(json))
        expected = {
            'layers': [
                {
                    'title': 'My graph',
                    'type': 'scatter',
                    'x_field': 'id',
                    'aggregation': '',
                    'y_field': 'name',
                    'color': '#00aaff',
                    'colorfield': '',
                    'has_y2_field': 'True',
                    'y2_field': '',
                    'color2': '#ffaa00',
                    'colorfield2': '',
                    'popup_display_child_plot': 'False',
                    'only_show_child': 'True',
                    'layerId': self.layer.id(),
                    'order': 0
                }
            ]
        }
        self.assertDictEqual(expected, data)

        data = table_manager._from_json_legacy_dataviz(data)
        expected = {
            'layers': [
                {
                    'title': 'My graph',
                    'type': 'scatter',
                    'x_field': 'id',
                    'aggregation': '',
                    'popup_display_child_plot': 'False',
                    'only_show_child': 'True',
                    'layerId': self.layer.id(),
                    'order': 0,
                    'traces': [
                        {
                            'y_field': 'name',
                            'color': '#00aaff',
                            'colorfield': '',
                        }
                    ]
                }
            ]
        }
        self.assertDictEqual(expected, data)

        self.assertEqual(table_manager.table.rowCount(), 0)
        table_manager.from_json(json)
        self.assertEqual(table_manager.table.rowCount(), 1)

        # To Lizmap 3.4
        data = table_manager.to_json(version=LwcVersions.Lizmap_3_4)
        expected = {
            '0': {
                'title': 'My graph',
                'type': 'scatter',
                'x_field': 'id',
                'aggregation': 'sum',
                'display_legend': 'True',
                'traces': [
                    {
                        'y_field': 'name',
                        'color': '#00aaff',
                        'colorfield': '',
                    }, {
                        'y_field': 'name',
                        'color': '#ffaa00',
                        'colorfield': '',
                    }
                ],
                'stacked': 'False',
                'horizontal': 'False',
                'popup_display_child_plot': 'False',
                'only_show_child': 'True',
                'display_when_layer_visible': 'False',
                'layerId': self.layer.id(),
                'order': 0
            }
        }
        expected_traces = expected['0'].pop('traces')
        data_traces = data['0'].pop('traces')
        self.assertDictEqual(data, expected)
        for exp, got in zip(expected_traces, data_traces):
            self.assertDictEqual(exp, got)

        # To Lizmap 3.3
        data = table_manager.to_json(version=LwcVersions.Lizmap_3_3)
        expected = {
            '0': {
                'title': 'My graph',
                'type': 'scatter',
                'x_field': 'id',
                'aggregation': 'sum',
                'display_legend': 'True',
                'y_field': 'name',
                'color': '#00aaff',
                'colorfield': '',
                # 'y2_field': 'name',
                # 'color2': '#ffaa00',
                # 'colorfield2': '',
                'stacked': 'False',
                'horizontal': 'False',
                'popup_display_child_plot': 'False',
                'only_show_child': 'True',
                'display_when_layer_visible': 'False',
                'layerId': self.layer.id(),
                'order': 0
            }
        }
        self.assertDictEqual(data, expected)

    def test_dataviz_legacy_3_3_with_2_traces(self):
        """Test table manager with dataviz format 3.3."""
        table = QTableWidget()
        definitions = DatavizDefinitions()

        table_manager = TableManager(
            None, definitions, None, table, None, None, None, None)

        # Lizmap 3.3
        json = {
            '0': {
                'title': 'My graph',
                'type': 'scatter',
                'x_field': 'id',
                'aggregation': '',
                'y_field': 'name',
                'color': '#00aaff',
                'colorfield': '',
                'has_y2_field': 'True',
                'y2_field': 'name',
                'color2': '#ffaa00',
                'colorfield2': '',
                'popup_display_child_plot': 'False',
                'only_show_child': 'True',
                'layerId': self.layer.id(),
                'order': 0
            }
        }
        data = table_manager._from_json_legacy_order(copy.deepcopy(json))
        expected = {
            'layers': [
                {
                    'title': 'My graph',
                    'type': 'scatter',
                    'x_field': 'id',
                    'aggregation': '',
                    'y_field': 'name',
                    'color': '#00aaff',
                    'colorfield': '',
                    'has_y2_field': 'True',
                    'y2_field': 'name',
                    'color2': '#ffaa00',
                    'colorfield2': '',
                    'popup_display_child_plot': 'False',
                    'only_show_child': 'True',
                    'layerId': self.layer.id(),
                    'order': 0
                }
            ]
        }
        self.assertDictEqual(expected, data)

        data = table_manager._from_json_legacy_dataviz(data)
        expected = {
            'layers': [
                {
                    'title': 'My graph',
                    'type': 'scatter',
                    'x_field': 'id',
                    'aggregation': '',
                    'popup_display_child_plot': 'False',
                    'only_show_child': 'True',
                    'layerId': self.layer.id(),
                    'order': 0,
                    'traces': [
                        {
                            'y_field': 'name',
                            'color': '#00aaff',
                            'colorfield': '',
                        }, {
                            'y_field': 'name',
                            'color': '#ffaa00',
                            'colorfield': '',
                        }
                    ]
                }
            ]
        }
        self.assertDictEqual(expected, data)

        self.assertEqual(table_manager.table.rowCount(), 0)
        table_manager.from_json(json)
        self.assertEqual(table_manager.table.rowCount(), 1)

        # To Lizmap 3.4
        data = table_manager.to_json(version=LwcVersions.Lizmap_3_4)
        expected = {
            '0': {
                'title': 'My graph',
                'type': 'scatter',
                'x_field': 'id',
                'aggregation': 'sum',
                'display_legend': 'True',
                'traces': [
                    {
                        'y_field': 'name',
                        'color': '#00aaff',
                        'colorfield': '',
                    }, {
                        'y_field': 'name',
                        'color': '#ffaa00',
                        'colorfield': '',
                    }
                ],
                'stacked': 'False',
                'horizontal': 'False',
                'popup_display_child_plot': 'False',
                'only_show_child': 'True',
                'display_when_layer_visible': 'False',
                'layerId': self.layer.id(),
                'order': 0
            }
        }
        expected_traces = expected['0'].pop('traces')
        data_traces = data['0'].pop('traces')
        self.assertDictEqual(data, expected)
        for exp, got in zip(expected_traces, data_traces):
            self.assertDictEqual(exp, got)

        # To Lizmap 3.3
        data = table_manager.to_json(version=LwcVersions.Lizmap_3_3)
        expected = {
            '0': {
                'title': 'My graph',
                'type': 'scatter',
                'x_field': 'id',
                'aggregation': 'sum',
                'display_legend': 'True',
                'y_field': 'name',
                'color': '#00aaff',
                'colorfield': '',
                'y2_field': 'name',
                'color2': '#ffaa00',
                'colorfield2': '',
                'stacked': 'False',
                'horizontal': 'False',
                'popup_display_child_plot': 'False',
                'only_show_child': 'True',
                'display_when_layer_visible': 'False',
                'layerId': self.layer.id(),
                'order': 0
            }
        }
        self.assertDictEqual(data, expected)

    def test_dataviz_box(self):
        """Box chart has an empty key."""
        layer = QgsVectorLayer(plugin_test_data_path('lines.geojson'), 'lines', 'ogr')
        QgsProject.instance().addMapLayer(layer)
        self.assertTrue(layer.isValid())

        table = QTableWidget()
        definitions = DatavizDefinitions()

        table_manager = TableManager(
            None, definitions, None, table, None, None, None, None)

        json = {
            '0': {
                'title': 'My graph',
                'type': 'box',
                'x_field': 'id',
                'aggregation': '',
                'y_field': 'name',
                'color': '#00aaff',
                'colorfield': '',
                'has_y2_field': 'True',
                'y2_field': 'name',
                'color2': '#ffaa00',
                'colorfield2': '',
                'popup_display_child_plot': 'False',
                'only_show_child': 'True',
                'layerId': layer.id(),
                'order': 0
            }
        }

        self.assertEqual(table_manager.table.rowCount(), 0)
        table_manager.from_json(json)
        self.assertEqual(table_manager.table.rowCount(), 1)
        data = table_manager.to_json()

        expected = {
            '0': {
                'title': 'My graph',
                'type': 'box',
                'x_field': 'id',
                'aggregation': '',  # It must stay empty
                'traces': [
                    {
                        'color': '#00aaff',
                        'colorfield': '',
                        'y_field': 'name'
                    }, {
                        'color': '#ffaa00',
                        'colorfield': '',
                        'y_field': 'name'
                    }
                ],
                'display_legend': 'True',
                'display_when_layer_visible': 'False',
                'horizontal': 'False',
                'popup_display_child_plot': 'False',
                'stacked': 'False',
                'only_show_child': 'True',
                'layerId': layer.id(),
                'order': 0
            }
        }
        self.assertDictEqual(data, expected)

    def test_dataviz(self):
        """Test we can read dataviz 3.4 format."""
        table_manager = TableManager(
            None, DatavizDefinitions(), None, QTableWidget(), None, None, None, None)

        json = {
            '0': {
                'title': 'My graph',
                'type': 'scatter',
                'x_field': 'id',
                'aggregation': '',
                'layout': {'1': '2'},
                'traces': [
                    {
                        'y_field': 'name',
                        'color': '#00aaff',
                        'colorfield': '',
                    }  # Single trace
                ],
                'popup_display_child_plot': 'False',
                'only_show_child': 'True',
                'layerId': self.layer.id(),
                'order': 0
            }
        }

        json_legacy = table_manager._from_json_legacy_order(copy.deepcopy(json))
        expected = {
            'layers': [
                {
                    'title': 'My graph',
                    'type': 'scatter',
                    'x_field': 'id',
                    'aggregation': '',
                    'layout': {'1': '2'},
                    'traces': [
                        {
                            'y_field': 'name',
                            'color': '#00aaff',
                            'colorfield': '',
                        },
                    ],
                    'popup_display_child_plot': 'False',
                    'only_show_child': 'True',
                    'layerId': self.layer.id(),
                    'order': 0
                }
            ]
        }
        self.assertDictEqual(expected, json_legacy)

        json_legacy = table_manager._from_json_legacy_dataviz(json_legacy)
        expected = {
            'layers': [
                {
                    'title': 'My graph',
                    'type': 'scatter',
                    'x_field': 'id',
                    'aggregation': '',
                    'layout': {'1': '2'},
                    'traces': [
                        {
                            'y_field': 'name',
                            'color': '#00aaff',
                            'colorfield': ''
                        }, {
                            'y_field': 'name',
                            'color': '#00aaff',
                            'colorfield': ''
                        }
                    ],
                    'popup_display_child_plot': 'False',
                    'only_show_child': 'True',
                    'layerId': self.layer.id(),
                    'order': 0
                }
            ]
        }
        self.assertCountEqual(expected, json_legacy)

        self.assertEqual(table_manager.table.rowCount(), 0)
        table_manager.from_json(json)
        # self.assertEqual(table_manager.table.rowCount(), 1)

    def test_filter_by_polygon(self):
        """ Test table manager with filter by polygon. """
        table_manager = TableManager(
            None, FilterByPolygonDefinitions(), None, QTableWidget(), None, None, None, None)

        json = {
            'config': {
                'polygon_layer_id': self.layer.id(),
                'group_field': 'id',
            },
            'layers': [
                {
                    "layer": self.layer.id(),
                    "primary_key": "id",
                    "spatial_relationship": "intersects",
                    "filter_mode": "display_and_editing"
                }
            ]
        }
        self.assertEqual(table_manager.table.rowCount(), 0)
        table_manager.from_json(json)
        self.assertEqual(table_manager.table.rowCount(), 1)

        output = table_manager.to_json()
        # Global widget are not defined in this test
        json['config'] = {}
        self.assertEqual(output, json)

    def test_tool_tip(self):
        """Test table manager with tooltip layer."""
        table = QTableWidget()
        definitions = ToolTipDefinitions()

        table_manager = TableManager(
            None, definitions, None, table, None, None, None, None)

        json = {
            'lines': {
                'fields': 'id,name',
                'displayGeom': 'False',
                'colorGeom': '',
                'layerId': self.layer.id(),
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
                'layerId': self.layer.id(),
                'order': 0
            }
        }
        self.assertEqual(table_manager.table.rowCount(), 0)
        table_manager.from_json(json)
        self.assertEqual(table_manager.table.rowCount(), 1)
        data = table_manager.to_json()

        # Automatically added, so we add it manually for the comparaison
        json['lines']['custom_config'] = 'False'

        self.assertDictEqual(data, json)

    def test_time_manager_table(self):
        """Test table manager with time manager."""
        table = QTableWidget()
        definitions = TimeManagerDefinitions()

        table_manager = TableManager(
            None, definitions, None, table, None, None, None, None)

        # JSON from 3.3 with all fields
        json = {
            'lines': {
                'startAttribute': 'id',
                'label': 'name',
                'group': 'fake',
                'groupTitle': 'fake',
                'layerId': self.layer.id(),
                'order': 0
            }
        }
        self.assertEqual(table_manager.table.rowCount(), 0)
        table_manager.from_json(json)
        self.assertEqual(table_manager.table.rowCount(), 1)
        data = table_manager.to_json()
        expected = {
            'lines': {
                'startAttribute': 'id',
                'attributeResolution': 'years',  # missing from the input, default value in definitions
                'layerId': self.layer.id(),
                'order': 0
            }
        }
        self.assertDictEqual(data, expected)

        table_manager.truncate()

        # Minimum fields from 3.3
        json = {
            'lines': {
                'startAttribute': 'id',
                'layerId': self.layer.id(),
                'order': 0
            }
        }
        self.assertEqual(table_manager.table.rowCount(), 0)
        table_manager.from_json(json)
        self.assertEqual(table_manager.table.rowCount(), 1)
        data = table_manager.to_json()
        self.assertDictEqual(data, expected)

        table_manager.truncate()

        # JSON from 3.4
        json = {
            'lines': {
                'startAttribute': 'id',
                'endAttribute': 'id',
                'attributeResolution': 'minutes',
                'layerId': self.layer.id(),
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
        table = QTableWidget()
        definitions = EditionDefinitions()

        table_manager = TableManager(
            None, definitions, None, table, None, None, None, None)

        json = {
            'lines': {
                'layerId': self.layer.id(),
                'geometryType': 'line',
                'capabilities': {
                    'createFeature': 'True',
                    'allow_without_geom': 'False',
                    'modifyAttribute': 'True',
                    'modifyGeometry': 'True',
                    'deleteFeature': 'True'
                },
                'acl': 'edition_group',
                'snap_layers': [self.layer.id()],
                'snap_segments': 'False',
                'snap_intersections': 'True',
                'order': 0
            }
        }
        json_legacy = table_manager._from_json_legacy_order(copy.deepcopy(json))
        json_legacy = table_manager._from_json_legacy_capabilities(json_legacy)
        expected = {
            'layers': [
                {
                    'layerId': self.layer.id(),
                    'createFeature': 'True',
                    'allow_without_geom': 'False',
                    'modifyAttribute': 'True',
                    'modifyGeometry': 'True',
                    'deleteFeature': 'True',
                    'acl': 'edition_group',
                    'snap_layers': [self.layer.id()],
                    'snap_segments': 'False',
                    'snap_intersections': 'True',
                    # 'snap_vertices_tolerance': 10, these values are added later by defaults
                    # 'snap_segments_tolerance': 10,
                    # 'snap_intersections_tolerance': 10,
                    'order': 0
                },
            ]
        }
        self.assertDictEqual(expected, json_legacy)

        self.assertEqual(table_manager.table.rowCount(), 0)
        table_manager.from_json(copy.deepcopy(json))
        self.assertEqual(table_manager.table.rowCount(), 1)
        data = table_manager.to_json()
        json = {
            'lines': {
                'layerId': self.layer.id(),
                'geometryType': 'line',
                'capabilities': {
                    'allow_without_geom': 'False',
                    'createFeature': 'True',
                    'modifyAttribute': 'True',
                    'modifyGeometry': 'True',
                    'deleteFeature': 'True'
                },
                'acl': 'edition_group',
                'snap_layers': [self.layer.id()],
                'snap_vertices': 'False',
                'snap_segments': 'False',
                'snap_intersections': 'True',
                'snap_vertices_tolerance': 10,
                'snap_segments_tolerance': 10,
                'snap_intersections_tolerance': 10,
                'provider': 'ogr',
                'order': 0
            }
        }
        self.assertDictEqual(json, data)

    def test_locate_by_layer(self):
        """Test table manager with locate by layer."""
        layer_2 = QgsVectorLayer(plugin_test_data_path('lines.geojson'), 'lines_2', 'ogr')
        QgsProject.instance().addMapLayer(layer_2)
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
                'layerId': self.layer.id(),
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
                    'layerId': self.layer.id(),
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
                'layerId': self.layer.id(),
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
        field = 'id'
        table = QTableWidget()
        definitions = AtlasDefinitions()
        definitions._use_single_row = False

        table_manager = TableManager(
            None, definitions, AtlasEditionDialog, table, None, None, None, None)

        self.assertEqual(table.columnCount(), len(definitions.layer_config.keys()))

        # JSON from LWC 3.4 and above
        layer_1 = {
            'layer': self.layer.id(),
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
        table_manager.layers_has_been_deleted([self.layer.id()])
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
            {'layer': [self.layer.id(), self.layer.id()]},
            table_manager._primary_keys()
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
        table = QTableWidget()

        definitions = AtlasDefinitions()
        definitions._use_single_row = False
        table_manager = TableManager(
            None, definitions, AtlasEditionDialog, table, None, None, None, None)

        json = {
            'layers': [
                {
                    'layer': self.layer.id(),
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
        field = 'id'
        table = QTableWidget()
        definitions = AtlasDefinitions()
        definitions._use_single_row = False

        json = {
            'atlasEnabled': 'True',  # Will not be used
            'atlasLayer': self.layer.id(),
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
                    'layer': self.layer.id(),
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
            'atlasLayer': self.layer.id(),
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
