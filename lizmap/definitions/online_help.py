"""Online help definitions. """

__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from qgis.core import QgsSettings
from qgis.PyQt.QtCore import QLocale, QUrl

DOMAIN = 'https://docs.lizmap.com'
VERSION = 'current'
ONLINE_HELP_LANGUAGES = ('en', 'es', 'it', 'ja', 'pt', 'fi', 'fr')


def online_help(page: str = '', version=VERSION) -> QUrl:
    """ Online help URL according to locale and version. """
    locale = QgsSettings().value("locale/userLocale", QLocale().name())
    locale = locale[0:2]
    if locale not in ONLINE_HELP_LANGUAGES:
        locale = 'en'

    # noinspection PyArgumentList
    return QUrl(f"{DOMAIN}/{version}/{locale}/{page}")
