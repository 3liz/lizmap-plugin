__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import json
import os

from enum import Enum
from functools import partial
from pathlib import Path
from typing import List, Tuple, Union

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsAuthMethodConfig,
    QgsMessageLog,
    QgsNetworkContentFetcher,
)
from qgis.PyQt.QtCore import QPoint, Qt, QUrl, QVariant
from qgis.PyQt.QtGui import (
    QColor,
    QCursor,
    QDesktopServices,
    QGuiApplication,
    QIcon,
)
from qgis.PyQt.QtNetwork import QNetworkReply
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHeaderView,
    QMenu,
    QMessageBox,
    QTableWidgetItem,
)

from lizmap.dialog_server_form import LizmapServerInfoForm
from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.qgis_plugin_tools.tools.version import version
from lizmap.tools import lizmap_user_folder


class TableCell(Enum):
    """ Cells in the table. """
    Url = 0
    Login = 1
    LizmapVersion = 2
    QgisVersion = 3
    Action = 4


class Color(Enum):
    """ Color used in the table. """
    Success = QColor("green")
    Critical = QColor("red")
    Advice = QColor("orange")  # Warning is a Python builtin
    Normal = QColor("black")


class ServerManager:
    """ Fetch the Lizmap server version for a list of server. """

    def __init__(
            self, parent, table, add_button, remove_button, edit_button, refresh_button, label_no_server,
            up_button, down_button
    ):
        self.parent = parent
        self.table = table
        self.add_button = add_button
        self.remove_button = remove_button
        self.edit_button = edit_button
        self.refresh_button = refresh_button
        self.up_button = up_button
        self.down_button = down_button
        self.label_no_server = label_no_server

        # Network
        self.fetchers = {}

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
        self.table.setColumnCount(5)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.cellDoubleClicked.connect(self.edit_row)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.context_menu_requested)

        # Headers
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)

        item = QTableWidgetItem(tr('URL'))
        item.setToolTip(tr('URL of the server.'))
        self.table.setHorizontalHeaderItem(TableCell.Url.value, item)

        item = QTableWidgetItem(tr('Login'))
        item.setToolTip(tr('Login of the administrator.'))
        self.table.setHorizontalHeaderItem(TableCell.Login.value, item)

        tooltip = tr('Version detected on the server')

        item = QTableWidgetItem(tr('Lizmap Version'))
        item.setToolTip(tooltip)
        self.table.setHorizontalHeaderItem(TableCell.LizmapVersion.value, item)

        item = QTableWidgetItem(tr('QGIS Server Version'))
        item.setToolTip(tooltip)
        self.table.setHorizontalHeaderItem(TableCell.QgisVersion.value, item)

        item = QTableWidgetItem(tr('Action'))
        item.setToolTip(tr('If there is any action to do on the server'))
        self.table.setHorizontalHeaderItem(TableCell.Action.value, item)

        # Connect
        self.add_button.clicked.connect(self.add_row)
        self.remove_button.clicked.connect(self.remove_row)
        self.edit_button.clicked.connect(self.edit_row)
        self.refresh_button.clicked.connect(self.refresh_table)
        self.up_button.clicked.connect(self.move_server_up)
        self.down_button.clicked.connect(self.move_server_down)

        # Actions
        self.load_table()

    @staticmethod
    def login_for_id(auth_id) -> str:
        """ Get the login for a given auth ID in the password manager. """
        auth_manager = QgsApplication.authManager()
        if not auth_manager.masterPasswordIsSet():
            return ''

        conf = QgsAuthMethodConfig()
        auth_manager.loadAuthenticationConfig(auth_id, conf, True)
        if conf.id():
            return conf.config('username', '')

        return ''

    def add_row(self):
        """ Add a new row in the table, asking the URL to the user. """
        dialog = LizmapServerInfoForm(self.parent)
        result = dialog.exec_()

        if result != QDialog.Accepted:
            return

        row = self.table.rowCount()
        self.table.setRowCount(row + 1)
        self._edit_row(row, dialog.current_url(), dialog.auth_id)
        self.save_table()
        self.check_display_warning_no_server()

    def _fetch_cells(self, row: int) -> tuple:
        """ Fetch the URL and the authid in the cells. """
        url_item = self.table.item(row, TableCell.Url.value)
        login_item = self.table.item(row, TableCell.Login.value)
        url = url_item.data(Qt.UserRole)
        auth_id = login_item.data(Qt.UserRole)
        return url, auth_id

    def edit_row(self):
        """ Edit the selected row in the table. """
        selection = self.table.selectedIndexes()

        if len(selection) <= 0:
            return

        row = selection[0].row()
        url, auth_id = self._fetch_cells(row)

        dialog = LizmapServerInfoForm(self.parent, url=url, auth_id=auth_id)
        result = dialog.exec_()

        if result != QDialog.Accepted:
            return

        self._edit_row(row, dialog.current_url(), dialog.auth_id)
        self.save_table()
        self.check_display_warning_no_server()

    def remove_row(self):
        """ Remove the selected row from the table. """
        selection = self.table.selectedIndexes()

        if len(selection) <= 0:
            return

        row = selection[0].row()
        self.table.clearSelection()
        self.table.removeRow(row)
        if row in self.fetchers.keys():
            del self.fetchers[row]
        self.save_table()
        self.check_display_warning_no_server()

    def _edit_row(self, row: int, server_url: str, auth_id: str):
        """ Internal function to edit a row. """
        # URL
        cell = QTableWidgetItem()
        cell.setText(server_url)
        cell.setData(Qt.UserRole, server_url)
        self.table.setItem(row, TableCell.Url.value, cell)

        # Login
        cell = QTableWidgetItem()
        cell.setText(self.login_for_id(auth_id))
        cell.setData(Qt.UserRole, auth_id)
        self.table.setItem(row, TableCell.Login.value, cell)

        # LWC Version
        cell = QTableWidgetItem()
        cell.setText(tr(''))
        cell.setData(Qt.UserRole, None)
        self.table.setItem(row, TableCell.LizmapVersion.value, cell)

        # QGIS Version
        cell = QTableWidgetItem()
        cell.setText('')
        cell.setData(Qt.UserRole, '')
        self.table.setItem(row, TableCell.QgisVersion.value, cell)

        # Action
        cell = QTableWidgetItem()
        cell.setText('')
        cell.setData(Qt.UserRole, '')
        self.table.setItem(row, TableCell.Action.value, cell)

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
        for row in range(self.table.rowCount()):
            url, auth_id = self._fetch_cells(row)
            self.fetch(url, auth_id, row)

    def fetch(self, url: str, auth_id: str, row: int):
        """ Fetch the JSON file and call the function when it's finished. """
        self.display_action(row, False, tr('Fetching…'))
        self.fetchers[row] = QgsNetworkContentFetcher()
        self.fetchers[row].finished.connect(partial(self.request_finished, row))

        if not url.endswith('/'):
            url += '/'

        if auth_id:
            QgsMessageLog.logMessage("Using the token for {}".format(url), "Lizmap", Qgis.Info)

        url_version = '{}index.php/view/app/metadata'.format(url)
        self.fetchers[row].fetchContent(QUrl(url_version), auth_id)

    def request_finished(self, row: int):
        """ Dispatch the answer to update the GUI. """
        _, auth_id = self._fetch_cells(row)

        login = self.login_for_id(auth_id)

        lizmap_cell = QTableWidgetItem()
        qgis_cell = QTableWidgetItem()
        self.table.setItem(row, TableCell.LizmapVersion.value, lizmap_cell)
        self.table.setItem(row, TableCell.QgisVersion.value, qgis_cell)

        reply = self.fetchers[row].reply()

        if not reply:
            lizmap_cell.setText(tr('Error'))
            self.display_action(row, Qgis.Warning, 'Temporary not available')
            return

        if reply.error() != QNetworkReply.NoError:
            if reply.error() == QNetworkReply.HostNotFoundError:
                self.display_action(row, Qgis.Warning, 'Host can not be found. Is-it an intranet server ?')
            if reply.error() == QNetworkReply.ContentNotFoundError:
                self.display_action(
                    row,
                    Qgis.Critical,
                    'Not a valid Lizmap URL or this version is already not maintained < 3.2')
            else:
                self.display_action(row, Qgis.Critical, reply.errorString())
            lizmap_cell.setText(tr('Error'))
            return

        content = self.fetchers[row].contentAsString()
        if not content:
            self.display_action(row, Qgis.Critical, 'Not a valid Lizmap URL')
            return

        try:
            content = json.loads(content)
        except json.JSONDecodeError:
            self.display_action(row, Qgis.Critical, 'Not a JSON document.')
            return

        qgis_server = content.get('qgis_server')
        if not qgis_server:
            self.display_action(row, Qgis.Critical, 'No "qgis_server" in the JSON document')
            return

        mime_type = qgis_server.get('mime_type')
        if not mime_type:
            self.display_action(
                row,
                Qgis.Critical,
                'QGIS Server is not loaded properly. Check the settings in the administration interface.'
            )
            return

        info = content.get('info')
        if not info:
            self.display_action(row, Qgis.Critical, 'No "info" in the JSON document')
            return

        # Lizmap version
        lizmap_version = info.get('version')
        if not info:
            self.display_action(row, Qgis.Critical, 'No "version" in the JSON document')
            return

        lizmap_cell.setText(lizmap_version)

        # Markdown
        markdown = '**Versions :**\n\n'
        markdown += '* Lizmap Web Client : {}\n'.format(lizmap_version)
        markdown += '* Lizmap plugin : {}\n'.format(version())
        markdown += '* QGIS Desktop : {}\n'.format(Qgis.QGIS_VERSION.split('-')[0])
        qgis_cell.setData(Qt.UserRole, markdown)

        # LWC version split
        lizmap_version_split = self._split_lizmap_version(lizmap_version)
        branch = lizmap_version_split[0], lizmap_version_split[1]

        # QGIS Server info
        qgis_server_info = content.get('qgis_server_info')

        # QGIS Server version
        if not qgis_server_info and branch == (3, 5):
            # Running > 3.5.x-pre but < 3.5.1
            # We bypass the metadata section
            self.update_action_version(lizmap_version, None, row, login)
            # Make a better warning to upgrade ASAP
            markdown += '* QGIS Server and plugins unknown status\n'
            qgis_cell.setData(Qt.UserRole, markdown)
            return

        if qgis_server_info and "error" not in qgis_server_info.keys():
            # The current user is an admin, running at least LWC >= 3.5.1
            qgis_version = qgis_server_info.get('metadata').get('version')
            qgis_cell.setText(qgis_version)

            plugins = qgis_server_info.get('plugins')
            # plugins = {'atlasprint': {'version': '3.2.2'}}
            # Temporary, add plugins as markdown in the data
            markdown += '* QGIS Server : {}\n'.format(qgis_version)
            for plugin, info in plugins.items():
                markdown += '* QGIS Server plugin {} : {}\n'.format(plugin, info['version'])
            qgis_cell.setData(Qt.UserRole, markdown)
            self.update_action_version(lizmap_version, qgis_version, row, login)
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
            qgis_cell.setData(Qt.UserRole, markdown)
            self.update_action_version(lizmap_version, None, row)
            return

        if branch >= (3, 5):
            # QGIS Server is either not setup or no login
            if not login:
                # No admin login provided and running LWC >= 3.5
                markdown += '* QGIS Server and plugins unknown status because no admin login provided\n'
                qgis_cell.setData(Qt.UserRole, markdown)
                self.update_action_version(lizmap_version, None, row)
                return
            else:
                if "error" in qgis_server_info.keys():
                    if qgis_server_info['error'] == 'NO_ACCESS':
                        markdown += (
                            '* QGIS Server and plugins unknown status because the login provided is not an '
                            'administrator\n'
                        )
                        qgis_cell.setData(Qt.UserRole, markdown)
                        self.update_action_version(lizmap_version, None, row, login, error=qgis_server_info['error'])
                        return

                    markdown += (
                        '* QGIS Server and plugins unknown status because of the settings in QGIS Server, '
                        'please review your server settings in the Lizmap Web Client administration interface, '
                        'then in the "Server Information" panel.\n'
                    )
                    qgis_cell.setData(Qt.UserRole, markdown)
                    self.update_action_version(lizmap_version, None, row, login, error=qgis_server_info['error'])
                    return

        # Unknown
        markdown += '* QGIS Server and plugins unknown status\n'
        qgis_cell.setData(Qt.UserRole, markdown)
        self.update_action_version(lizmap_version, None, row)

    def load_table(self):
        """ Load the table by reading the user configuration file. """
        user_file = self.user_settings()
        if not os.path.exists(user_file):
            return

        with open(user_file, 'r') as json_file:
            json_content = json.loads(json_file.read())

        for i, server in enumerate(json_content):
            row = self.table.rowCount()
            self.table.setRowCount(row + 1)
            auth_id = json_content[i].get('auth_id', '')
            self._edit_row(row, json_content[i]['url'], auth_id)

        self.check_display_warning_no_server()

    def save_table(self):
        """ Save the table as JSON in the user configuration file. """
        rows = self.table.rowCount()
        data = []
        for row in range(rows):
            url, auth_id = self._fetch_cells(row)
            data.append({
                'url': url,
                'auth_id': auth_id,
            })

        json_file_content = json.dumps(
            data,
            sort_keys=False,
            indent=4
        )
        json_file_content += '\n'

        with open(self.user_settings(), 'w') as json_file:
            json_file.write(json_file_content)

    def check_display_warning_no_server(self):
        """ If we should display or not if there isn't server configured. """
        self.label_no_server.setVisible(self.table.rowCount() == 0)

    def update_action_version(
            self, lizmap_version: str, qgis_version: Union[str, None], row: int, login: str = None,
            error: str = None,
    ):
        """ When we know the version, we can check the latest release from LWC with the file in cache. """
        version_file = Path(lizmap_user_folder()).joinpath('released_versions.json')
        if not version_file.exists():
            return

        level, messages = self._messages_for_version(lizmap_version, qgis_version, login, version_file, error)
        self.display_action(row, level, '\n'.join(messages))

    @staticmethod
    def _messages_for_version(
            lizmap_version: str, qgis_version: Union[str, None], login: str, json_path: Path,
            error: str = '',
    ) -> Tuple[Qgis.MessageLevel, List[str]]:
        """Returns the list of messages and the color to use."""

        # fixme, qgis_version is not used for now
        _ = qgis_version

        with open(json_path, 'r') as json_file:
            json_content = json.loads(json_file.read())

        split_version = lizmap_version.split('.')
        if len(split_version) not in (3, 4):
            # 3.4.0-pre but also 3.4.0-rc.1
            QgsMessageLog.logMessage(
                "The version '{}' is not correct.".format(lizmap_version), "Lizmap", Qgis.Critical)

        branch = '{}.{}'.format(split_version[0], split_version[1])
        full_version = '{}.{}'.format(branch, split_version[2].split('-')[0])

        messages = []
        level = Qgis.Warning

        # Special case for 3.5.0, 3.5.1-pre, 3.5.1-pre.5110
        # Upgrade ASAP, keep it for a few months
        if full_version == '3.5.0' or (full_version == '3.5.1' and len(split_version[2].split('-')) == 2):
            messages.append(
                '⚠ ' + tr(
                    "Upgrade to 3.5.1 as soon as possible, some critical issues were detected with this version."))
            return Qgis.Critical, messages

        is_dev_version = False
        for i, json_version in enumerate(json_content):
            if json_version['branch'] == branch:
                if not json_version['maintained']:
                    if i == 0:
                        # Not maintained, but a dev version
                        messages.append(tr('A dev version, warrior !') + ' 👍')
                        level = Qgis.Success
                        is_dev_version = True
                    else:
                        # Upgrade because the branch is not maintained anymore
                        messages.append(tr('Version {version} not maintained anymore').format(version=branch))
                        level = Qgis.Critical

                # Remember a version can be 3.4.2-pre
                items_bugfix = split_version[2].split('-')
                is_pre_package = len(items_bugfix) > 1
                bugfix = int(items_bugfix[0])
                latest_bugfix = int(json_version['latest_release_version'].split('.')[2])
                if json_version['latest_release_version'] != full_version or is_pre_package:

                    if is_dev_version:
                        return level, messages

                    if bugfix > latest_bugfix:
                        # Congratulations :)
                        messages.append(tr('Higher than a public release') + ' 👍')
                        level = Qgis.Success

                    elif bugfix < latest_bugfix or is_pre_package:
                        # The user is not running the latest bugfix release on the maintained branch

                        if bugfix + 2 < latest_bugfix:
                            # Let's make it clear when they are 2 release late
                            level = Qgis.Critical

                        if bugfix == 0 and json_version['maintained']:
                            # I consider a .0 version fragile
                            messages.append(tr("Running a .0 version, upgrade to the latest bugfix release"))
                        elif bugfix != 0 and json_version['maintained']:
                            messages.append(
                                tr(
                                    'Not latest bugfix release, {version} is available'
                                ).format(version=json_version['latest_release_version']))

                        if is_pre_package:
                            # Pre-release, maybe the package got some updates
                            messages.append(' ' + tr('and you are not running a production package'))

                if int(split_version[0]) >= 3 and int(split_version[1]) >= 5:
                    # Running 3.5.X
                    if not login:
                        messages.append(tr('No login provided'))
                        level = Qgis.Warning

                    if login and error == "NO_ACCESS":
                        messages.append(tr('The login is not an administrator'))
                        level = None  # Not blocking, None will make it default font color

                    if login and error and error != 'NO_ACCESS':
                        messages.append(tr(
                            'Please check your "Server Information" panel in the Lizmap administration interface. '
                            'There is an error reading the QGIS Server configuration.'
                        ))
                        level = Qgis.Critical

                if len(messages) == 0:
                    level = Qgis.Success
                    messages.append("👍")

                return level, messages

        # This should not happen
        return Qgis.Critical, [f"Version {branch} has not been detected as a known version."]

    @staticmethod
    def _split_lizmap_version(lwc_version: str) -> tuple:
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
        if level == Qgis.Success:
            color = Color.Success.value
        elif level == Qgis.Critical:
            color = Color.Critical.value
        elif level == Qgis.Warning:
            color = Color.Advice.value
        else:
            # color = Color.Normal.value
            color = None

        if color:
            cell.setData(Qt.ForegroundRole, QVariant(color))
        else:
            cell.setData(Qt.ForegroundRole, None)
        self.table.setItem(row, TableCell.Action.value, cell)

    def context_menu_requested(self, position: QPoint):
        """ Opens the custom context menu with a right click in the table. """
        item = self.table.itemAt(position)
        if not item:
            return

        top_menu = QMenu(self.table)
        menu = top_menu.addMenu("Menu")

        edit_url = menu.addAction(tr("Edit URL") + "…")
        edit_url.triggered.connect(self.edit_row)

        open_url = menu.addAction(tr("Open URL") + "…")
        left_item = self.table.item(item.row(), TableCell.Url.value)
        url = left_item.data(Qt.UserRole)
        slot = partial(QDesktopServices.openUrl, QUrl(url))
        open_url.triggered.connect(slot)

        action_item = self.table.item(item.row(), TableCell.Action.value)
        action_data = action_item.data(Qt.DisplayRole)
        action_required = action_item.data(Qt.ForegroundRole) in (Color.Advice.value, Color.Critical.value)

        qgis_server_item = self.table.item(item.row(), TableCell.QgisVersion.value)
        data = qgis_server_item.data(Qt.UserRole)

        show_all_versions = menu.addAction(tr("Display all versions") + "…")
        slot = partial(self.display_all_versions, data)
        show_all_versions.triggered.connect(slot)

        server_as_markdown = menu.addAction(tr("Copy versions in the clipboard"))
        data = qgis_server_item.data(Qt.UserRole)
        slot = partial(self.copy_as_markdown, data, action_data, action_required)
        server_as_markdown.triggered.connect(slot)

        # noinspection PyArgumentList
        menu.exec_(QCursor.pos())

    def copy_as_markdown(self, data: str, action_data: str, action_required: bool):
        """ Copy the server information. """
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(data)
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

    def display_all_versions(self, data: str):
        """ Display the markdown in a message box. """
        data = data.replace('*', '')
        QMessageBox.information(
            self.parent,
            tr('Server versions'),
            data,
            QMessageBox.Ok)

    @staticmethod
    def released_versions():
        """ Path to the release file from LWC. """
        return os.path.join(lizmap_user_folder(), 'released_versions.json')

    @staticmethod
    def user_settings():
        """ Path to the user file configuration. """
        return os.path.join(lizmap_user_folder(), 'user_servers.json')
