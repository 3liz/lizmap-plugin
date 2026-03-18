"""Training features for the Lizmap plugin.

This module provides the TrainingManager class which handles training
operations using the delegate pattern.
"""
import tempfile

from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsAuthMethodConfig,
    QgsCoordinateReferenceSystem,
    QgsEditFormConfig,
    QgsExpression,
    QgsFileDownloader,
    QgsLayerTree,
    QgsLayerTreeGroup,
    QgsMapLayer,
    QgsMapLayerModel,
    QgsMapLayerProxyModel,
    QgsMasterLayoutInterface,
    QgsProject,
    QgsRasterLayer,
    QgsRectangle,
    QgsSettings,
    QgsVectorLayer,
    QgsWkbTypes,
)

from qgis.gui import QgsFileWidget
from qgis.utils import OverrideCursor
from qgis.PyQt.QtCore import (
    QCoreApplication,
    QEventLoop,
    QStorageInfo,
    Qt,
    QTranslator,
    QUrl,
)
from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt.QtWidgets import (
    QAction,
    QApplication,
    QDialogButtonBox,
    QFileDialog,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTreeWidgetItem,
    QWidget,
)

from ..definitions.definitions import ServerComboData
from lizmap.definitions.lizmap_cloud import (
    CLOUD_MAX_PARENT_FOLDER,
    CLOUD_NAME,
    CLOUD_QGIS_MIN_RECOMMENDED,
    TRAINING_PROJECT,
    TRAINING_ZIP,
    WORKSHOP_DOMAINS,
    WORKSHOP_FOLDER_ID,
    WORKSHOP_FOLDER_PATH,
    WorkshopType,
)

from ..definitions.online_help import Panels
from ..definitions.qgis_settings import Settings
from ..saas import check_project_ssl_postgis, is_lizmap_cloud, webdav_url
from ..toolbelt.i18n import tr

if TYPE_CHECKING:
    from ..dialogs.main import LizmapDialog

from .. import logger


