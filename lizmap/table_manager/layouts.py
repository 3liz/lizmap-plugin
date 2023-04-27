""" Table manager for layouts. """

import logging

from enum import Enum
from typing import Optional

from qgis.core import QgsProject
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QDialog

from lizmap.definitions.base import BaseDefinitions
from lizmap.definitions.definitions import LwcVersions
from lizmap.qgis_plugin_tools.tools.resources import plugin_name
from lizmap.table_manager.base import TableManager

LOGGER = logging.getLogger(plugin_name())


__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


class TableManagerLayouts(TableManager):

    """ Table manager for layouts. """

    def __init__(
            self, parent, definitions: BaseDefinitions, edition: Optional[QDialog], table, edit_button, up_button,
            down_button):
        TableManager.__init__(self, parent, definitions, edition, table, None, edit_button, up_button, down_button)

    @staticmethod
    def label_dictionary_list() -> str:
        """ The label in the CFG file prefixing the list. """
        return "list"

    def load_qgis_layouts(self, data: dict):
        """ Load QGIS layouts into the table. """
        LOGGER.debug("Loading all layouts from the QGIS project :")
        tmp_layout_cfg = {}
        if data:
            for layout in data.get(self.label_dictionary_list()):
                tmp = dict(layout)
                # Remove the name of the layout, it's now the key of the dictionary
                del tmp['layout']
                tmp_layout_cfg[layout.get('layout')] = tmp

        # Previous print from <= LWC 3.6 was activated or not
        # Do not break pre-existing format
        if self.parent:
            current_version = self.parent.current_lwc_version()
            if current_version:
                legacy_print_checkbox = (
                        self.parent.cbActivatePrint.isChecked() or current_version <= LwcVersions.Lizmap_3_6)
            else:
                legacy_print_checkbox = False
        else:
            legacy_print_checkbox = False

        # For all layouts in the project already loaded
        for layout in QgsProject.instance().layoutManager().printLayouts():
            # TODO check for report ?
            LOGGER.debug("  * reading layout {}".format(layout.name()))
            row = self.table.rowCount()
            self.table.setRowCount(row + 1)

            # We create the empty structure
            json = dict()

            # We fill with the layout name
            json['layout'] = layout.name()

            # We first fill with None or default values from definitions
            for key, values in self.definitions.layer_config.items():

                if key == 'layout':
                    continue

                json[key] = None
                default = values.get('default')
                if isinstance(default, Enum):
                    default = default.value['data']

                if default is not None:
                    # Be careful, default can an empty string...
                    json[key] = default

                if legacy_print_checkbox and key == 'dpi_available':
                    json['dpi_available'] = ('100', '200', '300')

                if legacy_print_checkbox and key == 'formats_available':
                    json['formats_available'] = ('pdf', 'png', 'jpeg', 'svg')

            # Then we override by the CFG file
            if layout.name() in tmp_layout_cfg.keys():
                for item_key, cfg_value in tmp_layout_cfg[layout.name()].items():
                    json[item_key] = cfg_value

            self._edit_row(row, json)

    def layout_renamed(self, layout, new_name: str):
        """ When a layout has been renamed in the project. """
        # The 'layout' has already the new name !
        # Shame, I need to make a diff to find which one was it...
        _ = layout

        row = self.table.rowCount()

        lizmap_layouts = []
        for i in range(row):
            cell = self.table.item(i, 0)
            if not cell:
                continue

            lizmap_layouts.append(cell.data(Qt.UserRole))

        qgis_layouts = []
        for layout in QgsProject.instance().layoutManager().printLayouts():
            qgis_layouts.append(layout.name())

        # Make the diff
        diff = [x for x in lizmap_layouts if x not in qgis_layouts]

        # Logically, it must be only one in the diff...
        if len(diff) >= 2:
            # Sorry, I don't know which one it was.
            return
        elif len(diff) == 0:
            # Strange, no diff
            # Nothing to do
            return

        old_name = diff[0]

        for i in range(row):
            cell = self.table.item(i, 0)
            if not cell:
                continue

            value = cell.data(Qt.UserRole)
            if value == old_name:
                LOGGER.info("Renaming layout from '{}' to '{}'".format(old_name, new_name))
                cell.setData(Qt.UserRole, new_name)
                cell.setText(new_name)
                break

    def layout_removed(self, name: str):
        """ When a layout has been removed from the project. """
        # A layout removed is the same behavior as a layer deleted in other tables.
        # We only need to make it as a list.
        self.layers_has_been_deleted([name])
