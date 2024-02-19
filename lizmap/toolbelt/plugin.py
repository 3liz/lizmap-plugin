from os.path import abspath, join
from pathlib import Path

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QDateTime, QDir, Qt

from lizmap.toolbelt.resources import metadata_config


def lizmap_user_folder() -> Path:
    """ Get the Lizmap user folder.

    If the folder does not exist, it will create it.

    On Linux: .local/share/QGIS/QGIS3/profiles/default/Lizmap
    """
    path = abspath(join(QgsApplication.qgisSettingsDirPath(), 'Lizmap'))

    if not QDir(path).exists():
        QDir().mkdir(path)

    lizmap_path = Path(path)

    cache_dir = lizmap_path.joinpath("cache_server_metadata")
    if not cache_dir.exists():
        QDir().mkdir(str(cache_dir))

    return lizmap_path


def user_settings() -> Path:
    """ Path to the user file configuration. """
    return lizmap_user_folder().joinpath('user_servers.json')


def plugin_date() -> QDateTime:
    """Return the version defined in metadata.txt."""
    date = metadata_config()["general"]["dateTime"]
    return QDateTime().fromString(date, Qt.ISODate)
