"""Tests for DXF export access control functionality."""

from pathlib import Path

import pytest

from qgis.core import QgsProject, QgsVectorLayer
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QTableWidget

from lizmap.table_manager.dxf_export import TableManagerDxfExport
from lizmap.toolbelt.convert import ambiguous_to_bool

from .compat import TestCase


@pytest.fixture()
def wfs_layer(data: Path) -> QgsVectorLayer:
    """Create a WFS-enabled vector layer for testing."""
    layer = QgsVectorLayer(str(data.joinpath("lines.geojson")), "test_lines", "ogr")
    assert layer.isValid()

    # Add to project and configure as WFS
    project = QgsProject.instance()
    project.addMapLayer(layer)

    # Enable WFS for this layer
    project.writeEntry("WFSLayers", "/", [layer.id()])

    yield layer
    project.clear()


@pytest.fixture()
def non_wfs_layer(data: Path) -> QgsVectorLayer:
    """Create a non-WFS vector layer for testing."""
    layer = QgsVectorLayer(str(data.joinpath("points.geojson")), "test_points", "ogr")
    assert layer.isValid()

    project = QgsProject.instance()
    project.addMapLayer(layer)

    yield layer
    project.clear()


class TestTableManagerDxfExport(TestCase):
    """Test the DXF export table manager."""

    def test_initialization(self):
        """Test table manager initialization."""
        # Initialize manager
        table = QTableWidget()
        TableManagerDxfExport(table)

        # Check table is configured correctly
        self.assertEqual(table.columnCount(), 2)
        self.assertEqual(table.rowCount(), 0)

    def test_use_single_row(self):
        """Test use_single_row returns False."""
        table = QTableWidget()
        manager = TableManagerDxfExport(table)

        self.assertFalse(manager.use_single_row())

    def test_wfs_fields_used(self):
        """Test wfs_fields_used returns empty dict."""
        table = QTableWidget()
        manager = TableManagerDxfExport(table)

        self.assertDictEqual(manager.wfs_fields_used(), {})

    def test_load_empty_config(self):
        """Test loading with no config data."""
        table = QTableWidget()
        manager = TableManagerDxfExport(table)

        # Load with None
        manager.load_wfs_layers(None)
        self.assertEqual(table.rowCount(), 0)

        # Load with empty dict
        manager.load_wfs_layers({})
        self.assertEqual(table.rowCount(), 0)

        # Load with dict without layers
        manager.load_wfs_layers({'options': {}})
        self.assertEqual(table.rowCount(), 0)

    def test_load_wfs_layers(self, wfs_layer: QgsVectorLayer):
        """Test loading WFS layers from config."""
        table = QTableWidget()
        manager = TableManagerDxfExport(table)

        # Prepare config data
        config = {
            'layers': {
                'test_lines': {
                    'id': wfs_layer.id(),
                    'dxfExportEnabled': False
                }
            }
        }

        # Load layers
        manager.load_wfs_layers(config)

        # Should have 1 row (the WFS layer)
        self.assertEqual(table.rowCount(), 1)

        # Check layer name
        name_item = table.item(0, 0)
        self.assertEqual(name_item.text(), 'test_lines')
        self.assertEqual(name_item.data(Qt.ItemDataRole.UserRole), wfs_layer.id())

        # Check checkbox state (should be unchecked because dxfExportEnabled=False)
        checkbox_item = table.item(0, 1)
        self.assertEqual(checkbox_item.checkState(), Qt.CheckState.Unchecked)

    def test_load_wfs_layers_enabled(self, wfs_layer: QgsVectorLayer):
        """Test loading WFS layers with enabled=True."""
        table = QTableWidget()
        manager = TableManagerDxfExport(table)

        config = {
            'layers': {
                'test_lines': {
                    'id': wfs_layer.id(),
                    'dxfExportEnabled': True
                }
            }
        }

        manager.load_wfs_layers(config)

        # Check checkbox state (should be checked)
        checkbox_item = table.item(0, 1)
        self.assertEqual(checkbox_item.checkState(), Qt.CheckState.Checked)

    def test_load_wfs_layers_boolean_conversion(self, wfs_layer: QgsVectorLayer):
        """Test that string booleans are properly converted."""
        table = QTableWidget()
        manager = TableManagerDxfExport(table)

        # Test with string "False"
        config = {
            'layers': {
                'test_lines': {
                    'id': wfs_layer.id(),
                    'dxfExportEnabled': 'False'  # String, not boolean
                }
            }
        }

        manager.load_wfs_layers(config)
        checkbox_item = table.item(0, 1)
        # Should be unchecked because ambiguous_to_bool("False") == False
        self.assertEqual(checkbox_item.checkState(), Qt.CheckState.Unchecked)

        # Test with string "True"
        table.setRowCount(0)
        config['layers']['test_lines']['dxfExportEnabled'] = 'True'
        manager.load_wfs_layers(config)
        checkbox_item = table.item(0, 1)
        self.assertEqual(checkbox_item.checkState(), Qt.CheckState.Checked)

    def test_load_wfs_layers_default_value(self, wfs_layer: QgsVectorLayer):
        """Test that missing dxfExportEnabled defaults to True."""
        table = QTableWidget()
        manager = TableManagerDxfExport(table)

        config = {
            'layers': {
                'test_lines': {
                    'id': wfs_layer.id()
                    # No dxfExportEnabled key
                }
            }
        }

        manager.load_wfs_layers(config)
        checkbox_item = table.item(0, 1)
        # Should default to checked
        self.assertEqual(checkbox_item.checkState(), Qt.CheckState.Checked)

    def test_load_ignores_non_wfs_layers(self, non_wfs_layer: QgsVectorLayer):
        """Test that non-WFS layers are not loaded."""
        table = QTableWidget()
        manager = TableManagerDxfExport(table)

        config = {
            'layers': {
                'test_points': {
                    'id': non_wfs_layer.id(),
                    'dxfExportEnabled': True
                }
            }
        }

        manager.load_wfs_layers(config)

        # Should have 0 rows because layer is not WFS-enabled
        self.assertEqual(table.rowCount(), 0)

    def test_to_json_empty_table(self):
        """Test to_json with empty table."""
        table = QTableWidget()
        manager = TableManagerDxfExport(table)

        result = manager.to_json()

        self.assertDictEqual(result, {'layers': []})

    def test_to_json_with_layers(self, wfs_layer: QgsVectorLayer):
        """Test to_json with populated table."""
        table = QTableWidget()
        manager = TableManagerDxfExport(table)

        # Populate from project
        manager.populate_from_project()

        # Uncheck first layer
        checkbox_item = table.item(0, 1)
        checkbox_item.setCheckState(Qt.CheckState.Unchecked)

        result = manager.to_json()

        # Check structure
        self.assertIn('layers', result)
        self.assertEqual(len(result['layers']), 1)

        # Check layer data
        layer_data = result['layers'][0]
        self.assertEqual(layer_data['layerId'], wfs_layer.id())
        self.assertEqual(layer_data['enabled'], False)

    def test_to_json_checked_layer(self, wfs_layer: QgsVectorLayer):
        """Test to_json with checked layer."""
        table = QTableWidget()
        manager = TableManagerDxfExport(table)

        manager.populate_from_project()

        # Keep layer checked (default)
        result = manager.to_json()

        layer_data = result['layers'][0]
        self.assertEqual(layer_data['enabled'], True)

    def test_populate_from_project(self, wfs_layer: QgsVectorLayer):
        """Test populate_from_project method."""
        table = QTableWidget()
        manager = TableManagerDxfExport(table)

        # Initially empty
        self.assertEqual(table.rowCount(), 0)

        # Populate
        manager.populate_from_project()

        # Should have 1 WFS layer
        self.assertEqual(table.rowCount(), 1)

        # Check defaults
        name_item = table.item(0, 0)
        self.assertEqual(name_item.text(), 'test_lines')

        checkbox_item = table.item(0, 1)
        # Should default to checked
        self.assertEqual(checkbox_item.checkState(), Qt.CheckState.Checked)

    def test_populate_ignores_non_wfs(self, non_wfs_layer: QgsVectorLayer):
        """Test populate_from_project ignores non-WFS layers."""
        table = QTableWidget()
        manager = TableManagerDxfExport(table)

        manager.populate_from_project()

        # Should have 0 rows
        self.assertEqual(table.rowCount(), 0)

    def test_populate_multiple_layers(self, wfs_layer: QgsVectorLayer, data: Path):
        """Test populate_from_project with multiple WFS layers."""
        # Add another WFS layer
        layer2 = QgsVectorLayer(str(data.joinpath("points.geojson")), "test_points", "ogr")
        assert layer2.isValid()

        project = QgsProject.instance()
        project.addMapLayer(layer2)

        # Enable WFS for both layers
        project.writeEntry("WFSLayers", "/", [wfs_layer.id(), layer2.id()])

        table = QTableWidget()
        manager = TableManagerDxfExport(table)

        manager.populate_from_project()

        # Should have 2 rows
        self.assertEqual(table.rowCount(), 2)

        # Both should be checked by default
        for row in range(2):
            checkbox_item = table.item(row, 1)
            self.assertEqual(checkbox_item.checkState(), Qt.CheckState.Checked)

    def test_truncate(self, wfs_layer: QgsVectorLayer):
        """Test truncate method."""
        table = QTableWidget()
        manager = TableManagerDxfExport(table)

        # Populate first
        manager.populate_from_project()
        self.assertEqual(table.rowCount(), 1)

        # Truncate
        manager.truncate()
        self.assertEqual(table.rowCount(), 0)

    def test_set_lwc_version(self):
        """Test set_lwc_version is a no-op."""
        table = QTableWidget()
        manager = TableManagerDxfExport(table)

        # Should not raise
        manager.set_lwc_version("3.7")
        manager.set_lwc_version("3.6")


