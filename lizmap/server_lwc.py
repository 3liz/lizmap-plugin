__copyright__ = 'Copyright 2024, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import json
import logging
import os
import time

from enum import Enum
from functools import partial
from pathlib import Path
from typing import List, Optional, Tuple, Union

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsAuthMethodConfig,
    QgsMessageLog,
    QgsNetworkContentFetcher,
    QgsSettings,
)
from qgis.PyQt.QtCore import QPoint, Qt, QUrl, QVariant
from qgis.PyQt.QtGui import (
    QColor,
    QCursor,
    QDesktopServices,
    QGuiApplication,
    QIcon,
)
from qgis.PyQt.QtNetwork import QNetworkReply, QNetworkRequest
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHeaderView,
    QListWidget,
    QMenu,
    QMessageBox,
    QTableWidgetItem,
    QVBoxLayout,
)

from lizmap.definitions.definitions import (
    DEV_VERSION_PREFIX,
    UNSTABLE_VERSION_PREFIX,
    ReleaseStatus,
    ServerComboData,
)
from lizmap.definitions.lizmap_cloud import CLOUD_QGIS_MIN_RECOMMENDED
from lizmap.dialogs.main import LizmapDialog
from lizmap.dialogs.server_wizard import (
    CreateFolderWizard,
    NamePage,
    ServerWizard,
)
from lizmap.saas import is_lizmap_cloud, webdav_properties
from lizmap.toolbelt.convert import to_bool
from lizmap.toolbelt.i18n import tr
from lizmap.toolbelt.plugin import lizmap_user_folder, user_settings
from lizmap.toolbelt.version import format_qgis_version, qgis_version, version

LOGGER = logging.getLogger('Lizmap')


class TableCell(Enum):
    """ Cells in the table. """
    Url = 0
    Name = 1
    Login = 2
    LizmapVersion = 3
    QgisVersion = 4
    Action = 5
    ActionText = 6


class Color(Enum):
    """ Color used in the table. """
    Success = QColor("green")
    Critical = QColor("red")
    Advice = QColor("orange")  # Warning is a Python builtin
    Normal = QColor("black")


MAX_DAYS = 7


def is_numeric(v: Union[str, int]) -> bool:
    try:
        int(v)
        return True
    except ValueError:
        return False


