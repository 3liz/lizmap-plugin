"""Test table manager.

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
"""

import copy

from pathlib import Path

import pytest

from qgis.core import QgsProject, QgsVectorLayer
from qgis.PyQt.QtWidgets import QComboBox, QTableWidget, QTreeWidget

from lizmap.definitions.atlas import AtlasDefinitions
from lizmap.definitions.attribute_table import AttributeTableDefinitions
from lizmap.definitions.dataviz import DatavizDefinitions
from lizmap.definitions.definitions import LwcVersions
from lizmap.definitions.edition import EditionDefinitions
from lizmap.definitions.filter_by_form import FilterByFormDefinitions
from lizmap.definitions.filter_by_login import FilterByLoginDefinitions
from lizmap.definitions.filter_by_polygon import FilterByPolygonDefinitions
from lizmap.definitions.layouts import LayoutsDefinitions
from lizmap.definitions.locate_by_layer import LocateByLayerDefinitions
from lizmap.definitions.time_manager import TimeManagerDefinitions
from lizmap.definitions.tooltip import ToolTipDefinitions
from lizmap.drag_drop_dataviz_manager import DragDropDatavizManager
from lizmap.forms.atlas_edition import AtlasEditionDialog
from lizmap.table_manager.base import TableManager
from lizmap.table_manager.layouts import TableManagerLayouts

from .compat import TestCase


@pytest.fixture()
def layer(data: Path) -> None:
    layer = QgsVectorLayer(str(data.joinpath('lines.geojson')), 'lines', 'ogr')
    assert layer.isValid()

    QgsProject.instance().addMapLayer(layer)
    yield layer
    QgsProject.instance().clear()


