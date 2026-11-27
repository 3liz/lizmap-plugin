from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Protocol,
)
from urllib.parse import unquote

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsExpressionContextUtils,
    QgsProject,
    QgsSettings,
)

if TYPE_CHECKING:
    from qgis.gui import QgisInterface

from qgis.PyQt.QtCore import (
    Qt,
    QUrl,
)
from qgis.PyQt.QtGui import (
    QDesktopServices,
    QIcon,
)
from qgis.PyQt.QtWidgets import (
    QMessageBox,
    QPushButton,
)
from qgis.utils import OverrideCursor

from lizmap.definitions.definitions import (
    DURATION_WARNING_BAR,
    RepositoryComboData,
    ServerComboData,
)

from ..definitions.definitions import LwcVersions
from ..definitions.online_help import Panels
from ..definitions.qgis_settings import Settings
from ..dialogs.server_wizard import CreateFolderWizard
from ..server_dav import WebDav
from ..sync.backends.admin_api import (
    HTTP_FORBIDDEN,
    HTTP_NOT_FOUND,
    HTTP_UNAUTHORIZED,
    LizmapAdminApi,
)
from ..sync.backends.base import BackendError
from ..sync.backends.webdav import WebDavBackend, WebDavServer
from ..sync.gui.new_repository_dialog import NewRepositoryDialog
from ..sync.gui.options_dialog import SyncOptionsDialog, load_options, save_options
from ..sync.gui.project_checks import (
    checkpoint_sqlite,
    layers_with_pending_edits,
    project_files,
)
from ..sync.gui.sync_panel import SyncContext, SyncPanel, SyncUnavailable
from ..sync.model import Direction
from ..sync.options import SyncOptions, read_rules, read_rules_text, write_rules
from ..sync.pair import PairKind, SyncPair
from ..sync.state import StateError, SyncState, state_file_name
from ..toolbelt.i18n import tr
from ..toolbelt.resources import (
    load_icon,
    window_icon,
)
from ..toolbelt.strings import human_size, path_to_url

if TYPE_CHECKING:
    from ..dialogs.main import LizmapDialog

from .. import logger

# Identifier of the shared media in the state of the synchronisation, instead of a repository
SHARED_MEDIA_STATE = "__shared_media__"


class LizmapProtocol(Protocol):
    dlg: "LizmapDialog"
    project: QgsProject

    iface: "QgisInterface"

    @property
    def lwc_version(self) -> LwcVersions: ...

    def refresh_single_layer(self, row: int): ...


