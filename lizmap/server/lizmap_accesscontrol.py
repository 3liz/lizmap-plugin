__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'

import os
import json

from typing import List, Dict, Union

from qgis.core import (
    Qgis,
    QgsMessageLog,
    QgsMapLayer,
)
from qgis.server import (
    QgsServerInterface,
    QgsAccessControlFilter,
)


class LizmapAccessControlFilter(QgsAccessControlFilter):

    def __init__(self, server_iface: 'QgsServerInterface') -> None:
        super().__init__(server_iface)

        self.iface = server_iface

    # def layerFilterExpression(self, layer: 'QgsVectorLayer') -> str:
    #     """ Return an additional expression filter """
    #     return super().layerFilterExpression(layer)
    #
    # def layerFilterSubsetString(self, layer: 'QgsVectorLayer') -> str:
    #     """ Return an additional subset string (typically SQL) filter """
    #     return super().layerFilterSubsetString(layer)

    def layerPermissions(self, layer: 'QgsMapLayer') -> QgsAccessControlFilter.LayerPermissions:
        """ Return the layer rights """
        # Get default layer rights
        rights = super().layerPermissions(layer)

        # Get Lizmap user groups provided by the request
        groups = self.get_lizmap_groups()

        # If groups is empty, no Lizmap user groups provided by the request
        # The default layer rights is applied
        if len(groups) == 0:
            return rights

        # Get Lizmap config
        cfg = self.get_lizmap_config()
        if not cfg:
            # Lizmap config is empty
            QgsMessageLog.logMessage("Lizmap config is empty", "lizmap", Qgis.Warning)
            # Default layer rights applied
            return rights

        # Check Lizmap config layers
        if 'layers' not in cfg or not cfg['layers']:
            # Lizmap config has no options
            QgsMessageLog.logMessage("Lizmap config has no layers", "lizmap", Qgis.Warning)
            # Default layer rights applied
            return rights

        # Get layers config
        cfg_layers = cfg['layers']
        # Get layer name
        layer_name = layer.name()

        # Check lizmap edition config
        layer_id = layer.id()
        if 'editionLayers' in cfg and cfg['editionLayers']:
            if layer_id in cfg['editionLayers'] and cfg['editionLayers'][layer_id]:
                edit_layer = cfg['editionLayers'][layer_id]

                # Check if edition is possible
                # By default not
                can_edit = False
                if 'acl' in edit_layer and edit_layer['acl']:
                    # acl is defined and not an empty string
                    # authorization defined for edition
                    group_edit = edit_layer['acl'].split(',')
                    group_edit = [g.strip() for g in group_edit]

                    # check if a group is in authorization groups list
                    if len(group_edit) != 0:
                        for g in groups:
                            if g in group_edit:
                                can_edit = True
                    else:
                        can_edit = True
                else:
                    # acl is not defined or an empty string
                    # no authorization defined for edition
                    can_edit = True

                if can_edit and 'capabilities' in edit_layer and edit_layer['capabilities']:
                    # A user group can edit the layer and capabilities
                    # edition for the layer is defined in Lizmap edition config
                    edit_layer_cap = cfg['editionLayers'][layer_id]['capabilities']
                    if edit_layer_cap['createFeature'] == 'True':
                        rights.canInsert = True
                    else:
                        rights.canInsert = False
                    if edit_layer_cap['modifyAttribute'] == 'True' or edit_layer_cap['modifyGeometry'] == 'True':
                        rights.canUpdate = True
                    else:
                        rights.canUpdate = False
                    if edit_layer_cap['deleteFeature'] == 'True':
                        rights.canDelete = True
                    else:
                        rights.canDelete = False
                else:
                    # Any user groups can edit the layer or capabilities
                    # edition for the layer is not defined in Lizmap
                    # edition config
                    # Reset edition rights
                    rights.canInsert = rights.canUpdate = rights.canDelete = False
            else:
                # The layer has no editionLayers config defined
                # Reset edition rights
                QgsMessageLog.logMessage(
                    "No edition config defined for layer: %s (%s)" % (layer_name, layer_id), "lizmap", Qgis.Info)
                rights.canInsert = rights.canUpdate = rights.canDelete = False
        else:
            # No editionLayers defined
            # Reset edition rights
            QgsMessageLog.logMessage("Lizmap config has no editionLayers", "lizmap", Qgis.Info)
            rights.canInsert = rights.canUpdate = rights.canDelete = False

        # Check Lizmap layer config
        if layer_name not in cfg_layers or not cfg_layers[layer_name]:
            # Lizmap layer config not defined
            QgsMessageLog.logMessage("Lizmap config has no layer: %s" % layer_name, "lizmap", Qgis.Warning)
            # Default layer rights applied
            return rights

        # Check Lizmap layer group visibility
        cfg_layer = cfg_layers[layer_name]
        if 'group_visibility' not in cfg_layer or not cfg_layer['group_visibility']:
            # Lizmap config has no options
            QgsMessageLog.logMessage("No Lizmap layer group visibility for: %s" % layer_name, "lizmap", Qgis.Info)
            # Default layer rights applied
            return rights

        # Get Lizmap layer group visibility
        group_visibility = cfg_layer['group_visibility'].split(',')
        group_visibility = [g.strip() for g in group_visibility]

        # If one Lizmap user group provided in request headers is
        # defined in Lizmap layer group visibility, the default layer
        # rights is applied
        for g in groups:
            if g in group_visibility:
                QgsMessageLog.logMessage(
                    "Group %s is in Lizmap layer group visibility for: %s" % (g, layer_name),
                    "lizmap", Qgis.Info)
                return rights

        # The lizmap user groups provided gy the request are not
        # authorized to get access to the layer
        QgsMessageLog.logMessage(
            "Groups %s is in Lizmap layer group visibility for: %s" % (', '.join(groups), layer_name),
            "lizmap", Qgis.Info)
        rights.canRead = False
        rights.canInsert = rights.canUpdate = rights.canDelete = False
        return rights

    # def authorizedLayerAttributes(self, layer: 'QgsVectorLayer', attributes: 'Iterable[str]') -> 'List[str]':
    #     """ Return the authorised layer attributes """
    #     return super().authorizedLayerAttributes(layer, attributes)
    #
    # def allowToEdit(self, layer: 'QgsVectorLayer', feature: 'QgsFeature') -> bool:
    #     """ Are we authorise to modify the following geometry """
    #     return super().allowToEdit(layer, feature)

    def cacheKey(self) -> str:
        """ The key used to cache documents """
        default_cache_key = super().cacheKey()

        # Get Lizmap user groups provided by the request
        groups = self.get_lizmap_groups()

        # If groups is empty, no Lizmap user groups provided by the request
        # The default cache key is returned
        if len(groups) == 0:
            return default_cache_key

        # Get Lizmap config
        cfg = self.get_lizmap_config()
        if not cfg:
            # Lizmap config is empty
            QgsMessageLog.logMessage("Lizmap config is empty", "lizmap", Qgis.Warning)
            # The default cache key is returned
            return default_cache_key

        # Check Lizmap config layers
        if 'layers' not in cfg or not cfg['layers']:
            # Lizmap config has no options
            QgsMessageLog.logMessage("Lizmap config has no layers", "lizmap", Qgis.Warning)
            # The default cache key is returned
            return default_cache_key

        # Check group_visibility in Lizmap config layers
        cfg_layers = cfg['layers']
        has_group_visibility = False
        for l_name, cfg_layer in cfg_layers.items():
            # check group_visibility in config
            if 'group_visibility' not in cfg_layer or not cfg_layer['group_visibility']:
                continue

            # get group_visibility as list
            group_visibility = cfg_layer['group_visibility'].split(',')
            group_visibility = [g.strip() for g in group_visibility]

            # the group_visibility was just an empty string
            if len(group_visibility) == 1 and groups[0] == '':
                continue

            has_group_visibility = True
            break

        # group_visibility option is defined in Lizmap config layers
        if has_group_visibility:
            # The group provided in request is anonymous
            if len(groups) == 1 and groups[0] == '':
                return '@@'
            # for other groups, removing duplicates and joining
            return '@@'.join(list(set(groups)))

        return default_cache_key

    def get_lizmap_config(self) -> Union[Dict, None]:
        """ Get Lizmap config """
        # Get QGIS Project path
        config_path = self.iface.configFilePath()
        if not os.path.exists(config_path):
            # QGIS Project path does not exist as a file
            # No Lizmap config
            return None

        # Get Lizmap config path
        config_path += '.cfg'
        if not os.path.exists(config_path):
            # Lizmap config path does not exist
            QgsMessageLog.logMessage("Lizmap config does not exist", "lizmap", Qgis.Info)
            # No Lizmap config
            return None

        # Get Lizmap config
        with open(config_path, 'r') as cfg_file:
            # noinspection PyBroadException
            try:
                cfg = json.loads(cfg_file.read())
                return cfg
            except Exception:
                # Lizmap config is not a valid JSON file
                QgsMessageLog.logMessage("Lizmap config not well formed", "lizmap", Qgis.Critical)
                return None

    def get_lizmap_groups(self) -> 'List[str]':
        """ Get Lizmap user groups provided by the request """
        # Defined groups
        groups = []

        # Get request handler
        handler = self.iface.requestHandler()

        # Get Lizmap User Groups in request headers
        headers = handler.requestHeaders()
        if headers:
            QgsMessageLog.logMessage("Request headers provided", "lizmap", Qgis.Info)
            # Get Lizmap user groups defined in request headers
            user_groups = headers.get('X-Lizmap-User-Groups')
            if user_groups is not None:
                groups = [g.strip() for g in user_groups.split(',')]
                QgsMessageLog.logMessage("Lizmap user groups in request headers", "lizmap", Qgis.Info)
        else:
            QgsMessageLog.logMessage("No request headers provided", "lizmap", Qgis.Info)

        if len(groups) != 0:
            return groups
        else:
            QgsMessageLog.logMessage("No lizmap user groups in request headers", "lizmap", Qgis.Info)

        # Get group in parameters
        params = handler.parameterMap()
        if params:
            # Get Lizmap user groups defined in parameters
            user_groups = params.get('LIZMAP_USER_GROUPS')
            if user_groups is not None:
                groups = [g.strip() for g in user_groups.split(',')]
                QgsMessageLog.logMessage("Lizmap user groups in parameters", "lizmap", Qgis.Info)

        return groups