class TrainingManager:
    """Manager for training operations in the Lizmap plugin.

    This class handles all training related functionality using the delegate
    pattern, providing a cleaner separation of concerns.
    """

    def __init__(
        self,
        *,
        dlg: "LizmapDialog",
        project: QgsProject,
        download_error: Callable,
    ):
        """Initialize the TrainingManager."""
        self.dlg = dlg
        self.project = project
        self.download_error = download_error

    def initialize(self, current_login: str) -> None:
        self.dlg.name_training_folder.setPlaceholderText(current_login)

        # When a ZIP is provided for the training
        self.dlg.path_training_folder_zip.setStorageMode(QgsFileWidget.StorageMode.GetDirectory)
        self.dlg.path_training_folder_zip.setDialogTitle(tr("Choose a folder to store the your data about the training"))
        self.dlg.download_training_data_zip.clicked.connect(partial(self.download_training_data_clicked, WorkshopType.ZipFile))
        self.dlg.open_training_project_zip.clicked.connect(partial(self.open_training_project_clicked, WorkshopType.ZipFile))
        self.dlg.open_training_folder_zip.clicked.connect(partial(self.open_training_folder_clicked, WorkshopType.ZipFile))

        # When an individual QGS file is provided for the training
        self.dlg.path_training_folder_qgs.setStorageMode(QgsFileWidget.StorageMode.GetDirectory)
        self.dlg.path_training_folder_qgs.setDialogTitle(tr("Choose a folder to store the your data about the training"))
        self.dlg.download_training_data_qgs.clicked.connect(partial(self.download_training_data_clicked, WorkshopType.IndividualQgsFile))
        self.dlg.open_training_project_qgs.clicked.connect(partial(self.open_training_project_clicked, WorkshopType.IndividualQgsFile))
        self.dlg.open_training_folder_qgs.clicked.connect(partial(self.open_training_folder_clicked, WorkshopType.IndividualQgsFile))


    def check_training_panel(self) -> None:
        """Check if the training panel should be visible or not."""
        current_url = self.dlg.current_server_info(ServerComboData.ServerUrl.value)
        # By default, set to a long training, with ZIP file
        # We check now step by step if it's a short training
        # with the login used with an existing QGS file on the server.
        self.dlg.workshop_type.setCurrentWidget(self.dlg.training_panel)

        if not current_url:
            self.dlg.mOptionsListWidget.item(Panels.Training).setHidden(True)
            return

        if bool([domain for domain in WORKSHOP_DOMAINS if (domain in current_url)]):
            self.dlg.mOptionsListWidget.item(Panels.Training).setHidden(False)

        logger.info(
            "Current server has been detected as a training server, set as long workshop by default for now. "
            "Checking then if it can be a short workshop."
        )

        metadata = self.dlg.current_server_info(ServerComboData.JsonMetadata.value)
        repositories = metadata.get("repositories")
        if not repositories:
            return

        from lizmap.definitions.lizmap_cloud import WORKSHOP_FOLDER_ID

        workshop = repositories.get(WORKSHOP_FOLDER_ID)
        if not workshop:
            return

        auth_id = self.dlg.current_server_info(ServerComboData.AuthId.value)
        user_project = workshop["projects"].get(self.login_from_auth_id(auth_id))
        if not user_project:
            return

        # Now set, to a short training with the prepared project
        # TODO remove or improve very soon
        # Fixme, the settings must be used, and not the UI checkbox
        self.dlg.send_webdav.setChecked(True)
        self.dlg.checkbox_save_project.setChecked(True)
        self.dlg.radio_beginner.setChecked(True)
        self.dlg.workshop_type.setCurrentWidget(self.dlg.quick_workshop_panel)
        logger.info(
            f"Remote project '{user_project.get('title')}', matching the user connected, "
            f"has been detected on the server. So set the workshop as short."
        )

    def download_training_data_clicked(self, workshop_type: str = WorkshopType.ZipFile):
        """ Download the hard coded ZIP. """
        if workshop_type == WorkshopType.IndividualQgsFile:
            if not self.dlg.path_training_folder_qgs.filePath():
                return
        else:
            if not self.dlg.path_training_folder_zip.filePath():
                return

        metadata = self.dlg.current_server_info(ServerComboData.JsonMetadata.value)
        url = webdav_url(metadata)
        if not url:
            self.dlg.display_message_bar(
                CLOUD_NAME,
                tr("WebDAV is not available on the instance '{}'").format(
                    self.dlg.current_server_info(ServerComboData.ServerUrl.value)),
                level=Qgis.MessageLevel.Critical,
            )

        if workshop_type == WorkshopType.IndividualQgsFile:
            auth_id = self.dlg.current_server_info(ServerComboData.AuthId.value)
            user_project = self.login_from_auth_id(auth_id)
            url_path = f"{url}/{WORKSHOP_FOLDER_PATH}/{user_project}.qgs"
            destination = str(
                self.training_folder_destination(WorkshopType.IndividualQgsFile).joinpath(f'{user_project}.qgs'))
        else:
            url_path = f"{url}/{TRAINING_ZIP}"
            destination = str(Path(tempfile.gettempdir()).joinpath(TRAINING_ZIP))

        downloader = QgsFileDownloader(
            QUrl(url_path),
            destination,
            delayStart=True,
            authcfg=self.dlg.current_server_info(ServerComboData.AuthId.value),
        )
        loop = QEventLoop()
        downloader.downloadExited.connect(loop.quit)
        downloader.downloadError.connect(self.download_error)
        # downloader.downloadCanceled.connect(self.download_canceled)
        if workshop_type == WorkshopType.IndividualQgsFile:
            downloader.downloadCompleted.connect(self.download_completed_qgs)
        else:
            downloader.downloadCompleted.connect(self.download_completed_zip)
        downloader.startDownload()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        loop.exec()

    @staticmethod
    def login_from_auth_id(auth_id: str) -> str:
        """ Login used in the QGIS password manager from an Auth ID. """
        auth_manager = QgsApplication.authManager()
        conf = QgsAuthMethodConfig()
        auth_manager.loadAuthenticationConfig(auth_id, conf, True)
        return conf.config('username')

    def training_folder_destination(self, workshop_type: str = WorkshopType.ZipFile) -> Optional[Path]:
        """ Destination folder where to store the data. """
        if workshop_type == WorkshopType.IndividualQgsFile:
            output = Path(self.dlg.path_training_folder_qgs.filePath())
            QgsSettings().setValue(Settings.key(Settings.LizmapRepository), WORKSHOP_FOLDER_ID)
        else:
            file_path = self.dlg.path_training_folder_zip.filePath()
            if not file_path:
                return None

            destination = self.destination_name()
            output = Path(file_path).joinpath(destination)
            QgsSettings().setValue(Settings.key(Settings.LizmapRepository), destination)

        if not output:
            return None

        if not output.exists():
            output.mkdir()

        return output

    def open_training_folder_clicked(self, workshop_type: str = WorkshopType.ZipFile):
        """ Open the training folder set above. """
        file_path = self.training_folder_destination(workshop_type)
        if not file_path:
            return

        # noinspection PyArgumentList
        QDesktopServices.openUrl(QUrl(f"file://{file_path}"))

    def open_training_project_clicked(self, workshop_type: str = WorkshopType.ZipFile):
        """ Open the training project in QGIS Desktop. """
        file_path = self.training_folder_destination(workshop_type)
        if workshop_type == WorkshopType.IndividualQgsFile:
            auth_id = self.dlg.current_server_info(ServerComboData.AuthId.value)
            user_project = self.login_from_auth_id(auth_id)
            project_path = str(file_path.joinpath(f"{user_project}.qgs"))
        else:
            user_project = self.current_login()
            project_path = str(file_path.joinpath(TRAINING_PROJECT))

        if not file_path:
            return

        with OverrideCursor(Qt.CursorShape.WaitCursor):
            self.project.read(project_path)
            # Rename the project
            self.project.writeEntry("WMSServiceTitle", "/", user_project)

        # Enable the "Upload" panel
        item = self.dlg.mOptionsListWidget.item(Panels.Upload)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEnabled)

        variables = self.project.customVariables()
        if 'lizmap_user' in list(variables.keys()):
            del variables['lizmap_user']
        if 'lizmap_user_groups' in list(variables.keys()):
            del variables['lizmap_user_groups']
        self.project.setCustomVariables(variables)

    def download_completed_qgs(self):
        """ Extract the downloaded QGS. """
        # We start again about CFG file
        metadata = self.dlg.current_server_info(ServerComboData.JsonMetadata.value)
        url = webdav_url(metadata)
        auth_id = self.dlg.current_server_info(ServerComboData.AuthId.value)
        user_project = self.login_from_auth_id(auth_id)
        url_path = f"{url}/{WORKSHOP_FOLDER_PATH}/{user_project}.qgs.cfg"
        destination = str(
            self.training_folder_destination(WorkshopType.IndividualQgsFile).joinpath(f'{user_project}.qgs.cfg'))

        downloader = QgsFileDownloader(
            QUrl(url_path),
            destination,
            delayStart=True,
            authcfg=self.dlg.current_server_info(ServerComboData.AuthId.value),
        )
        loop = QEventLoop()
        downloader.downloadExited.connect(loop.quit)
        downloader.downloadError.connect(self.download_error)
        # downloader.downloadCanceled.connect(self.download_canceled)
        downloader.downloadCompleted.connect(self.download_completed)
        downloader.startDownload()
        loop.exec()

