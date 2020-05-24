import os
import json

from qgis.core import Qgis, QgsMessageLog
from qgis.server import QgsServerInterface, QgsAccessControlFilter

from typing import List, Dict, Iterable
from qgis.core import QgsMapLayer, QgsVectorLayer, QgsFeature


class LizmapAccessControlFilter(QgsAccessControlFilter):

    def __init__(self, server_iface: 'QgsServerInterface') -> None:
        super().__init__(server_iface)

        self.iface = server_iface

    def layerFilterExpression(self, layer: 'QgsVectorLayer') -> str:
        """ Return an additional expression filter """
        return super().layerFilterExpression(layer)

    def layerFilterSubsetString(self, layer: 'QgsVectorLayer') -> str:
        """ Return an additional subset string (typically SQL) filter """
        return super().layerFilterSubsetString(layer)

    def layerPermissions(self, layer: 'QgsMapLayer') -> QgsAccessControlFilter.LayerPermissions:
        """ Return the layer rights """
        # Get default layer rights
        rights = super().layerPermissions(layer)

        # Get Lizmap config
        cfg = self.getLizmapConfig()
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

        # Check Lizmap layer config
        cfg_layers = cfg['layers']
        layer_name = layer.name()
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

        # Get Lizmap user groups provided by the request
        groups = self.getLizmapGroups()

        # If groups is empty, no Lizmap user groups provided by the request
        # The default layre rights is applied
        if len(groups) == 0:
            return rights

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

    def authorizedLayerAttributes(self, layer: 'QgsVectorLayer', attributes: 'Iterable[str]') -> 'List[str]':
        """ Return the authorised layer attributes """
        return super().authorizedLayerAttributes(layer, attributes)

    def allowToEdit(self, layer: 'QgsVectorLayer', feature: 'QgsFeature') -> bool:
        """ Are we authorise to modify the following geometry """
        return super().allowToEdit(layer, feature)

    def cacheKey(self) -> str:
        """ The key used to cache documents """
        defaultCacheKey = super().cacheKey()

        # Get Lizmap user groups provided by the request
        groups = self.getLizmapGroups()

        # If groups is empty, no Lizmap user groups provided by the request
        # The default cache key is returned
        if len(groups) == 0:
            return defaultCacheKey

        # Get Lizmap config
        cfg = self.getLizmapConfig()
        if not cfg:
            # Lizmap config is empty
            QgsMessageLog.logMessage("Lizmap config is empty", "lizmap", Qgis.Warning)
            # The default cache key is returned
            return defaultCacheKey

        # Check Lizmap config layers
        if 'layers' not in cfg or not cfg['layers']:
            # Lizmap config has no options
            QgsMessageLog.logMessage("Lizmap config has no layers", "lizmap", Qgis.Warning)
            # The default cache key is returned
            return defaultCacheKey

        # Check group_visibility in Lizmap config layers
        cfg_layers = cfg['layers']
        hasGroupVisibility = False
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

            hasGroupVisibility = True
            break

        # group_visibility option is defined in Lizmap config layers
        if hasGroupVisibility:
            # The group provided in request is anonymous
            if len(groups) == 1 and groups[0] == '':
                return '@@'
            # for other groups, removing duplicates and joining
            return '@@'.join(list(set(groups)))

        return defaultCacheKey

    def getLizmapConfig(self) -> 'Dict':
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
        cfg = None
        with open(config_path, 'r') as cfg_file:
            try:
                cfg = json.loads(cfg_file.read())
            except Exception:
                # Lizmap config is not a valid JSON file
                QgsMessageLog.logMessage("Lizmap config not well formed", "lizmap", Qgis.Error)
                cfg = None
                return cfg

        return cfg

    def getLizmapGroups(self) -> 'List[str]':
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
            userGroups = headers.get('X-Lizmap-User-Groups')
            if userGroups is not None:
                groups = [g.strip() for g in userGroups.split(',')]
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
            userGroups = params.get('LIZMAP_USER_GROUPS')
            if userGroups is not None:
                groups = [g.strip() for g in userGroups.split(',')]
                QgsMessageLog.logMessage("Lizmap user groups in parameters", "lizmap", Qgis.Info)

        return groups
