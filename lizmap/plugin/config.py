import json

from shutil import copyfile
from typing import (
    TYPE_CHECKING,
    Dict,
    Protocol,
)

from qgis.core import (
    QgsProject,
    QgsRectangle,
)

if TYPE_CHECKING:
    from qgis.gui import QgisInterface

from qgis.PyQt.QtWidgets import (
    QMessageBox,
)

from lizmap.definitions.definitions import (
    Html,
)
from lizmap.dialogs.main import LizmapDialog
from lizmap.toolbelt.convert import ambiguous_to_bool
from lizmap.toolbelt.i18n import tr

if TYPE_CHECKING:
    from ..dialogs.main import LizmapDialog

from .. import logger


class LizmapProtocol(Protocol):
    dlg: "LizmapDialog"
    iface: "QgisInterface"
    project: QgsProject
    layers_table: Dict
    global_options: Dict
    is_dev_version: bool


# MixIn classe
class ConfigFileManager(LizmapProtocol):
    def read_cfg_file(self, skip_tables: bool = False) -> Dict:
        """Get the saved configuration from the project.qgs.cfg config file.

        Populate the gui fields accordingly

        skip_tables is only used in tests, as we don't have "table managers".
        It's only for testing the "layer" panel.
        """
        json_options = {}
        json_file = self.dlg.cfg_file()
        if json_file.exists():
            with open(json_file, encoding='utf-8') as f:
                json_file_reader = f.read()

            try:
                sjson = json.loads(json_file_reader)
                json_options = sjson['options']
                for key in self.layers_table:
                    if key in sjson:
                        self.layers_table[key]['jsonConfig'] = sjson[key]
                    else:
                        self.layers_table[key]['jsonConfig'] = {}

                    manager = self.layers_table[key].get('manager')
                    if manager:

                        manager.truncate()

                        if key == 'layouts':
                            manager.load_qgis_layouts(sjson.get(key, {}))
                            continue

                        if key == 'dxfExport':
                            # Pass full sjson so manager can read from layers section
                            manager.load_wfs_layers(sjson)
                            continue

                        if key in sjson:
                            manager.from_json(sjson[key])
                        else:
                            # get a subset of the data to give to the table form
                            data = {k: json_options[k] for k in json_options if k.startswith(manager.definitions.key())}
                            if data:
                                manager.from_json(data)

                        if key == 'datavizLayers':
                            self.dataviz_mngr.read_cfg(sjson)

            except Exception as e:
                if self.is_dev_version:
                    raise
                logger.critical(e)
                copyfile(json_file, '{}.back'.format(json_file))
                message = tr(
                    'Errors encountered while reading the last layer tree state. '
                    'Please re-configure the options in the Layers tab completely. '
                    'The previous .cfg has been saved as .cfg.back')
                QMessageBox.critical(
                    self.dlg, tr('Lizmap Error'), message, QMessageBox.StandardButton.Ok)
                self.dlg.log_panel.append(message, abort=True, style=Html.P)
                logger.critical('Error while reading the Lizmap configuration file')

        else:
            logger.info('Lizmap CFG does not exist for this project.')
            for key in self.layers_table:
                manager = self.layers_table[key].get('manager')
                if manager:
                    manager.truncate()

        # Set the global options (map, tools, etc.)
        for key, item in self.global_options.items():
            if item.get('widget'):
                if item.get('tooltip'):
                    item['widget'].setToolTip(item.get('tooltip'))

                if item['wType'] in ('checkbox', 'radio'):
                    # Block signals while setting values to avoid triggering actions during config load
                    item['widget'].blockSignals(True)
                    item['widget'].setChecked(item['default'])
                    if key in json_options:
                        item['widget'].setChecked(ambiguous_to_bool(json_options[key]))
                    item['widget'].blockSignals(False)

                if item['wType'] == 'scale':
                    item['widget'].setShowCurrentScaleButton(True)
                    item['widget'].setMapCanvas(self.iface.mapCanvas())
                    item['widget'].setAllowNull(False)
                    value = json_options.get(key)
                    if value:
                        item['widget'].setScale(value)
                    else:
                        item['widget'].setScale(item['default'])

                if item['wType'] in ('text', 'textarea'):
                    if isinstance(item['default'], (list, tuple)):
                        item['widget'].setText(", ".join(map(str, item['default'])))
                    else:
                        item['widget'].setText(str(item['default']))
                    if key in json_options:
                        if isinstance(json_options[key], (list, tuple)):
                            item['widget'].setText(", ".join(map(str, json_options[key])))
                        else:
                            item['widget'].setText(str(json_options[key]))

                if item['wType'] == 'extent':
                    if key in json_options:
                        extent = QgsRectangle(
                            json_options[key][0],
                            json_options[key][1],
                            json_options[key][2],
                            json_options[key][3]
                        )
                        item['widget'].setOriginalExtent(extent, self.project.crs())
                        item['widget'].setOutputExtentFromOriginal()

                if item['wType'] == 'wysiwyg':
                    item['widget'].set_html_content(str(item['default']))
                    if key in json_options:
                        item['widget'].set_html_content(json_options[key])

                if item['wType'] == 'spinbox':
                    item['widget'].setValue(int(item['default']))
                    if key in json_options:
                        item['widget'].setValue(int(json_options[key]))

                if item['wType'] == 'list':
                    if isinstance(item['list'][0], (list, tuple)):
                        # New way with icon, tooltip, translated label
                        pass
                    else:
                        # Legacy way
                        for i, item_config in enumerate(item['list']):
                            item['widget'].setItemData(i, item_config)

                        if item['default'] in item['list']:
                            index = item['widget'].findData(item['default'])
                            item['widget'].setCurrentIndex(index)

                    if key in json_options:
                        index = item['widget'].findData(json_options[key])
                        if index:
                            item['widget'].setCurrentIndex(index)

            map_scales = json_options.get('mapScales', self.global_options['mapScales']['default'])
            min_scale = json_options.get('minScale', self.global_options['minScale']['default'])
            max_scale = json_options.get('maxScale', self.global_options['maxScale']['default'])
            use_native = json_options.get('use_native_zoom_levels')
            project_crs = json_options.get('projection')
            if project_crs:
                project_crs = project_crs.get('ref')

            self.set_map_scales_in_ui(
                map_scales=map_scales,
                min_scale=min_scale,
                max_scale=max_scale,
                use_native=use_native,
                project_crs=project_crs,
            )

        # Set layer combobox
        for key, item in self.global_options.items():
            if item.get('widget'):
                if item['wType'] == 'layers':
                    if key in json_options:
                        for lyr in self.project.mapLayers().values():
                            if lyr.id() == json_options[key]:
                                item['widget'].setLayer(lyr)
                                break

        # Then set field combobox
        for key, item in self.global_options.items():
            if item.get('widget'):
                if item['wType'] == 'fields':
                    if key in json_options:
                        item['widget'].setField(str(json_options[key]))

        self.dlg.check_ign_french_free_key()
        self.dlg.follow_map_theme_toggled()

        # Set DXF export table enabled state based on global checkbox
        dxf_manager = self.layers_table.get('dxfExport', {}).get('manager')
        if dxf_manager:
            dxf_enabled = self.dlg.checkbox_dxf_export_enabled.isChecked()
            dxf_manager.table.setEnabled(dxf_enabled)

        out = '' if json_file.exists() else 'out'
        logger.info(f'Dialog has been loaded successful, with{out} Lizmap configuration file')

        if self.project.fileName().lower().endswith('qgs'):
            # Manage lizmap_user project variable
            variables = self.project.customVariables()
            if 'lizmap_user' in variables and not self.dlg.check_cfg_file_exists() and not skip_tables:
                # The variable 'lizmap_user' exists in the project as a variable
                # But no CFG was found, maybe the project has been renamed.
                message = tr(
                    'We have detected that this QGIS project has been used before with the Lizmap plugin (due to the '
                    'variable "lizmap_user" in your project properties dialog).'
                )
                message += '\n\n'
                message += tr(
                    "However, we couldn't detect the Lizmap configuration file '{}' anymore. A new "
                    "configuration from scratch is used."
                ).format(self.dlg.cfg_file())
                message += '\n\n'
                message += tr(
                    'Did you rename this QGIS project file ? If you want to keep your previous configuration, you '
                    'should find your previous Lizmap configuration file and use the path above. Lizmap will load it.'
                )
                QMessageBox.warning(
                    self.dlg, tr('New Lizmap configuration'), message, QMessageBox.StandardButton.Ok)

            # Add default variables in the project
            if not variables.get('lizmap_user'):
                variables['lizmap_user'] = ''
            if not variables.get('lizmap_user_groups'):
                variables['lizmap_user_groups'] = list()
            self.project.setCustomVariables(variables)

        # Fill the layer tree
        data = self.populate_layer_tree()

        # Fill base-layer startup
        self.on_baselayer_checkbox_change()
        self.set_startup_baselayer_from_config()
        self.dlg.default_lizmap_folder()

        # The return is used in tests
        return data
