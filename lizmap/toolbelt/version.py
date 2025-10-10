"""Tools about version."""

from typing import Tuple

from lizmap.toolbelt.resources import metadata_config

PACKAGE_NAME = "lizmap"


def version(remove_prefix: bool = True) -> str:
    """Return the version defined in metadata.txt."""
    v = metadata_config()["general"]["version"]
    if remove_prefix:
        v = v.removeprefix("v")
    return v


def qgis_version_info(
    version_int: int,
    increase_odd_number: bool = True,
) -> Tuple[int, int, int]:
    """Split a QGIS int version number into major, minor, bugfix.

    If increase_odd_number is True and if the minor version is a dev version,
    the next stable minor version is set.
    Useful for QGIS, where stable versions are even numbers only.
    """
    major = version_int // 100 // 100
    minor = version_int // 100 % 100
    patch = version_int % 100

    if increase_odd_number and minor % 2 and minor < 99:
        minor += 1

    return (major, minor, patch)


def format_version_integer(version_string: str) -> str:
    """Transform version string to integers to allow comparing versions.

    Transform "0.1.2" into "000102"
    Transform "10.9.12" into "100912"
    """
    if version_string in ("master", "dev"):
        return "000000"

    version_string = version_string.strip()

    output = ""

    for a in version_string.split("."):
        if "-" in a:
            a = a.split("-")[0]
        output += str(a.zfill(2))

    return output
