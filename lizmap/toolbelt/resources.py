"""Tools to work with resource files."""

import configparser
import functools

from importlib import resources
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Type,
    Union,
    cast,
)

if TYPE_CHECKING:
    from qgis.PyQt.QtGui import QIcon


PACKAGE_NAME = "lizmap"


def plugin_path(*args: Union[str, Path]) -> Path:
    """Get the path to plugin root folder.

    :param args List of path elements e.g. ['img', 'logos', 'image.png']
    :type args: str

    :return: Absolute path to the plugin path.
    :rtype: str
    """
    # Use the canonical way to get module resources path
    return cast("Path", resources.files(PACKAGE_NAME)).joinpath(*args)


def plugin_name() -> str:
    """Return the plugin name according to metadata.txt.

    :return: The plugin name.
    :rtype: basestring
    """
    return metadata_config()["general"]["name"]


@functools.cache
def metadata_config() -> configparser.ConfigParser:
    """Get the INI config parser for the metadata file.

    :return: The config parser object.
    :rtype: ConfigParser
    """
    path = plugin_path("metadata.txt")
    config = configparser.ConfigParser()
    config.read(path)
    return config


def resources_path(*args: Union[str, Path]) -> str:
    """Get the path to our resources folder."""
    return str(plugin_path("resources", *args))


def load_icon(*args: Union[str, Path]) -> "QIcon":
    from qgis.PyQt.QtGui import QIcon

    return QIcon(resources_path("icons", *args))


@functools.cache
def window_icon() -> "QIcon":
    return load_icon("icon.png")


def load_ui(*args) -> Type:
    """Get compiled UI file.

    :param args List of path elements e.g. ['img', 'logos', 'image.png']
    :type args: str

    :return: Compiled UI file.
    """
    from qgis.PyQt import uic

    ui_class, _ = uic.loadUiType(resources_path("ui", *args))
    return ui_class