class WebDavManager(LizmapProtocol):
    _webdav: WebDav
    sync_panel: SyncPanel

    # Called on __init__()
    def initialize_webdav(self):
        self._webdav = WebDav()
        self._webdav.setup_webdav_dialog(self.dlg)

        self.dlg.button_refresh_date_webdav.setIcon(QIcon(QgsApplication.iconPath("mActionRefresh.svg")))
        self.dlg.button_refresh_date_webdav.setText("")
        self.dlg.button_refresh_date_webdav.setToolTip("The date time of the file on the server.")
        self.dlg.button_refresh_date_webdav.clicked.connect(self.check_latest_update_webdav)

        self.dlg.button_create_repository.clicked.connect(self.create_new_repository)
        self.dlg.button_create_repository.setIcon(QIcon(":/images/themes/default/mActionNewFolder.svg"))
        self.dlg.button_create_media_remote.setIcon(QIcon(":/images/themes/default/mActionNewFolder.svg"))
        self.dlg.button_create_media_local.setIcon(QIcon(":/images/themes/default/mActionNewFolder.svg"))
        buttons = (
            self.dlg.button_upload_thumbnail,
            self.dlg.button_upload_action,
            self.dlg.button_upload_webdav,
            self.dlg.button_upload_media,
        )
        for button in buttons:
            button.setIcon(load_icon("upload.svg"))
            button.setText("")
            self.dlg.set_tooltip_webdav(button)
        self.dlg.button_upload_thumbnail.clicked.connect(self.upload_thumbnail)
        self.dlg.button_upload_action.clicked.connect(self.upload_action)
        self.dlg.button_upload_webdav.clicked.connect(self.send_files)
        self.dlg.button_upload_media.clicked.connect(self.upload_media)
        self.dlg.button_create_media_remote.clicked.connect(self.create_media_dir_remote)
        self.dlg.button_create_media_local.clicked.connect(self.create_media_dir_local)

        # Synchronisation, replacing the previous widgets when the WebDAV module supports it
        self.sync_panel = SyncPanel(
            self.dlg.page_upload,
            self.sync_context,
            self.dlg.repository_combo,
            self.new_repository,
            self.open_sync_options,
        )
        self.sync_panel.synchronised.connect(self._after_synchronisation)
        self.sync_panel.directionChanged.connect(self._save_sync_direction)
        self.sync_panel.setVisible(False)
        layout = self.dlg.page_upload.layout()
        layout.insertWidget(0, self.sync_panel)
        # The automatic upload when saving stays visible with both interfaces
        layout.addWidget(self.dlg.send_webdav)

    def _sync_server(self) -> WebDavServer | None:
        """WebDAV capabilities of the current server, if it supports the synchronisation.

        :return: The capabilities, None if the WebDAV module is missing or too old.
        """
        metadata = self.dlg.server_combo.currentData(ServerComboData.JsonMetadata.value)
        server = WebDavServer.from_metadata(metadata)
        return server if server and server.supports_sync else None

    def sync_context(self) -> SyncContext:
        """Build the context of the synchronisation, after checking the project.

        Called by the synchronisation panel when the user clicks on "Compare".

        :return: The context.
        :raises SyncUnavailable: With a message for the user if the synchronisation is not possible.
        """
        server = self._sync_server()
        if server is None:
            raise SyncUnavailable(tr("The WebDAV module of the server must be upgraded to synchronise."))

        # Repository on the server
        repository_id = self.dlg.current_repository(RepositoryComboData.Id)
        repository_path = self.dlg.current_repository(RepositoryComboData.Path)
        if not repository_id:
            raise SyncUnavailable(tr("Choose a Lizmap repository."))
        try:
            url = server.repository_url(repository_path)
        except ValueError:
            raise SyncUnavailable(
                tr(
                    "The directory of the repository <b>{}</b> is outside of the root directory of the "
                    "repositories on the server, it can't be synchronised."
                ).format(repository_id)
            ) from None

        # The project must be saved, as a QGS file
        if not self.project.fileName():
            raise SyncUnavailable(tr("Save the project first."))
        project_file = Path(self.project.fileName())
        if project_file.suffix.lower() != ".qgs":
            raise SyncUnavailable(tr("Lizmap Web Client needs a QGS project, not a QGZ one."))
        pending = layers_with_pending_edits(self.project)
        if pending:
            raise SyncUnavailable(tr("Save the edits of these layers first: {}").format(", ".join(pending)))
        if self.project.isDirty():
            answer = QMessageBox.question(
                self.dlg,
                tr("Unsaved project"),
                tr("The project has unsaved changes. Do you want to save it before the comparison?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                raise SyncUnavailable(tr("Save the project before the comparison."))
            self.project.write()

        # Files used by the layers, GeoPackage edits written in the main files
        root = project_file.parent.resolve()
        files = project_files(self.project, root)
        for path, error in checkpoint_sqlite(list(files.values())).items():
            logger.warning(f"Synchronisation, checkpoint of {path} : {error}")

        server_url = self.dlg.server_combo.currentData(ServerComboData.ServerUrl.value)
        auth_id = self.dlg.server_combo.currentData(ServerComboData.AuthId.value)
        repository_label = self.dlg.repository_combo.currentText() or repository_id

        # The repository, and the "media" directory shared by all repositories, "../media" locally
        options = load_options()
        pairs = [
            self._sync_pair(
                PairKind.Repository,
                tr('Repository "{}"').format(repository_label),
                WebDavBackend(url, auth_id),
                unquote(url[len(server.url) :]),
                root,
                server_url,
                repository_id,
                options,
            ),
            self._sync_pair(
                PairKind.SharedMedia,
                tr("Shared media"),
                WebDavBackend(server.shared_media_url(), auth_id),
                unquote(server.shared_media_url()[len(server.url) :]),
                root.parent.joinpath("media"),
                server_url,
                SHARED_MEDIA_STATE,
                options,
            ),
        ]
        return SyncContext(
            pairs=pairs,
            server_label=server.url,
            protected_paths=frozenset(files),
            project_path=project_file.name,
        )

    @staticmethod
    def _sync_pair(
        kind: PairKind,
        label: str,
        backend: WebDavBackend,
        remote_label: str,
        root: Path,
        server_url: str,
        state_key: str,
        options: SyncOptions,
    ) -> SyncPair:
        """Build a pair of directories, with its state and its settings.

        :param kind: Kind of pair.
        :param label: Name displayed in the tree.
        :param backend: The directory on the server.
        :param remote_label: Path of the directory on the WebDAV server.
        :param root: The local directory.
        :param server_url: URL of the Lizmap server.
        :param state_key: Identifier of the remote directory in the state, such as the repository.
        :param options: The options of the synchronisation.
        :return: The pair.
        """
        # State of the last synchronisation, in the QGIS profile
        state_file = Path(QgsApplication.qgisSettingsDirPath()).joinpath(
            "lizmap", "sync", state_file_name(server_url, state_key, str(root))
        )
        try:
            state = SyncState.load(state_file, server_url, state_key, str(root))
        except StateError as e:
            logger.warning(f"Synchronisation state ignored : {e}")
            state = SyncState(server_url, state_key, str(root))

        # Direction chosen by the user, then the options
        saved = QgsSettings().value(Settings.key(f"{Settings.SyncDirection}/{kind.value}"), "", str)
        direction = Direction(saved) if saved in {d.value for d in Direction} else None
        settings = options.pair_settings(kind, direction)

        # Excluded files, from the rules file of the directory
        patterns, invalid = read_rules(root)
        if invalid:
            logger.warning(f"Synchronisation, unsupported rules in {root} : {', '.join(invalid)}")

        return SyncPair(
            kind=kind,
            label=label,
            backend=backend,
            root=root,
            state=state,
            state_file=state_file,
            rules=options.exclude_rules(patterns),
            settings=settings,
            remote_label=remote_label,
        )

    def open_sync_options(self) -> bool:
        """Edit the options of the synchronisation.

        The excluded files are written in the rules file of each directory, the other options
        are personal settings.

        :return: True if the user changed the options.
        """
        if not self.project.fileName():
            self.dlg.display_message_bar(
                "Lizmap", tr("Save the project first."), level=Qgis.MessageLevel.Warning
            )
            return False

        root = Path(self.project.fileName()).parent.resolve()
        roots = {PairKind.Repository: root, PairKind.SharedMedia: root.parent.joinpath("media")}
        labels = {PairKind.Repository: tr("Repository"), PairKind.SharedMedia: tr("Shared media")}
        rules = {kind: (labels[kind], read_rules_text(path)) for kind, path in roots.items()}

        dialog = SyncOptionsDialog(self.dlg, load_options(), rules)
        if not dialog.exec():
            return False

        save_options(dialog.options())
        for kind, text in dialog.changed_rules().items():
            write_rules(roots[kind], text)
        return True

    @staticmethod
    def _save_sync_direction(kind: PairKind, direction: Direction):
        """Keep the direction chosen by the user for a kind of pair.

        :param kind: The kind of pair.
        :param direction: The direction.
        """
        QgsSettings().setValue(Settings.key(f"{Settings.SyncDirection}/{kind.value}"), direction.value)

    def _after_synchronisation(self, project_downloaded: bool):
        """Warn the user if the open project has been replaced by the synchronisation.

        :param project_downloaded: True if the project file has been downloaded.
        """
        if project_downloaded:
            self.dlg.display_message_bar(
                "Lizmap",
                tr("The project file has been replaced by the version of the server, reopen the project."),
                level=Qgis.MessageLevel.Warning,
                duration=DURATION_WARNING_BAR,
            )

    def check_webdav(self):
        """Check if we can enable or the webdav, according to the current selected server."""

        # I hope temporary, to force the version displayed
        self.dlg.refresh_helper_target_version(self.lwc_version)

        def disable_upload_panel():
            self.dlg.mOptionsListWidget.item(Panels.Upload).setHidden(True)
            if self.dlg.mOptionsListWidget.currentRow() == Panels.Upload:
                self.dlg.mOptionsListWidget.setCurrentRow(Panels.Information)

        # FIXME: This cannot happend
        if not self._webdav:
            self.dlg.webdav_frame.setVisible(False)
            self.dlg.button_upload_thumbnail.setVisible(False)
            self.dlg.button_upload_action.setVisible(False)
            self.dlg.button_upload_media.setVisible(False)
            self.dlg.button_create_media_remote.setVisible(False)
            disable_upload_panel()
            return

        self._webdav.config_project()

        # The dialog is already given.
        # We can check if WebDAV is supported.
        if self._webdav.setup_webdav_dialog():
            # self.dlg.group_upload.setVisible(True)
            # self.dlg.send_webdav.setEnabled(True)
            # self.dlg.send_webdav.setVisible(True)
            self.dlg.webdav_frame.setVisible(True)
            self.dlg.button_upload_thumbnail.setVisible(True)
            self.dlg.button_upload_action.setVisible(True)
            self.dlg.button_upload_media.setVisible(True)
            self.dlg.button_create_media_remote.setVisible(True)
            self.dlg.mOptionsListWidget.item(Panels.Upload).setHidden(False)

            # The synchronisation replaces the previous widgets if the WebDAV module supports it.
            # The previous widgets are kept for the servers without the WebDAV module 1.3: Lizmap Web Client
            # 3.8, or a newer version with an older module. To remove when these servers are not supported.
            sync = self._sync_server() is not None
            self.sync_panel.setVisible(sync)
            self.dlg.scrollArea_16.setVisible(not sync)
        else:
            self.sync_panel.setVisible(False)
            self.dlg.scrollArea_16.setVisible(True)
            # self.dlg.group_upload.setVisible(False)
            # self.dlg.send_webdav.setChecked(False)
            # self.dlg.send_webdav.setEnabled(False)
            # self.dlg.send_webdav.setVisible(False)
            self.dlg.webdav_frame.setVisible(False)
            self.dlg.button_upload_thumbnail.setVisible(False)
            self.dlg.button_upload_action.setVisible(False)
            self.dlg.button_upload_media.setVisible(False)
            self.dlg.button_create_media_remote.setVisible(False)
            disable_upload_panel()

    def refresh_single_layer(self, row: int):
        """Refresh a single layer status."""
        relative_path_layer = self.dlg.table_files.item(row, 1).data(self.dlg.table_files.RELATIVE_PATH)
        # Refresh date and size from the server
        result, error = self._webdav.file_stats(path_to_url(relative_path_layer))
        if result:
            self.dlg.table_files.file_status(
                row, result.last_modified_pretty, human_size(result.content_length)
            )
        elif result is None and not error:
            self.dlg.table_files.file_status(row, tr("Error"), tr("Not found on the server"))
        else:
            self.dlg.table_files.file_status(row, tr("Error"), error)

    def refresh_all_layers(self):
        """Refresh the status of all layers."""
        for row in range(self.dlg.table_files.rowCount()):
            self.dlg.table_files.file_status(row, tr("Work in progress"), tr("Work in progress"))

        with OverrideCursor(Qt.CursorShape.WaitCursor):
            for row in range(self.dlg.table_files.rowCount()):
                self.refresh_single_layer(row)

    def send_all_layers(self):
        """Send all layers from the table on the server."""
        for row in range(self.dlg.table_files.rowCount()):
            self.dlg.table_files.file_status(row, tr("Work in progress"), tr("Work in progress"))

        with OverrideCursor(Qt.CursorShape.WaitCursor):
            for row in range(self.dlg.table_files.rowCount()):
                relative_path_layer = self.dlg.table_files.item(row, 1).data(
                    self.dlg.table_files.RELATIVE_PATH
                )
                absolute_path_layer = self.dlg.table_files.item(row, 1).data(
                    self.dlg.table_files.ABSOLUTE_PATH
                )

                # Create recursive directories
                self._webdav.make_dirs_recursive(relative_path_layer, exists_ok=True)

                # Upload the layer path
                self._webdav.put_file(absolute_path_layer, relative_path_layer)

                # Refresh date and size from the server
                result, error = self._webdav.file_stats(path_to_url(relative_path_layer))
                if result:
                    self.dlg.table_files.file_status(
                        row, result.last_modified_pretty, human_size(result.content_length)
                    )
                elif result is None and not error:
                    self.dlg.table_files.file_status(row, tr("Error"), tr("Not found on the server"))
                else:
                    self.dlg.table_files.file_status(row, tr("Error"), error)

    def new_repository(self):
        """Create a repository from the synchronisation panel.

        With Lizmap Web Client 3.10 or newer, the repository is created with the administration API,
        in a new directory or in an existing one not used yet. Otherwise, the previous wizard is used.
        """
        server_url = self.dlg.server_combo.currentData(ServerComboData.ServerUrl.value)
        auth_id = self.dlg.server_combo.currentData(ServerComboData.AuthId.value)
        if not server_url:
            return

        api = LizmapAdminApi(server_url, auth_id)
        try:
            with OverrideCursor(Qt.CursorShape.WaitCursor):
                paths = api.paths()
        except BackendError as e:
            if e.http_status == HTTP_NOT_FOUND:
                # The API doesn't exist before Lizmap Web Client 3.10
                self.create_new_repository()
                return
            if e.http_status in (HTTP_UNAUTHORIZED, HTTP_FORBIDDEN):
                message = tr("You must be an administrator of the server to create a repository.")
            else:
                message = str(e)
            self.dlg.display_message_bar(
                "Lizmap", message, level=Qgis.MessageLevel.Warning, duration=DURATION_WARNING_BAR
            )
            return

        metadata = self.dlg.server_combo.currentData(ServerComboData.JsonMetadata.value) or {}
        repositories = metadata.get("repositories") or {}
        existing = repositories.keys() if isinstance(repositories, dict) else []
        dialog = NewRepositoryDialog(self.dlg, api, paths, existing)
        if not dialog.exec() or not dialog.created_key:
            return

        # Selected once the list of the repositories is refreshed from the server
        QgsExpressionContextUtils.setProjectVariable(self.project, "lizmap_repository", dialog.created_key)
        self.dlg.refresh_versions_button.click()
        self.dlg.display_message_bar(
            "Lizmap",
            tr("The repository <b>{}</b> has been created.").format(dialog.created_key),
            level=Qgis.MessageLevel.Success,
            duration=DURATION_WARNING_BAR,
        )

    def create_new_repository(self):
        """Open wizard to create a new remote repository."""
        dialog = CreateFolderWizard(
            self.dlg,
            webdav_server=self._webdav.dav_server,
            auth_id=self._webdav.auth_id,
            url=self._webdav.server_url(),
        )
        dialog.exec()
        self.dlg.refresh_versions_button.click()

    def send_webdav(self) -> tuple[bool, str, str]:
        """Sync the QGS and CFG file over the webdav."""
        folder = self.dlg.current_repository(RepositoryComboData.Path)
        if not folder:
            # Maybe we are on a new server ?
            return False, "", ""

        with OverrideCursor(Qt.CursorShape.WaitCursor):
            qgis_exists, error = self._webdav.check_exists_qgs()
        if error:
            self.iface.messageBar().pushMessage(
                "Lizmap",
                error,
                level=Qgis.MessageLevel.Critical,
                duration=DURATION_WARNING_BAR,
            )
            return False, "", ""

        server = self.dlg.server_combo.currentData(ServerComboData.ServerUrl.value)
        if not qgis_exists:
            box = QMessageBox(self.dlg)
            box.setIcon(QMessageBox.Icon.Question)
            box.setWindowIcon(window_icon())
            box.setWindowTitle(tr("The project is not published yet"))
            box.setText(
                tr(
                    'The project <b>"{}"</b> does not exist yet on the server <br>'
                    '<b>"{}"</b> '
                    'in the folder <b>"{}"</b>.'
                    "<br><br>"
                    "Do you want to publish it for the first time in this directory ?"
                ).format(self.project.baseName(), server, folder)
            )
            box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            box.setDefaultButton(QMessageBox.StandardButton.No)
            result = box.exec()
            if result == QMessageBox.StandardButton.No:
                return False, "", ""

        with OverrideCursor(Qt.CursorShape.WaitCursor):
            flag, error, url = self._webdav.send_all_project_files()
        if not flag:
            # Error while sending files
            logger.error(error)
            self.iface.messageBar().pushMessage(
                "Lizmap", error, level=Qgis.MessageLevel.Critical, duration=DURATION_WARNING_BAR
            )
            return False, error, ""

        logger.debug(f"Webdav has been OK : {url}")
        self.check_latest_update_webdav()

        if flag and qgis_exists:
            # Everything went fine
            return True, "", url

        # Only the first time if the project didn't exist before
        # noinspection PyArgumentList
        QDesktopServices.openUrl(QUrl(url))
        return True, "", url

    def check_latest_update_webdav(self):
        """Check the latest date about QGS file on the server."""
        with OverrideCursor(Qt.CursorShape.WaitCursor):
            self.dlg.line_qgs_date.setText("")
            result, error = self._webdav.file_stats_qgs()
            if result:
                url = self._webdav.project_url()
                self.dlg.webdav_last_update.setText(f'<a href="{url}">{result.last_modified_pretty}</a>')
                self.dlg.webdav_last_update.setOpenExternalLinks(True)
                self.dlg.set_tooltip_webdav(self.dlg.button_upload_webdav, result.last_modified_pretty)
                self.dlg.line_qgs_date.setText(
                    f"{result.last_modified_pretty} : {human_size(result.content_length)}"
                )
            elif result is None and not error:
                directory = self.dlg.current_repository()
                self.dlg.line_qgs_date.setText(
                    tr("Project {name} not found in {folder}").format(
                        name=self.project.baseName(), folder=directory
                    )
                )
            else:
                self.dlg.webdav_last_update.setText(tr("Error"))
                self.dlg.webdav_last_update.setToolTip(error)
                self.dlg.line_qgs_date.setText(error)
                logger.error(error)

    def check_all_dates_dav(self):
        """Check all dates on the Web DAV server."""
        self.check_latest_update_webdav()
        self._refresh_cfg()
        self._refresh_thumbnail()
        self._refresh_action()

        # Media
        self.dlg.line_media_date.setText("")
        with OverrideCursor(Qt.CursorShape.WaitCursor):
            result, error = self._webdav.file_stats_media()
            if result:
                self.dlg.line_media_date.setText(result.last_modified_pretty)
            else:
                self.dlg.line_media_date.setText(error)

    def remove_remote_file(self, button: QPushButton):
        """Remove a remote file."""
        if self._question_remove_remote_file():
            return
        with OverrideCursor(Qt.CursorShape.WaitCursor):
            if "qgs" in button.objectName():
                self._webdav.remove_qgs()
                self.check_latest_update_webdav()
            elif "cfg" in button.objectName():
                self._webdav.remove_cfg()
                self._refresh_cfg()
            elif "action" in button.objectName():
                self._webdav.remove_action()
                self._refresh_action()
            elif "thumbnail" in button.objectName():
                self._webdav.remove_thumbnail()
                self._refresh_thumbnail()

    def remove_remote_layer_index(self, row: int):
        """Remove a layer from the remote server."""
        if self._question_remove_remote_file():
            return
        relative_path_layer = self.dlg.table_files.item(row, 1).data(self.dlg.table_files.RELATIVE_PATH)
        self._webdav.remove_file(str(relative_path_layer))
        self.refresh_single_layer(row)

    def upload_action(self):
        """Upload the action file on the server."""
        with OverrideCursor(Qt.CursorShape.WaitCursor):
            result, error = self._webdav.send_action()
        if not result and error:
            self.dlg.display_message_bar(
                "Lizmap",
                error,
                level=Qgis.MessageLevel.Critical,
                duration=DURATION_WARNING_BAR,
            )
            return

        if result:
            self.dlg.display_message_bar(
                "Lizmap",
                tr("Upload of the action file is successful."),
                level=Qgis.MessageLevel.Success,
                duration=DURATION_WARNING_BAR,
            )
            file_stats, error = self._webdav.file_stats_action()
            if error:
                logger.error(error)
                return
            self.dlg.set_tooltip_webdav(self.dlg.button_upload_action, file_stats.last_modified_pretty)
            self.dlg.line_action_date.setText(file_stats.last_modified_pretty)

    def _refresh_cfg(self):
        """Refresh CFG."""
        with OverrideCursor(Qt.CursorShape.WaitCursor):
            directory = self.dlg.current_repository()
            self.dlg.line_cfg_date.setText("")
            result, error = self._webdav.file_stats_cfg()
            if result:
                self.dlg.line_cfg_date.setText(
                    f"{result.last_modified_pretty} : {human_size(result.content_length)}"
                )
            elif result is None and not error:
                self.dlg.line_cfg_date.setText(
                    tr("Project {name} not found in {folder}").format(
                        name=self.project.baseName(), folder=directory
                    )
                )
            else:
                self.dlg.line_cfg_date.setText(error)

    def _refresh_action(self):
        """Refresh action."""
        with OverrideCursor(Qt.CursorShape.WaitCursor):
            self.dlg.line_action_date.setText("")
            result, error = self._webdav.file_stats_action()
            if result:
                self.dlg.line_action_date.setText(result.last_modified_pretty)
                self.dlg.set_tooltip_webdav(self.dlg.button_upload_action, result.last_modified_pretty)
            else:
                self.dlg.line_action_date.setText(error)

    def _refresh_thumbnail(self):
        """Refresh thumbnail."""
        with OverrideCursor(Qt.CursorShape.WaitCursor):
            directory = self.dlg.current_repository()
            self.dlg.line_thumbnail_date.setText("")
            result, error = self._webdav.file_stats_thumbnail()
            if result:
                self.dlg.line_thumbnail_date.setText(
                    f"{result.last_modified_pretty} : {human_size(result.content_length)}"
                )
                self.dlg.set_tooltip_webdav(self.dlg.button_upload_thumbnail, result.last_modified_pretty)
            elif result is None and not error:
                self.dlg.line_thumbnail_date.setText(
                    tr("Project thumbnail {name} not found in {folder}").format(
                        name=self.project.baseName(), folder=directory
                    )
                )
            else:
                self.dlg.line_thumbnail_date.setText(error)

    def _question_remove_remote_file(self) -> bool:
        """Question to confirme deletion on the remote server."""
        box = QMessageBox(self.dlg)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowIcon(window_icon())
        box.setWindowTitle(tr("Remove a remote file"))
        box.setText(tr("Are you sure you want to remove the remote file ?"))
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        result = box.exec()
        return result == QMessageBox.StandardButton.No

    def create_media_dir_remote(self):
        """Create the remote "media" directory."""
        directory = self.dlg.current_repository(RepositoryComboData.Path)
        if not directory:
            return

        with OverrideCursor(Qt.CursorShape.WaitCursor):
            result, msg = self._webdav.file_stats_media()
        if result is not None:
            self.dlg.display_message_bar(
                "Lizmap",
                tr(
                    'The "media" directory was already existing on the server. '
                    "Please check with a file browser."
                ),
                level=Qgis.MessageLevel.Info,
                duration=DURATION_WARNING_BAR,
                more_details=msg,
            )
            return

        box = QMessageBox(self.dlg)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowIcon(window_icon())
        box.setWindowTitle(tr('Create "media" directory on the server'))
        box.setText(
            tr(
                'Are you sure you want to create the "media" directory on the '
                "server <strong>{server}</strong> in the "
                "Lizmap repository <strong>{name}</strong> ?"
            ).format(
                server=self.dlg.server_combo.currentText(),
                name=self.dlg.repository_combo.currentText(),
            )
        )
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        result = box.exec()
        if result == QMessageBox.StandardButton.No:
            return

        directory += "media/"
        result, msg = self._webdav.make_dir(directory)
        if not result and msg:
            self.dlg.display_message_bar(
                "Lizmap", msg, level=Qgis.MessageLevel.Critical, duration=DURATION_WARNING_BAR
            )
            return

        self.dlg.display_message_bar(
            "Lizmap",
            tr('The "media" directory has been created'),
            level=Qgis.MessageLevel.Success,
            duration=DURATION_WARNING_BAR,
        )

    def create_media_dir_local(self):
        """Create the local "media" directory."""
        media = Path(self.project.fileName()).parent.joinpath("media")
        media.mkdir(exist_ok=True)
        self.dlg.display_message_bar(
            "Lizmap",
            tr('The local <a href="file://{}">"media"</a> directory has been created').format(media),
            level=Qgis.MessageLevel.Success,
            duration=DURATION_WARNING_BAR,
        )

    def upload_media(self):
        """Upload the current media path on the server."""
        current_path = self.dlg.inLayerLink.text()

        # On Windows, it's like media\photo.png
        # TODO check line below
        # current_path = current_path.replace('\\', '/')

        if not current_path.startswith("media/"):
            self.dlg.display_message_bar(
                "Lizmap",
                tr('Path not starting by "media/"'),
                level=Qgis.MessageLevel.Critical,
                duration=DURATION_WARNING_BAR,
            )
            return

        current_file = Path(self.project.absolutePath()).joinpath(current_path)
        if not current_file.exists():
            self.dlg.display_message_bar(
                "Lizmap",
                tr("Path does not exist"),
                level=Qgis.MessageLevel.Critical,
                duration=DURATION_WARNING_BAR,
            )
            return

        if not current_file.is_file():
            self.dlg.display_message_bar(
                "Lizmap",
                tr("Path is not a file"),
                level=Qgis.MessageLevel.Critical,
                duration=DURATION_WARNING_BAR,
            )
            return

        with OverrideCursor(Qt.CursorShape.WaitCursor):
            result, message = self._webdav.send_media(current_file)
        if not result and message:
            self.dlg.display_message_bar(
                "Lizmap", message, level=Qgis.MessageLevel.Critical, duration=DURATION_WARNING_BAR
            )
            return

        msg = tr("File send")
        self.dlg.display_message_bar(
            "Lizmap",
            f'<a href="{self._webdav.media_url(current_path)}">{msg}</a>',
            level=Qgis.MessageLevel.Success,
            duration=DURATION_WARNING_BAR,
        )
        return

    def upload_thumbnail(self):
        """Upload the thumbnail on the server."""
        with OverrideCursor(Qt.CursorShape.WaitCursor):
            result, message = self._webdav.send_thumbnail()
        if not result and message:
            self.dlg.display_message_bar(
                "Lizmap", message, level=Qgis.MessageLevel.Critical, duration=DURATION_WARNING_BAR
            )
            return

        if result:
            box = QMessageBox(self.dlg)
            box.setIcon(QMessageBox.Icon.Information)
            box.setWindowIcon(window_icon())
            box.setWindowTitle(tr("Cache about the thumbnail"))
            box.setText(
                tr(
                    "The upload of the thumbnail is successful. You can open it in your "
                    '<a href="{}">web-browser</a>.'
                ).format(message)
                + "<br><br>"
                + tr(
                    "However, you might have some cache in your web-browser, "
                    "for the next {number} hours. You should do a "
                    "CTRL + F5 (or CTRL + MAJ + R or similar) to force the refresh "
                    "of the page without using the web-browser cache."
                ).format(number=24)
            )
            box.setStandardButtons(QMessageBox.StandardButton.Ok)
            box.setDefaultButton(QMessageBox.StandardButton.Ok)
            box.exec()

            file_stats, error = self._webdav.file_stats_thumbnail()
            if error:
                logger.error(error)
                return
            self.dlg.set_tooltip_webdav(self.dlg.button_upload_thumbnail, file_stats.last_modified_pretty)
            self.dlg.line_thumbnail_date.setText(file_stats.last_modified_pretty)

    def send_files(self) -> tuple[bool, str]:
        """Send both files to the server, designed for UI interaction.

        With a waiting cursor and sending messages to the message bar.
        """
        with OverrideCursor(Qt.CursorShape.WaitCursor):
            result, _, url = self.send_webdav()
        return result, url
