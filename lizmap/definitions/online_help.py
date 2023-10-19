"""Online help definitions. """

__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from qgis.core import QgsSettings
from qgis.PyQt.QtCore import QLocale, QUrl

DOMAIN = 'https://docs.lizmap.com'
VERSION = 'current'
ONLINE_HELP_LANGUAGES = ('en', 'es', 'it', 'ja', 'pt', 'fi', 'fr')

CLOUD = 'https://docs.lizmap.cloud'
CLOUD_HELP_LANGUAGES = ('en', 'fr')


def current_locale() -> str:
    """ Get the main language, with 2 characters only. """
    locale = QgsSettings().value("locale/userLocale", QLocale().name())
    locale = locale[0:2]
    return locale


def online_cloud_help(page: str = '') -> QUrl:
    """ Online help URL according to locale and version. """
    locale = current_locale()
    if locale not in CLOUD_HELP_LANGUAGES:
        locale = 'en'
    return QUrl(f"{CLOUD}/{locale}/{page}")


def online_lwc_help(page: str = '', version=VERSION) -> QUrl:
    """ Online help URL according to locale and version. """
    locale = current_locale()
    if locale not in ONLINE_HELP_LANGUAGES:
        locale = 'en'

    if page is None:
        page = ''

    # noinspection PyArgumentList
    return QUrl(f"{DOMAIN}/{version}/{locale}/{page}")


# When editing this mapping, it must be done in the definition/corresponding.py file

MAPPING_INDEX_DOC = {
    0: 'publish/lizmap_plugin/information.html',
    1: 'publish/lizmap_plugin/map_options.html',
    2: 'publish/lizmap_plugin/layers.html',
    3: 'publish/lizmap_plugin/basemap.html',
    4: 'publish/lizmap_plugin/attribute_table.html',
    5: 'publish/lizmap_plugin/editing.html',
    6: None,  # Layouts
    7: 'publish/lizmap_plugin/form_filtering.html',
    8: 'publish/lizmap_plugin/dataviz.html',
    9: 'publish/lizmap_plugin/filtered_layers_login.html',
    10: 'publish/configuration/action_popup.html',  # TODO move into the plugin section
    11: 'publish/lizmap_plugin/time_manager.html',
    12: 'publish/lizmap_plugin/atlas.html',
    13: 'publish/lizmap_plugin/locate_by_layer.html',
    14: 'publish/lizmap_plugin/tooltip.html',
    15: None,
}
