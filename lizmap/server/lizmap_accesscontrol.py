__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'

from typing import Dict, List, Union

from qgis.core import (
    Qgis,
    QgsExpression,
    QgsMapLayer,
    QgsMessageLog,
    QgsVectorLayer,
)
from qgis.server import QgsAccessControlFilter, QgsServerInterface

from .core import (
    config_value_to_boolean,
    get_lizmap_config,
    get_lizmap_groups,
    get_lizmap_layer_login_filter,
    get_lizmap_layers_config,
    get_lizmap_override_filter,
    get_lizmap_user_login,
)


class LizmapAccessControlFilter(QgsAccessControlFilter):

    def __init__(self, server_iface: 'QgsServerInterface') -> None:
        super().__init__(server_iface)

        self.iface = server_iface

    def layerFilterExpression(self, layer: 'QgsVectorLayer') -> str:
        """ Return an additional expression filter """
        # Disabling Lizmap layer filter expression for QGIS Server <= 3.16.1 and <= 3.10.12
        # Fix in QGIS Server https://github.com/qgis/QGIS/pull/40556 3.18.0, 3.16.2, 3.10.13
        if 31013 <= Qgis.QGIS_VERSION_INT < 31099 or 31602 <= Qgis.QGIS_VERSION_INT:
            QgsMessageLog.logMessage("Lizmap layerFilterExpression", "lizmap", Qgis.Info)
            filter_exp = self.get_lizmap_layer_filter(layer)
            if filter_exp:
                return filter_exp

            return super().layerFilterExpression(layer)
        else:
            message = (
                "Lizmap layerFilterExpression disabled, you should consider upgrading QGIS Server to >= "
                "3.10.13 or >= 3.16.2")
            QgsMessageLog.logMessage(message, "lizmap", Qgis.Critical)
            return ''

    def layerFilterSubsetString(self, layer: 'QgsVectorLayer') -> str:
        """ Return an additional subset string (typically SQL) filter """
        QgsMessageLog.logMessage("Lizmap layerFilterSubsetString", "lizmap", Qgis.Info)
        filter_exp = self.get_lizmap_layer_filter(layer)
        if filter_exp:
            return filter_exp

        return super().layerFilterSubsetString(layer)

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
            # Default layer rights applied
            return rights

        # Get layers config
        cfg_layers = get_lizmap_layers_config(cfg)
        if not cfg_layers:
            # Default layer rights applied
            return rights

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
        group_visibility = [g.strip() for g in cfg_layer['group_visibility']]

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
            # The default cache key is returned
            return default_cache_key

        # Get layers config
        cfg_layers = get_lizmap_layers_config(cfg)
        if not cfg_layers:
            # The default cache key is returned
            return default_cache_key

        # Check group_visibility in Lizmap config layers
        has_group_visibility = False
        for l_name, cfg_layer in cfg_layers.items():
            # check group_visibility in config
            if 'group_visibility' not in cfg_layer or not cfg_layer['group_visibility']:
                continue

            # clean group_visibility
            group_visibility = [g.strip() for g in cfg_layer['group_visibility']]

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

        return get_lizmap_config(self.iface.configFilePath())

    def get_lizmap_groups(self) -> 'List[str]':
        """ Get Lizmap user groups provided by the request """

        return get_lizmap_groups(self.iface.requestHandler())

    def get_lizmap_user_login(self) -> str:
        """ Get Lizmap user login provided by the request """

        return get_lizmap_user_login(self.iface.requestHandler())

    def get_lizmap_override_filter(self) -> str:
        """ Get Lizmap user login provided by the request """

        return get_lizmap_override_filter(self.iface.requestHandler())

    def get_lizmap_layer_filter(self, layer: 'QgsVectorLayer') -> str:
        """ Get lizmap layer filter based on login filter """
        layer_filter = ''

        # Get Lizmap config
        cfg = self.get_lizmap_config()
        if not cfg:
            # Return empty filter
            return layer_filter

        # Get layers config
        cfg_layers = get_lizmap_layers_config(cfg)
        if not cfg_layers:
            # Return empty filter
            return layer_filter

        # Get layer name
        layer_name = layer.name()
        # Check that
        if layer_name not in cfg_layers:
            # Return empty filter
            return layer_filter

        # Get layer login filter
        cfg_layer_login_filter = get_lizmap_layer_login_filter(cfg, layer_name)
        if not cfg_layer_login_filter:
            # Return empty filter
            return layer_filter

        # Layer login fliter only for edition does not filter layer
        is_edition_only = 'edition_only' in cfg_layer_login_filter
        if is_edition_only and config_value_to_boolean(cfg_layer_login_filter['edition_only']):
            return layer_filter

        # Get Lizmap user groups provided by the request
        groups = self.get_lizmap_groups()
        user_login = self.get_lizmap_user_login()

        # If groups is empty, no Lizmap user groups provided by the request
        # Return empty filter
        if len(groups) == 0 and not user_login:
            return layer_filter

        # Override filter
        override_filter = self.get_lizmap_override_filter()
        if override_filter:
            return layer_filter

        attribute = cfg_layer_login_filter['filterAttribute']

        # Default filter for no user connected
        # we use expression tools also for subset string
        layer_filter = QgsExpression.createFieldEqualityExpression(attribute, 'all')

        # If groups is not empty but the only group like user login has no name
        # Return the filter for no user connected
        if len(groups) == 1 and groups[0] == '' and user_login == '':
            return layer_filter

        # List of quoted values for expression
        quoted_values = []
        if config_value_to_boolean(cfg_layer_login_filter['filterPrivate']):
            # If filter is private use user_login
            quoted_values.append(QgsExpression.quotedString(user_login))
        else:
            # Else use user groups
            quoted_values = [QgsExpression.quotedString(g) for g in groups]
        # Add all to quoted values
        quoted_values.append(QgsExpression.quotedString('all'))

        # Build filter
        layer_filter = '{} IN ({})'.format(
            QgsExpression.quotedColumnRef(attribute),
            ', '.join(quoted_values)
        )

        # Return build filter
        return layer_filter