class TestBooleanConversion(TestCase):
    """Test the ambiguous_to_bool utility function used for converting config values."""

    def test_ambiguous_to_bool_true_values(self):
        """Test conversion of various true values."""
        self.assertTrue(ambiguous_to_bool(True))
        self.assertTrue(ambiguous_to_bool('True'))
        self.assertTrue(ambiguous_to_bool('true'))
        self.assertTrue(ambiguous_to_bool('TRUE'))
        self.assertTrue(ambiguous_to_bool(1))
        self.assertTrue(ambiguous_to_bool('1'))

    def test_ambiguous_to_bool_false_values(self):
        """Test conversion of various false values."""
        self.assertFalse(ambiguous_to_bool(False))
        self.assertFalse(ambiguous_to_bool('False'))
        self.assertFalse(ambiguous_to_bool('false'))
        self.assertFalse(ambiguous_to_bool('FALSE'))
        self.assertFalse(ambiguous_to_bool(0))
        self.assertFalse(ambiguous_to_bool('0'))
        self.assertFalse(ambiguous_to_bool('', default_value=False))
        self.assertFalse(ambiguous_to_bool(None, default_value=False))


class TestDxfExportIntegration(TestCase):
    """Integration tests for DXF export save/load cycle."""

    def test_round_trip_save_load(self, wfs_layer: QgsVectorLayer):
        """Test that saving and loading preserves checkbox states."""
        table = QTableWidget()
        manager = TableManagerDxfExport(table)

        # Populate and set one layer to disabled
        manager.populate_from_project()
        checkbox_item = table.item(0, 1)
        checkbox_item.setCheckState(Qt.CheckState.Unchecked)

        # Export to JSON
        exported = manager.to_json()

        # Create config as it would be saved
        config = {
            'layers': {
                'test_lines': {
                    'id': wfs_layer.id(),
                    'dxfExportEnabled': exported['layers'][0]['enabled']
                }
            }
        }

        # Clear table and reload
        table2 = QTableWidget()
        manager2 = TableManagerDxfExport(table2)
        manager2.load_wfs_layers(config)

        # Check it's still unchecked
        checkbox_item2 = table2.item(0, 1)
        self.assertEqual(checkbox_item2.checkState(), Qt.CheckState.Unchecked)

    def test_backward_compatibility_missing_dxf_key(self, wfs_layer: QgsVectorLayer):
        """Test that old configs without dxfExportEnabled still work."""
        table = QTableWidget()
        manager = TableManagerDxfExport(table)

        # Config without dxfExportEnabled (old format)
        config = {
            'layers': {
                'test_lines': {
                    'id': wfs_layer.id(),
                    'title': 'Test Layer'
                    # No dxfExportEnabled key
                }
            }
        }

        # Should load without error and default to enabled
        manager.load_wfs_layers(config)

        self.assertEqual(table.rowCount(), 1)
        checkbox_item = table.item(0, 1)
        self.assertEqual(checkbox_item.checkState(), Qt.CheckState.Checked)
