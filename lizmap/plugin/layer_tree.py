"""Layer tree panel configuration"""
import contextlib
import hashlib
import json
import os

from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Union,
)

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsLayerTree,
    QgsLayerTreeGroup,
    QgsLayerTreeNode,
    QgsMapLayer,
    QgsMapLayerModel,
    QgsProject,
    QgsRasterLayer,
    QgsSettings,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QMessageBox,
    QTreeWidgetItem,
)

from ..definitions.definitions import (
    DURATION_WARNING_BAR,
    GroupNames,
    Html,
    LayerProperties,
    LwcVersions,
    PredefinedGroup,
)
from ..definitions.online_help import Panels
from ..dialogs.main import LizmapDialog
from ..toolbelt.convert import ambiguous_to_bool, as_boolean, cast_to_group, cast_to_layer
from ..toolbelt.i18n import tr
from ..toolbelt.layer import (
    get_layer_wms_parameters,
    layer_property,
    set_layer_property,
)
from ..widgets.project_tools import (
    is_layer_wms_excluded,
)

if TYPE_CHECKING:
    from qgis.gui import QgisInterface

    from ..dialogs.main import LizmapDialog

from .. import logger
from ..config import layerOptionDefinitions
from .helpers import display_error, string_to_list
from .lwc_versions import LwcVersionManager


