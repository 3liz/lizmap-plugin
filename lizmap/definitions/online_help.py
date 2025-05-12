"""Online help definitions. """

__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from qgis.core import QgsSettings
from qgis.PyQt.QtCore import QLocale, QUrl

from lizmap.definitions.lizmap_cloud import (
    CLOUD_ONLINE_LANGUAGES,
    CLOUD_ONLINE_URL,
)

DOMAIN = 'https://docs.lizmap.com'
VERSION = 'current'
ONLINE_HELP_LANGUAGES = ('en', 'es', 'it', 'ja', 'pt', 'fi', 'fr')


def current_locale() -> str:
    """ Get the main language, with 2 characters only. """
    locale = QgsSettings().value("locale/userLocale", QLocale().name())
    locale = locale[0:2]
    return locale


def online_cloud_help(page: str = '') -> QUrl:
    """ Online help URL according to locale and version. """
    locale = current_locale()
    if locale not in CLOUD_ONLINE_LANGUAGES:
        locale = 'en'
    return QUrl(f"{CLOUD_ONLINE_URL}/{locale}/{page}")


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

class Panels:
    Information = 0
    MapOptions = 1
    Layers = 2
    Basemap = 3
    AttributeTable = 4
    Editing = 5
    Layouts = 6
    FormFiltering = 7
    Dataviz = 8
    FilteredLayers = 9
    Actions = 10
    TimeManager = 11
    Atlas = 12
    LocateByLayer = 13
    ToolTip = 14
    Checks = 15
    AutoFix = 16
    Settings = 17
    Upload = 18
    Training = 19


MAPPING_INDEX_DOC = {
    Panels.Information: 'publish/lizmap_plugin/information.html',
    Panels.MapOptions: 'publish/lizmap_plugin/map_options.html',
    Panels.Layers: 'publish/lizmap_plugin/layers.html',
    Panels.Basemap: 'publish/lizmap_plugin/basemap.html',
    Panels.AttributeTable: 'publish/lizmap_plugin/attribute_table.html',
    Panels.Editing: 'publish/lizmap_plugin/editing.html',
    Panels.Layouts: None,  # Layouts
    Panels.FormFiltering: 'publish/lizmap_plugin/form_filtering.html',
    Panels.Dataviz: 'publish/lizmap_plugin/dataviz.html',
    Panels.FilteredLayers: 'publish/lizmap_plugin/filtered_layers_login.html',
    Panels.Actions: 'publish/lizmap_plugin/actions.html',
    Panels.TimeManager: 'publish/lizmap_plugin/time_manager.html',
    Panels.Atlas: 'publish/lizmap_plugin/atlas.html',
    Panels.LocateByLayer: 'publish/lizmap_plugin/locate_by_layer.html',
    Panels.ToolTip: 'publish/lizmap_plugin/tooltip.html',
    Panels.Checks: None,  # Log/checks
    Panels.AutoFix: None,  # Auto-fix
    Panels.Settings: None,  # Settings
    Panels.Upload: None,
    Panels.Training: None,
}


def pg_service_help() -> QUrl:
    """ Open the QGIS.org documentation about PG Service. """
    # The QGIS documentation is better than the PostgreSQL doc :/
    return _qgis_help('user_manual/managing_data_source/opening_data.html#postgresql-service-connection-file')


def qgis_theme_help() -> QUrl:
    """ Open the theme help page. """
    return _qgis_help('user_manual/introduction/general_tools.html#map-themes')


def _qgis_help(page: str) -> QUrl:
    """ Open a QGIS help page. """
    return QUrl(
        f"https://docs.qgis.org/latest/{current_locale()}/docs/{page}"
    )
