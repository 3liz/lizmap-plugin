__copyright__ = 'Copyright 2021, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from qgis.core import Qgis, QgsExpression, QgsMapLayer, QgsVectorLayer
from qgis.server import QgsAccessControlFilter, QgsServerInterface

from lizmap.server.core import (
    get_lizmap_config,
    get_lizmap_groups,
    get_lizmap_layer_login_filter,
    get_lizmap_layers_config,
    get_lizmap_override_filter,
    get_lizmap_user_login,
    is_editing_context,
    to_bool,
)
from lizmap.server.filter_by_polygon import (
    ALL_FEATURES,
    NO_FEATURES,
    FilterByPolygon,
)
from lizmap.server.logger import Logger, log_output_value, profiling


class LizmapAccessControlFilter(QgsAccessControlFilter):

    def __init__(self, server_iface: QgsServerInterface) -> None:
        super().__init__(server_iface)

        self.iface = server_iface

    def layerFilterExpression(self, layer: QgsVectorLayer) -> str:
        """ Return an additional expression filter """
        # Disabling Lizmap layer filter expression for QGIS Server <= 3.16.1 and <= 3.10.12
        # Fix in QGIS Server https://github.com/qgis/QGIS/pull/40556 3.18.0, 3.16.2, 3.10.13
        if 31013 <= Qgis.QGIS_VERSION_INT < 31099 or 31602 <= Qgis.QGIS_VERSION_INT:
            Logger.info("Lizmap layerFilterExpression")
            filter_exp = self.get_lizmap_layer_filter(layer)
            if filter_exp:
                return filter_exp

            return super().layerFilterExpression(layer)
        else:
            message = (
                "Lizmap layerFilterExpression disabled, you should consider upgrading QGIS Server to >= "
                "3.10.13 or >= 3.16.2")
            Logger.critical(message)
            return ALL_FEATURES

    def layerFilterSubsetString(self, layer: QgsVectorLayer) -> str:
        """ Return an additional subset string (typically SQL) filter """
        Logger.info("Lizmap layerFilterSubsetString")
        filter_exp = self.get_lizmap_layer_filter(layer)
        if filter_exp:
            return filter_exp

        return super().layerFilterSubsetString(layer)

    def layerPermissions(self, layer: QgsMapLayer) -> QgsAccessControlFilter.LayerPermissions:
        """ Return the layer rights """
        # Get default layer rights
        rights = super().layerPermissions(layer)

        # Get Lizmap user groups provided by the request
        groups = get_lizmap_groups(self.iface.requestHandler())

        # If groups is empty, no Lizmap user groups provided by the request
        # The default layer rights is applied
        if len(groups) == 0:
            return rights

        # Get Lizmap config
        cfg = get_lizmap_config(self.iface.configFilePath())
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

                    rights.canInsert = to_bool(edit_layer_cap['createFeature'])
                    rights.canDelete = to_bool(edit_layer_cap['deleteFeature'])
                    rights.canUpdate = any([
                        to_bool(edit_layer_cap['modifyAttribute']),
                        to_bool(edit_layer_cap['modifyGeometry']),
                    ])

                else:
                    # Any user groups can edit the layer or capabilities
                    # edition for the layer is not defined in Lizmap
                    # edition config
                    # Reset edition rights
                    rights.canInsert = rights.canUpdate = rights.canDelete = False
            else:
                # The layer has no editionLayers config defined
                # Reset edition rights
                Logger.info(
                    "No edition config defined for layer: %s (%s)" % (layer_name, layer_id))
                rights.canInsert = rights.canUpdate = rights.canDelete = False
        else:
            # No editionLayers defined
            # Reset edition rights
            Logger.info("Lizmap config has no editionLayers")
            rights.canInsert = rights.canUpdate = rights.canDelete = False

        # Check Lizmap layer config
        if layer_name not in cfg_layers or not cfg_layers[layer_name]:
            # Lizmap layer config not defined
            Logger.info("Lizmap config has no layer: %s" % layer_name)
            # Default layer rights applied
            return rights

        # Check Lizmap layer group visibility
        cfg_layer = cfg_layers[layer_name]
        if 'group_visibility' not in cfg_layer or not cfg_layer['group_visibility']:
            # Lizmap config has no options
            Logger.info("No Lizmap layer group visibility for: %s" % layer_name)
            # Default layer rights applied
            return rights

        # Get Lizmap layer group visibility
        group_visibility = [g.strip() for g in cfg_layer['group_visibility']]

        # If one Lizmap user group provided in request headers is
        # defined in Lizmap layer group visibility, the default layer
        # rights is applied
        for g in groups:
            if g in group_visibility:
                Logger.info(
                    "Group %s is in Lizmap layer group visibility for: %s" % (g, layer_name))
                return rights

        # The lizmap user groups provided gy the request are not
        # authorized to get access to the layer
        Logger.info(
            "Groups %s is in Lizmap layer group visibility for: %s" % (', '.join(groups), layer_name))
        rights.canRead = False
        rights.canInsert = rights.canUpdate = rights.canDelete = False
        return rights

    # def authorizedLayerAttributes(
    #         self, layer: 'QgsVectorLayer', attributes: 'Iterable[str]') -> 'List[str]':
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
        groups = get_lizmap_groups(self.iface.requestHandler())

        # If groups is empty, no Lizmap user groups provided by the request
        # The default cache key is returned
        if len(groups) == 0:
            return default_cache_key

        # Get Lizmap config
        cfg = get_lizmap_config(self.iface.configFilePath())
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

    @profiling
    @log_output_value
    def get_lizmap_layer_filter(self, layer: QgsVectorLayer) -> str:
        """ Get lizmap layer filter based on login filter """

        # Check first the headers to avoid unnecessary config file reading
        # Override filter
        if get_lizmap_override_filter(self.iface.requestHandler()):
            return ALL_FEATURES

        # Get Lizmap user groups provided by the request
        groups = get_lizmap_groups(self.iface.requestHandler())
        user_login = get_lizmap_user_login(self.iface.requestHandler())

        # If groups is empty, no Lizmap user groups provided by the request
        if len(groups) == 0 and not user_login:
            return ALL_FEATURES

        # If headers content implies to check for filter, read the Lizmap config
        # Get Lizmap config
        cfg = get_lizmap_config(self.iface.configFilePath())
        if not cfg:
            return ALL_FEATURES

        # Get layers config
        cfg_layers = get_lizmap_layers_config(cfg)
        if not cfg_layers:
            return ALL_FEATURES

        # Get layer name
        layer_name = layer.name()
        # Check the layer in the CFG
        if layer_name not in cfg_layers:
            return ALL_FEATURES

        try:
            edition_context = is_editing_context(self.iface.requestHandler())
            filter_polygon_config = FilterByPolygon(
                cfg.get("filter_by_polygon"), layer, edition_context, use_st_intersect=False)
            polygon_filter = ALL_FEATURES
            if filter_polygon_config.is_filtered():
                if not filter_polygon_config.is_valid():
                    Logger.critical(
                        "The filter by polygon configuration is not valid.\n All features are hidden : "
                        "{}".format(NO_FEATURES))
                    return NO_FEATURES

                # polygon_filter is set, we have a value to filter
                polygon_filter = filter_polygon_config.subset_sql(groups)

        except Exception as e:
            Logger.log_exception(e)
            Logger.critical(
                "An error occurred when trying to read the filtering by polygon.\nAll features are hidden : "
                "{}".format(NO_FEATURES))
            return NO_FEATURES

        if polygon_filter:
            Logger.info("The polygon filter subset string is not null : {}".format(polygon_filter))

        # Get layer login filter
        cfg_layer_login_filter = get_lizmap_layer_login_filter(cfg, layer_name)
        if not cfg_layer_login_filter:
            if polygon_filter:
                return polygon_filter
            return ALL_FEATURES

        # Layer login filter only for edition does not filter layer
        is_edition_only = 'edition_only' in cfg_layer_login_filter
        if is_edition_only and to_bool(cfg_layer_login_filter['edition_only']):
            if polygon_filter:
                return polygon_filter
            return ALL_FEATURES

        attribute = cfg_layer_login_filter['filterAttribute']

        # If groups is not empty but the only group like user login has no name
        # Return the filter for no user connected
        if len(groups) == 1 and groups[0] == '' and user_login == '':

            # Default filter for no user connected
            # we use expression tools also for subset string
            login_filter = QgsExpression.createFieldEqualityExpression(attribute, 'all')
            if polygon_filter:
                return '{} AND {}'.format(polygon_filter, login_filter)

            return login_filter

        login_filter = self._filter_by_login(cfg_layer_login_filter, groups, user_login)
        if polygon_filter:
            return '{} AND {}'.format(polygon_filter, login_filter)

        return login_filter

    @staticmethod
    def _filter_by_login(cfg_layer_login_filter: dict, groups: tuple, login: str) -> str:
        """ Build the string according to the filter by login configuration.

        :param cfg_layer_login_filter: The Lizmap Filter by login configuration.
        :param groups: List of groups for the current user
        :param login: The current user
        """
        # List of quoted values for expression
        quoted_values = []

        if to_bool(cfg_layer_login_filter['filterPrivate']):
            # If filter is private use user_login
            quoted_values.append(QgsExpression.quotedString(login))
        else:
            # Else use user groups
            quoted_values = [QgsExpression.quotedString(g) for g in groups]

        # Add all to quoted values
        quoted_values.append(QgsExpression.quotedString('all'))

        # Build filter
        layer_filter = '{} IN ({})'.format(
            QgsExpression.quotedColumnRef(cfg_layer_login_filter['filterAttribute']),
            ', '.join(quoted_values)
        )

        return layer_filter
