__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import json
import os

from qgis.core import QgsNetworkContentFetcher
from qgis.PyQt.QtCore import QDate, QLocale, QUrl
from qgis.PyQt.QtWidgets import QDialog

from lizmap.definitions.definitions import LwcVersions
from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.tools import lizmap_user_folder


class VersionChecker:

    def __init__(self, dialog: QDialog, url):
        """ Update the dialog when versions has been fetched. """
        self.dialog = dialog
        self.url = url
        self.fetcher = None
        self.json = None

    def fetch(self):
        """ Fetch the JSON file and call the function when it's finished. """
        self.fetcher = QgsNetworkContentFetcher()
        self.fetcher.finished.connect(self.request_finished)
        self.fetcher.fetchContent(QUrl(self.url))

    def request_finished(self):
        """ Dispatch the answer to update the GUI. """
        content = self.fetcher.contentAsString()
        if not content:
            return

        # Update the UI
        released_versions = json.loads(content)
        self.update_lwc_releases(released_versions)
        self.update_lwc_selector(released_versions)

        # Cache the file
        content += '\n'
        folder = lizmap_user_folder()
        with open(os.path.join(folder, "released_versions.json"), "w") as output:
            output.write(content)

    def update_lwc_selector(self, released_versions: dict):
        """ Update LWC selector showing outdated versions. """
        for i, json_version in enumerate(released_versions):
            if not json_version['maintained']:
                index = self.dialog.combo_lwc_version.findData(LwcVersions(json_version['branch']))
                text = self.dialog.combo_lwc_version.itemText(index)

                if i == 0:
                    # If it's the first item in the list AND not maintained, then it's the next LWC version
                    new_text = text + ' - ' + tr('Next')
                else:
                    new_text = text + ' - ' + tr('Not maintained')
                self.dialog.combo_lwc_version.setItemText(index, new_text)

    def update_lwc_releases(self, released_versions: dict):
        """ Update labels about latest releases. """
        template = (
            '<a href="https://github.com/3liz/lizmap-web-client/releases/tag/{tag}">'
            '{tag}   -    {date}'
            '</a>')

        i = 0
        for json_version in released_versions:
            qdate = QDate.fromString(
                json_version['latest_release_date'],
                "yyyy-MM-dd")
            date_string = qdate.toString(QLocale().dateFormat(QLocale.ShortFormat))
            if json_version['maintained']:
                if i == 0:
                    text = template.format(
                        tag=json_version['latest_release_version'],
                        date=date_string,
                    )
                    self.dialog.lwc_version_latest.setText(text)
                elif i == 1:
                    text = template.format(
                        tag=json_version['latest_release_version'],
                        date=date_string,
                    )
                    self.dialog.lwc_version_oldest.setText(text)
                i += 1
