"""Project management"""

import contextlib
import os
import re

from pathlib import Path
from shutil import copyfile
from typing import (
    TYPE_CHECKING,
    Dict,
    Optional,
    Protocol,
    Tuple,
)

from pyplugin_installer.version_compare import compareVersions
from qgis.core import (
    Qgis,
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsLayerTreeGroup,
    QgsMapLayer,
    QgsProject,
    QgsSettings,
)

if TYPE_CHECKING:
    from qgis.gui import QgisInterface

from qgis.core import QgsProjectServerValidator
from qgis.PyQt.QtCore import (
    QStorageInfo,
    Qt,
)
from qgis.PyQt.QtGui import (
    QTextCursor,
)
from qgis.PyQt.QtWidgets import (
    QMessageBox,
)
from qgis.utils import OverrideCursor
from qgis.utils import plugins as all_plugins

from lizmap.config import MappingQgisGeometryType
from lizmap.definitions.definitions import (
    DEV_VERSION_PREFIX,
    DURATION_WARNING_BAR,
    GroupNames,
    Html,
    LwcVersions,
    ReleaseStatus,
    ServerComboData,
)
from lizmap.definitions.lizmap_cloud import (
    CLOUD_MAX_PARENT_FOLDER,
    CLOUD_NAME,
    CLOUD_QGIS_MIN_RECOMMENDED,
)
from lizmap.definitions.online_help import (
    Panels,
)
from lizmap.definitions.qgis_settings import Settings
from lizmap.dialogs.confirmation_text_box import ConfirmationTextMessageBox
from lizmap.dialogs.main import LizmapDialog
from lizmap.ogc_project_validity import OgcProjectValidity
from lizmap.project_checker_tools import (  # duplicated_layer_with_filter_legend,
    ALLOW_PARENT_FOLDER,
    FORCE_LOCAL_FOLDER,
    FORCE_PG_USER_PASS,
    PREVENT_AUTH_DB,
    PREVENT_ECW,
    PREVENT_OTHER_DRIVE,
    PREVENT_SERVICE,
    count_legend_items,
    duplicated_label_legend,
    duplicated_layer_name_or_group,
    duplicated_rule_key_legend,
    project_invalid_pk,
    project_safeguards_checks,
    project_tos_layers,
    project_trust_layer_metadata,
    simplify_provider_side,
    trailing_layer_group_name,
    use_estimated_metadata,
)

from ..saas import check_project_ssl_postgis, is_lizmap_cloud
from ..toolbelt.convert import ambiguous_to_bool, as_boolean
from ..toolbelt.git import next_git_tag
from ..toolbelt.i18n import tr
from ..toolbelt.layer import (
    get_layer_wms_parameters,
    relative_path,
    remove_all_ghost_layers,
)
from ..toolbelt.resources import window_icon
from ..toolbelt.strings import unaccent
from ..toolbelt.version import (
    format_version_integer,
    qgis_version_info,
    version,
)
from ..widgets.check_project import Check, SourceField
from ..widgets.project_tools import (
    empty_baselayers,
    is_layer_published_wfs,
)

if TYPE_CHECKING:
    from ..dialogs.main import LizmapDialog
    from ..table_manager.base import TableManager

from .. import logger
from .layer_tree import LayerTreeManager


class LizmapProtocol(Protocol):
    dlg: "LizmapDialog"
    project: QgsProject
    layers_table: Dict
    current_path: Optional[str]

    iface: "QgisInterface"

    @property
    def layerList(self) -> Dict: ...


