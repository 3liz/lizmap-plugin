""" Tools to work with resource files. """

import configparser

from os.path import abspath, dirname, join, pardir

from qgis.PyQt import uic

__copyright__ = "Copyright 2024, 3Liz"
__license__ = "GPL version 3"
__email__ = "info@3liz.org"


def plugin_path(*args):
    """Get the path to plugin root folder.

    :param args List of path elements e.g. ['img', 'logos', 'image.png']
    :type args: str

    :return: Absolute path to the plugin path.
    :rtype: str
    """
    path = dirname(__file__)
    path = abspath(abspath(join(path, pardir)))
    for item in args:
        path = abspath(join(path, item))

    return path


def plugin_name():
    """Return the plugin name according to metadata.txt.

    :return: The plugin name.
    :rtype: basestring
    """
    metadata = metadata_config()
    name = metadata["general"]["name"]
    return name


def metadata_config() -> configparser:
    """Get the INI config parser for the metadata file.

    :return: The config parser object.
    :rtype: ConfigParser
    """
    path = plugin_path("metadata.txt")
    config = configparser.ConfigParser()
    config.read(path, encoding='utf8')
    return config


def resources_path(*args):
    """Get the path to our resources folder.

    :param args List of path elements e.g. ['img', 'logos', 'image.png']
    :type args: str

    :return: Absolute path to the resources folder.
    :rtype: str
    """
    path = abspath(abspath(join(plugin_path(), "resources")))
    for item in args:
        path = abspath(join(path, item))

    return path


def load_ui(*args):
    """Get compile UI file.

    :param args List of path elements e.g. ['img', 'logos', 'image.png']
    :type args: str

    :return: Compiled UI file.
    """
    ui_class, _ = uic.loadUiType(resources_path("ui", *args))
    return ui_class
