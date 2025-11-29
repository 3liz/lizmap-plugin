""" Table manager for DXF export. """

from qgis.core import QgsProject, QgsVectorLayer
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QTableWidgetItem

from lizmap.toolbelt.convert import to_bool
from lizmap.widgets.project_tools import is_layer_published_wfs


class TableManagerDxfExport:

    """ Simple table manager for DXF export - just shows WFS layers with checkboxes. """

    def __init__(self, table):
        """ Constructor. """
        self.table = table

        # Setup table columns
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(['Layer', 'Enabled for DXF Export'])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(self.table.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(self.table.SelectionMode.SingleSelection)

    def load_wfs_layers(self, data: dict):
        """ Load all WFS-enabled layers into the table with checkboxes.

        Reads dxfExportEnabled from each layer's configuration in the layers section.
        The 'data' parameter contains the full CFG including the layers section.
        Only populates the table if there's a config (not empty).
        """
        # Clear table
        self.table.setRowCount(0)

        # If no config data at all, keep table empty
        if not data or not data.get('layers'):
            return

        # Extract layer-specific DXF settings from layers configuration
        layers_config = data.get('layers', {})
        enabled_layers = {}
        for layer_name, layer_data in layers_config.items():
            layer_id = layer_data.get('id')
            enabled = to_bool(layer_data.get('dxfExportEnabled', True))  # Default to enabled, convert to bool
            if layer_id:
                enabled_layers[layer_id] = enabled

        # Iterate through all vector layers in the project
        project = QgsProject.instance()
        row = 0
        for layer in project.mapLayers().values():
            if not isinstance(layer, QgsVectorLayer):
                continue

            # Check if layer is published as WFS
            if not is_layer_published_wfs(project, layer.id()):
                continue

            # Column 1: Enabled checkbox
            enabled = enabled_layers.get(layer.id(), True)  # Default to enabled

            self.table.insertRow(row)

            # Column 0: Layer name (read-only, stores layer ID in user data)
            name_item = QTableWidgetItem(layer.name())
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            name_item.setData(Qt.ItemDataRole.UserRole, layer.id())
            self.table.setItem(row, 0, name_item)

            # Column 1: Enabled checkbox
            checkbox_item = QTableWidgetItem()
            checkbox_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            checkbox_item.setCheckState(Qt.CheckState.Checked if enabled else Qt.CheckState.Unchecked)
            self.table.setItem(row, 1, checkbox_item)

            row += 1

    def to_json(self):
        """ Export table data to JSON format for CFG file. """
        layers = []

        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            checkbox_item = self.table.item(row, 1)

            if name_item and checkbox_item:
                layer_id = name_item.data(Qt.ItemDataRole.UserRole)
                enabled = checkbox_item.checkState() == Qt.CheckState.Checked

                layers.append({
                    'layerId': layer_id,
                    'enabled': enabled
                })

        return {
            'layers': layers
        }

    def truncate(self):
        """ Clear the table. """
        self.table.setRowCount(0)

    def set_lwc_version(self, version):
        """ Set LWC version - no-op for DXF export as we don't have version-specific features. """
        pass

    def use_single_row(self):
        """ Return False since we use multiple rows for WFS layers. """
        return False

    def wfs_fields_used(self):
        """ Return empty dict since DXF export uses entire layers, not specific fields. """
        return {}

    def populate_from_project(self):
        """ Populate table with all WFS layers from the current project.

        This is called when the user enables DXF export to show available WFS layers.
        """
        # Clear table first
        self.table.setRowCount(0)

        # Get all WFS layers from project
        project = QgsProject.instance()
        row = 0
        for layer in project.mapLayers().values():
            if not isinstance(layer, QgsVectorLayer):
                continue

            # Check if layer is published as WFS
            if not is_layer_published_wfs(project, layer.id()):
                continue

            self.table.insertRow(row)

            # Column 0: Layer name (read-only, stores layer ID in user data)
            name_item = QTableWidgetItem(layer.name())
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            name_item.setData(Qt.ItemDataRole.UserRole, layer.id())
            self.table.setItem(row, 0, name_item)

            # Column 1: Enabled checkbox (default to checked)
            checkbox_item = QTableWidgetItem()
            checkbox_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            checkbox_item.setCheckState(Qt.CheckState.Checked)
            self.table.setItem(row, 1, checkbox_item)

            row += 1

    def layers_has_been_deleted(self, layer_ids):
        """When some layers have been deleted from QGIS, remove them from the table."""
        for layer_id in layer_ids:
            row = self.table.rowCount()
            for i in range(row):
                cell = self.table.item(i, 0)
                if not cell:
                    continue

                value = cell.data(Qt.ItemDataRole.UserRole)
                if value == layer_id:
                    self.table.removeRow(i)
                    break  # Layer found and removed, move to next layer_id
