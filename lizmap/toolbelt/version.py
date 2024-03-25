""" Tools about version. """

__copyright__ = 'Copyright 2024, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from qgis.core import Qgis

from lizmap.toolbelt.resources import metadata_config


def qgis_version():
    """ Return the QGIS version as integers. """
    # The API has changed in QGIS 3.12
    # Use the function layer
    # noinspection PyUnresolvedReferences
    return Qgis.QGIS_VERSION_INT


def version(remove_v_prefix=True) -> str:
    """Return the version defined in metadata.txt."""
    v = metadata_config()["general"]["version"]
    if v.startswith("v") and remove_v_prefix:
        v = v[1:]
    return v


def format_qgis_version(qgis_version: int) -> tuple:
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