class LayerTreeManager:

    def __init__(
        self,
        *,
        dlg: "LizmapDialog",
        project: QgsProject,
        is_dev_version: bool,
        lwc_version_mngr: LwcVersionManager,
        iface: "QgisInterface",
    ):
        self.dlg = dlg
        self.project = project
        self.is_dev_version = is_dev_version
        self.lwc_version_mngr = lwc_version_mngr
        self.layerList = {}
        self.layer_options_list = layerOptionDefinitions
        self.iface = iface

    @property
    def lwc_version(self) -> LwcVersions:
        return self.lwc_version_mngr.lwc_version

    def layers_config_file(self) -> Dict:
        """ Read the CFG file and returns the JSON content about 'layers'. """
        if not self.dlg.check_cfg_file_exists():
            return {}

        with open(self.dlg.cfg_file(), encoding='utf8') as f:
            json_file_reader = f.read()

        try:
            sjson = json.loads(json_file_reader)
            return sjson['layers']
        except Exception:
            if self.is_dev_version:
                raise
            message = tr(
                'Errors encountered while reading the last layer tree state. '
                'Please re-configure the options in the Layers tab completely'
            )
            QMessageBox.critical(self.dlg, tr('Lizmap Error'), '', QMessageBox.StandardButton.Ok)
            self.dlg.log_panel.append(message, abort=True, style=Html.P)
            return {}

    # Called by LizmapDialog.__init__
    def initialize(self):
        # Disable checkboxes on the layer tab
        self.enable_check_box_in_layer_tab(False)

        # Catch user interaction on layer tree and inputs
        self.dlg.layer_tree.itemSelectionChanged.connect(self.from_data_to_ui_for_layer_group)
        self.dlg.layer_tree.itemExpanded.connect(self._on_layer_tree_group_state_changed)
        self.dlg.layer_tree.itemCollapsed.connect(self._on_layer_tree_group_state_changed)
        self.dlg.layer_search_input.textChanged.connect(self._on_layer_search_changed)

        # Group helper
        self.dlg.add_group_hidden.setToolTip(tr(
            'Add a group which will be hidden by default on Lizmap Web '
            'Client. Some tables might be needed in the '
            'QGIS projet but not needed for display on the map and in the legend.'
        ))
        self.dlg.add_group_baselayers.setToolTip(tr(
            'Add a group called "baselayers", you can organize your layers inside, '
            'it will be displayed in a dropdown menu.'
        ))
        self.dlg.add_group_empty.setToolTip(tr(
            'Add a group which must stay empty. It will add an option in the base '
            'layer dropdown menu and allow the default background color defined '
            'in the project properties to be displayed.'
        ))
        self.dlg.add_group_overview.setToolTip(tr(
            'Add some layers in this group to make an overview map at a lower scale.'
        ))
        self.dlg.add_group_hidden.clicked.connect(self.add_group_hidden)
        self.dlg.add_group_baselayers.clicked.connect(self.add_group_baselayers)
        self.dlg.add_group_empty.clicked.connect(self.add_group_empty)
        self.dlg.add_group_overview.clicked.connect(self.add_group_overview)

    # Called by LizmapDialog.initGui()
    def init_gui(self):
        self.project.layersAdded.connect(self.new_added_layers)
        self.project.layerTreeRoot().nameChanged.connect(self.layer_renamed)

    def new_added_layers(self, layers: List[QgsMapLayer]):
        """ Reminder to open the plugin to update the CFG file. """
        if not self.dlg.check_cfg_file_exists():
            # Not a Lizmap project
            return

        # Get layer IDs already in the CFG file
        layer_ids = [f['id'] for f in self.layers_config_file().values()]
        names = []
        for layer in layers:
            if layer.id() not in layer_ids:
                names.append(layer.name())

        if len(names) <= 0:
            # The new loaded layer was in the CFG already
            # It happens when we load the project
            return

        if len(names) >= 2:
            msg = tr("Some new layers have been detected into this Lizmap project.")
            prefix = tr("Layers")
        else:
            msg = tr("A new layer has been detected into this Lizmap project.")
            prefix = tr("Layer")

        logger.info("New layer(s) detected : {}".format(','.join(names)))
        msg += ' ' + tr("Please open the plugin to update the Lizmap configuration file.") + ' '
        msg += prefix + ' : '
        msg += ','.join(names)
        self.iface.messageBar().pushMessage('Lizmap', msg, level=Qgis.MessageLevel.Warning, duration=DURATION_WARNING_BAR)

    def layer_renamed(self, _, name: str):
        """ When a layer/group is renamed in the legend. """
        if not self.dlg.check_cfg_file_exists():
            # Not a Lizmap project
            return

        # Temporary workaround for
        # https://github.com/3liz/lizmap-plugin/issues/498
        msg = tr(
            f"The layer '{name}' has been renamed. "
            "The configuration in the Lizmap <b>Layers</b> tab only must be checked."
        )
        self.iface.messageBar().pushMessage(
            'Lizmap',
            msg,
            level=Qgis.MessageLevel.Warning,
            duration=DURATION_WARNING_BAR,
        )

    def populate_layer_tree(self) -> Dict:
        """Populate the layer tree of the Layers tab from QGIS legend interface.

        Needs to be refactored.
        """
        self.dlg.layer_tree.clear()
        self.layerList = {}
        myDic = {}

        json_layers = self.layers_config_file()
        root = self.project.layerTreeRoot()

        # Recursively process layer tree nodes
        self.dlg._ignore_layer_tree_state = True
        try:
            self.process_node(myDic, root, None, json_layers)
            self.dlg.layer_tree.expandAll()          # default: all expanded
            self._restore_layer_tree_group_states()  # override with saved states (if any)
        finally:
            self.dlg._ignore_layer_tree_state = False

        # Add the myDic to the global layerList dictionary
        self.layerList = myDic

        self.enable_check_box_in_layer_tab(False)

        # The return is used in tests
        return json_layers

    def set_tree_item_data(self, myDic: Dict, item_type: str, item_key: str, json_layers: Dict):
        """Define default data or data from previous configuration for one item (layer or group)
        Used in the method populateLayerTree
        """
        # Type : group or layer
        myDic[item_key]['type'] = item_type

        # DEFAULT VALUES : generic default values for layers and group
        myDic[item_key]['name'] = item_key
        for key, item in self.layer_options_list.items():
            myDic[item_key][key] = item['default']
        myDic[item_key]['title'] = myDic[item_key]['name']

        # DEFAULT VALUES : layers have got more precise data
        keep_metadata = False
        if item_type == 'layer':
            layer = self.get_qgis_layer_by_id(item_key)
            # layer corrupted ?
            if not layer:
                error_msg = tr(
                    "The layer '{}' seems invalid. Check the layer configuration."
                ).format(item_key)
                display_error(self.dlg, error_msg)
                return

            # layer name
            myDic[item_key]['name'] = layer.name()
            # title and abstract
            myDic[item_key]['title'] = layer.name()
            if layer_property(layer, LayerProperties.Title):
                myDic[item_key]['title'] = layer_property(layer, LayerProperties.Title)
                keep_metadata = True
            if layer_property(layer, LayerProperties.Abstract):
                myDic[item_key]['abstract'] = layer_property(layer, LayerProperties.Abstract)
                keep_metadata = True

            if not myDic[item_key]['link']:
                myDic[item_key]['link'] = layer_property(layer, LayerProperties.DataUrl)

            # hide non geo layers (csv, etc.)
            # if layer.type() == 0:
            #    if layer.geometryType() == 4:
            #        self.l display = False

            # layer scale visibility
            if layer.hasScaleBasedVisibility():
                myDic[item_key]['minScale'] = layer.maximumScale()
                myDic[item_key]['maxScale'] = layer.minimumScale()
            # toggled : check if layer is toggled in qgis legend
            # myDic[itemKey]['toggled'] = layer.self.iface.legendInterface().isLayerVisible(layer)
            myDic[item_key]['toggled'] = False
            # group as layer : always False obviously because it is already a layer
            myDic[item_key]['groupAsLayer'] = False
            # embedded layer ?
            from_project = self.project.layerIsEmbedded(item_key)
            if os.path.exists(from_project):
                p_name = os.path.splitext(os.path.basename(from_project))[0]
                myDic[item_key]['sourceProject'] = p_name

        # OVERRIDE DEFAULT FROM CONFIGURATION FILE
        if myDic[item_key]['name'] in json_layers:
            json_key = myDic[item_key]['name']
            logger.info('Reading configuration from dictionary for layer {}'.format(json_key))
            # loop through layer options to override
            for key, item in self.layer_options_list.items():
                # override only for ui widgets
                if item.get('widget'):
                    if key in json_layers[json_key]:

                        if key == 'legend_image_option' and 'noLegendImage' in json_layers[json_key]:
                            if myDic[item_key].get('legend_image_option'):
                                # The key is already set before with noLegendImage
                                logger.info(
                                    "Skip key legend_image_option because it has been set previously with noLegendImage"
                                )
                                continue

                        # checkboxes
                        if item['wType'] in ('checkbox', 'radio'):
                            myDic[item_key][key] = as_boolean(json_layers[json_key][key])
                        # spin box
                        elif item['wType'] == 'spinbox':
                            if json_layers[json_key][key] != '':
                                myDic[item_key][key] = json_layers[json_key][key]
                        # text inputs
                        elif item['wType'] in ('text', 'textarea'):
                            if json_layers[json_key][key] != '':
                                if item.get('isMetadata'):  # title and abstract
                                    if not keep_metadata:
                                        myDic[item_key][key] = json_layers[json_key][key]
                                else:
                                    myDic[item_key][key] = json_layers[json_key][key]
                        # lists
                        elif item['wType'] == 'list':
                            # New way with data, label, tooltip and icon
                            datas = [j[0] for j in item['list']]
                            if json_layers[json_key][key] in datas:
                                myDic[item_key][key] = json_layers[json_key][key]

                else:
                    if key == 'noLegendImage' and 'noLegendImage' in json_layers.get(json_key):
                        tmp = 'hide_at_startup'  # Default value
                        if ambiguous_to_bool(json_layers[json_key].get('noLegendImage')):
                            tmp = 'disabled'
                        myDic[item_key]['legend_image_option'] = tmp

                    # logger.info('Skip key {} because no UI widget'.format(key))

                # popupContent
                if key == 'popupTemplate':
                    if key in json_layers[json_key]:
                        myDic[item_key][key] = json_layers[json_key][key]

    def process_node(
        self,
        myDic: Dict,
        node: QgsLayerTreeNode,
        parent_node: Optional[QTreeWidgetItem],
        json_layers: Dict,
    ):
        """
        Process a single node of the QGIS layer tree and adds it to Lizmap layer tree.

        Recursive function when it's a group in the legend.
        """
        for child in node.children():
            if QgsLayerTree.isGroup(child):
                child = cast_to_group(child)
                child_id = child.name()
                child_type = 'group'
                # noinspection PyCallByClass,PyArgumentList
                child_icon = QIcon(QgsApplication.iconPath('mActionFolder.svg'))
            elif QgsLayerTree.isLayer(child):
                child = cast_to_layer(child)
                child_id = child.layerId()
                child_type = 'layer'
                # noinspection PyArgumentList
                child_icon = QgsMapLayerModel.iconForLayer(child.layer())
            else:
                raise Exception('Unknown child type')

            # Select an existing item, select the header item or create the item
            if child_id in myDic:
                # If the item already exists in myDic, select it
                item = myDic[child_id]['item']

            elif child_id == '':
                # If the id is empty string, this is a root layer, select the headerItem
                item = self.dlg.layer_tree.headerItem()

            else:
                # else create the item and add it to the header item
                # add the item to the dictionary
                myDic[child_id] = {'id': child_id}
                if child_type == 'group':
                    # it is a group
                    self.set_tree_item_data(myDic, 'group', child_id, json_layers)
                else:
                    # it is a layer
                    self.set_tree_item_data(myDic, 'layer', child_id, json_layers)

                predefined_group = PredefinedGroup.No.value
                if parent_node is None:
                    if myDic[child_id]['name'] == 'hidden':
                        predefined_group = PredefinedGroup.Hidden.value
                    if myDic[child_id]['name'] == 'baselayers':
                        predefined_group = PredefinedGroup.Baselayers.value
                    if myDic[child_id]['name'].lower() == 'overview':
                        predefined_group = PredefinedGroup.Overview.value

                elif parent_node.data(0, Qt.ItemDataRole.UserRole + 1) == PredefinedGroup.Baselayers.value:
                    # Parent is "baselayers", children will be an item in the dropdown menu
                    predefined_group = PredefinedGroup.BaselayerItem.value
                elif parent_node.data(0, Qt.ItemDataRole.UserRole + 1) != PredefinedGroup.No.value:
                    # Others will be in "hidden" or "overview".
                    # TODO fixme maybe ?
                    predefined_group = PredefinedGroup.Hidden.value

                item = QTreeWidgetItem(
                    [
                        str(myDic[child_id]['name']),
                        str(myDic[child_id]['id']),
                        myDic[child_id]['type']
                    ]
                )
                if predefined_group != PredefinedGroup.No.value:
                    text = tr('Special group for Lizmap Web Client')
                    if self.is_dev_version:
                        # For debug purpose only about groups
                        text += f'. Data group ID {Qt.ItemDataRole.UserRole} : {predefined_group}'
                    item.setToolTip(0, myDic[child_id]['name'] + ' - ' + text)
                elif is_layer_wms_excluded(self.project, myDic[child_id]['name']):
                    text = tr(
                        'The layer is excluded from WMS service, in the '
                        '"Project Properties" → "QGIS Server" → "WMS" → "Excluded Layers"'
                    )
                    item.setToolTip(0, myDic[child_id]['name'] + ' - ' + text)
                else:
                    item.setToolTip(0, myDic[child_id]['name'])
                item.setIcon(0, child_icon)
                item.setData(0, Qt.ItemDataRole.UserRole + 1, predefined_group)
                myDic[child_id]['item'] = item

                # Move group or layer to its parent node
                if not parent_node:
                    self.dlg.layer_tree.addTopLevelItem(item)
                else:
                    parent_node.addChild(item)

            if child_type == 'group':
                self.process_node(myDic, child, item, json_layers)

    def from_data_to_ui_for_layer_group(self):
        """ Restore layer/group values into each field when selecting a layer in the tree. """
        # At the beginning, enable all widgets.
        self.dlg.panel_layer_all_settings.setEnabled(True)
        self.dlg.group_layer_metadata.setEnabled(True)
        self.dlg.group_layer_tree_options.setEnabled(True)
        self.dlg.checkbox_popup.setEnabled(True)
        self.dlg.frame_layer_popup.setEnabled(True)
        self.dlg.group_layer_embedded.setEnabled(True)
        # for key, val in self.layer_options_list.items():
        #     if val.get('widget'):
        #         val.get('widget').setEnabled(True)

        i_key = self._current_selected_item_in_config()
        if i_key:
            self.enable_check_box_in_layer_tab(True)
        else:
            self.enable_check_box_in_layer_tab(False)

        # i_key can be either a layer name or a group name
        if i_key:
            # get information about the layer or the group from the layerList dictionary
            selected_item = self.layerList[i_key]

            # set options
            for key, val in self.layer_options_list.items():
                if val.get('widget'):

                    if val.get('tooltip'):
                        val['widget'].setToolTip(val.get('tooltip'))

                    if val['wType'] in ('text', 'textarea'):
                        if val['type'] == 'list':
                            data = selected_item[key]
                            if isinstance(data, str):
                                # It should be a list, but it has been temporary a string during the dev process
                                data = [data]
                            text = ','.join(data)
                        else:
                            text = selected_item[key]
                        if val['wType'] == 'text':
                            val['widget'].setText(text)
                        else:
                            # Abstract is the only textarea
                            val['widget'].setPlainText(text)
                    elif val['wType'] == 'spinbox':
                        val['widget'].setValue(int(selected_item[key]))
                    elif val['wType'] in ('checkbox', 'radio'):
                        val['widget'].setChecked(selected_item[key])
                        children = val.get('children')
                        if children:
                            exclusive = val.get('exclusive', False)
                            if exclusive:
                                is_enabled = not selected_item[key]
                            else:
                                is_enabled = selected_item[key]
                            self.layer_options_list[children]['widget'].setEnabled(is_enabled)
                            if self.layer_options_list[children]['wType'] == 'checkbox' and not is_enabled:
                                if self.layer_options_list[children]['widget'].isChecked():
                                    self.layer_options_list[children]['widget'].setChecked(False)

                    elif val['wType'] == 'list':
                        # New way with data, label, tooltip and icon
                        index = val['widget'].findData(selected_item[key])

                        if index < 0 and val.get('default'):
                            # Get back to default
                            index = val['widget'].findData(val['default'])

                        val['widget'].setCurrentIndex(index)

                    # deactivate wms checkbox if not needed
                    if key == 'externalWmsToggle':
                        wms_enabled = self.get_item_wms_capability(selected_item)
                        logger.debug(
                            f"Selected layer '{selected_item}' return value for WMS capability is '{wms_enabled}'")
                        if wms_enabled is not None:
                            self.dlg.cbExternalWms.setEnabled(wms_enabled)
                            if wms_enabled:
                                self.dlg.cbExternalWms.toggled.connect(self.external_wms_toggled)
                                self.external_wms_toggled()
                            else:
                                self.dlg.cbExternalWms.setChecked(False)
                                with contextlib.suppress(TypeError):
                                    # Raise TypeError if the object was not connected
                                    self.dlg.cbExternalWms.toggled.disconnect(self.external_wms_toggled)

            layer = self._current_selected_layer()  # It can be a layer or a group

            # Disable popup configuration for groups and raster
            # Disable QGIS popup for layer without geom
            is_vector = isinstance(layer, QgsVectorLayer)
            # is_raster = isinstance(layer, QgsRasterLayer)
            # noinspection PyUnresolvedReferences
            has_geom = is_vector and layer.wkbType() != QgsWkbTypes.Type.NoGeometry
            self.dlg.btConfigurePopup.setEnabled(has_geom)
            self.dlg.btQgisPopupFromForm.setEnabled(is_vector)
            self.dlg.button_generate_html_table.setEnabled(is_vector)
            self.layer_options_list['popupSource']['widget'].setEnabled(is_vector)

            if self.lwc_version >= LwcVersions.Lizmap_3_7 and not self.dlg.cbLayerIsBaseLayer.isChecked():
                # Starting from LWC 3.7, this checkbox is deprecated
                self.dlg.cbLayerIsBaseLayer.setEnabled(False)

            # For a group, there isn't the toggle option, #298, TEMPORARY DISABLED
            tooltip = tr(
                "If the layer is displayed by default. On a layer, if the map theme is used, this checkbox does not "
                "have any effect.")
            self.layer_options_list['toggled']['widget'].setToolTip(tooltip)
            # try:
            #     # We always disconnect everything
            #     self.layer_options_list['groupAsLayer']['widget'].disconnect()
            # except TypeError:
            #     pass
            #
            # if isinstance(layer, QgsMapLayer):
            #     # Always enabled
            #     self.layer_options_list['toggled']['widget'].setEnabled(True)
            #     tooltip = tr("If the layer is displayed by default")
            #     self.layer_options_list['toggled']['widget'].setToolTip(tooltip)
            # else:
            #     # It depends on the "Group as layer" checked or not, so it has a signal
            #     self.layer_options_list['groupAsLayer']['widget'].stateChanged.connect(
            #         self.enable_or_not_toggle_checkbox)
            #     self.enable_or_not_toggle_checkbox()

            # Checkbox display children features
            self.dlg.relation_stacked_widget.setCurrentWidget(self.dlg.page_no_relation)
            if is_vector:
                if len(self.project.relationManager().referencedRelations(layer)) >= 1:
                    # We display options
                    self.dlg.relation_stacked_widget.setCurrentWidget(self.dlg.page_display_relation)

        else:
            # set default values for this layer/group
            for key, val in self.layer_options_list.items():
                if val.get('widget'):
                    if val['wType'] in ('text', 'textarea'):
                        if isinstance(val['default'], (list, tuple)):
                            text = ','.join(val['default'])
                        else:
                            text = val['default']
                        if val['wType'] == 'text':
                            val['widget'].setText(text)
                        else:
                            # Abstract is the only textarea for now
                            # We shouldn't have any default value, but let's support it
                            val['widget'].setPlainText(text)
                    elif val['wType'] == 'spinbox':
                        val['widget'].setValue(val['default'])
                    elif val['wType'] in ('checkbox', 'radio'):
                        val['widget'].setChecked(val['default'])
                    elif val['wType'] == 'list':

                        # New way with data, label, tooltip and icon
                        index = val['widget'].findData(val['default'])
                        val['widget'].setCurrentIndex(index)

        self.enable_popup_source_button()
        self.dlg.follow_map_theme_toggled()

        if self.lwc_version >= LwcVersions.Lizmap_3_7:
            if self._current_item_predefined_group() == PredefinedGroup.BaselayerItem.value:
                self.dlg.group_layer_tree_options.setEnabled(False)
                self.dlg.checkbox_popup.setEnabled(False)
                self.dlg.frame_layer_popup.setEnabled(False)

            elif self._current_item_predefined_group() in (
                    PredefinedGroup.Overview.value,
                    PredefinedGroup.Baselayers.value,
                    PredefinedGroup.BackgroundColor.value,
                    PredefinedGroup.Hidden.value,
            ):
                self.dlg.panel_layer_all_settings.setEnabled(False)

        layer = self._current_selected_layer()
        if isinstance(layer, QgsMapLayer):
            if is_layer_wms_excluded(self.project, layer.name()):
                self.dlg.panel_layer_all_settings.setEnabled(False)

            if isinstance(layer, QgsVectorLayer):
                if not layer.isSpatial():
                    self.layer_options_list['toggled']['widget'].setEnabled(False)

    def enable_check_box_in_layer_tab(self, value: bool):
        """Enable/Disable checkboxes and fields of the Layer tab."""
        for key, item in self.layer_options_list.items():
            if item.get('widget') and key != 'sourceProject':
                item['widget'].setEnabled(value)
        self.dlg.btConfigurePopup.setEnabled(value)
        self.dlg.btQgisPopupFromForm.setEnabled(value)
        self.dlg.button_generate_html_table.setEnabled(value)

    def external_wms_toggled(self):
        """ Disable the format combobox is the checkbox third party WMS is checked. """
        self.dlg.liImageFormat.setEnabled(not self.dlg.cbExternalWms.isChecked())

    def enable_popup_source_button(self):
        """Enable or not the "Configure" button according to the popup source."""
        data = self.layer_options_list['popupSource']['widget'].currentData()
        self.dlg.btConfigurePopup.setVisible(data in ('lizmap', 'qgis'))
        self.dlg.widget_qgis_maptip.setVisible(data == 'qgis')
        self.dlg.button_maptip_preview.setVisible(data == 'qgis')

        if data == 'lizmap':
            layer = self._current_selected_layer()
            self.dlg.widget_deprecated_lizmap_popup.setVisible(isinstance(layer, QgsVectorLayer))
        else:
            self.dlg.widget_deprecated_lizmap_popup.setVisible(False)

    def get_item_wms_capability(self, selected_item: Dict) -> bool:
        """
        Check if an item in the tree is a layer
        and if it is a WMS layer
        """
        wms_enabled = False
        is_layer = selected_item['type'] == 'layer'
        if is_layer:
            layer = self.get_qgis_layer_by_id(selected_item['id'])
            if layer and layer.providerType() in ['wms'] and get_layer_wms_parameters(layer):
                wms_enabled = True
        return wms_enabled

    def _current_item_predefined_group(self) -> Optional[PredefinedGroup]:
        """ Get the current group type. """
        item = self.dlg.layer_tree.currentItem()
        if not item:
            return None

        text = item.text(1)
        if text not in self.layerList:
            return None

        return item.data(0, Qt.ItemDataRole.UserRole + 1)

    def _current_selected_item_in_config(self) -> Optional[str]:
        """ Either a group or a layer name. """
        item = self.dlg.layer_tree.currentItem()
        if not item:
            return None

        text = item.text(1)
        if text not in self.layerList:
            return None

        return text

    def _current_selected_layer(self) -> Optional[QgsMapLayer]:
        """ Current selected map layer in the tree. """
        lid = self._current_selected_item_in_config()
        if not lid:
            logger.warning('No item selected in the Lizmap layer tree.')
            return None

        layers = [layer for layer in self.project.mapLayers().values() if layer.id() == lid]
        if not layers:
            logger.warning('Layers not found with searched text from the tree : {}'.format(lid))
            return None

        return layers[0]

    # These methods are self contained

    def _layer_tree_state_key(self) -> str:
        """Return QgsSettings key for group expand states of the current project."""
        project_path = self.project.fileName()
        if not project_path:
            return ''
        key_hash = hashlib.sha256(project_path.encode('utf-8')).hexdigest()
        return f'lizmap/layer_tree_group_states/{key_hash}'

    def _save_layer_tree_group_states(self):
        """Persist expanded/collapsed state of group items to QgsSettings."""
        if not self._layer_tree_state_key():
            return
        states: Dict = {}
        self._collect_group_states(self.dlg.layer_tree.invisibleRootItem(), states)
        QgsSettings().setValue(self._layer_tree_state_key(), json.dumps(states))

    def _collect_group_states(self, parent_item: QTreeWidgetItem, states: Dict):
        """Recursively collect expanded state for group items."""
        for i in range(parent_item.childCount()):
            item = parent_item.child(i)
            if item.text(2) == 'group':
                states[item.text(1)] = item.isExpanded()
                self._collect_group_states(item, states)

    def _restore_layer_tree_group_states(self):
        """Restore saved expanded/collapsed state to group items."""
        key = self._layer_tree_state_key()
        if not key:
            return
        stored = QgsSettings().value(key)
        if stored is None:
            return
        try:
            states = json.loads(stored)
        except (json.JSONDecodeError, TypeError):
            return
        self._apply_group_states(self.dlg.layer_tree.invisibleRootItem(), states)

    def _apply_group_states(self, parent_item: QTreeWidgetItem, states: Dict):
        """Recursively apply expanded state to group items."""
        for i in range(parent_item.childCount()):
            item = parent_item.child(i)
            if item.text(2) == 'group':
                group_id = item.text(1)
                if group_id in states:
                    item.setExpanded(states[group_id])
                self._apply_group_states(item, states)

    def _on_layer_tree_group_state_changed(self, item: Any):
        """Save group states when user manually expands or collapses a group."""
        if not self.dlg._ignore_layer_tree_state:
            self._save_layer_tree_group_states()

    def _on_layer_search_changed(self, text: str):
        """Restore group states when search filter is cleared."""
        if not text.strip():
            self.dlg._ignore_layer_tree_state = True
            self._restore_layer_tree_group_states()
            self.dlg._ignore_layer_tree_state = False

    def get_qgis_layer_by_id(self, my_id: str) -> Optional[QgsMapLayer]:
        """ Get a QgsMapLayer by its ID. """
        return self.project.mapLayers().get(my_id, None)

    def save_value_layer_group_data(self, key: str):
        """ Save the new value from the UI in the global layer property self.layerList.

        Function called the corresponding UI widget has sent changed signal.
        """
        key = str(key)
        layer_or_group_text = self._current_selected_item_in_config()
        if not layer_or_group_text:
            return

        # get the definition for this property
        layer_option = self.layer_options_list[key]
        # modify the property for the selected item
        if layer_option['wType'] == 'text':
            text = layer_option['widget'].text()
            if layer_option['type'] == 'list':
                text = string_to_list(text)
            self.layerList[layer_or_group_text][key] = text
            self.set_layer_metadata(layer_or_group_text, key)
        elif layer_option['wType'] == 'textarea':
            self.layerList[layer_or_group_text][key] = layer_option['widget'].toPlainText()
            self.set_layer_metadata(layer_or_group_text, key)
        elif layer_option['wType'] == 'spinbox':
            self.layerList[layer_or_group_text][key] = layer_option['widget'].value()
        elif layer_option['wType'] in ('checkbox', 'radio'):
            checked = layer_option['widget'].isChecked()
            self.layerList[layer_or_group_text][key] = checked
            children = layer_option.get('children')
            if children:
                exclusive = layer_option.get('exclusive', False)
                if exclusive:
                    is_enabled = not checked
                else:
                    is_enabled = checked
                self.layer_options_list[children]['widget'].setEnabled(is_enabled)
                if self.layer_options_list[children]['wType'] == 'checkbox' and not is_enabled:
                    if self.layer_options_list[children]['widget'].isChecked():
                        self.layer_options_list[children]['widget'].setChecked(False)
        elif layer_option['wType'] == 'list':
            # New way with data, label, tooltip and icon
            datas = [j[0] for j in layer_option['list']]
            self.layerList[layer_or_group_text][key] = datas[layer_option['widget'].currentIndex()]

        # Deactivate the "exclude" widget if necessary
        if 'exclude' in layer_option \
                and layer_option['wType'] == 'checkbox' \
                and layer_option['widget'].isChecked() \
                and layer_option['exclude']['widget'].isChecked():
            layer_option['exclude']['widget'].setChecked(False)
            self.layerList[layer_or_group_text][layer_option['exclude']['key']] = False

    def set_layer_metadata(self, layer_or_group: str, key: str):
        """Set the title/abstract/link QGIS metadata when the corresponding item is changed
        Used in setLayerProperty"""
        if 'isMetadata' not in self.layer_options_list[key]:
            return

        # modify the layer.title|abstract|link() if possible
        if self.layerList[layer_or_group]['type'] != 'layer':
            return

        layer = self.get_qgis_layer_by_id(layer_or_group)
        if not isinstance(layer, QgsMapLayer):
            return

        if key == 'title':
            set_layer_property(layer, LayerProperties.Title, self.layerList[layer_or_group][key])

        if key == 'abstract':
            set_layer_property(layer, LayerProperties.Abstract, self.layerList[layer_or_group][key])

    def disable_legacy_empty_base_layer(self):
        """ Legacy checkbox until it's removed. """
        # We suppose we are in LWC >= 3.7 otherwise the button is blue
        if self.lwc_version >= LwcVersions.Lizmap_3_7:
            self.dlg.cbAddEmptyBaselayer.setChecked(False)

    def add_group_hidden(self):
        """ Add the hidden group. """
        self._add_group_legend(GroupNames.Hidden)

    def add_group_baselayers(self):
        """ Add the baselayers group. """
        self._add_group_legend(GroupNames.BaseLayers)
        self.disable_legacy_empty_base_layer()

    def add_group_empty(self):
        """ Add the default background color. """
        baselayers = self._add_group_legend(GroupNames.BaseLayers)
        self._add_group_legend(GroupNames.BackgroundColor, parent=baselayers)
        self.disable_legacy_empty_base_layer()

    def add_group_overview(self):
        """ Add the overview group. """
        label = 'overview'
        if self.lwc_version < LwcVersions.Lizmap_3_7:
            label = 'Overview'
        self._add_group_legend(label, exclusive=False)

    def _add_group_legend(
            self, label: str, exclusive: bool = False, parent: QgsLayerTreeGroup = None,
            project: QgsProject = None,
        ) -> QgsLayerTreeGroup:
        """ Add a group in the legend. """
        if project is None:
            project = self.project

        if parent:
            root_group = parent
        else:
            root_group = project.layerTreeRoot()

        qgis_group = self.existing_group(root_group, label)
        if qgis_group:
            return qgis_group

        new_group = root_group.addGroup(label)
        if exclusive:
            new_group.setIsMutuallyExclusive(True, -1)
        return new_group

    @staticmethod
    def existing_group(
        root_group: QgsLayerTree,
        label: str,
        index: bool = False,
    ) -> Optional[Union[QgsLayerTreeGroup, int]]:
        """ Return the existing group in the legend if existing.

        It will either return the group itself if found, or its index.
        """
        if not root_group:
            return None

        # Iterate over all child (layers and groups)
        children = root_group.children()
        i = -1
        for child in children:
            if not QgsLayerTree.isGroup(child):
                i += 1
                continue

            qgis_group = cast_to_group(child)
            qgis_group: QgsLayerTreeGroup
            count_children = len(qgis_group.children())
            if count_children >= 1 or qgis_group.name() == label:
                # We do not want to count empty groups
                # Except for the one we are looking for
                i += 1

            if qgis_group.name() == label:
                return i if index else qgis_group

        return None

    def _add_base_layer(
        self,
        source: str,
        name: str,
        attribution_url: Optional[str] = None,
        attribution_name: Optional[str] = None,
    ):
        """ Add a base layer to the "baselayers" group. """
        self.add_group_baselayers()
        raster = QgsRasterLayer(source, name, 'wms')
        self.project.addMapLayer(raster, False)  # False to not add it in the legend, only in the project

        if attribution_url:
            set_layer_property(raster, LayerProperties.AttributionUrl, attribution_url)
            set_layer_property(raster, LayerProperties.DataUrl, attribution_url)
        if attribution_name:
            set_layer_property(raster, LayerProperties.Attribution, attribution_name)
        root_group = self.project.layerTreeRoot()

        groups = root_group.findGroups()
        for qgis_group in groups:
            qgis_group: QgsLayerTreeGroup
            if qgis_group.name() == 'baselayers':
                node = qgis_group.addLayer(raster)
                node.setExpanded(False)
                break

        self.dlg.display_message_bar(
            tr('New layer'),
            tr('Please close and reopen the dialog to display your layer in the tab "{tab_name}".').format(
                tab_name=self.dlg.mOptionsListWidget.item(Panels.Layers).text()
            ),
            Qgis.MessageLevel.Warning,
        )
