import logging
import os
import shutil
import sys

from pathlib import Path

from qgis.core import QgsApplication


# Path the 'qgis.utils.iface' property
# Which is not initialized when QGIS app
# is initialized from testing module
def _patch_iface():
    import qgis.utils

    from qgis.testing.mocked import get_iface
    qgis.utils.iface = get_iface()


# NOTE: we cannot use qgis.testing.start_app() directly
# because it does not allow us to initialize the qgis settings
# path as we want.
def start_app(rootdir: Path, cleanup: bool = True):
    from qgis.PyQt.QtCore import QCoreApplication, Qt

    sys.path.append("/usr/share/qgis/python/plugins/")  # for processing

    display = os.getenv("DISPLAY")
    if not display:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"

    global QGISAPP

    QCoreApplication.setOrganizationName(QgsApplication.QGIS_ORGANIZATION_NAME)
    QCoreApplication.setOrganizationName(QgsApplication.QGIS_ORGANIZATION_DOMAIN)
    QCoreApplication.setApplicationName(QgsApplication.QGIS_APPLICATION_NAME)

    QCoreApplication.setAttribute(
        Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True
    )

    load_qgis_settings(rootdir)

    # See https://github.com/python/mypy/issues/5732
    QGISAPP = QgsApplication(  # type: ignore [name-defined]
        [],
        True,
        platformName="3liz-tests",
    )

    install_logger_hook(verbose=True)

    QGISAPP.initQgis()  # type: ignore [name-defined]
    print(QGISAPP.showSettings())  # type: ignore [name-defined]

    # Patch 'iface' in qgis.utils
    _patch_iface()

    if cleanup:
        import atexit

        @atexit.register
        def exitQgis():
            QGISAPP.exitQgis()


def init_processing():
    sys.path.append("/usr/share/qgis/python/plugins/")

    from processing.core.Processing import Processing
    Processing.initialize()


def load_qgis_settings(rootdir: Path):
    from qgis.core import QgsSettings
    from qgis.PyQt.QtCore import QSettings

    path = rootdir.joinpath(".qgis-settings")

    os.environ["QGIS_CUSTOM_CONFIG_PATH"] = str(path)
    os.environ["QGIS_OPTIONS_PATH"] = str(path)

    settings_path = path.joinpath("profiles", "default")

    # Copy the ini file at correct location
    settings_file = settings_path.joinpath(
        QgsApplication.QGIS_ORGANIZATION_DOMAIN,
        "QGIS3.ini",
    )
    settings_file.parent.mkdir(parents=True, exist_ok=True)

    # Copy the ini file
    settings = rootdir.joinpath("qgis_settings.ini")
    if settings.exists():
        shutil.copyfile(settings, settings_file)

    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(settings_path))

    qgssettings = QgsSettings()
    print("Settings loaded from ", qgssettings.fileName())


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