class ProjectManager(LizmapProtocol):

    _current_path: Optional[Path]

    def initialize_project_management(self):
        self._current_path = None
        self.project.fileNameChanged.connect(self.filename_changed)
        self.project.projectSaved.connect(self.project_saved)
        self.filename_changed()

    def project_saved(self):
        """ When the project is saved. """
        if not self.dlg.check_cfg_file_exists():
            return

        try:
            if not self.layerList:
                # The user didn't open the plugin since QGIS has started
                # Sorry, we don't know if the user added/removed layers, maybe nothing
                return
        except AttributeError:
            # self.attributeError is defined in __init__ but not found
            return

        # Check the number of layers between the project and the Lizmap configuration file.
        list_cfg = list(self.layerList.keys())
        list_qgs = count_legend_items(self.project.layerTreeRoot(), self.project, [])
        if len(list_cfg) != len(list_qgs):
            logger.debug(
                "Difference in counts between CFG and QGS\n\nList in CFG : {}\nList in QGS : {}".format(
                    ','.join(list_cfg), ','.join(list_qgs)))

    def filename_changed(self):
        """ When the current project has been renamed. """
        if os.getenv("QGIS_PLUGIN_AUTO_SAVING"):
            # Special variable set from QGIS autoSaver plugin
            return

        if not self.project.absoluteFilePath():
            return

        new_path = Path(self.project.absoluteFilePath())
        if str(new_path).endswith('.bak'):
            # We skip, it's from the QGIS plugin autoSaver
            return

        if 'autoSaver' in all_plugins:
            # Until https://github.com/enricofer/autoSaver/pull/22 is merged
            return

        new_cfg = new_path.with_suffix('.qgs.cfg')
        if new_cfg.exists():
            # The CFG was already here, let's keep the previous one
            return

        if self._current_path and new_path != self._current_path and not as_boolean(os.getenv("CI")):
            old_cfg = self._current_path.with_suffix('.qgs.cfg')
            if old_cfg.exists():
                box = QMessageBox(self.dlg)
                box.setIcon(QMessageBox.Icon.Question)
                box.setWindowIcon(window_icon() )
                box.setWindowTitle(tr('Project has been renamed'))
                box.setText(tr(
                    'The previous project located at "{}" was associated to a Lizmap configuration. '
                    'Do you want to copy the previous Lizmap configuration file to this new project ?'
                ).format(self._current_path))
                box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                box.setDefaultButton(QMessageBox.StandardButton.No)
                result = box.exec()
                if result == QMessageBox.StandardButton.No:
                    return

                copyfile(str(old_cfg), str(new_cfg))
                logger.info("Project has been renamed and Lizmap configuration file has been copied as well.")

        self._current_path = new_path

    def project_config_file(
        self,
        lwc_version: LwcVersions,
        with_gui: bool = True,
        check_server: bool = True,
        ignore_error: bool = False,
    ) -> Optional[Dict]:
        """ Get the JSON CFG content. """

        if lwc_version >= LwcVersions.Lizmap_3_6:
            logger.info(f"Update project OGC validity for LWC version {lwc_version.value}")
            # Set shortnames if it's not set
            ogc_projet_validity = OgcProjectValidity(self.project)
            ogc_projet_validity.add_shortnames()
            ogc_projet_validity.set_project_short_name()

            validator = QgsProjectServerValidator()
            valid, _results = validator.validate(self.project)
            logger.info(f"Project has been detected : {'VALID' if valid else 'NOT valid'} according to OGC validation.")

        if not self.check_project(lwc_version, with_gui, check_server, ignore_error):
            # Some blocking issues, we can not continue
            return None

        server_metadata = self.dlg.server_combo.currentData(ServerComboData.JsonMetadata.value)

        logger.info(f"Writing Lizmap configuration file for LWC version {lwc_version.value}")
        current_version = self.global_options['metadata']['lizmap_plugin_version']['default']
        if self.is_dev_version:
            next_version = next_git_tag()
            if next_version != 'next':
                current_version = next_version

        target_status = self.dlg.server_combo.currentData(ServerComboData.LwcBranchStatus.value)
        if not target_status:
            target_status = ReleaseStatus.Unknown

        if is_lizmap_cloud(server_metadata):
            eol = (ReleaseStatus.Retired, ReleaseStatus.SecurityBugfixOnly)
            if self.dlg.current_server_info(ServerComboData.LwcBranchStatus.value) in eol:
                if self.dlg.current_server_info(ServerComboData.LwcBranchStatus.value) == ReleaseStatus.Retired:
                    msg = tr(
                        'This version of Lizmap Web Client is now <strong>not supported anymore</strong>.'
                    )
                else:
                    msg = tr(
                        'This version of Lizmap Web Client is <strong>nearly not supported anymore</strong>. '
                        'It is in <strong>security bugfix mode only</strong>, it means only critical bugfix are fixed '
                        'and soon the branch will be declared <strong>not maintained</strong>.'
                    )
                QMessageBox.warning(
                    self.dlg,
                    CLOUD_NAME,
                    tr(
                        'You current server <a href="{server_url}">{server_url}</a> is running '
                        'Lizmap Web Client version {lwc_version}.'
                    ).format(
                        server_url=self.dlg.current_server_info(ServerComboData.ServerUrl.value),
                        lwc_version=lwc_version.value,
                    )
                    + "<br><br>"
                    + msg
                    + "<br><br>"
                    + "<strong>"
                    + tr(
                        'Please visit your administration panel in your web browser, in the dashboard, and '
                        'ask for the update.'
                    )
                    + "</strong>"
                    + "<br><br>"
                    + tr(
                        'You might have some old project which need an update from you. The list is written on the '
                        'dashboard. Projects are not deleted during the update of Lizmap Web Client, '
                        'they will be only invisible on the main landing page until they are updated by you.'
                    )
                    + "<br><br>"
                    + tr('This is not blocking your current usage of the plugin, only to advise you.'),
                    QMessageBox.StandardButton.Ok
                )

            qgis_server_info = server_metadata.get('qgis_server_info')
            md = qgis_server_info.get('metadata')
            qgis_server_version = tuple([int(i) for i in md.get('version').split('.')])
            if qgis_server_version < CLOUD_QGIS_MIN_RECOMMENDED:
                QMessageBox.warning(
                    self.dlg,
                    CLOUD_NAME,
                    tr(
                        'You current server <a href="{server_url}">{server_url}</a> is running '
                        'QGIS Server {version}.'
                    ).format(
                        server_url=self.dlg.current_server_info(ServerComboData.ServerUrl.value),
                        version=md.get('version'),
                    )
                    + "<br><br>"
                    + tr(
                        'This version of QGIS Server has now reached its end of life and is not supported '
                        'anymore by QGIS.org since {month_and_year}, see the '
                        '<a href="https://www.qgis.org/en/site/getinvolved/development/roadmap.html#release-schedule">'
                        'QGIS roadmap'
                        '</a>.'
                    ).format(
                        month_and_year=tr("February 2024"),  # About QGIS 3.28
                    )
                    + "<br><br>"
                    + tr(
                        'Please visit your administration panel in your web browser, in the dashboard, and '
                        'ask for the update.'
                    )
                    + "<br><br>"
                    + tr('This is not blocking your current usage of the plugin, only to advise you.'),
                    QMessageBox.StandardButton.Ok
                )

        metadata = {
            'qgis_desktop_version': Qgis.versionInt(),
            'lizmap_plugin_version_str': current_version,
            'lizmap_plugin_version': int(format_version_integer(current_version)),
            'lizmap_web_client_target_version': int(format_version_integer('{}.0'.format(lwc_version.value))),
            'lizmap_web_client_target_status': target_status.value,
            'instance_target_url': self.dlg.server_combo.currentData(ServerComboData.ServerUrl.value)
        }
        repository = self.dlg.current_repository()
        if repository:
            metadata['instance_target_repository'] = repository

        profiler = QgsApplication.profiler()
        # We need to compute ourselves the total, QgsRuntimeProfiler::totalTime always returns 0
        time_total = 0
        group = 'projectload'
        for child in profiler.childGroups('', group):
            value = profiler.profileTime(child, group)
            time_total += value

        liz2json = dict()
        liz2json['metadata'] = metadata
        liz2json['warnings'] = self.dlg.check_results.to_json_summarized()
        liz2json['debug'] = {
            'total_time': time_total,
        }
        liz2json["options"] = dict()
        liz2json["layers"] = dict()

        # projection
        projection = self.dlg.widget_initial_extent.outputCrs()
        liz2json['options']['projection'] = dict()
        liz2json['options']['projection']['proj4'] = projection.toProj()
        liz2json['options']['projection']['ref'] = projection.authid()

        # WMS extent from project properties, QGIS server tab
        liz2json['options']['bbox'] = self.project.readListEntry('WMSExtent', '')[0]

        # set initialExtent values if not defined
        if self.dlg.widget_initial_extent.outputExtent().isNull():
            self.set_initial_extent_from_project()

        # GUI user defined options
        for key, item in self.global_options.items():
            if item.get('widget'):
                input_value = None
                # Get field value depending on widget type
                if item['wType'] == 'text':
                    input_value = item['widget'].text().strip(' \t')

                if item['wType'] == 'scale':
                    input_value = item['widget'].scale()
                    if input_value == item['default']:
                        # Only save if different from the default value
                        continue

                if item['wType'] == 'wysiwyg':
                    input_value = item['widget'].html_content().strip(' \t')

                if item['wType'] == 'textarea':
                    input_value = item['widget'].toPlainText().strip(' \t')

                if item['wType'] == 'spinbox':
                    input_value = item['widget'].value()

                if item['wType'] == 'checkbox':
                    input_value = str(item['widget'].isChecked())

                if item['wType'] == 'list':
                    input_value = item['widget'].currentData()

                if item['wType'] == 'layers':
                    lay = item['widget'].layer(item['widget'].currentIndex())
                    input_value = lay.id()

                if item['wType'] == 'fields':
                    input_value = item['widget'].currentField()

                if item['wType'] == 'extent':
                    input_value = item['widget'].outputExtent()

                # Cast value depending of data type
                if item['type'] == 'string':
                    if item['wType'] in ('text', 'textarea'):
                        input_value = str(input_value)
                    else:
                        input_value = str(input_value)

                elif item['type'] in ('intlist', 'floatlist', 'list'):
                    if item['type'] == 'intlist':
                        input_value = [int(a) for a in input_value.split(', ') if a.isdigit()]
                    elif item['type'] == 'floatlist':
                        if item['wType'] != 'extent':
                            input_value = [float(a) for a in input_value.split(', ')]
                        else:
                            input_value = [
                                input_value.xMinimum(),
                                input_value.yMinimum(),
                                input_value.xMaximum(),
                                input_value.yMaximum(),
                            ]
                    else:
                        input_value = [a.strip() for a in input_value.split(',') if a.strip()]

                elif item['type'] == 'integer':
                    # noinspection PyBroadException
                    try:
                        input_value = int(input_value)
                    except Exception:
                        input_value = int(item['default'])

                elif item['type'] == 'boolean':
                    input_value = item['widget'].isChecked()
                    if not item.get('use_proper_boolean'):
                        input_value = str(input_value)

                # Add value to the option
                if item['type'] == 'boolean':
                    if not ambiguous_to_bool(input_value):
                        if not item.get('always_export'):
                            continue

                if item['type'] in ('list', 'string'):
                    if not input_value:
                        # Empty list or string
                        if not item.get('always_export'):
                            continue

                liz2json["options"][key] = input_value

            # Since LWC 3.7, we are managing manually these values
            if key == 'mapScales':
                liz2json["options"]['mapScales'] = self.map_scales()
            if key == 'minScale':
                liz2json["options"]['minScale'] = self.minimum_scale_value()
            if key == 'maxScale':
                liz2json["options"]['maxScale'] = self.maximum_scale_value()
            if key == 'use_native_zoom_levels':
                liz2json["options"]['use_native_zoom_levels'] = self.dlg.use_native_scales.isChecked()
            if key == 'automatic_permalink':
                liz2json["options"]['automatic_permalink'] = self.dlg.automatic_permalink.isChecked()

        for key in self.layers_table:
            manager = self.layers_table[key].get('manager')
            if manager:
                try:
                    data = manager.to_json()
                except (AttributeError, ) as e:
                    import traceback
                    panel_name = self.dlg.mOptionsListWidget.item(self.layers_table[key].get('panel', key)).text()
                    QMessageBox.critical(
                        self.dlg,
                        'Lizmap',
                        tr(
                            'An error has been raised while saving table "<strong>{name}</strong>", maybe it was due '
                            'to invalid layers ?'
                        ).format(name=panel_name) + '\n\n'
                        + tr(
                            'If yes, saving the Lizmap configuration file with invalid layers in the legend is not '
                            'currently supported by the plugin.'
                        ) + '\n\n'
                        + tr(
                            'Please visit the corresponding tab "<strong>{name}</strong>" and check if you have a '
                            'warning in one of the column.'
                        ).format(name=panel_name) + '\n\n'
                        + tr(
                            'If not, it was a bug, please report it. The process is stopping.'
                        ) + '\n\n'
                        + tr('Error') + ' : ' + str(e) + '\n\n'
                        + traceback.format_exc()
                    )
                    return None

                if key == 'layouts':
                    # The print combobox is removed
                    # Let's remove from the CFG file
                    if lwc_version >= LwcVersions.Lizmap_3_7:
                        with contextlib.suppress(KeyError):
                            del liz2json['options']['print']
                    else:
                        # We do not want to save this table if it's less than LWC 3.7
                        logger.info("Skipping the 'layout' table because version is less than LWC 3.7")
                        continue

                if key == 'dxfExport':
                    # Store DXF export data to be processed during layer building loop
                    # This avoids trying to write to liz2json['layers'] before layers are added
                    continue

                if manager.use_single_row() and manager.table.rowCount() == 1:
                    liz2json['options'].update(data)
                else:
                    liz2json[key] = data

        # Drag drop dataviz designer
        if self.drag_drop_dataviz:
            # In tests, we don't have the variable set
            liz2json['options']['dataviz_drag_drop'] = self.drag_drop_dataviz.to_json()

        base_layers_group = LayerTreeManager.existing_group(
            self.project.layerTreeRoot(),
            GroupNames.BaseLayers,
        )

        if base_layers_group:
            base_layers_group: QgsLayerTreeGroup
            base_layers_group.setIsMutuallyExclusive(True, -1)

            default_background_color_index = LayerTreeManager.existing_group(
                base_layers_group,
                GroupNames.BackgroundColor,
                index=True,
            )

            if default_background_color_index is not None and default_background_color_index >= 0:
                liz2json["options"]["default_background_color_index"] = default_background_color_index

        if not isinstance(self.layerList, dict):
            # Wierd bug when the dialog was not having a server at the beginning
            # The navigation in the menu was not allowed
            # The user added a server → navigation allowed
            # But the project has not been loaded in the plugin
            # The layer tree is empty
            QMessageBox.warning(
                self.dlg,
                'Lizmap',
                tr(
                    '"Apply" or "OK" are not supported right now. Please close the dialog et reopen the plugin.'
                    'You will be able to save the Lizmap configuration file after.'
                ) + '\n\n'
                + tr('Sorry for the inconvenience.')
            )
            return None

        # Get DXF export data to apply during layer building
        # Always get the data if table has content, regardless of global enable state
        # This preserves user settings when they temporarily disable DXF export globally
        dxf_layer_settings = {}
        dxf_manager = self.layers_table.get('dxfExport', {}).get('manager')
        if dxf_manager:
            dxf_data = dxf_manager.to_json()
            # Build map from layer ID to enabled status
            for layer_config in dxf_data.get('layers', []):
                layer_id = layer_config.get('layerId')
                enabled = layer_config.get('enabled', True)
                if layer_id:
                    dxf_layer_settings[layer_id] = enabled

        # gui user defined layers options
        for k, v in self.layerList.items():
            layer = False
            if v['groupAsLayer']:
                layer_type = 'layer'
            else:
                layer_type = 'group'

            if self.get_qgis_layer_by_id(k):
                layer_type = 'layer'

            # ~ # add layerOption only for geo layers
            # ~ if geometryType != 4:
            layer_options = dict()
            layer_options["id"] = str(k)
            layer_options["name"] = str(v['name'])
            layer_options["type"] = layer_type

            geometry_type = -1
            if layer_type == 'layer':
                layer = self.get_qgis_layer_by_id(k)
                if layer and layer.type() == QgsMapLayer.LayerType.VectorLayer:  # if it is a vector layer:
                    geometry_type = layer.geometryType()

            # geometry type
            if geometry_type != -1:
                layer_options["geometryType"] = MappingQgisGeometryType[layer.geometryType()]

            # extent
            if layer:
                extent = layer.extent()
                if extent.isNull() or extent.isEmpty():
                    logger.info(f"Layer '{layer.name()}' has null or empty extent.")
                layer_options['extent'] = [
                    extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum()]
                if any(x != x for x in layer_options['extent']):
                    if layer.isSpatial():
                        # https://github.com/3liz/lizmap-plugin/issues/571
                        if 33600 <= Qgis.versionInt() < 33603:
                            msg = tr('A bug has been identified with QGIS 3.36.0 to 3.36.2 included, please change.')
                        else:
                            msg = ""
                        QMessageBox.warning(
                            self.dlg,
                            'Lizmap',
                            msg
                            + tr(
                                'Please check your layer extent for "{}" with the ID "{}".'
                                'The extent does not seem valid.'
                            ).format(layer.name(), layer.id()) + '\n\n'
                            + tr(
                                'You can visit vector layer properties → Information tab → Information from provider → '
                                'Extent.'
                            ) + '\n\n'
                            + tr(
                                'Then in the "Source" tab, you can recompute the extent or check your logs in QGIS.'
                            ) + '\n\n'
                            + tr(
                                'The extent has been set to a default value 0,0,0,0.'
                            )
                        )
                    layer_options['extent'] = [0, 0, 0, 0]
                layer_options['crs'] = layer.crs().authid()

            # styles
            if isinstance(layer, QgsMapLayer):
                ls = layer.styleManager().styles()
                if len(ls) > 1:
                    layer_options['styles'] = ls

            # Loop through the layer options and set properties from the dictionary
            for key, val in self.layer_options_list.items():
                property_value = v[key]
                if val['type'] == 'string':
                    if val['wType'] in ('text', 'textarea'):
                        property_value = str(property_value)
                    elif val['wType'] == 'list' and isinstance(property_value, tuple):
                        # Process later, do not cast for now
                        pass
                    else:
                        property_value = str(property_value)
                elif val['type'] == 'integer':
                    # noinspection PyBroadException
                    try:
                        property_value = int(property_value)
                    except Exception:
                        property_value = 1
                elif val['type'] in ('boolean', 'radio'):
                    if not val.get('use_proper_boolean'):
                        property_value = str(property_value)

                if key == 'link':
                    # TODO check media or ../media
                    pass

                if key in ('legend_image_option', 'noLegendImage'):
                    if layer_options.get('legend_image_option') and key == 'noLegendImage':
                        # Let's skip, the key is already saved
                        continue

                    if layer_options.get('noLegendImage') and key == 'legend_image_option':
                        # Let's skip, the key is already saved
                        continue

                    max_version = val.get('max_version')
                    if max_version and lwc_version > max_version:
                        # logger.info("Skipping key '{}' because of max_version.".format(key))
                        continue

                    min_version = val.get('min_version')
                    if min_version and lwc_version < min_version:
                        # logger.info("Skipping key '{}' because of min_version.".format(key))
                        continue

                    if key == 'noLegendImage':
                        # We take the value of legend_image_option
                        property_value = str(False)
                        if v['legend_image_option'] == 'disabled':
                            property_value = str(True)
                        if v['legend_image_option'] == 'expand_at_startup' and with_gui:
                            # We keep False
                            QMessageBox.warning(
                                self.dlg,
                                tr('Legend image'),
                                tr(
                                    'Be careful, the option "Expand at startup" for the layer "{layer_name}" is not '
                                    'available for your Lizmap Web Client target version {target}.'
                                ).format(layer_name=k, target=lwc_version.value)
                                + '\n\n'
                                + tr('Falling back to "Hide at startup" in the configuration file.')
                                + '\n\n'
                                + tr('This option is only available for Lizmap Web Client 3.6 and above.')
                            )

                    if isinstance(property_value, tuple):
                        property_value = property_value[0]

                    # logger.info("Saving {} = {} for layer {}".format(key, property_value, k))

                layer_options[key] = property_value

            # Cache Metatile: unset metatileSize if empty
            # this is to avoid, but LWC must change accordingly to avoid using empty metatileSize
            # (2.2.0 does not handle it)

            # unset metatileSize
            meta_tile_size = layer_options.get('metatileSize')
            if meta_tile_size is not None and isinstance(meta_tile_size, str) and not re.match(r'\d,\d', meta_tile_size):
                del layer_options['metatileSize']

            # unset cacheExpiration if False
            cached = layer_options.get('cached')
            if cached and not ambiguous_to_bool(cached):
                del layer_options['cacheExpiration']

            # unset clientCacheExpiration if not needed
            client_cache = layer_options.get('clientCacheExpiration')
            if client_cache and client_cache < 0:
                del layer_options['clientCacheExpiration']

            # unset externalWms if False
            external_wms = layer_options.get('externalWmsToggle')
            if external_wms and not ambiguous_to_bool(external_wms):
                del layer_options['externalWmsToggle']

            # unset source project and repository if needed
            source_repository = layer_options.get('sourceRepository')
            source_project = layer_options.get('sourceProject')
            if not source_repository or not source_project:
                del layer_options['sourceRepository']
                del layer_options['sourceProject']

            # set popupSource to auto if set to lizmap and no lizmap conf found
            if ambiguous_to_bool(layer_options['popup']) and layer_options['popupSource'] == 'lizmap' \
                    and layer_options['popupTemplate'] == '':
                layer_options['popupSource'] = 'auto'

            if layer_options.get("geometryType") in ('point', 'line', 'polygon'):
                if layer_options.get('popupSource') == 'lizmap' and ambiguous_to_bool(layer_options.get('popup')):
                    QMessageBox.warning(
                        self.dlg,
                        tr('Deprecated feature'),
                        tr(
                            'The layer "{}" is vector layer and the popup is a "Lizmap HTML". This kind of popup is '
                            'deprecated for vector layer, you should switch to another kind of popup, for instance to '
                            'a "QGIS HTML maptip". This will be removed in a future version of Lizmap.'
                        ).format(layer_options["name"]),
                        QMessageBox.StandardButton.Ok
                    )

            # Add external WMS options if needed
            if isinstance(layer, QgsMapLayer) and as_boolean(layer_options.get('externalWmsToggle')):
                # Only for layers stored in disk
                if layer.providerType() == 'wms':
                    wms_params = get_layer_wms_parameters(layer)
                    if wms_params:
                        layer_options['externalAccess'] = wms_params
                    else:
                        layer_options['externalWmsToggle'] = str(False)
                else:
                    layer_options['externalWmsToggle'] = str(False)

            layer_options.pop('serverFrame', None)

            layer_options.pop('popupFrame', None)

            # Add DXF export setting if applicable
            # Write settings regardless of global enable state to preserve user choices
            if k in dxf_layer_settings:
                # Only add if this layer is published as WFS
                if is_layer_published_wfs(self.project, k):
                    layer_options['dxfExportEnabled'] = dxf_layer_settings[k]

            # Add layer options to the json object
            liz2json["layers"][v['name']] = layer_options

        return liz2json

    def check_project(
        self,
        lwc_version: LwcVersions,
        with_gui: bool = True,
        check_server: bool = True,
        ignore_error: bool = False,
    ) -> bool:
        """ Check the project against all rules defined. """
        # Import must be done after QTranslator
        from lizmap.widgets.check_project import (
            Checks,
            Error,
            Severities,
            SourceLayer,
        )
        server_metadata = self.dlg.server_combo.currentData(ServerComboData.JsonMetadata.value)
        lizmap_cloud = is_lizmap_cloud(server_metadata)
        beginner_mode = QgsSettings().value(Settings.key(Settings.BeginnerMode), True, bool)
        severities = Severities()

        self.dlg.check_results.truncate()
        checks = Checks()

        # Fill the HTML table with all rules
        self.dlg.html_help.setHtml(
            checks.html(
                severity=severities.blocking if beginner_mode else severities.important,
                lizmap_cloud=lizmap_cloud
            )
        )

        validator = QgsProjectServerValidator()
        valid, results = validator.validate(self.project)
        logger.info(f"Project has been detected : {'VALID' if valid else 'NOT valid'} according to OGC validation.")
        if not valid:
            self.dlg.check_results.add_error(
                Error(
                    Path(self.project.fileName()).name,
                    Checks().OgcValid,
                )
            )

        self.dlg.check_api_key_address()

        if with_gui:
            self.dlg.enable_all_fixer_buttons(False)

        duplicated_in_cfg = duplicated_layer_name_or_group(self.project)
        for name, count in duplicated_in_cfg.items():
            if count >= 2:
                source = '"{}" → "'.format(name) + tr("count {} layers").format(count)
                self.dlg.check_results.add_error(Error(source, checks.DuplicatedLayerNameOrGroup))

        # Layer ID as short name
        if lwc_version >= LwcVersions.Lizmap_3_6:
            use_layer_id, _ = self.project.readEntry('WMSUseLayerIDs', '/')
            if as_boolean(use_layer_id):
                self.dlg.check_results.add_error(Error(Path(self.project.fileName()).name, checks.WmsUseLayerIds))

        if lwc_version >= LwcVersions.Lizmap_3_7 and with_gui:
            # To remove soon, after a few versions of LWC 3.7
            json_meta = self.dlg.current_server_info(ServerComboData.JsonMetadata.value)
            impacted_versions = ('3.7.0', '3.7.1', '3.7.2', '3.7.3')
            crs_inverted = self.project.crs().hasAxisInverted()
            is_not_4326 = self.project.crs() != QgsCoordinateReferenceSystem('4326')
            if json_meta and crs_inverted and is_not_4326 and json_meta['info']['version'] in impacted_versions:
                # https://github.com/3liz/lizmap-web-client/issues/4191
                self.dlg.check_results.add_error(Error(Path(self.project.fileName()).name, checks.CrsInvertedAxis))

            results = duplicated_rule_key_legend(self.project)
            if results:
                self.dlg.log_panel.append(tr("Duplicated rule key in the legend"), Html.H2)
                self.dlg.log_panel.append("<br>")
                self.dlg.log_panel.start_table()
                self.dlg.log_panel.append(
                    "<tr><th>{}</th><th>{}</th><th>{}</th></tr>".format(tr('Layer'), tr('Key'), tr('Count'))
                )

                i = 0
                for layer_id, rules in results.items():
                    layer = self.project.mapLayer(layer_id)
                    # Add one error per layer is enough
                    self.dlg.check_results.add_error(
                        Error(
                            layer.name(),
                            checks.DuplicatedRuleKeyLegend,
                            source_type=SourceLayer(layer.name(), layer.id()),
                        )
                    )

                    # But explain inside each layer which keys are duplicated
                    for rule, count in rules.items():
                        self.dlg.log_panel.add_row(i)
                        self.dlg.log_panel.append(layer.name(), Html.Td)
                        self.dlg.log_panel.append(rule, Html.Td)
                        self.dlg.log_panel.append(count, Html.Td)
                        self.dlg.log_panel.end_row()
                        i += 1

                self.dlg.log_panel.end_table()

            results = duplicated_label_legend(self.project)
            if results:
                self.dlg.log_panel.append(tr("Duplicated labels in the legend"), Html.H2)
                self.dlg.log_panel.append("<br>")
                self.dlg.log_panel.append("<em>" + tr("A leading or a trailing spaces can be added.") + "</em>")
                self.dlg.log_panel.start_table()
                self.dlg.log_panel.append(
                    "<tr><th>{}</th><th>{}</th><th>{}</th></tr>".format(tr('Layer'), tr('Label'), tr('Count'))
                )

                i = 0
                for layer_id, rules in results.items():
                    layer = self.project.mapLayer(layer_id)
                    # Add one error per layer is enough
                    self.dlg.check_results.add_error(
                        Error(
                            layer.name(),
                            checks.DuplicatedRuleKeyLabelLegend,
                            source_type=SourceLayer(layer.name(), layer.id()),
                        )
                    )

                    # But explain inside each layer which keys are duplicated
                    for label, count in rules.items():
                        self.dlg.log_panel.add_row(i)
                        self.dlg.log_panel.append(layer.name(), Html.Td)
                        self.dlg.log_panel.append(label, Html.Td)
                        self.dlg.log_panel.append(count, Html.Td)
                        self.dlg.log_panel.end_row()
                        i += 1

                self.dlg.log_panel.end_table()

        if check_server:

            # Global safeguards in the QGIS profile
            prevent_ecw = QgsSettings().value(Settings.key(Settings.PreventEcw), True, bool)
            prevent_auth_id = QgsSettings().value(Settings.key(Settings.PreventPgAuthDb), True, bool)
            prevent_service = QgsSettings().value(Settings.key(Settings.PreventPgService), True, bool)
            force_pg_user_pass = QgsSettings().value(Settings.key(Settings.ForcePgUserPass), True, bool)
            prevent_other_drive = QgsSettings().value(Settings.key(Settings.PreventDrive), True, bool)
            allow_parent_folder = QgsSettings().value(Settings.key(Settings.AllowParentFolder), False, bool)
            count_parent_folder = QgsSettings().value(Settings.key(Settings.NumberParentFolder), 2, int)

            # Override safeguards by Lizmap Cloud
            lizmap_cloud = is_lizmap_cloud(server_metadata)
            if lizmap_cloud:
                prevent_ecw = True
                prevent_auth_id = True
                force_pg_user_pass = True
                prevent_other_drive = True
                if count_parent_folder > CLOUD_MAX_PARENT_FOLDER:
                    count_parent_folder = CLOUD_MAX_PARENT_FOLDER
                # prevent_service = False  We encourage service
                # allow_parent_folder = False Of course we can

            # Override safeguards by beginner mode
            if beginner_mode:
                prevent_ecw = True
                prevent_auth_id = True
                force_pg_user_pass = True
                prevent_other_drive = True
                count_parent_folder = 0
                prevent_service = True
                allow_parent_folder = False

            # List of safeguards are now defined
            summary = []
            if prevent_ecw:
                summary.append(PREVENT_ECW)
            if prevent_auth_id:
                summary.append(PREVENT_AUTH_DB)
            if prevent_service:
                summary.append(PREVENT_SERVICE)
            if force_pg_user_pass:
                summary.append(FORCE_PG_USER_PASS)
            if prevent_other_drive:
                summary.append(PREVENT_OTHER_DRIVE)
            if allow_parent_folder:
                summary.append(ALLOW_PARENT_FOLDER + " : " + tr("{} folder(s)").format(count_parent_folder))
            else:
                summary.append(FORCE_LOCAL_FOLDER)

            parent_folder = relative_path(count_parent_folder)

            results = project_safeguards_checks(
                self.project,
                prevent_ecw=prevent_ecw,
                prevent_auth_id=prevent_auth_id,
                prevent_service=prevent_service,
                force_pg_user_pass=force_pg_user_pass,
                prevent_other_drive=prevent_other_drive,
                allow_parent_folder=allow_parent_folder,
                parent_folder=parent_folder,
                lizmap_cloud=lizmap_cloud,
            )
            # Let's show a summary
            self.dlg.log_panel.append(tr("Safeguards"), Html.H2)
            if lizmap_cloud:
                self.dlg.log_panel.append(
                    tr("According to global settings, overridden then by {} :").format(CLOUD_NAME), Html.P)
            else:
                self.dlg.log_panel.append(tr("According to global settings"), Html.P)

            self.dlg.log_panel.start_table()
            for i, rule in enumerate(summary):
                self.dlg.log_panel.add_row(i)
                self.dlg.log_panel.append(rule, Html.Td)
                self.dlg.log_panel.end_row()
            self.dlg.log_panel.end_table()

            self.dlg.log_panel.append("<br>")

            # Severity depends on beginner mode
            severity = severities.blocking if beginner_mode else severities.important
            # But override severities for Lizmap Cloud
            # Because even with a 'normal' user, it won't work
            override = (
                checks.PreventEcw.data,
                checks.PgForceUserPass.data,
                checks.AuthenticationDb.data,
                checks.PreventDrive.data,
            )

            for layer, error in results.items():
                error: Check

                if error.data in override:
                    severity = severities.blocking

                self.dlg.check_results.add_error(
                    Error(
                        layer.name,
                        error,
                        source_type=SourceLayer(layer.name, layer.layer_id),
                    ),
                    lizmap_cloud=lizmap_cloud,
                    severity=severity,
                )

            if results:
                if beginner_mode:
                    self.dlg.log_panel.append(tr(
                        "The process is stopping, the Lizmap configuration file is not going to be generated because "
                        "some safeguards are not compatible and you are using the 'Beginner' mode. Either fix these "
                        "issues or switch to a 'Normal' mode if you know what you are doing."
                    ), Html.P, level=Qgis.MessageLevel.Critical)
                else:
                    self.dlg.log_panel.append(tr(
                        "The process is continuing but these layers might be invisible if the server is not well "
                        "configured or if the project is not correctly uploaded to the server."
                    ), Html.P)

        if check_server:

            if lizmap_cloud:
                error, _message = check_project_ssl_postgis(self.project)
                for layer in error:
                    self.dlg.check_results.add_error(
                        Error(
                            layer.name,
                            checks.SSLConnection,
                            source_type=SourceLayer(layer.name, layer.layer_id),
                        )
                    )
                    self.dlg.enabled_ssl_button(True)

            autogenerated_keys, not_int4 = project_invalid_pk(self.project)
            for layer in autogenerated_keys:
                self.dlg.check_results.add_error(
                    Error(
                        layer.name,
                        checks.MissingPk,
                        source_type=SourceLayer(layer.name, layer.layer_id),
                    )
                )
            for layer in not_int4:
                self.dlg.check_results.add_error(
                    Error(
                        layer.name,
                        checks.NotInt4Pk,
                        source_type=SourceLayer(layer.name, layer.layer_id),
                    )
                )

            results = trailing_layer_group_name(self.project.layerTreeRoot(), self.project, [])
            for result in results:
                self.dlg.check_results.add_error(result)

            # TOS checks from the server
            # These checks are only done if we find the server configuration below, starting with version 2.9.4
            tos_checks = server_metadata.get("qgis_server_info").get("external_providers_tos_checks")
            if tos_checks is not None:
                # Server configuration, if set to True, it means an API key is required, the default behavior
                google = tos_checks.get('google', False)
                bing = tos_checks.get('bing', False)

                # If an API key is provided, we do not report these layers
                if self.dlg.inGoogleKey.text() != '':
                    google = False

                if self.dlg.inBingKey.text() != '':
                    bing = False

                if google or bing:
                    for layer in project_tos_layers(self.project, google, bing):
                        self.dlg.check_results.add_error(
                            Error(
                                layer.name,
                                checks.LayerMissingApiKey,
                                source_type=SourceLayer(layer.name, layer.layer_id),
                            ),
                            lizmap_cloud=lizmap_cloud,
                        )

            # if lwc_version >= LwcVersions.Lizmap_3_7:
            #     # Temporary disabled, I think there are some valid use cases for this for now.
            #     results = duplicated_layer_with_filter_legend(self.project)
            #     if results:
            #         self.dlg.log_panel.append(checks.DuplicatedLayerFilterLegend.title, Html.H2)
            #         self.dlg.log_panel.start_table()
            #         self.dlg.log_panel.append(
            #             "<tr><th>{}</th><th>{}</th><th>{}</th></tr>".format(
            #                 tr('Datasource'), tr('Filters'), tr('Layers'))
            #         )
            #         for i, result in enumerate(results):
            #             for uri, filters in result.items():
            #                 self.dlg.log_panel.add_row(i)
            #                 self.dlg.log_panel.append(uri, Html.Td)
            #
            #                 # Icon
            #                 for k, v in filters.items():
            #                     if k == "_wkb_type":
            #                         icon = QgsIconUtils.iconForWkbType(v)
            #                         break
            #                 else:
            #                     icon = QIcon(':/images/themes/default/algorithms/mAlgorithmMergeLayers.svg')
            #
            #                 del filters["_wkb_type"]
            #
            #                 uri_filter = '<ul>' + ''.join([f"<li>{k}</li>" for k in filters.keys()]) + '</ul>'
            #                 self.dlg.log_panel.append(uri_filter, Html.Td)
            #
            #                 layer_names = '<ul>' + ''.join([f"<li>{k}</li>" for k in filters.values()]) + '</ul>'
            #                 self.dlg.log_panel.append(layer_names, Html.Td)
            #
            #                 self.dlg.log_panel.end_row()
            #
            #                 self.dlg.check_results.add_error(
            #                     Error(
            #                         uri,
            #                         checks.DuplicatedLayerFilterLegend,
            #                     ),
            #                     icon=icon,
            #                 )
            #
            #         self.dlg.log_panel.end_table()
            #
            #         self.dlg.log_panel.append(tr(
            #             'Checkboxes are supported natively in the legend. Using filters for the same '
            #             'datasource are highly discouraged.'
            #         ), style=Html.P)

        results = simplify_provider_side(self.project)
        for layer in results:
            self.dlg.check_results.add_error(
                Error(
                    layer.name,
                    checks.SimplifyGeometry,
                    source_type=SourceLayer(layer.name, layer.layer_id),
                )
            )
            self.dlg.enabled_simplify_geom(True)

        data = {}
        for key in self.layers_table:
            manager: TableManager = self.layers_table[key].get('manager')
            if manager:
                for layer_id, fields in manager.wfs_fields_used().items():
                    if layer_id not in data:
                        data[layer_id] = []
                    for f in fields:
                        if f not in data[layer_id]:
                            data[layer_id].append(f)

        for layer_id, fields in data.items():
            layer = self.project.mapLayer(layer_id)
            if not layer:
                # Fixme, the layer has been removed from QGIS Desktop, but was still in the CFG file.
                # :func:clean_project()
                continue

            if not is_layer_published_wfs(self.project, layer.id()):
                self.dlg.check_results.add_error(
                    Error(
                        layer.name(),
                        checks.MissingWfsLayer,
                        source_type=SourceLayer(layer.name(), layer.id()),
                    )
                )

            for field in fields:
                if field in layer.excludeAttributesWfs():
                    self.dlg.check_results.add_error(
                        Error(
                            field,
                            checks.MissingWfsField,
                            source_type=SourceField(field, layer.id()),
                        )
                    )

        results = use_estimated_metadata(self.project)
        for layer in results:
            self.dlg.check_results.add_error(
                Error(
                    layer.name,
                    checks.EstimatedMetadata,
                    source_type=SourceLayer(layer.name, layer.layer_id),
                )
            )
            self.dlg.enabled_estimated_md_button(True)

        if not self.dlg.mOptionsListWidget.item(Panels.Training).isHidden():
            # Make the life easier a little bit for short workshops.
            project_trust_layer_metadata(self.project, True)
        elif not project_trust_layer_metadata(self.project):
            self.dlg.check_results.add_error(Error(Path(self.project.fileName()).name, checks.TrustProject))
            self.dlg.enabled_trust_project(True)

        if empty_baselayers(self.project):
            self.dlg.check_results.add_error(
                Error(Path(self.project.fileName()).name, checks.EmptyBaseLayersGroup)
            )

        if self.dlg.check_qgis_version(message_bar=True):
            self.dlg.check_results.add_error(Error(tr('Global'), checks.ServerVersion))

        if server_metadata:
            min_required_version = server_metadata.get('lizmap_desktop_plugin_version')
            if min_required_version:
                current_version = version()
                if current_version in DEV_VERSION_PREFIX:
                    current_version = next_git_tag()
                min_required_version = qgis_version_info(min_required_version, increase_odd_number=False)
                min_required_version = '.'.join([str(i) for i in min_required_version])
                if compareVersions(current_version, min_required_version) == 2:
                    self.dlg.check_results.add_error(Error(tr('Global'), checks.PluginDesktopVersion))

        # Not blocking, we change it in the background
        if self.project.readNumEntry("WMSMaxAtlasFeatures", '')[0] <= 0:
            logger.info("The maximum atlas features was less than '1'. We set it to '1' to at least have a value.")
            self.project.writeEntry("WMSMaxAtlasFeatures", "/", 1)

        self.dlg.check_results.sort()

        if with_gui and self.dlg.check_results.has_rows():
            self.dlg.mOptionsListWidget.setCurrentRow(Panels.Checks)
            self.dlg.tab_log.setCurrentIndex(0)
            self.dlg.out_log.moveCursor(QTextCursor.MoveOperation.Start)
            self.dlg.out_log.ensureCursorVisible()

        beginner_mode = QgsSettings().value(Settings.key(Settings.BeginnerMode), True, bool)
        mode = tr('beginner') if beginner_mode else tr('normal')
        if self.dlg.check_results.has_blocking():
            msg = tr(
                'You are using the "{mode}" mode and you have some <strong>blocking</strong> checks.').format(mode=mode)
        else:
            msg = tr('You are using the "{mode}" mode.').format(mode=mode)
        self.dlg.label_check_resume.setText(msg)

        self.dlg.auto_fix_tooltip(lizmap_cloud)
        self.dlg.label_autofix.setVisible(self.dlg.has_auto_fix())
        self.dlg.push_visit_settings.setVisible(self.dlg.has_auto_fix())

        if self.dlg.check_results.has_blocking() and not ignore_error:
            self.dlg.display_message_bar(
                tr("Blocking issue"),
                tr("The project has at least one blocking issue. The file is not saved."),
                Qgis.MessageLevel.Critical,
            )

            return False

        important_issues = self.dlg.check_results.has_importants()
        if important_issues >= 1 and lizmap_cloud:
            base_name = self.project.baseName()
            dialog = ConfirmationTextMessageBox(important_issues, f"{base_name}:{important_issues}")
            result = dialog.exec()
            self.dlg.log_panel.append(tr(
                "{count} error(s) have been found on the project, user has agreed with these errors : {result}"
            ).format(count=important_issues, result="<strong>" + tr("Yes") + "<strong>" if result else tr("No")), Html.P)
            if not result:
                return False

        return True

    def check_project_clicked(self):
        """ Launch the check on the current project. """
        lwc_version = self.lwc_version
        # Let's trigger UI refresh according to latest releases, if it wasn't available on startup
        self.lwc_version_changed()
        with OverrideCursor(Qt.CursorShape.WaitCursor):
            self.check_project(lwc_version)

    def clean_project(self):
        """Clean a little the QGIS project.

        Mainly ghost layers for now.
        """
        layers = remove_all_ghost_layers()
        if layers:
            message = tr(
                'Lizmap has found these layers which are ghost layers: {}. '
                'They have been removed. You must save your project.').format(', '.join(layers))
            # noinspection PyUnresolvedReferences
            self.iface.messageBar().pushMessage('Lizmap', message, level=Qgis.MessageLevel.Warning, duration=DURATION_WARNING_BAR)

    def check_global_project_options(self) -> Tuple[bool, str]:
        """Checks that the needed options are correctly set : relative path, project saved, etc.

        :return: Flag if the project is valid and an error message.
        :rtype: bool, basestring
        """
        base_message = "<br>" + tr("This is needed before using other tabs in the plugin.")
        message = tr('You need to open a QGIS project, using the QGS extension.')
        if not self.project.fileName():
            return False, message + base_message

        if not self.project.fileName().lower().endswith('qgs'):
            message += "\n\n" + tr(
                "Your extension is QGZ. Please save again the project using the other extension.")
            return False, message + base_message

        if self.project.baseName() != unaccent(self.project.baseName()):
            message = tr(
                "Your file name has some accents in its name. The project file name mustn't have accents in its name.")
            return False, message + base_message

        message = tr(
            "You mustn't open the QGS file located in your local webdav directory. Please open a local copy of the "
            "project.")
        # Windows
        network_dav = []
        for i in QStorageInfo.mountedVolumes():
            # Mapping table between 'Z:/' and
            # \\demo.snap.lizmap.com@SSL\DavWWWRoot\lizmap_3_6\dav.php\
            if 'dav.php' in i.device().data().decode():
                network_dav.append(i.rootPath())
        if self.project.fileName().startswith(tuple(network_dav)):
            return False, message + base_message

        # Linux : /run/user/1000/gvfs/dav:host=...,ssl=true,....,prefix=%2Flizmap_3_6%2Fdav.php/...tests_projects/..qgs
        if 'dav.php' in self.project.fileName():
            return False, message + base_message

        # Check if Qgis/capitaliseLayerName is set
        settings = QgsSettings()
        if settings.value('Qgis/capitaliseLayerName') and settings.value('Qgis/capitaliseLayerName', type=bool):
            message = tr(
                'Please deactivate the option "Capitalize layer names" in the tab "Canvas and legend" '
                'in the QGIS option dialog, as it could cause issues with Lizmap.')
            return False, message + base_message

        # Check relative/absolute path
        if ambiguous_to_bool(self.project.readEntry('Paths', 'Absolute')[0]):
            message = tr(
                'The project layer paths must be set to relative. '
                'Please change this options in the project settings.')
            return False, message + base_message

        # check if a title has been given in the project QGIS Server tab configuration
        # first set the WMSServiceCapabilities to true
        if not self.project.readEntry('WMSServiceCapabilities', '/')[1]:
            self.project.writeEntry('WMSServiceCapabilities', '/', str(True))
        if self.project.readEntry('WMSServiceTitle', '')[0] == '':
            self.project.writeEntry('WMSServiceTitle', '', self.project.baseName())

        # check if a bbox has been given in the project QGIS Server tab configuration
        project_wms_extent, _ = self.project.readListEntry('WMSExtent', '')
        full_extent = self.iface.mapCanvas().extent()
        if not project_wms_extent:
            project_wms_extent.append(str(full_extent.xMinimum()))
            project_wms_extent.append(str(full_extent.yMinimum()))
            project_wms_extent.append(str(full_extent.xMaximum()))
            project_wms_extent.append(str(full_extent.yMaximum()))
            self.project.writeEntry('WMSExtent', '', project_wms_extent)
        else:
            if not project_wms_extent[0] or not project_wms_extent[1] or not \
                    project_wms_extent[2] or not project_wms_extent[3]:
                project_wms_extent[0] = str(full_extent.xMinimum())
                project_wms_extent[1] = str(full_extent.yMinimum())
                project_wms_extent[2] = str(full_extent.xMaximum())
                project_wms_extent[3] = str(full_extent.yMaximum())
                self.project.writeEntry('WMSExtent', '', project_wms_extent)

        return True, ''