class TestTableManager(TestCase):

    def test_form_filter(self, layer: QgsVectorLayer):
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
                'layerId': layer.id(),
                'order': 0
            },
            '1': {
                'title': 'Line filtering',
                'type': 'numeric',
                'field': 'id',  # Numeric and 'field', this is a < 3.7 format
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
        data = table_manager.to_json(version=LwcVersions.Lizmap_3_6)

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

        # Version >= 3.7
        data = table_manager.to_json(version=LwcVersions.Lizmap_3_7)

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
                'start_field': 'id',
                'format': 'checkboxes',
                'order': 1
            }
        }
        self.assertDictEqual(data, expected)

        self.assertDictEqual({}, table_manager.wfs_fields_used())

    def test_form_filter_3_7(self, layer: QgsVectorLayer):
        """ Test to write to 3.6 format. """
        table_manager = TableManager(
            None, FilterByFormDefinitions(), None, QTableWidget(), None, None, None, None)

        json = {
            '0': {
                'title': 'Line filtering',
                'type': 'numeric',
                'start_field': 'id',
                'end_field': 'id',
                'min_date': '',
                'max_date': '',
                'format': 'checkboxes',
                'splitter': '',
                'provider': 'ogr',
                'layerId': layer.id(),
                'order': 0
            }
        }

        self.assertEqual(table_manager.table.rowCount(), 0)
        table_manager.from_json(json)
        self.assertEqual(table_manager.table.rowCount(), 1)
        data = table_manager.to_json(version=LwcVersions.Lizmap_3_6)

        expected = {
            '0': {
                'layerId': layer.id(),
                'provider': 'ogr',
                'title': 'Line filtering',
                'type': 'numeric',
                'field': 'id',
                # Not used, but we keep it in memory, more convenient if the end user has just temporary changed its
                # LWC version
                'end_field': 'id',
                'format': 'checkboxes',
                'order': 0
            }
        }
        self.assertDictEqual(data, expected)

        data = table_manager.to_json(version=LwcVersions.Lizmap_3_7)
        expected = {
            '0': {
                'layerId': layer.id(),
                'provider': 'ogr',
                'title': 'Line filtering',
                'type': 'numeric',
                'start_field': 'id',
                'end_field': 'id',
                'format': 'checkboxes',
                'order': 0
            }
        }
        self.assertDictEqual(data, expected)

        self.assertDictEqual({}, table_manager.wfs_fields_used())

    def test_filter_by_login(self, layer: QgsVectorLayer):
        """Test table manager with filter by login."""
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
        data = table_manager.to_json(LwcVersions.latest())

        expected = {
            'lines': {
                'edition_only': 'False',
                'filterAttribute': 'name',
                'allow_multiple_acl_values': False,
                'filterPrivate': 'False',
                'layerId': layer.id(),
                'order': 0
            }
        }
        self.assertDictEqual(data, expected)
        self.assertDictEqual({}, table_manager.wfs_fields_used())

    def test_layout_definitions(self, data: Path, layer: QgsVectorLayer):
        """ Test layout definitions. """
        table = QTableWidget()
        definitions = LayoutsDefinitions()

        QgsProject.instance().read(str(data.joinpath('print.qgs')))

        # Without the legacy checkbox, all default values from the definitions
        table_manager = TableManagerLayouts(
            None, definitions, None, table, None, None, None)

        self.assertEqual(table_manager.table.rowCount(), 0)
        cfg = {
            "list": [
                {
                    "layout": "A4 Landscape",
                    "enabled": False,
                    "allowed_groups": [
                        'admins',
                        'group_a',
                    ],
                    "formats_available": (
                        "pdf",
                        "png",
                    ),
                    "default_format": "pdf",
                    "dpi_available": (
                        "100",
                        "300",
                    ),
                    "default_dpi": "300"
                },
                {
                    "layout": "Cadastre",
                    "enabled": True,
                    "allowed_groups": 'im,an,admin',  # input as a string, output as array
                    "formats_available": (
                        "pdf",
                    ),
                    "default_format": "pdf",
                    "dpi_available": (
                        "100",
                    ),
                    "default_dpi": "100"
                },
            ]
        }
        table_manager.load_qgis_layouts(cfg)
        self.assertEqual(table_manager.table.rowCount(), 4)

        data = table_manager.to_json(LwcVersions.latest())
        expected = {
            "config": {},
            "list": [
                {
                    "layout": "A4 Landscape",
                    "enabled": False,  # Value overriden by the CFG file compare to other layouts.
                    "allowed_groups": [
                        'admins',
                        'group_a',
                    ],
                    "formats_available": (
                        "pdf",
                        "png"
                    ),
                    "default_format": "pdf",
                    "dpi_available": (
                        "100",
                        "300"
                    ),
                    "default_dpi": "300"
                },
                {
                    "layout": "Cadastre",
                    "enabled": True,
                    "allowed_groups": [
                        "im",
                        "an",
                        "admin",
                    ],
                    "formats_available": (
                        "pdf",
                    ),
                    "default_format": "pdf",
                    "dpi_available": (
                        "100",
                    ),
                    "default_dpi": "100"
                },
                {
                    "layout": "Local planning",
                    "enabled": True,
                    # "allowed_groups": [],
                    "formats_available": (
                        "pdf",
                    ),
                    "default_format": "pdf",
                    "dpi_available": (
                        "100",
                    ),
                    "default_dpi": "100"
                },
                {
                    "layout": "Economy",
                    "enabled": True,
                    # "allowed_groups": [],
                    "formats_available": (
                        "pdf",
                    ),
                    "default_format": "pdf",
                    "dpi_available": (
                        "100",
                    ),
                    "default_dpi": "100"
                }
            ]
        }
        self.assertDictEqual(data, expected)

        self.assertDictEqual({}, table_manager.wfs_fields_used())

    def test_dataviz_definitions(self, layer: QgsVectorLayer):
        """Test dataviz collections keys."""
        table_manager = TableManager(
            None, DatavizDefinitions(), None, QTableWidget(), None, None, None, None)
        expected = [
            'type', 'title', 'title_popup', 'description', 'layerId', 'x_field', 'aggregation',
            'traces', 'html_template', 'layout', 'popup_display_child_plot', 'trigger_filter', 'stacked',
            'horizontal', 'only_show_child', 'display_legend', 'display_when_layer_visible', 'uuid',
        ]
        self.assertListEqual(expected, table_manager.keys)

    def test_remove_extra_field_dataviz(self, layer: QgsVectorLayer):
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
                'layerId': layer.id(),
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
                    'layerId': layer.id(),
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

        self.assertDictEqual({}, table_manager.wfs_fields_used())

    def test_dataviz_legacy_3_3_with_1_trace(self, layer: QgsVectorLayer):
        """Test table manager with dataviz format 3.3 with only 1 trace"""
        table = QTableWidget()
        definitions = DatavizDefinitions()

        table_manager = TableManager(
            None, definitions, None, table, None, None, None, None)

        # Lizmap 3.3
        json = {
            '0': {
                'title': 'My graph',
                'title_popup': 'My filtered plot',
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
                'layerId': layer.id(),
                'order': 0
            }
        }
        data = table_manager._from_json_legacy_order(copy.deepcopy(json))
        expected = {
            'layers': [
                {
                    'title': 'My graph',
                    'title_popup': 'My filtered plot',
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
                    'layerId': layer.id(),
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
                    'title_popup': 'My filtered plot',
                    'type': 'scatter',
                    'x_field': 'id',
                    'aggregation': '',
                    'popup_display_child_plot': 'False',
                    'only_show_child': 'True',
                    'layerId': layer.id(),
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
                'title_popup': 'My filtered plot',
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
                'trigger_filter': True,
                'only_show_child': 'True',
                'display_when_layer_visible': 'False',
                'layerId': layer.id(),
                'uuid': data['0']['uuid'],
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
                'title_popup': 'My filtered plot',
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
                'trigger_filter': True,
                'popup_display_child_plot': 'False',
                'only_show_child': 'True',
                'display_when_layer_visible': 'False',
                'layerId': layer.id(),
                'uuid': data['0']['uuid'],
                'order': 0
            }
        }
        self.assertDictEqual(data, expected)

        self.assertDictEqual({layer.id(): ['id', 'name']}, table_manager.wfs_fields_used())

    def test_dataviz_legacy_3_3_with_2_traces(self, layer: QgsVectorLayer):
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
                'layerId': layer.id(),
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
                    'layerId': layer.id(),
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
                    'layerId': layer.id(),
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
                'trigger_filter': True,
                'popup_display_child_plot': 'False',
                'only_show_child': 'True',
                'display_when_layer_visible': 'False',
                'layerId': layer.id(),
                'order': 0
            }
        }
        expected_traces = expected['0'].pop('traces')
        data_traces = data['0'].pop('traces')
        del data['0']['uuid']
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
                'trigger_filter': True,
                'only_show_child': 'True',
                'display_when_layer_visible': 'False',
                'layerId': layer.id(),
                'order': 0
            }
        }
        del data['0']['uuid']
        self.assertDictEqual(data, expected)

        self.assertDictEqual(
            {
                layer.id(): ['id', 'name', 'name'],
            },
            table_manager.wfs_fields_used())

    def test_dataviz_box(self, data: Path, layer: QgsVectorLayer):
        """Box chart has an empty key about aggregation."""

        table = QTableWidget()
        definitions = DatavizDefinitions()

        table_manager = TableManager(
            None, definitions, None, table, None, None, None, None)

        json = {
            '0': {
                'title': 'My graph',
                'type': 'box',
                'x_field': 'id',
                'aggregation': '',  # Empty key
                'y_field': 'first name',
                'color': '#00aaff',
                'colorfield': 'first color field',
                'has_y2_field': 'True',
                'y2_field': 'second name',
                'color2': '#ffaa00',
                'colorfield2': 'second color field',
                'popup_display_child_plot': 'False',
                'only_show_child': 'True',
                'layerId': layer.id(),
                'order': 0
            }
        }

        self.assertEqual(table_manager.table.rowCount(), 0)
        table_manager.from_json(json)
        self.assertEqual(table_manager.table.rowCount(), 1)
        data = table_manager.to_json(LwcVersions.latest())

        expected = {
            '0': {
                'title': 'My graph',
                'type': 'box',
                'x_field': 'id',
                'aggregation': '',  # It must stay empty
                'traces': [
                    {
                        'color': '#00aaff',
                        'colorfield': 'first color field',
                        'y_field': 'first name'
                    }, {
                        'color': '#ffaa00',
                        'colorfield': 'second color field',
                        'y_field': 'second name'
                    }
                ],
                'trigger_filter': True,
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
        self.assertTrue('_plot_' in data['0']['uuid'])
        del data['0']['uuid']
        self.assertDictEqual(data, expected)

        self.assertDictEqual(
            {
                layer.id(): [
                    'id',
                    'first name',
                    'first color field',
                    'second name',
                    'second color field',
                ]
            },
            table_manager.wfs_fields_used()
        )

    def test_dataviz_3_4(self, layer: QgsVectorLayer):
        """Test we can read dataviz 3.4 format."""
        table_widget = QTableWidget()
        definitions = DatavizDefinitions()
        table_manager = TableManager(
            None, definitions, None, table_widget, None, None, None, None)

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
                'layerId': layer.id(),
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
                    'layerId': layer.id(),
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
                    'layerId': layer.id(),
                    'order': 0
                }
            ]
        }
        self.assertCountEqual(expected, json_legacy)

        self.assertEqual(table_manager.table.rowCount(), 0)
        table_manager.from_json(json)
        # self.assertEqual(table_manager.table.rowCount(), 1)

        # Drag and drop
        # We need the table to be populated with data.
        self.assertEqual(1, table_widget.rowCount())
        tree_widget = QTreeWidget()
        combo = QComboBox()
        dd_manager = DragDropDatavizManager(None, definitions, table_widget, tree_widget, combo)
        dd_manager.load_dataviz_list_from_main_table()
        self.assertEqual(1, combo.count())
        self.assertEqual(0, dd_manager.count_lines())
        dd_manager.add_current_plot_from_combo()
        self.assertEqual(1, dd_manager.count_lines())

        self.assertDictEqual({layer.id(): ['id', 'name']}, table_manager.wfs_fields_used())

    def test_filter_by_polygon(self, layer: QgsVectorLayer):
        """ Test table manager with filter by polygon. """
        table_manager = TableManager(
            None, FilterByPolygonDefinitions(), None, QTableWidget(), None, None, None, None)

        json = {
            'config': {
                'polygon_layer_id': layer.id(),
                'group_field': 'id',
                'filter_by_user': False,
            },
            'layers': [
                {
                    "layer": layer.id(),
                    "primary_key": "id",
                    "spatial_relationship": "intersects",
                    "filter_mode": "display_and_editing"
                }
            ]
        }
        self.assertEqual(table_manager.table.rowCount(), 0)
        table_manager.from_json(json)
        self.assertEqual(table_manager.table.rowCount(), 1)

        output = table_manager.to_json(LwcVersions.latest())
        # Global widget are not defined in this test
        json['config'] = {}
        json['layers'][0]['use_centroid'] = False  # Default value
        self.assertEqual(output, json)

        self.assertDictEqual({}, table_manager.wfs_fields_used())

    def test_tool_tip(self, layer: QgsVectorLayer):
        """Test table manager with tooltip layer."""
        table = QTableWidget()
        definitions = ToolTipDefinitions()

        table_manager = TableManager(
            None, definitions, None, table, None, None, None, None)

        json = {
            'lines': {
                'fields': 'id,name',
                'template': '<p>[% \"nom\" %]</p>\n',
                'displayGeom': 'False',
                'colorGeom': '',
                'layerId': layer.id(),
                'order': 0
            }
        }
        self.assertEqual(table_manager.table.rowCount(), 0)
        table_manager.from_json(json)
        self.assertEqual(table_manager.table.rowCount(), 1)
        data = table_manager.to_json(LwcVersions.latest())
        json['lines'].pop('colorGeom')
        self.assertDictEqual(data, json)

        self.assertDictEqual({layer.id(): ['id', 'name']}, table_manager.wfs_fields_used())

    def test_attribute_table(self, layer: QgsVectorLayer):
        """Test table manager with attribute table."""
        table = QTableWidget()
        definitions = AttributeTableDefinitions()

        table_manager = TableManager(
            None, definitions, None, table, None, None, None, None)

        json = {
            'lines': {
                'primaryKey': 'id',
                'hiddenFields': 'id,name,value',
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
        data = table_manager.to_json(LwcVersions.latest())

        # Automatically added, so we add it manually for the comparaison
        json['lines']['custom_config'] = 'False'

        # Allowing groups for exporting
        # Check the default value to True, by default
        # https://github.com/3liz/lizmap-plugin/issues/629
        json['lines']['export_enabled'] = True
        self.assertIsNone(json['lines'].get('export_allowed_groups'))

        self.assertDictEqual(data, json)

        self.assertDictEqual({layer.id(): ['id']}, table_manager.wfs_fields_used())

    def test_attribute_table_export_acl(self, layer: QgsVectorLayer):
        """Test table manager with attribute table with export ACL"""
        table = QTableWidget()
        definitions = AttributeTableDefinitions()

        table_manager = TableManager(
            None, definitions, None, table, None, None, None, None)

        # Check the default value to False
        # https://github.com/3liz/lizmap-plugin/issues/629
        json = {
            'lines': {
                'primaryKey': 'id',
                'export_enabled': False,  # Set it to "False" to try the default value #629
                'export_allowed_groups': [
                    'admins',
                    'publishers',
                ],
                'hiddenFields': 'id,name,value',
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
        data = table_manager.to_json(LwcVersions.latest())

        # Automatically added, so we add it manually for the comparaison
        json['lines']['custom_config'] = 'False'

        self.assertDictEqual(data, json)

        self.assertDictEqual({layer.id(): ['id']}, table_manager.wfs_fields_used())

    def test_time_manager_table(self, layer: QgsVectorLayer):
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
                'layerId': layer.id(),
                'order': 0
            }
        }
        self.assertEqual(table_manager.table.rowCount(), 0)
        table_manager.from_json(json)
        self.assertEqual(table_manager.table.rowCount(), 1)
        data = table_manager.to_json(LwcVersions.latest())
        expected = {
            'lines': {
                'startAttribute': 'id',
                'attributeResolution': 'years',  # missing from the input, default value in definitions
                'layerId': layer.id(),
                'order': 0
            }
        }
        self.assertDictEqual(data, expected)

        table_manager.truncate()

        # Minimum fields from 3.3
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
        data = table_manager.to_json(LwcVersions.latest())
        self.assertDictEqual(data, expected)

        table_manager.truncate()

        # JSON from 3.4
        json = {
            'lines': {
                'startAttribute': 'id',
                'endAttribute': 'id',
                'attributeResolution': 'minutes',
                'layerId': layer.id(),
                'order': 0
            }
        }
        self.assertEqual(table_manager.table.rowCount(), 0)
        table_manager.from_json(json)
        self.assertEqual(table_manager.table.rowCount(), 1)
        data = table_manager.to_json(LwcVersions.latest())
        self.assertDictEqual(data, json)

        self.assertDictEqual({layer.id(): ['id']}, table_manager.wfs_fields_used())

    # NOTE: for QGIS 3.40+ only PostgresSQL layers are supported for editing capa
    # bilities
    @pytest.mark.skip(reason="Unsupported")
    def test_edition_layer(self, layer: QgsVectorLayer):
        """Test table manager with edition layer."""
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
                    'allow_without_geom': 'False',
                    'modifyAttribute': 'True',
                    'modifyGeometry': 'True',
                    'deleteFeature': 'True'
                },
                'acl': 'edition_group',
                'snap_layers': [layer.id()],
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
                    'layerId': layer.id(),
                    'createFeature': 'True',
                    'allow_without_geom': 'False',
                    'modifyAttribute': 'True',
                    'modifyGeometry': 'True',
                    'deleteFeature': 'True',
                    'acl': 'edition_group',
                    'snap_layers': [layer.id()],
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
        data = table_manager.to_json(LwcVersions.latest())
        json = {
            'lines': {
                'layerId': layer.id(),
                'geometryType': 'line',
                'capabilities': {
                    'allow_without_geom': 'False',
                    'createFeature': 'True',
                    'modifyAttribute': 'True',
                    'modifyGeometry': 'True',
                    'deleteFeature': 'True'
                },
                'acl': 'edition_group',
                'snap_layers': [layer.id()],
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

        self.assertDictEqual(
            {
                layer.id(): [
                    ''  # In a GeoJSON, the primary key is empty. But in production, a PostgreSQL layer will have a PK
                ]
            },
            table_manager.wfs_fields_used())

    def test_locate_by_layer(self, data: Path, layer: QgsVectorLayer):
        """Test table manager with locate by layer."""
        layer_2 = QgsVectorLayer(str(data.joinpath('lines.geojson')), 'lines_2', 'ogr')
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
        data = table_manager.to_json(LwcVersions.latest())

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

        self.assertDictEqual(
            {
                layer_2.id(): ['name'],
                layer.id(): ['name', 'id']
            }, table_manager.wfs_fields_used())

    def test_unavailable_layer_table_manager(self, layer: QgsVectorLayer):
        """ Test we can keep layer which is unavailable at the moment. """
        table = QTableWidget()
        definitions = AtlasDefinitions()

        table_manager = TableManager(
            None, definitions, AtlasEditionDialog, table, None, None, None, None)

        self.assertEqual(table_manager.table.rowCount(), 0)

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
        table_manager.from_json(json)
        self.assertEqual(table_manager.table.rowCount(), 1)
        data = table_manager.to_json(version=LwcVersions.Lizmap_3_6)

        expected = {
            'atlasLayer': 'ID_WHICH_DOES_NOT_EXIST',
            'atlasPrimaryKey': 'id',
            'atlasDisplayLayerDescription': 'False',
            'atlasFeatureLabel': 'name',
            'atlasSortField': 'name',
            'atlasHighlightGeometry': 'True',
            'atlasZoom': 'center',
            'atlasDisplayPopup': 'True',
            'atlasTriggerFilter': 'True',
            'atlasDuration': 5,
            'atlasEnabled': 'True',
            'atlasMaxWidth': 25
        }
        self.assertDictEqual(expected, data)

    def test_table_manager(self, layer: QgsVectorLayer):
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
        data = table_manager.to_json(LwcVersions.latest())
        self.assertDictEqual(data, json)

        # QGIS notify layer has been deleted
        table_manager.layers_has_been_deleted(['another_layer_ID_in_canvas'])
        self.assertEqual(table_manager.table.rowCount(), 1)
        table_manager.layers_has_been_deleted([layer.id()])
        self.assertEqual(table_manager.table.rowCount(), 0)

        data = table_manager.to_json(LwcVersions.latest())
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
            {'layer': [layer.id(), layer.id()]},
            table_manager._primary_keys()
        )

        data = table_manager.to_json(LwcVersions.latest())
        self.assertDictEqual(data, {'layers': [layer_1, layer_2]})

        # We select second row and we move up
        table.setCurrentCell(1, 0)
        table_manager.move_layer_up()

        # Export and check order
        data = table_manager.to_json(LwcVersions.latest())
        self.assertDictEqual(data, {'layers': [layer_2, layer_1]})

        # We select first row and we move up
        table.setCurrentCell(0, 0)
        table_manager.move_layer_up()
        # Nothing happen, we are on top
        data = table_manager.to_json(LwcVersions.latest())
        self.assertDictEqual(data, {'layers': [layer_2, layer_1]})

        table_manager.move_layer_down()
        data = table_manager.to_json(LwcVersions.latest())
        self.assertDictEqual(data, {'layers': [layer_1, layer_2]})

        # We select first row and we remove it
        table.setCurrentCell(0, 0)
        table_manager.remove_selection()
        data = table_manager.to_json(LwcVersions.latest())
        self.assertDictEqual(data, {'layers': [layer_2]})

        table_manager.truncate()
        self.assertEqual(table_manager.table.rowCount(), 0)

        # We select first row and we edit it
        # table.selectRow(0)
        # self.assertEqual(table_manager.edit_existing_row(), QDialog.Accepted)

    def test_atlas_missing_json_parameter(self, layer: QgsVectorLayer):
        """Test if we can load CFG file with missing parameter."""
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

        self.assertDictEqual({}, table_manager.wfs_fields_used())

    def test_table_manager_3_3(self, layer: QgsVectorLayer):
        """Test we can read/write to LWC 3.3 format."""
        field = 'id'
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

        data = table_manager.to_json(LwcVersions.latest())
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
        data = table_manager.to_json(LwcVersions.latest())

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
