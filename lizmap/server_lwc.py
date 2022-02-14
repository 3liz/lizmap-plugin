__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import json
import os

from functools import partial
from typing import Union

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
        self.table.setHorizontalHeaderItem(0, item)

        item = QTableWidgetItem(tr('Login'))
        item.setToolTip(tr('Login of the administrator.'))
        self.table.setHorizontalHeaderItem(1, item)

        tooltip = tr('Version detected on the server')

        item = QTableWidgetItem(tr('Lizmap Version'))
        item.setToolTip(tooltip)
        self.table.setHorizontalHeaderItem(2, item)

        item = QTableWidgetItem(tr('QGIS Version'))
        item.setToolTip(tooltip)
        self.table.setHorizontalHeaderItem(3, item)

        item = QTableWidgetItem(tr('Action'))
        item.setToolTip(tr('If there is any action to do on the server'))
        self.table.setHorizontalHeaderItem(4, item)

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
        url_item = self.table.item(row, 0)
        login_item = self.table.item(row, 1)
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
        self.table.setItem(row, 0, cell)

        # Login
        cell = QTableWidgetItem()
        cell.setText(self.login_for_id(auth_id))
        cell.setData(Qt.UserRole, auth_id)
        self.table.setItem(row, 1, cell)

        # LWC Version
        cell = QTableWidgetItem()
        cell.setText(tr(''))
        cell.setData(Qt.UserRole, None)
        self.table.setItem(row, 2, cell)

        # QGIS Version
        cell = QTableWidgetItem()
        cell.setText('')
        cell.setData(Qt.UserRole, '')
        self.table.setItem(row, 3, cell)

        # Action
        cell = QTableWidgetItem()
        cell.setText('')
        cell.setData(Qt.UserRole, '')
        self.table.setItem(row, 4, cell)

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
            QgsMessageLog.logMessage("Using the token for {}".format(url), "Lizmap", Qgis.Critical)

        url_version = '{}index.php/view/app/metadata'.format(url)
        if Qgis.QGIS_VERSION_INT < 31000:
            QgsMessageLog.logMessage(
                "Skipping the authentification for the Lizmap server {}. QGIS must be 3.10 minimum to use the "
                "authentification when doing HTTP requests.".format(url),
                "Lizmap",
                Qgis.Critical
            )
            self.fetchers[row].fetchContent(QUrl(url_version))
        else:
            # QGIS 3.10 and higher have authentification support
            self.fetchers[row].fetchContent(QUrl(url_version), auth_id)

    def request_finished(self, row: int):
        """ Dispatch the answer to update the GUI. """
        _, auth_id = self._fetch_cells(row)

        login = self.login_for_id(auth_id)

        lizmap_cell = QTableWidgetItem()
        qgis_cell = QTableWidgetItem()
        self.table.setItem(row, 2, lizmap_cell)
        self.table.setItem(row, 3, qgis_cell)

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

        # QGIS Server version
        qgis_version = None
        if not content.get('qgis_server_info') and lizmap_version.startswith('3.5'):
            # Running < 3.5.1
            # We bypass the metadata section
            self.update_action_version(lizmap_version, qgis_version, row, login)
            # Make a better warning to upgrade ASAP
            markdown += '* QGIS Server and plugins unknown status\n'
            qgis_cell.setData(Qt.UserRole, markdown)
            return

        qgis_server_info = content.get('qgis_server_info')
        if qgis_server_info and "error" not in qgis_server_info.keys():
            # The current user is an admin, running at least LWC 3.5.1
            qgis_version = qgis_server_info.get('metadata').get('version')
            qgis_cell.setText(qgis_version)

            plugins = qgis_server_info.get('plugins')
            # plugins = {'atlasprint': {'version': '3.2.2'}}
            # Temporary, add plugins as markdown in the data
            markdown += '* QGIS Server : {}\n'.format(qgis_version)
            for plugin, info in plugins.items():
                markdown += '* QGIS Server plugin {} : {}\n'.format(plugin, info['version'])
        else:
            markdown += '* QGIS Server and plugins unknown status\n'

        qgis_cell.setData(Qt.UserRole, markdown)
        self.update_action_version(lizmap_version, qgis_version, row, login)

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
            self, lizmap_version: str, qgis_version: Union[str, None], row: int, login: str):
        """ When we know the version, we can check the latest release from LWC with the file in cache. """

        version_file = os.path.join(lizmap_user_folder(), 'released_versions.json')
        if not os.path.exists(version_file):
            return

        with open(version_file, 'r') as json_file:
            json_content = json.loads(json_file.read())

        split_version = lizmap_version.split('.')
        if len(split_version) not in (3, 4):
            # 3.4.0-pre but also 3.4.0-rc.1
            QgsMessageLog.logMessage(
                "The version '{}' is not correct.".format(lizmap_version), "Lizmap", Qgis.Critical)

        # Debug
        # split_version = ('3', '5', '1')
        # split_version = ('3', '5', '1-pre')

        branch = '{}.{}'.format(split_version[0], split_version[1])
        full_version = '{}.{}'.format(branch, split_version[2].split('-')[0])

        messages = []
        level = Qgis.Warning

        for i, json_version in enumerate(json_content):
            if json_version['branch'] == branch:
                if not json_version['maintained']:
                    if i == 0:
                        # Not maintained, but a dev version
                        messages.append(tr('A dev version, warrior !') + ' 👍')
                        level = Qgis.Success
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
                    if bugfix > latest_bugfix:
                        # Congratulations :)
                        messages.append(tr('Higher than a public release') + ' 👍')
                        level = Qgis.Success

                    elif bugfix < latest_bugfix or is_pre_package:
                        # The user is not running the latest bugfix release on the maintained branch

                        if bugfix + 2 < latest_bugfix:
                            # Let's make it clear when they are 2 release late
                            level = Qgis.Critical

                        if bugfix == 0:
                            # I consider a .0 version fragile
                            messages.append(tr("Running a .0 version, upgrade to the latest bugfix release"))
                        else:
                            messages.append(
                                tr(
                                    'Not latest bugfix release, {version} is available'
                                ).format(version=json_version['latest_release_version']))

                        if is_pre_package:
                            # Pre-release, maybe the package got some updates
                            messages.append(' ' + tr('and you are not running a production package'))

                # TODO check the login against the response from QGIS Server if the user is not admin
                if not login and int(split_version[0]) >= 3 and int(split_version[1]) >= 5:
                    messages.append(tr('No login provided'))
                    level = Qgis.Warning

                self.display_action(row, level, '\n'.join(messages))
                break
        else:
            # This should not happen
            self.display_action(
                row, Qgis.Critical, f"Version {branch} has not been detected has a known version.")

    def display_action(self, row, level, message):
        """ Display the action if needed to the user with a color. """
        cell = QTableWidgetItem()
        cell.setText(message)
        cell.setToolTip(message)
        if level == Qgis.Success:
            color = QColor("green")
        elif level == Qgis.Critical:
            color = QColor("red")
        else:
            color = QColor("orange")
        cell.setData(Qt.ForegroundRole, QVariant(color))
        self.table.setItem(row, 4, cell)

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
        left_item = self.table.item(item.row(), 0)
        url = left_item.data(Qt.UserRole)
        slot = partial(QDesktopServices.openUrl, QUrl(url))
        open_url.triggered.connect(slot)

        qgis_server_item = self.table.item(item.row(), 3)
        data = qgis_server_item.data(Qt.UserRole)

        show_all_versions = menu.addAction(tr("Display all versions") + "…")
        slot = partial(self.display_all_versions, data)
        show_all_versions.triggered.connect(slot)

        server_as_markdown = menu.addAction(tr("Copy versions in the clipboard"))
        data = qgis_server_item.data(Qt.UserRole)
        slot = partial(self.copy_as_markdown, data)
        server_as_markdown.triggered.connect(slot)

        # noinspection PyArgumentList
        menu.exec_(QCursor.pos())

    @staticmethod
    def copy_as_markdown(data):
        """ Copy the server information. """
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(data)

    def display_all_versions(self, data):
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
