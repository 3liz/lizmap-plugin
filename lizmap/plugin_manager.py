__copyright__ = 'Copyright 2022, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from qgis.PyQt.QtCore import QDateTime, Qt, QLocale
from qgis.utils import iface
from pyplugin_installer import instance


class PluginManager:

    def __init__(self):
        plugin_manager = instance()
        plugin_manager.exportPluginsToManager()

        plugins = {
            'cadastre': 'https://github.com/3liz/QgisCadastrePlugin/releases/tag/{tag}',
            'lizmap': 'https://github.com/3liz/lizmap-plugin/releases/tag/{tag}',
            'wfsOutputExtension': 'https://github.com/3liz/qgis-wfsOutputExtension/releases/tag/{tag}',
            'atlasprint': 'https://github.com/3liz/qgis-atlasprint/releases/tag/{tag}',
        }
        self.metadata = {}
        for plugin, url in plugins.items():
            plugin_metadata = iface.pluginManagerInterface().pluginMetadata(plugin)
            if not plugin_metadata:
                continue

            name = plugin_metadata['name']
            latest_stable_version = plugin_metadata['version_available']
            latest_stable_date = QDateTime.fromString(
                plugin_metadata['update_date'],
                Qt.ISODateWithMs
            )
            date_string = latest_stable_date.toString(QLocale().dateFormat(QLocale.ShortFormat))

            template = (
                '{name} <a href="{url}">'
                '{tag}   -    {date}'
                '</a>'
            )
            tag_url = url.format(tag=latest_stable_version)
            self.metadata[name] = template.format(name=name, url=tag_url, tag=latest_stable_version, date=date_string)
