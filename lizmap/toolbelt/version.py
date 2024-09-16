""" Tools about version. """

__copyright__ = 'Copyright 2024, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from typing import Union

from qgis.core import Qgis

from lizmap.toolbelt.resources import metadata_config


def qgis_version():
    """ Return the QGIS version as integers. """
    return Qgis.versionInt()


def version(remove_v_prefix=True) -> str:
    """Return the version defined in metadata.txt."""
    v = metadata_config()["general"]["version"]
    if v.startswith("v") and remove_v_prefix:
        v = v[1:]
    return v


def format_qgis_version(input_version: Union[int, str], increase_odd_number=True) -> tuple:
    """ Split a QGIS int version number into major, minor, bugfix.

     If increase_odd_number is True and if the minor version is a dev version, the next stable minor version is set.
     Useful for QGIS, where stable versions are even numbers only.
     """
    if isinstance(input_version, str) and '.' in input_version:
        input_version = format_version_integer(input_version)

    input_version = str(input_version)

    bug_fix = int(input_version[-2:])
    input_version = input_version[:-2]

    minor = int(input_version[-2:])
    if minor % 2 and increase_odd_number:
        minor += 1

    major = int(input_version[:-2])

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