class ServerManager:
    """ Fetch the Lizmap server version for a list of server. """

    def __init__(
            self, parent: LizmapDialog, table, add_button, add_first_server, remove_button, edit_button, refresh_button,
            up_button, down_button, function_check_dialog_validity
    ):
        self.parent = parent
        self.table = table
        self.add_button = add_button
        self.add_first_server = add_first_server
        self.remove_button = remove_button
        self.edit_button = edit_button
        self.refresh_button = refresh_button
        self.up_button = up_button
        self.down_button = down_button
        self.server_combo = parent.server_combo
        self.check_dialog_validity = function_check_dialog_validity

        # QGIS desktop version tuple, eg (3, 22)
        current = format_qgis_version(qgis_version())
        self.qgis_desktop = (int(current[0]), int(current[1]))

        # Network
        self.fetchers = {}

        # First new server
        self.add_first_server.clicked.connect(self.add_button.click)

        # Icons and tooltips
        self.remove_button.setIcon(QIcon(QgsApplication.iconPath('symbologyRemove.svg')))
        self.remove_button.setText('')
        self.remove_button.setToolTip(tr('Remove the selected server from the list'))

        self.add_button.setIcon(QIcon(QgsApplication.iconPath('symbologyAdd.svg')))
        self.add_button.setText('')
        self.add_button.setToolTip(tr('Add a new server in the list'))

        self.edit_button.setIcon(QIcon(QgsApplication.iconPath('symbologyEdit.svg')))
        self.edit_button.setText('')
        self.edit_button.setToolTip(tr('Edit the selected server in the list'))

        self.refresh_button.setIcon(QIcon(QgsApplication.iconPath('mActionRefresh.svg')))
        self.refresh_button.setText('')
        self.refresh_button.setToolTip(tr('Refresh all servers'))

        self.up_button.setIcon(QIcon(QgsApplication.iconPath('mActionArrowUp.svg')))
        self.up_button.setText('')
        self.up_button.setToolTip(tr('Move the server up'))

        self.down_button.setIcon(QIcon(QgsApplication.iconPath('mActionArrowDown.svg')))
        self.down_button.setText('')
        self.down_button.setToolTip(tr('Move the server down'))

        # Table
        self.table.setColumnCount(7)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.cellDoubleClicked.connect(self.edit_row)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.context_menu_requested)

        # Headers
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        # URL of the server, hidden
        item = QTableWidgetItem(tr('URL'))
        item.setToolTip(tr('URL of the server.'))
        self.table.setHorizontalHeaderItem(TableCell.Url.value, item)
        self.table.setColumnHidden(0, True)

        # Name of the server
        item = QTableWidgetItem(tr('Name'))
        item.setToolTip(tr('Name of the server.'))
        self.table.setHorizontalHeaderItem(TableCell.Name.value, item)

        # Login used, hidden
        item = QTableWidgetItem(tr('Login'))
        item.setToolTip(tr('Login of the administrator.'))
        self.table.setHorizontalHeaderItem(TableCell.Login.value, item)
        self.table.setColumnHidden(2, True)

        tooltip = tr('Version detected on the server')

        # Lizmap Web Client version
        item = QTableWidgetItem(tr('Lizmap Version'))
        item.setToolTip(tooltip)
        self.table.setHorizontalHeaderItem(TableCell.LizmapVersion.value, item)

        # QGIS Server version
        item = QTableWidgetItem(tr('QGIS Server Version'))
        item.setToolTip(tooltip)
        self.table.setHorizontalHeaderItem(TableCell.QgisVersion.value, item)

        # Action needed
        item = QTableWidgetItem(tr('Action'))
        item.setToolTip(tr('If there is any action to do on the server'))
        self.table.setHorizontalHeaderItem(TableCell.Action.value, item)

        # Hidden one to store the action text, as HTML
        item = QTableWidgetItem('Action text')
        self.table.setHorizontalHeaderItem(TableCell.ActionText.value, item)
        self.table.setColumnHidden(6, True)

        # Connect
        self.add_button.clicked.connect(self.add_row)
        self.remove_button.clicked.connect(self.remove_row)
        self.edit_button.clicked.connect(self.edit_row)
        self.refresh_button.clicked.connect(self.refresh_table)
        self.up_button.clicked.connect(self.move_server_up)
        self.down_button.clicked.connect(self.move_server_down)

        # Actions
        self.clean_cache()
        self.load_table()
        self.visible_new_server_button()

    def visible_new_server_button(self):
        """ Make the new server button visible only when we do not have a server yet. """
        self.add_first_server.setVisible(self.table.rowCount() == 0)

    @staticmethod
    def config_for_id(auth_id: str) -> Optional[QgsAuthMethodConfig]:
        """ Fetch the authentication settings for a given token. """
        auth_manager = QgsApplication.authManager()
        if not auth_manager.masterPasswordIsSet():
            LOGGER.warning(f"Master password is not set, could not look for ID {auth_id}")
            return None

        conf = QgsAuthMethodConfig()
        auth_manager.loadAuthenticationConfig(auth_id, conf, True)
        if not conf.id():
            LOGGER.debug(f"Skipping password ID {auth_id}, it wasn't found in the password manager")
            return None

        # LOGGER.info("Found password ID {}".format(auth_id))
        return conf

    @classmethod
    def clean_cache(cls, force=False):
        """ Remove all files in the server cache directory older than X days. """
        now = time.time()
        cache_dir = lizmap_user_folder().joinpath("cache_server_metadata")
        for item in cache_dir.glob('*'):
            if os.stat(item).st_mtime < now - MAX_DAYS * 86400:
                item.unlink()
            elif force:
                item.unlink()

    @classmethod
    def cache_file_for_name(cls, name: str) -> Path:
        """ Return a cache file name according to a server name. """
        name = name.replace('/', '-')
        cache_file = lizmap_user_folder().joinpath("cache_server_metadata").joinpath(f'{name}.json')
        return cache_file

    def check_validity_servers(self) -> bool:
        """ Check if all servers are valid with at least a login. """
        if self.table.rowCount() == 0:
            # At least one server minimum for all
            return False

        current = version()
        if current in ('master', 'dev') or 'alpha' in current:
            # For developers, we bypass this check :)
            return True

        if to_bool(os.getenv("LIZMAP_ADVANCED_USER")):
            # For advanced users with an environment variable, we bypass as well
            return True

        # All rows must have a login
        for row in range(self.table.rowCount()):
            login = self.table.item(row, TableCell.Login.value).data(Qt.ItemDataRole.DisplayRole)
            if not login:
                # All rows must have a login
                return False

        # For LWC ≥ 3.6, rows must have QGIS server version
        for row in range(self.table.rowCount()):
            qgis_server = self.table.item(row, TableCell.QgisVersion.value).data(Qt.ItemDataRole.UserRole + 1)
            if isinstance(qgis_server, bool):
                # It means QGIS server is not configured correctly.
                return False

        return True

    def check_lwc_version(self, version_check: str) -> bool:
        """ Check if the given LWC version is at least in the table. """
        for row in range(self.table.rowCount()):
            lwc_version = self.table.item(row, TableCell.LizmapVersion.value).data(Qt.ItemDataRole.DisplayRole)
            if lwc_version and lwc_version.startswith(version_check):
                return True

        return False

    def check_admin_login_provided(self) -> bool:
        """ Check if the given LWC version is at least in the table. """
        if any(item in version() for item in DEV_VERSION_PREFIX):
            return True

        if to_bool(os.getenv("LIZMAP_ADVANCED_USER")):
            return True

        missing = False
        for row in range(self.table.rowCount()):
            if not self.table.item(row, TableCell.Login.value).data(Qt.ItemDataRole.DisplayRole):
                missing = True

        if not missing:
            return True

        # Try again, this is a hack
        # Weird bug, sometimes, the master password is not set, so the login column is not filled
        # Maybe by loading again all logins, we can avoid the "false" return
        self.load_table()
        for row in range(self.table.rowCount()):
            if not self.table.item(row, TableCell.Login.value).data(Qt.ItemDataRole.DisplayRole):
                return False

        return True

    def add_row(self):
        """ Add a new row in the table, asking the URL to the user. """
        existing = self.existing_json_server_list()
        dialog = ServerWizard(self.parent, existing)
        result = dialog.exec()

        if result != QDialog.DialogCode.Accepted:
            return

        row = self.table.rowCount()
        self.table.setRowCount(row + 1)
        self._edit_row(row, dialog.current_url(), dialog.auth_id, dialog.current_name())
        # Add a new server is done in the wizard
        # self.save_table()
        self.refresh_server_combo()

    def _fetch_cells(self, row: int) -> tuple:
        """ Fetch the URL and the authid in the cells. """
        try:
            # When we are reloading the plugin
            # I'm not sure why ...
            self.table
        except AttributeError:
            return None, None, None

        url_item = self.table.item(row, TableCell.Url.value)
        login_item = self.table.item(row, TableCell.Login.value)
        name_item = self.table.item(row, TableCell.Name.value)
        url = url_item.data(Qt.ItemDataRole.UserRole)
        auth_id = login_item.data(Qt.ItemDataRole.UserRole)
        name = name_item.data(Qt.ItemDataRole.UserRole)
        return url, auth_id, name

    def edit_row(self):
        """ Edit the selected row in the table. """
        selection = self.table.selectedIndexes()

        if len(selection) <= 0:
            return

        row = selection[0].row()
        url, auth_id, name = self._fetch_cells(row)

        data = []
        existing = self.existing_json_server_list()
        for i, server in enumerate(existing):
            if server.get('url') != url:
                data.append({'url': server.get('url'), 'auth_id': auth_id})
        dialog = ServerWizard(self.parent, data, url=url, auth_id=auth_id, name=name)
        result = dialog.exec()

        if result != QDialog.DialogCode.Accepted:
            return

        self._edit_row(row, dialog.current_url(), dialog.auth_id, dialog.current_name())
        # In edit mode, the saving is not done in the wizard
        self.save_table()
        self.refresh_server_combo()

    def remove_row(self):
        """ Remove the selected row from the table. """
        selection = self.table.selectedIndexes()

        if len(selection) <= 0:
            return

        row = selection[0].row()

        _, auth_id, _ = self._fetch_cells(row)
        if auth_id:
            # Do not try to remove from QPM if no login was provided
            auth_manager = QgsApplication.authManager()
            result = auth_manager.removeAuthenticationConfig(auth_id)
            if not result:
                QMessageBox.critical(
                    self.parent,
                    tr('QGIS Authentication database'),
                    tr(
                        "We couldn't remove the login/password from the QGIS authentication database. "
                        "Please remove manually the line '{}' from your QGIS authentication database in the your QGIS "
                        "global settings, then 'Authentication' tab.").format(auth_id),
                    QMessageBox.StandardButton.Ok)
                self.table.clearSelection()
                return
            LOGGER.debug(f"Row {auth_id} removed from the QGIS authentication database")

        self.table.clearSelection()
        self.table.removeRow(row)
        if row in self.fetchers.keys():
            del self.fetchers[row]
        self.save_table()
        self.refresh_server_combo()
        self.parent.refresh_combo_repositories()

    def _edit_row(self, row: int, server_url: str, auth_id: str, name: str):
        """ Internal function to edit a row. """
        login = tr('Unknown')
        conf = self.config_for_id(auth_id)
        if conf:
            login = conf.config('username', '')

        # URL
        cell = QTableWidgetItem()
        cell.setData(Qt.ItemDataRole.UserRole, server_url)
        self.table.setItem(row, TableCell.Url.value, cell)

        # Name
        cell = QTableWidgetItem()
        cell.setText(name)
        cell.setData(Qt.ItemDataRole.ToolTipRole, tr(
            '<b>URL</b> {}<br>'
            '<b>Login</b> {}<br>'
            '<b>Password ID</b> {}').format(server_url, login, auth_id))
        cell.setData(Qt.ItemDataRole.UserRole, name)
        self.table.setItem(row, TableCell.Name.value, cell)

        # Login
        cell = QTableWidgetItem()
        cell.setText(login)
        cell.setData(Qt.ItemDataRole.UserRole, auth_id)
        self.table.setItem(row, TableCell.Login.value, cell)

        # LWC Version
        cell = QTableWidgetItem()
        cell.setText('')
        cell.setData(Qt.ItemDataRole.UserRole, None)
        self.table.setItem(row, TableCell.LizmapVersion.value, cell)

        # QGIS Version
        cell = QTableWidgetItem()
        cell.setText('')
        cell.setData(Qt.ItemDataRole.UserRole, '')
        self.table.setItem(row, TableCell.QgisVersion.value, cell)

        # Action
        cell = QTableWidgetItem()
        cell.setText('')
        cell.setData(Qt.ItemDataRole.UserRole, '')
        self.table.setItem(row, TableCell.Action.value, cell)

        # Action text, hidden
        cell = QTableWidgetItem()
        cell.setData(Qt.ItemDataRole.UserRole, '')
        self.table.setItem(row, TableCell.ActionText.value, cell)

        self.table.clearSelection()
        self.fetch(server_url, auth_id, row)

    def move_server_up(self):
        """Move the selected server up."""
        row = self.table.currentRow()
        if row <= 0:
            return
        column = self.table.currentColumn()
        self.table.insertRow(row - 1)
        for i in range(self.table.columnCount()):
            self.table.setItem(row - 1, i, self.table.takeItem(row + 1, i))
            self.table.setCurrentCell(row - 1, column)
        self.table.removeRow(row + 1)

    def move_server_down(self):
        """Move the selected server down."""
        row = self.table.currentRow()
        if row == self.table.rowCount() - 1 or row < 0:
            return
        column = self.table.currentColumn()
        self.table.insertRow(row + 2)
        for i in range(self.table.columnCount()):
            self.table.setItem(row + 2, i, self.table.takeItem(row, i))
            self.table.setCurrentCell(row + 2, column)
        self.table.removeRow(row)

    def refresh_table(self):
        """ Refresh all rows with the server status. """
        self.clean_cache(True)
        for row in range(self.table.rowCount()):
            url, auth_id, _ = self._fetch_cells(row)
            self.fetch(url, auth_id, row)

    def fetch(self, url: str, auth_id: str, row: int):
        """ Fetch the JSON file and call the function when it's finished. """
        self.display_action(row, False, tr('Fetching…'))
        self.fetchers[row] = QgsNetworkContentFetcher()
        self.fetchers[row].finished.connect(partial(self.request_finished, row))

        if auth_id:
            QgsMessageLog.logMessage(f"Using the token for <a href='{url}'>{url}</a>", "Lizmap", Qgis.MessageLevel.Info)

        request = QNetworkRequest()
        request.setUrl(QUrl(ServerWizard.url_metadata(url)))
        request.setAttribute(QNetworkRequest.FollowRedirectsAttribute, True)
        # According to QGIS debug panel, this is not working for now
        request.setAttribute(
            QNetworkRequest.Attribute.CacheLoadControlAttribute, QNetworkRequest.CacheLoadControl.PreferNetwork)
        self.fetchers[row].fetchContent(request, auth_id)

    def request_finished(self, row: int):
        """ Dispatch the answer to update the GUI. """
        try:
            # When we are reloading the plugin
            # I'm not sure why ...
            self.table
        except AttributeError:
            return

        url, auth_id, _ = self._fetch_cells(row)

        login = ''
        conf = self.config_for_id(auth_id)
        if conf:
            login = conf.config('username', '')

        lizmap_cell = QTableWidgetItem()
        qgis_cell = QTableWidgetItem()
        action_text_cell = QTableWidgetItem()
        self.table.setItem(row, TableCell.ActionText.value, action_text_cell)
        self.table.setItem(row, TableCell.LizmapVersion.value, lizmap_cell)
        self.table.setItem(row, TableCell.QgisVersion.value, qgis_cell)

        reply = self.fetchers[row].reply()

        if not reply:
            lizmap_cell.setText(tr('Error'))
            self.display_action(row, Qgis.MessageLevel.Warning, tr('Temporary not available'))
            return

        if reply.error() != QNetworkReply.NetworkError.NoError:
            if reply.error() == QNetworkReply.NetworkError.HostNotFoundError:
                self.display_action(row, Qgis.MessageLevel.Warning, tr('Host can not be found. Is-it an intranet server ?'))
            if reply.error() == QNetworkReply.NetworkError.ContentNotFoundError:
                self.display_action(
                    row,
                    Qgis.MessageLevel.Critical,
                    tr('Not a valid Lizmap URL or this version is already not maintained < 3.2'))
            else:
                self.display_action(row, Qgis.MessageLevel.Critical, reply.errorString())
            lizmap_cell.setText(tr('Error'))
            return

        content = self.fetchers[row].contentAsString()
        if not content:
            self.display_action(row, Qgis.MessageLevel.Critical, tr('Not a valid Lizmap URL'))
            return

        try:
            content = json.loads(content)
        except json.JSONDecodeError:
            self.display_action(row, Qgis.MessageLevel.Critical, tr('Not a JSON document.'))
            return

        info = content.get('info')
        if not info:
            self.display_action(row, Qgis.MessageLevel.Critical, tr('No "info" in the JSON document'))
            return

        # Lizmap version
        lizmap_version = info.get('version')
        if not info:
            self.display_action(row, Qgis.MessageLevel.Critical, tr('No "version" in the JSON document'))
            return

        # LWC version split
        lizmap_version_split = self.split_lizmap_version(lizmap_version)
        branch = lizmap_version_split[0], lizmap_version_split[1]

        qgis_server = content.get('qgis_server')
        if branch >= (3, 6):
            if qgis_server:
                if lizmap_version in ("3.6.0-beta.1", "3.6.0-beta.2", "3.6.0-rc.1"):
                    if not qgis_server.get('mime_type'):
                        self.display_action(
                            row,
                            Qgis.MessageLevel.Critical,
                            tr(
                                'QGIS Server is not loaded properly. Check the settings in the administration '
                                'interface.'
                            )
                        )
                        return
                else:
                    # Starting from LWC 3.6.0 RC 2
                    # https://github.com/3liz/lizmap-web-client/pull/3292
                    pass

        elif branch < (3, 6):
            # qgis_server must be in the JSON file
            if not qgis_server:
                self.display_action(row, Qgis.MessageLevel.Critical, tr('No "qgis_server" in the JSON document'))
                return

            mime_type = qgis_server.get('mime_type')
            if not mime_type:
                self.display_action(
                    row,
                    Qgis.MessageLevel.Critical,
                    tr('QGIS Server is not loaded properly. Check the settings in the administration interface.')
                )
                return

        lizmap_cell.setText(lizmap_version)

        # Reply is good at this step, let's save it in our cache
        server_alias = self.table.item(row, TableCell.Name.value).data(Qt.ItemDataRole.UserRole)
        json_file_content = json.dumps(
            content,
            sort_keys=False,
            indent=4
        )
        json_file_content += '\n'
        with open(self.cache_file_for_name(server_alias), 'w', encoding='utf8') as json_file:
            json_file.write(json_file_content)

        # Add the JSON metadata in the server combobox
        index = self.server_combo.findData(url, ServerComboData.ServerUrl.value)
        self.server_combo.setItemData(index, content, ServerComboData.JsonMetadata.value)
        LOGGER.info(f"Saving server metadata from network : {index} - {server_alias}")
        self.parent.tooltip_server_combo(index)
        # Server combo is refreshed, maybe we can allow the menu bar
        self.check_dialog_validity()

        # and refresh repositories if needed about the new metadata downloaded about repositories available
        if self.server_combo.currentData(ServerComboData.ServerUrl.value) == url:
            self.parent.refresh_combo_repositories()

        lwc_version_txt = f'* Lizmap Web Client : {lizmap_version}'
        git_hash = info.get('commit')
        if git_hash:
            lwc_version_txt += f" - commit {git_hash} https://github.com/3liz/lizmap-web-client/commit/{git_hash}"
        lwc_version_txt += '\n'

        # Markdown
        markdown = '**Versions :**\n\n'
        markdown += lwc_version_txt
        markdown += f'* Lizmap plugin : {version()}\n'
        markdown += '* QGIS Desktop : {}\n'.format(Qgis.QGIS_VERSION.split('-')[0])
        qgis_cell.setData(Qt.ItemDataRole.UserRole, markdown)
        qgis_cell.setData(Qt.ItemDataRole.UserRole + 1, content)

        # Only adding Lizmap saas if set to true
        if is_lizmap_cloud(content):
            markdown += '* Lizmap.com : Yes\n'

        # QGIS Server info
        qgis_server_info = content.get('qgis_server_info')

        # QGIS Server version
        if not qgis_server_info and branch == (3, 5):
            # Running > 3.5.x-pre but < 3.5.1
            # We bypass the metadata section
            self.update_action_version(lizmap_version, None, row, login)
            # Make a better warning to upgrade ASAP
            markdown += '* QGIS Server and plugins unknown status\n'
            qgis_cell.setData(Qt.ItemDataRole.UserRole, markdown)
            return

        if qgis_server_info and "error" not in qgis_server_info.keys():
            # The current user is an admin, running at least LWC >= 3.5.1
            qgis_metadata = qgis_server_info.get('metadata')
            qgis_server_version = qgis_metadata.get('version')
            qgis_cell.setText(qgis_server_version)

            plugins = qgis_server_info.get('plugins')
            # plugins = {'atlasprint': {'version': '3.2.2'}}
            # Temporary, add plugins as markdown in the data
            markdown += f'* QGIS Server : {qgis_server_version}\n'
            server_wrapper = qgis_server_info.get('py_qgis_server')
            if server_wrapper:
                wrapper_version = server_wrapper.get('version', 'Not used')
                wrapper_name = server_wrapper.get('name', 'Py-QGIS-Server or QJazz')
            else:
                # Legacy, old server running
                wrapper_version = qgis_metadata.get('py_qgis_server_version', 'Not used')
                wrapper_name = 'Py-QGIS-Server'

            markdown += f'* {wrapper_name} : {wrapper_version}\n'
            for plugin, info in plugins.items():
                plugin_version = info['version']
                if plugin_version.lower().startswith("not"):
                    # https://github.com/3liz/qgis-lizmap-server-plugin/commit/4e8e8c51102470eac0dc2ec622db9ab41d37f1c1
                    continue
                markdown += f'* QGIS Server plugin {plugin} : {plugin_version}\n'

            markdown += self.modules_to_markdown(content)
            qgis_cell.setData(Qt.ItemDataRole.UserRole, markdown)
            self.update_action_version(
                lizmap_version, qgis_server_version, row, login, lizmap_cloud=is_lizmap_cloud(content))
            return

        if branch < (3, 5):
            # Running LWC < 3.5.X
            markdown += '* QGIS Server and plugins unknown status because running Lizmap Web Client < 3.5\n'
            font = qgis_cell.font()
            font.setItalic(True)
            qgis_cell.setFont(font)
            qgis_cell.setText(tr("Not possible"))
            qgis_cell.setToolTip(
                tr("Not possible to determine QGIS Server version because you need at least Lizmap Web Client 3.5"))
            qgis_cell.setData(Qt.ItemDataRole.UserRole, markdown)
            self.update_action_version(lizmap_version, None, row)
            return

        if branch >= (3, 5):
            # QGIS Server is either not setup or no login
            if not login:
                # No admin login provided and running LWC >= 3.5
                markdown += '* QGIS Server and plugins unknown status because no admin login provided\n'
                qgis_cell.setData(Qt.ItemDataRole.UserRole, markdown)

                font = qgis_cell.font()
                font.setItalic(True)
                qgis_cell.setFont(font)
                qgis_cell.setText(tr("Not possible"))
                qgis_cell.setToolTip(
                    tr("Not possible to determine QGIS Server version because you didn't provide a login"))

                self.update_action_version(lizmap_version, None, row)
                return
            else:
                if "error" in qgis_server_info.keys():
                    if qgis_server_info['error'] in ('NO_ACCESS', 'WRONG_CREDENTIALS'):
                        markdown += (
                            '* QGIS Server and plugins unknown status because the login provided is not an '
                            'administrator\n'
                        )
                        qgis_cell.setData(Qt.ItemDataRole.UserRole, markdown)
                        self.update_action_version(lizmap_version, None, row, login, error=qgis_server_info['error'])
                        return

                    markdown += (
                        '* QGIS Server and plugins unknown status because of the settings in QGIS Server, '
                        'please review your server settings in the Lizmap Web Client administration interface, '
                        'then in the "Server Information" panel.\n'
                    )
                    qgis_cell.setData(Qt.ItemDataRole.UserRole, markdown)
                    self.update_action_version(lizmap_version, None, row, login, error=qgis_server_info['error'])
                    return

        # Unknown
        markdown += '* QGIS Server and plugins unknown status\n'
        qgis_cell.setData(Qt.ItemDataRole.UserRole, markdown)
        self.server_combo.setItemData(index, markdown, ServerComboData.MarkDown.value)
        self.update_action_version(lizmap_version, None, row)

    @classmethod
    def modules_to_markdown(cls, content: dict) -> str:
        """ Export the list of LWC modules to markdown. """
        # Available since LWC 3.8.2
        text = '\n<details>\n'
        text += '<summary>List of Lizmap Web Client modules :</summary>\n'
        text += '<br/>\n'
        modules = content.get("modules")
        if isinstance(modules, dict):
            if len(modules.keys()) >= 1:
                for module, info in modules.items():
                    text += f'* {module} : {info.get("version", "")}\n'
            else:
                text += '* No module\n'
        else:
            text += '* Version Lizmap Web Client 3.8 needed\n'
        text += '</details>\n'
        return text

    @classmethod
    def existing_json_server_list(cls) -> List:
        """ Read the JSON file and return its content. """
        user_file = user_settings()
        if not user_file.exists():
            return list()

        with open(user_file) as json_file:
            json_content = json.loads(json_file.read())

        # AuthID must be unique, it is used as data for the QComboBox for find
        unique_authid = []
        output = []
        for server in json_content:
            if server.get('auth_id') in unique_authid:
                continue
            output.append(dict(server))

        return output

    def refresh_server_combo(self):
        """ Refresh the server combobox. """
        servers = self.existing_json_server_list()

        self.server_combo.blockSignals(True)
        self.parent.repository_combo.blockSignals(True)

        self.server_combo.clear()

        for server in servers:
            url = server.get('url')
            auth_id = server.get('auth_id')
            name = server.get('name', NamePage.automatic_name(server.get('url')))
            self.server_combo.addItem(name, auth_id)
            index = self.server_combo.findData(auth_id, ServerComboData.AuthId.value)
            self.server_combo.setItemData(index, url, ServerComboData.ServerUrl.value)
            cache_file = self.cache_file_for_name(name)
            if cache_file.exists():
                with open(cache_file, encoding='utf8') as f:
                    metadata = json.load(f)
                    self.server_combo.setItemData(index, metadata, ServerComboData.JsonMetadata.value)
                    LOGGER.info(f"Loading server <a href='{url}'>{name}</a> using cache in the drop down list")
            else:
                self.server_combo.setItemData(index, {}, ServerComboData.JsonMetadata.value)
                LOGGER.info(
                    f"Loading server <a href='{url}'>{name}</a> without metadata in the drop down list")

            self.parent.tooltip_server_combo(index)

        # Restore previous value
        server = QgsSettings().value('lizmap/instance_target_url', '')
        if server:
            index = self.server_combo.findData(server, ServerComboData.ServerUrl.value)
            if index:
                self.server_combo.setCurrentIndex(index)

        self.server_combo.blockSignals(False)
        self.parent.repository_combo.blockSignals(False)
        self.parent.refresh_combo_repositories()
        self.check_dialog_validity()
        self.visible_new_server_button()

    def load_table(self):
        """ Load the table by reading the user configuration file. """
        servers = self.existing_json_server_list()
        self.migrate_password_manager(servers)

        # Truncate
        self.table.setRowCount(0)

        for server in servers:
            row = self.table.rowCount()
            self.table.setRowCount(row + 1)
            self._edit_row(
                row,
                server.get('url'),
                server.get('auth_id', ''),
                server.get('name', NamePage.automatic_name(server.get('url')))
            )

        self.refresh_server_combo()

    def save_table(self):
        """ Save the table as JSON in the user configuration file. """
        rows = self.table.rowCount()
        data = []
        for row in range(rows):
            url, auth_id, name = self._fetch_cells(row)
            data.append({
                'url': url,
                'auth_id': auth_id,
                'name': name,
            })

        json_file_content = json.dumps(
            data,
            sort_keys=False,
            indent=4
        )
        json_file_content += '\n'

        with open(user_settings(), 'w') as json_file:
            json_file.write(json_file_content)

    def update_action_version(
            self, lizmap_version: str, qgis_server_version, row: int, login: str = None,
            error: str = None,
            lizmap_cloud: bool = False,
    ):
        """ When we know the version, we can check the latest release from LWC with the file in cache. """
        version_file = lizmap_user_folder().joinpath('released_versions.json')
        if not version_file.exists():
            return

        level, messages, qgis_valid = self._messages_for_version(
            lizmap_version, qgis_server_version, login, version_file, self.qgis_desktop, error,
            lizmap_cloud=lizmap_cloud, is_dev=self.parent.is_dev_version)
        if isinstance(qgis_valid, bool) and not qgis_valid:
            self.table.item(row, TableCell.QgisVersion.value).setData(False, Qt.ItemDataRole.UserRole + 1)
            self.table.item(row, TableCell.QgisVersion.value).setText(tr("Configuration error"))

        self.display_action(row, level, '\n'.join(messages))

    @staticmethod
    def _messages_for_version(
            lizmap_version: str, server_version: str, login: str, json_path: Path,
            qgis_desktop: Tuple[int, int],
            error: str = '',
            lizmap_cloud: bool = False,
            is_dev: bool = False,
    ) -> Tuple[Qgis.MessageLevel, List[str], bool]:
        """Returns the list of messages and the color to use.

        The last returned value is a boolean if the QGIS server is valid or not. It's blocker to continue with this
        server.
        """
        with open(json_path) as json_file:
            json_content = json.loads(json_file.read())

        split_version = lizmap_version.split('.')
        if len(split_version) not in (3, 4):
            # 3.4.0-pre but also 3.4.0-rc.1
            # noinspection PyTypeChecker
            QgsMessageLog.logMessage(
                f"The version '{lizmap_version}' is not correct.", "Lizmap", Qgis.MessageLevel.Critical)

        branch = f'{split_version[0]}.{split_version[1]}'
        full_version = '{}.{}'.format(branch, split_version[2].split('-')[0])

        messages = []
        level = Qgis.MessageLevel.Warning

        # Special case for 3.5.0, 3.5.1-pre, 3.5.1-pre.5110
        # Upgrade ASAP, keep it for a few months
        if full_version == '3.5.0' or (full_version == '3.5.1' and len(split_version[2].split('-')) == 2):
            messages.append(
                '⚠ ' + tr(
                    "Upgrade to 3.5.1 as soon as possible, some critical issues were detected with this version."))
            # Return False for QGIS server status, considering blocking
            return Qgis.MessageLevel.Critical, messages, False

        is_dev_version = False
        for i, json_version in enumerate(json_content):
            if not json_version['branch'] == branch:
                continue

            qgis_server_valid = True
            status = ReleaseStatus.find(json_version['status'])
            if status in (ReleaseStatus.Dev, ReleaseStatus.ReleaseCandidate):
                messages.append(tr('A dev version, warrior !') + ' 👍')
                level = Qgis.MessageLevel.Success
                is_dev_version = True

                # In LWC source code, we have branch X.Y.0 even if we are in dev mode
                # But the online JSON public release might have nothing (because no public tag has been made)
                latest_release_version = json_version.get('latest_release_version')
                if latest_release_version:
                    bugfix = latest_release_version.split('.')[2]
                    if is_numeric(bugfix):
                        latest_bugfix = int(bugfix)
                    else:
                        # It will be a string :(
                        # Like 0-rc.4
                        latest_bugfix = bugfix
                else:
                    # So let's assume it's 0
                    latest_bugfix = 0
            else:
                # If we are not in dev or feature freeze, we have at least one public release
                latest_bugfix = int(json_version['latest_release_version'].split('.')[2])

            if status == ReleaseStatus.Retired:
                # Upgrade because the branch is not maintained anymore
                messages.append(tr('Version {version} not maintained anymore').format(version=branch))
                level = Qgis.MessageLevel.Critical
            elif status == ReleaseStatus.SecurityBugfixOnly:
                # Upgrade because the branch is not maintained anymore
                messages.append(tr('Version {version} not maintained anymore, only for security bugfix only').format(version=branch))

            # Remember a version can be 3.4.2-pre
            # Or 3.8.0-rc.4
            items_bugfix = split_version[2].split('-')
            is_pre_package = len(items_bugfix) > 1 and len(split_version) == 3
            bugfix = int(items_bugfix[0])

            if json_version['latest_release_version'] != full_version or is_pre_package:

                if is_dev_version and login:
                    pass
                    # We continue
                    # return level, messages

                if not is_numeric(latest_bugfix):
                    from pyplugin_installer.version_compare import (
                        compareVersions,
                    )
                    if compareVersions(lizmap_version, json_version['latest_release_version']) == 2:
                        # Like comparing 3.8.0-rc.4 and 3.8.0-rc.3
                        messages.append(
                            tr(
                                'Not latest bugfix release, {version} is available'
                            ).format(version=json_version['latest_release_version']))
                        level = Qgis.MessageLevel.Warning

                if is_numeric(latest_bugfix) and bugfix > latest_bugfix:
                    # Congratulations :)
                    if lizmap_cloud and not is_dev:
                        messages.append('👍')
                    else:
                        messages.append(tr('Higher than a public release') + ' 👍')
                    level = Qgis.MessageLevel.Success

                elif is_numeric(latest_bugfix) and bugfix < latest_bugfix or is_pre_package:
                    # The user is not running the latest bugfix release on the maintained branch

                    if bugfix + 2 < latest_bugfix:
                        # Let's make it clear when they are 2 release late
                        level = Qgis.MessageLevel.Critical

                    if bugfix == 0 and status == ReleaseStatus.Stable:
                        # I consider a .0 version fragile
                        # People upgrading to a major version but keeping a .0 version have skills to upgrade to
                        # a .1 version
                        messages.append(tr("Running a .0 version, upgrade to the latest bugfix release"))
                    elif bugfix != 0 and status in (ReleaseStatus.ReleaseCandidate, ReleaseStatus.Stable, ReleaseStatus.SecurityBugfixOnly, ReleaseStatus.Retired):
                        # Even if the branch is retired, we encourage people upgrading to the latest
                        if not lizmap_cloud:
                            # Only advertise if it's not a customer
                            messages.append(
                                tr(
                                    'Not latest bugfix release, {version} is available'
                                ).format(version=json_version['latest_release_version']))

                    if is_pre_package:
                        # Pre-release, maybe the package got some updates
                        messages.append('. ' + tr('This version is not based on a tag.'))

            if int(split_version[0]) >= 3 and int(split_version[1]) >= 5:
                # Running 3.5.X
                if not login:
                    messages.insert(0, tr('No administrator/publisher login provided'))
                    level = Qgis.MessageLevel.Critical
                    if int(split_version[1]) >= 6:
                        qgis_server_valid = False

                if login and error == "NO_ACCESS":
                    messages.insert(0, tr('The login is not a publisher/administrator'))
                    # Starting from version 3.9.2, login is required
                    level = Qgis.MessageLevel.Critical
                    if int(split_version[1]) >= 6:
                        qgis_server_valid = False

                if login and error == "WRONG_CREDENTIALS":
                    messages.insert(0, tr('Check your credentials, wrong login/password'))
                    # Starting from version 3.9.2, login is required
                    level = Qgis.MessageLevel.Critical
                    if int(split_version[1]) >= 6:
                        qgis_server_valid = False

                if login and error == 'HTTP_ERROR':
                    messages.insert(0, tr(
                        'Please check your "Server Information" panel in the Lizmap administration interface. '
                        'There is an error reading the QGIS Server configuration.'
                    ))
                    level = Qgis.MessageLevel.Critical
                    if int(split_version[1]) >= 6:
                        qgis_server_valid = False

                # Check QGIS server version against the desktop one
                if server_version:
                    split = server_version.split('.')
                    qgis_server = (int(split[0]), int(split[1]))
                    if qgis_server < qgis_desktop:
                        if to_bool(os.getenv("LIZMAP_ADVANCED_USER")):
                            # TODO if we can bypass this check for dev
                            pass
                        messages.insert(0, tr(
                            'QGIS Server version < QGIS Desktop version. Either upgrade your QGIS Server {}.{} or '
                            'downgrade your QGIS Desktop {}.{}'
                        ).format(qgis_server[0], qgis_server[1], qgis_desktop[0], qgis_desktop[1]))
                        level = Qgis.MessageLevel.Critical

                    qgis_server = (int(split[0]), int(split[1]), int(split[2]))
                    if lizmap_cloud and qgis_server < CLOUD_QGIS_MIN_RECOMMENDED:
                        messages.insert(0, tr(
                            'QGIS Server version {major}.{minor} is not maintained anymore by QGIS.org since '
                            '{month_and_year}. '
                            'Please visit your administration panel in the web browser to ask for the update.'
                        ).format(
                            major=qgis_server[0],
                            minor=qgis_server[1],
                            month_and_year=tr("February 2024"),  # About QGIS 3.28
                        ))
                        level = Qgis.MessageLevel.Critical

            if len(messages) == 0:
                level = Qgis.MessageLevel.Success
                messages.append("👍")

            return level, messages, qgis_server_valid

        # This should not happen
        return Qgis.MessageLevel.Critical, [f"Version {branch} has not been detected as a known version."], False

    @classmethod
    def split_lizmap_version(cls, lwc_version: str) -> tuple:
        """ Split a Lizmap Web Client version. """
        lizmap_version_split = lwc_version.split('.')
        items_bugfix = lizmap_version_split[2].split('-')
        is_pre_package = len(items_bugfix) > 1
        if not is_pre_package:
            # 3.5.2
            return (
                int(lizmap_version_split[0]),
                int(lizmap_version_split[1]),
                int(lizmap_version_split[2]),
            )

        if len(lizmap_version_split) == 3:
            # 3.5.2-pre
            return (
                int(lizmap_version_split[0]),
                int(lizmap_version_split[1]),
                int(items_bugfix[0]),
                items_bugfix[1],
            )

        # 3.5.2-pre.5204
        return (
            int(lizmap_version_split[0]),
            int(lizmap_version_split[1]),
            int(items_bugfix[0]),
            items_bugfix[1],
            int(lizmap_version_split[3]),
        )

    def display_action(self, row, level, message):
        """ Display the action if needed to the user with a color. """
        cell = QTableWidgetItem()
        cell.setText(message)
        cell.setToolTip(message)
        if level == Qgis.MessageLevel.Success:
            color = Color.Success.value
        elif level == Qgis.MessageLevel.Critical:
            color = Color.Critical.value
        elif level == Qgis.MessageLevel.Warning:
            color = Color.Advice.value
        else:
            # color = Color.Normal.value
            color = None

        if color:
            cell.setData(Qt.ItemDataRole.ForegroundRole, QVariant(color))
        else:
            cell.setData(Qt.ItemDataRole.ForegroundRole, None)
        self.table.setItem(row, TableCell.Action.value, cell)

    def context_menu_requested(self, position: QPoint):
        """ Opens the custom context menu with a right click in the table. """
        item = self.table.itemAt(position)
        if not item:
            return

        top_menu = QMenu(self.table)
        menu = top_menu.addMenu("Menu")

        edit_url = menu.addAction(tr("Edit server") + "…")
        edit_url.triggered.connect(self.edit_row)

        open_url = menu.addAction(tr("Open home page URL") + "…")
        left_item = self.table.item(item.row(), TableCell.Url.value)
        url = left_item.data(Qt.ItemDataRole.UserRole)
        slot = partial(QDesktopServices.openUrl, QUrl(url))
        open_url.triggered.connect(slot)

        open_server_info_url = menu.addAction(tr("Open server information URL") + "…")
        left_item = self.table.item(item.row(), TableCell.Url.value)
        url = left_item.data(Qt.ItemDataRole.UserRole)
        slot = partial(QDesktopServices.openUrl, QUrl(ServerWizard.url_server_info(url)))
        open_server_info_url.triggered.connect(slot)

        is_dev = (
            any(
                item in version() for item in UNSTABLE_VERSION_PREFIX
            ) or to_bool(os.getenv("LIZMAP_ADVANCED_USER"))
        )
        if is_dev:
            open_url = menu.addAction(tr("Open raw JSON file URL") + "…")
            left_item = self.table.item(item.row(), TableCell.Url.value)
            url = left_item.data(Qt.ItemDataRole.UserRole)
            slot = partial(QDesktopServices.openUrl, QUrl(ServerWizard.url_metadata(url)))
            open_url.triggered.connect(slot)

        action_item = self.table.item(item.row(), TableCell.Action.value)
        action_data = action_item.data(Qt.ItemDataRole.DisplayRole)
        action_required = action_item.data(Qt.ItemDataRole.ForegroundRole) in (Color.Advice.value, Color.Critical.value)

        qgis_server_item = self.table.item(item.row(), TableCell.QgisVersion.value)
        data = qgis_server_item.data(Qt.ItemDataRole.UserRole)

        show_all_versions = menu.addAction(tr("Display all versions") + "…")
        slot = partial(self.display_all_versions, data)
        show_all_versions.triggered.connect(slot)

        server_as_markdown = menu.addAction(tr("Copy versions in the clipboard for a support request"))
        data = qgis_server_item.data(Qt.ItemDataRole.UserRole)
        slot = partial(self.copy_as_markdown, data, action_data, action_required)
        server_as_markdown.triggered.connect(slot)

        webdav = webdav_properties(qgis_server_item.data(Qt.ItemDataRole.UserRole + 1))
        if webdav:
            login_item = self.table.item(item.row(), TableCell.Login.value)
            auth_id = login_item.data(Qt.ItemDataRole.UserRole)
            action_remote_repository = menu.addAction(tr("Create a remote Lizmap repository") + "…")
            qgis_dav = ServerWizard.trailing_slash(
                ServerWizard.trailing_slash(webdav.get('url'))
                + webdav.get('projects_path'))
            left_item = self.table.item(item.row(), TableCell.Url.value)
            url = left_item.data(Qt.ItemDataRole.UserRole)
            slot = partial(self.create_remote_repository, auth_id, qgis_dav, url)
            action_remote_repository.triggered.connect(slot)

        show_fonts = menu.addAction(tr("Show fonts available on QGIS Server") + "…")
        data = qgis_server_item.data(Qt.ItemDataRole.UserRole + 1)
        if data:
            data = data.get('qgis_server_info')
            fonts = data.get('fonts')
            if fonts is None:
                fonts = [tr('Upgrade your Lizmap server plugin to have the list of fonts.')]
            name_item = self.table.item(item.row(), TableCell.Name.value)
            slot = partial(self.show_fonts, fonts, name_item.data(Qt.ItemDataRole.DisplayRole))
            show_fonts.triggered.connect(slot)
        else:
            # HTTP Connection refused
            ...

        # noinspection PyArgumentList
        menu.exec(QCursor.pos())

    def create_remote_repository(self, authid: str, webdav_server: str, server: str):
        """ Open the wizard for repository creation. """
        dialog = CreateFolderWizard(self.parent, webdav_server=webdav_server, auth_id=authid, url=server)
        dialog.exec()

    def copy_as_markdown(self, data: str, action_data: str, action_required: bool):
        """ Copy the server information. """
        data += '\n' + self.parent.safeguards_to_markdown()
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(data)
        self.parent.display_message_bar(
            tr('Copied'), tr('Your versions have been copied in your clipboard.'), level=Qgis.MessageLevel.Success)
        if not action_required:
            return

        new_data = tr("Your versions have been copied in your clipboard.")
        new_data += "\n\n"
        new_data += tr("However, you have some actions to do on your server to do before opening a ticket.")
        new_data += "\n\n"
        new_data += tr(
            "For instance, if you are running an old version of Lizmap Web Client, your bug might be "
            "already fixed in a newer version.")
        new_data += "\n\n"
        new_data += tr("You should try to fix these issues : ")
        new_data += "\n\n"
        new_data += action_data
        self.display_all_versions(new_data)

    def show_fonts(self, data: list, alias: str):
        """ Show fonts available on QGIS server. """
        dialog = QDialog()
        dialog.setWindowTitle(tr('Fonts on QGIS Server on {server}').format(server=alias))
        layout = QVBoxLayout(self.parent)
        widget = QListWidget()
        widget.addItems(data)
        # noinspection PyArgumentList
        layout.addWidget(widget)
        dialog.setLayout(layout)
        dialog.exec()

    def display_all_versions(self, data: str):
        """ Display the markdown in a message box. """
        data = data.replace('*', '')
        data = data.replace('<details>', '')
        data = data.replace('</details>', '')
        data = data.replace('<summary>', '')
        data = data.replace('</summary>', '')
        data = data.replace('<br/>', '')
        QMessageBox.information(
            self.parent,
            tr('Server versions'),
            data,
            QMessageBox.StandardButton.Ok)

    @staticmethod
    def released_versions() -> Path:
        """ Path to the release file from LWC. """
        return lizmap_user_folder().joinpath('released_versions.json')

    def migrate_password_manager(self, servers: list):
        """ Migrate all servers in the QGIS authentication database to a better format in the QGIS API.

        This method will be removed in a few versions.
        """
        known_auth_config = []
        auth_manager = QgsApplication.authManager()

        # Lizmap server from JSON
        for server in servers:
            url = server.get('url')
            auth_id = server.get('auth_id')

            conf = self.config_for_id(auth_id)
            if not conf:
                # Let's continue, the user will be invited to edit the server
                continue

            known_auth_config.append(auth_id)

            if '@{}'.format(url) in conf.name():
                # Old format
                LOGGER.warning(f"Migrating the URL {url} in the QGIS authentication database")
                user = conf.config('username')
                password = conf.config('password')

                config = QgsAuthMethodConfig()
                config.setId(auth_id)
                config.setUri(url)
                config.setName(user)
                config.setMethod('Basic')
                config.setConfig('username', user)
                config.setConfig('password', password)
                config.setConfig('realm', QUrl(url).host())
                result = auth_manager.storeAuthenticationConfig(config, True)

                if not result:
                    LOGGER.critical("Error while migrating the server")

        # Other entries in the authentication database
        for config in auth_manager.configIds():
            if config in known_auth_config:
                continue

            conf = self.config_for_id(config)
            if not conf:
                # Why do we have None here ? It's supposed to be existing auth ID ...
                continue

            if '@' not in conf.name():
                continue

            split = conf.name().split('@')
            if QUrl(split[-1]).isValid():
                LOGGER.critical(
                    f"Is the password ID '{config}' in the QGIS authentication database a Lizmap server URL ? If yes, "
                    f"please remove it manually, otherwise skip this message. Go in the QGIS global properties, "
                    f"then 'Authentication' panel and check this ID."
                )
