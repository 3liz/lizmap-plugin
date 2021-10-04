__copyright__ = 'Copyright 2021, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from qgis.core import QgsProject
from qgis.server import QgsServerFilter, QgsServerInterface

from lizmap.server.core import get_lizmap_config, get_lizmap_groups
from lizmap.server.exception import LizmapFilterException
from lizmap.server.logger import Logger


class LizmapFilter(QgsServerFilter):

    def __init__(self, server_iface: QgsServerInterface) -> None:
        Logger.info('LizmapFilter.init')
        super().__init__(server_iface)

        self.iface = server_iface

    def requestReady(self):
        logger = Logger()
        # noinspection PyBroadException
        try:
            # Check first the headers to avoid unnecessary config file reading
            # Get Lizmap user groups defined in request headers
            groups = get_lizmap_groups(self.iface.requestHandler())

            # If groups is empty, no Lizmap user groups provided by the request
            # The request can be evaluated by QGIS Server
            if len(groups) == 0:
                return

            # Get Lizmap config
            cfg = get_lizmap_config(self.iface.configFilePath())
            if not cfg:
                # Lizmap config is empty
                logger.warning("Lizmap config is empty")
                # The request can be evaluated by QGIS Server
                return

            # Check Lizmap config options
            if 'options' not in cfg or not cfg['options']:
                # Lizmap config has no options
                logger.warning("Lizmap config has no options")
                # The request can be evaluated by QGIS Server
                return

            # Check project acl option
            cfg_options = cfg['options']
            if 'acl' not in cfg_options or not cfg_options['acl']:
                # No acl defined
                logger.info("No acl defined in Lizmap config")
                # The request can be evaluated by QGIS Server
                return

            # Get project acl option
            cfg_acl = cfg_options['acl']
            logger.info("Acl defined in Lizmap config")

            # If one Lizmap user group provided in request headers is
            # defined in project acl option, the request can be evaluated
            # by QGIS Server
            for group in groups:
                if group in cfg_acl:
                    return

            # The lizmap user groups provided in request header are not
            # authorized to get access to the QGIS Project
            exc = LizmapFilterException('Forbidden', 'No ACL permissions', response_code=403)

            # Get request handler
            handler = self.iface.requestHandler()
            # use setServiceException to be sure to stop the request
            handler.setServiceException(exc)

        except Exception as e:
            logger.log_exception(e)

    def responseComplete(self):
        # Remove lizmap variables for expression
        project = QgsProject.instance()
        custom_var = project.customVariables()
        custom_var.pop('lizmap_user', None)
        custom_var.pop('lizmap_user_groups', None)
        project.setCustomVariables(custom_var)
