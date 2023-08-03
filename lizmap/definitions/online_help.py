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


def _locale() -> str:
    """ Get the main language. """
    locale = QgsSettings().value("locale/userLocale", QLocale().name())
    locale = locale[0:2]
    return locale


def online_cloud_help(page: str = '') -> QUrl:
    """ Online help URL according to locale and version. """
    locale = _locale()
    if locale not in CLOUD_HELP_LANGUAGES:
        locale = 'en'
    return QUrl(f"{CLOUD}/{locale}/{page}")


def online_lwc_help(page: str = '', version=VERSION) -> QUrl:
    """ Online help URL according to locale and version. """
    locale = _locale()
    if locale not in ONLINE_HELP_LANGUAGES:
        locale = 'en'

    # noinspection PyArgumentList
    return QUrl(f"{DOMAIN}/{version}/{locale}/{page}")
