__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import json
import os

from functools import partial

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsMessageLog,
    QgsNetworkContentFetcher,
)
from qgis.PyQt.QtCore import QPoint, Qt, QUrl, QVariant
from qgis.PyQt.QtGui import QColor, QCursor, QDesktopServices, QIcon
from qgis.PyQt.QtNetwork import QNetworkReply
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QInputDialog,
    QLineEdit,
    QMenu,
    QTableWidgetItem,
)

from lizmap.qgis_plugin_tools.tools.i18n import tr
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
        self.table.setColumnCount(3)
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

        item = QTableWidgetItem(tr('Version'))
        item.setToolTip(tr('Version detected on the server'))
        self.table.setHorizontalHeaderItem(1, item)

        item = QTableWidgetItem(tr('Action'))
        item.setToolTip(tr('If there is any action to do on the server'))
        self.table.setHorizontalHeaderItem(2, item)

        # Connect
        self.add_button.clicked.connect(self.add_row)
        self.remove_button.clicked.connect(self.remove_row)
        self.edit_button.clicked.connect(self.edit_row)
        self.refresh_button.clicked.connect(self.refresh_table)
        self.up_button.clicked.connect(self.move_server_up)
        self.down_button.clicked.connect(self.move_server_down)

        # Actions
        self.load_table()

    def add_row(self):
        """ Add a new row in the table, asking the URL to the user. """
        server_url, result = QInputDialog.getText(
            self.parent,
            tr("New Lizmap Server"),
            tr("URL"),
            QLineEdit.Normal,
        )
        if not result:
            return

        row = self.table.rowCount()
        self.table.setRowCount(row + 1)
        self._edit_row(row, server_url)
        self.save_table()
        self.check_display_warning_no_server()

    def edit_row(self):
        """ Edit the selected row in the table. """
        selection = self.table.selectedIndexes()

        if len(selection) <= 0:
            return

        row = selection[0].row()
        item = self.table.item(row, 0)
        url = item.data(Qt.UserRole)

        server_url, result = QInputDialog.getText(
            self.parent,
            tr("Update Lizmap Server"),
            tr("URL"),
            QLineEdit.Normal,
            text=url
        )
        if not result:
            return

        self._edit_row(row, server_url)
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
        del self.fetchers[row]
        self.save_table()
        self.check_display_warning_no_server()

    def _edit_row(self, row, server_url):
        """ Internal function to edit a row. """
        # URL
        cell = QTableWidgetItem()
        cell.setText(server_url)
        cell.setData(Qt.UserRole, server_url)
        self.table.setItem(row, 0, cell)

        # Version
        cell = QTableWidgetItem()
        cell.setText(tr(''))
        cell.setData(Qt.UserRole, None)
        self.table.setItem(row, 1, cell)

        # Action
        cell = QTableWidgetItem()
        cell.setText('')
        cell.setData(Qt.UserRole, '')
        self.table.setItem(row, 2, cell)

        self.table.clearSelection()
        self.fetch(server_url, row)

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
            item = self.table.item(row, 0)
            url = item.data(Qt.UserRole)
            self.fetch(url, row)

    def fetch(self, url, row):
        """ Fetch the JSON file and call the function when it's finished. """
        self.display_action(row, False, 'Fetching…')
        self.fetchers[row] = QgsNetworkContentFetcher()
        self.fetchers[row].finished.connect(partial(self.request_finished, row))

        if not url.endswith('/'):
            url += '/'

        url_version = '{}index.php/view/app/metadata'.format(url)
        self.fetchers[row].fetchContent(QUrl(url_version))

    def request_finished(self, row):
        """ Dispatch the answer to update the GUI. """
        cell = QTableWidgetItem()

        reply = self.fetchers[row].reply()

        if not reply:
            cell.setText(tr('Error'))
            self.display_action(row, Qgis.Warning, 'Temporary not available')

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
            cell.setText(tr('Error'))
        else:

            content = self.fetchers[row].contentAsString()
            if not content:
                self.display_action(row, Qgis.Critical, 'Not a valid Lizmap URL')
                return

            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                self.display_action(row, Qgis.Critical, 'Not a JSON document.')
                return

            info = content.get('info')
            if not info:
                self.display_action(row, Qgis.Critical, 'No "info" in the JSON document')
                return

            version = info.get('version')
            if not info:
                self.display_action(row, Qgis.Critical, 'No "version" in the JSON document')
                return

            cell.setText(version)
            self.update_action_version(version, row)

        self.table.setItem(row, 1, cell)

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
            self._edit_row(row, json_content[i]['url'])

        self.check_display_warning_no_server()

    def save_table(self):
        """ Save the table as JSON in the user configuration file. """
        rows = self.table.rowCount()
        data = []
        for row in range(rows):
            item = self.table.item(row, 0)
            data.append({'url': item.data(Qt.UserRole)})

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

    def update_action_version(self, server_version, row):
        """ When we know the version, we can check the latest release from LWC with the file in cache. """
        version_file = os.path.join(lizmap_user_folder(), 'released_versions.json')
        if not os.path.exists(version_file):
            return

        with open(version_file, 'r') as json_file:
            json_content = json.loads(json_file.read())

        split_version = server_version.split('.')
        if len(split_version) not in [3, 4]:
            # 3.4.0-pre but also 3.4.0-rc.1
            QgsMessageLog.logMessage(
                "The version '{}' is not correct.".format(server_version), "Lizmap", Qgis.Critical)

        # Debug
        # split_version = ['3', '4', '2-pre']
        branch = '{}.{}'.format(split_version[0], split_version[1])
        full_version = '{}.{}'.format(branch, split_version[2].split('-')[0])

        messages = []
        level = Qgis.Warning

        for i, version in enumerate(json_content):
            if version['branch'] == branch:
                if not version['maintained']:
                    if i == 0:
                        messages.append(tr('A dev version, warrior !') + ' 👍')
                        level = Qgis.Success
                    else:
                        messages.append(tr('Version {version} not maintained anymore').format(version=branch))
                        level = Qgis.Critical

                # Remember a version can be 3.4.2-pre
                items_bugfix = split_version[2].split('-')
                bugfix = int(items_bugfix[0])
                latest_bugfix = int(version['latest_release_version'].split('.')[2])
                if version['latest_release_version'] != full_version:
                    if bugfix > latest_bugfix:
                        messages.append(tr('Higher than a public release') + ' 👍')

                    elif bugfix < latest_bugfix:
                        messages.append(tr('Not latest bugfix release'))
                        if len(items_bugfix) > 1:
                            # Pre release
                            messages.append(' ' + tr('and not a production package'))

                self.display_action(row, level, ', '.join(messages))
                break
        else:
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
        self.table.setItem(row, 2, cell)

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

        # noinspection PyArgumentList
        menu.exec_(QCursor.pos())

    @staticmethod
    def released_versions():
        """ Path to the release file from LWC. """
        return os.path.join(lizmap_user_folder(), 'released_versions.json')

    @staticmethod
    def user_settings():
        """ Path to the user file configuration. """
        return os.path.join(lizmap_user_folder(), 'user_servers.json')
