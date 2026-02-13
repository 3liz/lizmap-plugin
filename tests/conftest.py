import logging
import sys

from pathlib import Path

import pytest

from qgis.core import Qgis, QgsApplication
from qgis.PyQt import Qt

from .qgis_testing import start_app

# with warnings.catch_warnings():
#    warnings.filterwarnings("ignore", category=DeprecationWarning)
#    from osgeo import gdal


def pytest_report_header(config):
    from osgeo import gdal

    return (
        f"QGIS : {Qgis.versionInt()}\n"
        f"Python GDAL : {gdal.VersionInfo('VERSION_NUM')}\n"
        f"Python : {sys.version}\n"
        f"QT : {Qt.QT_VERSION_STR}"
    )


#
# Fixtures
#


@pytest.fixture(scope="session")
def rootdir(request: pytest.FixtureRequest) -> Path:
    return request.config.rootpath


@pytest.fixture(scope="session")
def data(rootdir: Path) -> Path:
    return rootdir.joinpath("data")


#
# Session
#


# Path the 'qgis.utils.iface' property
# Which is not initialized when QGIS app
# is initialized from testing module

def pytest_sessionstart(session):
    """Start qgis application"""
    sys.path.append("/usr/share/qgis/python")
    start_app(session.path, False)

#
# Logger hook
#


def install_logger_hook(verbose: bool = False) -> None:
    """Install message log hook"""
    from qgis.core import Qgis

    # Add a hook to qgis  message log
    def writelogmessage(message, tag, level):
        arg = f"{tag}: {message}"
        if level == Qgis.MessageLevel.Warning:
            logging.warning(arg)
        elif level == Qgis.MessageLevel.Critical:
            logging.error(arg)
        elif verbose:
            # Qgis is somehow very noisy
            # log only if verbose is set
            logging.info(arg)

    messageLog = QgsApplication.messageLog()
    messageLog.messageReceived.connect(writelogmessage)
