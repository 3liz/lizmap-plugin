"""
__copyright__ = 'Copyright 2022, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
"""
from collections import namedtuple
from typing import Optional

from pyplugin_installer import instance
from qgis.PyQt.QtCore import QDate, QDateTime, QLocale, Qt
from qgis.utils import iface

from . import logger
from .definitions.definitions import DEV_VERSION_PREFIX
from .server_lwc import ServerManager
from .toolbelt.plugin import plugin_date
from .toolbelt.version import version

Plugin = namedtuple('Plugin', ['name', 'version', 'date', 'template'])

DAYS_BEFORE_OUTDATED = 60


class QgisPluginManager:

    def __init__(self):
        plugin_manager = instance()
        plugin_manager.exportPluginsToManager()
        # plugin_manager.repositories.checkingDone.connect(self.checkingDone)
        # for key in repositories.allEnabled():
        #     repositories.requestFetching(key)

        plugins = {
            'cadastre': 'https://github.com/3liz/QgisCadastrePlugin/releases/tag/{tag}',
            'lizmap': 'https://github.com/3liz/lizmap-plugin/releases/tag/{tag}',
            'lizmap_server': 'https://github.com/3liz/qgis-lizmap-server-plugin/releases/tag/{tag}',
            'wfsOutputExtension': 'https://github.com/3liz/qgis-wfsOutputExtension/releases/tag/{tag}',
            'atlasprint': 'https://github.com/3liz/qgis-atlasprint/releases/tag/{tag}',
        }
        self.metadata = {}
        for plugin, url in plugins.items():
            try:
                plugin_metadata = iface.pluginManagerInterface().pluginMetadata(plugin)
                if not plugin_metadata:
                    continue

                name = plugin_metadata['name']
                latest_stable_version = plugin_metadata['version_available']
                latest_stable_date = QDateTime.fromString(
                    plugin_metadata['update_date'],
                    Qt.DateFormat.ISODateWithMs
                )
                date_string = latest_stable_date.toString(QLocale().dateFormat(QLocale.FormatType.ShortFormat))

                template = (
                    '{name} <a href="{url}">'
                    '{tag}   -    {date}'
                    '</a>'
                )
                tag_url = url.format(tag=latest_stable_version)
                self.metadata[name] = Plugin(
                    name=name,
                    version=latest_stable_version,
                    date=latest_stable_date,
                    template=template.format(name=name, url=tag_url, tag=latest_stable_version, date=date_string)
                )
            except KeyError:
                self.metadata[plugin] = Plugin(
                    name=plugin,
                    version=None,
                    date=QDate(),
                    template='{name} - Unknown'.format(name=plugin)
                )

    def current_plugin_needs_update(self) -> Optional[bool]:
        """ Return if the plugin is less than a few days late. """
        current_version = version()
        if current_version in DEV_VERSION_PREFIX:
            # We trust developers
            logger.debug("Version checker : in developers I trust")
            return False

        current_version = ServerManager.split_lizmap_version(current_version)

        if 'Lizmap' not in self.metadata:
            # No QGIS plugin manager, nothing we can do now...
            logger.debug("Version checker : NO QPM, nothing we can do now...")
            return False

        latest_version = self.metadata['Lizmap'].version
        if latest_version is None or latest_version == '':
            logger.debug("Version checker : NO QPM, nothing we can do now...")
            return False

        latest_version = ServerManager.split_lizmap_version(latest_version)
        if current_version >= latest_version:
            # Need to check this one if the previous check
            # The current version is equal to the version in QGIS plugin manager
            logger.warning(
                "Version checker : running a higher version than on plugins.qgis.org : "
                "current {current} >= latest {latest}".format(
                    current='.'.join([str(i) for i in current_version]),
                    latest='.'.join([str(i) for i in latest_version])
                )
            )
            return False

        # Not the latest version at this stage

        latest_date = self.metadata['Lizmap'].date
        current_plugin_date = plugin_date()

        if not latest_date.isValid() or not current_plugin_date.isValid():
            # We are missing some info, let's force them to update...
            logger.debug("Version checker : Missing some dates, they should upgrade")
            return True

        # We are nice, we let them quite a lot of days to update
        # Because we release a few versions per month
        must_update = latest_date.daysTo(current_plugin_date) > DAYS_BEFORE_OUTDATED
        logger.debug("Version checker : needs update : {}".format(must_update))
        return must_update

    def lizmap_version(self):
        return self.metadata['Lizmap'].template

    def lizmap_server_version(self):
        return self.metadata['Lizmap server'].template

    def cadastre_version(self):
        return self.metadata['cadastre'].template

    def wfs_output_extension_version(self):
        return self.metadata['wfsOutputExtension'].template

    def atlas_print_version(self):
        return self.metadata['atlasprint'].template
