"""Configuration file for PyTest."""

import sys

from osgeo import gdal
from qgis.PyQt import Qt
from qgis.core import Qgis

__copyright__ = 'Copyright 2019, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


def pytest_report_header(config):
    """Used by PyTest and Unittest."""
    message = 'QGIS : {}\n'.format(Qgis.QGIS_VERSION_INT)
    message += 'Python GDAL : {}\n'.format(gdal.VersionInfo('VERSION_NUM'))
    message += 'Python : {}\n'.format(sys.version)
    # message += 'Python path : {}'.format(sys.path)
    message += 'QT : {}'.format(Qt.QT_VERSION_STR)
    return message
