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
from qgis.PyQt.QtCore import Qt, QUrl, QVariant
from qgis.PyQt.QtGui import QColor, QIcon
from qgis.PyQt.QtNetwork import QNetworkReply
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QInputDialog,
    QLineEdit,
    QTableWidgetItem,
)

from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.tools import lizmap_user_folder


class ServerManager:

    """ Fetch the Lizmap server version for a list of server. """

    def __init__(
            self, parent, table, add_button, remove_button, edit_button, refresh_button, label_no_server):
        self.parent = parent
        self.table = table
        self.add_button = add_button
        self.remove_button = remove_button
        self.edit_button = edit_button
        self.refresh_button = refresh_button
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

        # Table
        self.table.setColumnCount(3)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.cellDoubleClicked.connect(self.edit_row)

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
        if len(split_version) != 3:
            QgsMessageLog.logMessage(
                "The version '{}' is not correct.".format(server_version), "Lizmap", Qgis.Critical)

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

                if version['latest_release_version'] != full_version:
                    messages.append(tr('Not latest bugfix release'))

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

    @staticmethod
    def released_versions():
        """ Path to the release file from LWC. """
        return os.path.join(lizmap_user_folder(), 'released_versions.json')

    @staticmethod
    def user_settings():
        """ Path to the user file configuration. """
        return os.path.join(lizmap_user_folder(), 'user_servers.json')
