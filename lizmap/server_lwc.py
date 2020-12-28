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

    def __init__(self, parent, table, add_button, remove_button, edit_button, label_no_server):
        self.parent = parent
        self.table = table
        self.add_button = add_button
        self.remove_button = remove_button
        self.edit_button = edit_button
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
        header.setSectionResizeMode(0, QHeaderView.Stretch)

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

        # Actions
        self.load_table()

    def add_row(self):
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
        self.fetch(server_url, row)
        self.check_display_warning_no_server()

    def remove_row(self):
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
        self.display_action(row, False, 'Wrong URL or the server is unreachable or too old.')

    def fetch(self, url, row):
        """ Fetch the JSON file and call the function when it's finished. """
        self.fetchers[row] = QgsNetworkContentFetcher()
        self.fetchers[row].finished.connect(partial(self.request_finished, row))

        if not url.endswith('/'):
            url += '/'

        url_version = '{}index.php/view/app/metadata'.format(url)
        self.fetchers[row].fetchContent(QUrl(url_version))

    def request_finished(self, row):
        """ Dispatch the answer to update the GUI. """
        content = self.fetchers[row].contentAsString()
        if not content:
            return

        try:
            version = json.loads(content)['info']['version']
        except json.JSONDecodeError:
            QgsMessageLog.logMessage("The URL for the Lizmap server is not correct.", "Lizmap", Qgis.Critical)
            return

        cell = QTableWidgetItem()
        cell.setText(version)
        self.table.setItem(row, 1, cell)
        self.update_action_version(version, row)

    def load_table(self):
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
        """ Save the table as JSON. """
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
        self.label_no_server.setVisible(self.table.rowCount() == 0)

    def update_action_version(self, server_version, row):
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
                        messages.append('Warrior ! 👍')
                        level = Qgis.Success
                    else:
                        messages.append(tr('Version not maintained anymore'))
                        level = Qgis.Critical

                if version['latest_release_version'] != full_version:
                    messages.append(tr('Not latest bugfix release'))

                self.display_action(row, level, ', '.join(messages))
                return

    def display_action(self, row, level, message):
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
        return os.path.join(lizmap_user_folder(), 'released_versions.json')

    @staticmethod
    def user_settings():
        return os.path.join(lizmap_user_folder(), 'user_servers.json')
