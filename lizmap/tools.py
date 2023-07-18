__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import os
import random
import re
import string
import subprocess
import unicodedata
import urllib.parse

from os.path import abspath, join
from pathlib import Path
from typing import List, Tuple, Union

from qgis.core import Qgis, QgsApplication, QgsProviderRegistry, QgsVectorLayer
from qgis.PyQt.QtCore import QDateTime, QDir, Qt

from lizmap.definitions.definitions import LayerProperties
from lizmap.qgis_plugin_tools.tools.resources import metadata_config


def unaccent(a_string: str) -> str:
    """ Return the unaccentuated string. """
    return ''.join(
        c for c in unicodedata.normalize('NFD', a_string) if unicodedata.category(c) != 'Mn')


def get_layer_wms_parameters(layer):
    """
    Get WMS parameters for a raster WMS layers
    """
    uri = layer.dataProvider().dataSourceUri()
    # avoid WMTS layers (not supported yet in Lizmap Web Client)
    if 'wmts' in uri or 'WMTS' in uri:
        return None

    # Split WMS parameters
    wms_params = dict((p.split('=') + [''])[:2] for p in uri.split('&'))

    # urldecode WMS url
    wms_params['url'] = urllib.parse.unquote(wms_params['url']).replace('&&', '&').replace('==', '=')

    return wms_params


def is_database_layer(layer) -> bool:
    """ Check if the layer is a database layer.

    It returns True for postgres, spatialite and gpkg files.
    """
    if layer.providerType() in ('postgres', 'spatialite'):
        return True

    uri = QgsProviderRegistry.instance().decodeUri('ogr', layer.source())
    extension = os.path.splitext(uri['path'])[1]
    if extension.lower() == '.gpkg':
        return True

    return False


def qgis_version():
    """ Return the QGIS version as integers. """
    # The API has changed in QGIS 3.12
    # Use the function layer
    # noinspection PyUnresolvedReferences
    return Qgis.QGIS_VERSION_INT


def human_size(byte_size, units=None):
    """ Returns a human-readable string representation of bytes """
    if not units:
        units = [' bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB']
    return str(byte_size) + units[0] if byte_size < 1024 else human_size(byte_size >> 10, units[1:])


def layer_property(layer: QgsVectorLayer, item_property: LayerProperties) -> str:
    if item_property == LayerProperties.DataUrl:
        return layer.dataUrl()
    else:
        raise NotImplementedError


def random_string(length: int = 5) -> str:
    """ Generate a random string with the given length. """
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(length))


def format_qgis_version(qgis_version) -> tuple:
    """ Split a QGIS int version number into major, minor, bugfix.

     If the minor version is a dev version, the next stable minor version is set.
     """
    qgis_version = str(qgis_version)
    major = int(qgis_version[0])
    minor = int(qgis_version[1:3])
    if minor % 2:
        minor += 1
    bug_fix = int(qgis_version[3:])
    return major, minor, bug_fix


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


def current_git_hash() -> str:
    """ Retrieve the current git hash number of the git repo (first 6 digit). """
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    git_show = subprocess.Popen(
        'git rev-parse --short=6 HEAD',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        cwd=repo_dir,
        universal_newlines=True,
        encoding='utf8'
    )
    hash_number = git_show.communicate()[0].partition('\n')[0]
    if hash_number == '':
        hash_number = 'unknown'
    return hash_number


def has_git() -> bool:
    """ Using Git command, trying to know if we are in a git directory. """
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    git_show = subprocess.Popen(
        'git rev-parse --git-dir',
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        shell=True,
        cwd=repo_dir,
        universal_newlines=True,
        encoding='utf8'
    )
    output = git_show.communicate()[0].partition('\n')[0]
    return output != ''


def next_git_tag():
    """ Using Git command, trying to guess the next tag. """
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    git_show = subprocess.Popen(
        'git describe --tags $(git rev-list --tags --max-count=1)',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        cwd=repo_dir,
        universal_newlines=True,
        encoding='utf8'
    )
    tag = git_show.communicate()[0].partition('\n')[0]
    if not tag:
        return 'next'
    versions = tag.split('.')
    text = '{}.{}.{}-alpha'.format(versions[0], versions[1], int(versions[2]) + 1)
    return text


def plugin_date() -> QDateTime:
    """Return the version defined in metadata.txt."""
    date = metadata_config()["general"]["dateTime"]
    return QDateTime().fromString(date, Qt.ISODate)


def to_bool(val: Union[str, int, float, bool, None], default_value: bool = True) -> bool:
    """ Convert lizmap config value to boolean """
    if isinstance(val, bool):
        return val

    if val is None or val == '':
        return default_value

    if isinstance(val, str):
        # For string, compare lower value to True string
        return val.lower() in ('yes', 'true', 't', '1')

    elif not val:
        # For value like False, 0, 0.0, None, empty list or dict returns False
        return False

    return default_value


def format_version_integer(version_string: str) -> str:
    """Transform version string to integers to allow comparing versions.

    Transform "0.1.2" into "000102"
    Transform "10.9.12" into "100912"
    """
    if version_string in ('master', 'dev'):
        return '000000'

    version_string = version_string.strip()

    output = ""

    for a in version_string.split("."):
        if '-' in a:
            a = a.split('-')[0]
        output += str(a.zfill(2))

    return output


def merge_strings(string_1: str, string_2: str) -> str:
    """ Merge two strings by removing the common part in between.

    'I like chocolate' and 'chocolate and banana' → 'I like chocolate and banana'
    """
    k = 0
    for i in range(1, len(string_2)):
        if string_1.endswith(string_2[:i]):
            k = i

    return string_1 + (string_2 if k is None else string_2[k:])


def convert_lizmap_popup(content: str, layer: QgsVectorLayer) -> Tuple[str, List[str]]:
    """ Convert an HTML Lizmap popup to QGIS HTML Maptip.

    If one or more field couldn't be found in the layer fields/alias, returned in errors.
    If all fields could be converted, an empty list is returned.
    """
    # An alias can have accent, space etc...
    pattern = re.compile(r"(\{\s?\$([_\w\s]+)\s?\})")
    lizmap_variables = pattern.findall(content)
    fields = layer.fields()

    translations = {}
    for field in fields:
        translations[field.name()] = field.alias()

    errors = []

    for variable in lizmap_variables:
        for field, alias in translations.items():
            if variable[1].strip() in (alias, field):
                content = content.replace(variable[0], '[% "{}" %]'.format(field))
                break
        else:
            errors.append(variable[1])

    return content, errors
