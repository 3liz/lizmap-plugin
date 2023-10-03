__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import json
import logging

from typing import Tuple

from qgis.core import Qgis, QgsNetworkContentFetcher
from qgis.PyQt.QtCore import QDate, QLocale, QUrl

from lizmap.definitions.definitions import (
    LwcVersions,
    ReleaseStatus,
    ServerComboData,
)
from lizmap.definitions.online_help import current_locale
from lizmap.dialogs.main import LizmapDialog
from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.tools import lizmap_user_folder

LOGGER = logging.getLogger('Lizmap')
DAYS_BEING_OUTDATED = 90


class VersionChecker:

    def __init__(self, dialog: LizmapDialog, url):
        """ Update the dialog when versions have been fetched. """
        self.dialog = dialog
        self.url = url
        self.fetcher = None
        self.json = None
        self.date_oldest_release_branch = None
        self.date_newest_release_branch = None
        self.oldest_release_branche = None
        self.newest_release_branch = None
        self.outdated = []

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
        try:
            released_versions = json.loads(content)
        except json.JSONDecodeError:
            # Issue reported by rldhont by mail
            LOGGER.error(
                "Error while reading the JSON file from Lizmap Web Client main repository, check the content with the "
                "QGIS debug panel"
            )
            return

        self.update_lwc_releases(released_versions)
        self.update_lwc_servers(released_versions)

        # Cache the file
        content += '\n'
        with open(lizmap_user_folder().joinpath("released_versions.json"), "w") as output:
            output.write(content)

    @classmethod
    def version_status(cls, status: str) -> Tuple[ReleaseStatus, str]:
        """ Return the release status according to the JSON content. """
        if status == 'dev':
            flag = ReleaseStatus.Dev
        elif status == 'feature_freeze':
            flag = ReleaseStatus.ReleaseCandidate
        elif status == 'stable':
            flag = ReleaseStatus.Stable
        elif status == 'retired':
            flag = ReleaseStatus.Retired
        else:
            flag = ReleaseStatus.Unknown

        return flag, cls.status_display_string(flag)

    @classmethod
    def status_display_string(cls, status: ReleaseStatus) -> str:
        """ Return a human display string status. """
        if status == ReleaseStatus.Dev:
            return tr('Next')
        elif status == ReleaseStatus.ReleaseCandidate:
            return tr('Feature freeze')
        elif status == ReleaseStatus.Stable:
            return tr('Stable')
        elif status == ReleaseStatus.Retired:
            return tr('Not maintained')
        elif status is None or status == ReleaseStatus.Unknown:
            return tr('Inconnu')
        else:
            raise Exception('Unknown status type : {}'.format(status))

    def update_lwc_servers(self, released_versions: dict):
        """ Update LWC version status for each server. """
        for index in range(self.dialog.server_combo.count()):
            version = self.dialog.current_lwc_version()

            for i, json_version in enumerate(released_versions):
                try:
                    lwc_version = LwcVersions(json_version['branch'])
                except ValueError:
                    # The version is found in the online JSON file
                    # But not in the Lizmap source code, in the "definitions.py" file
                    # We can continue, we do nothing with this version. It's not displayed in the UI.
                    continue

                if lwc_version != version:
                    continue

                flag, suffix = self.version_status(json_version.get('status'))
                self.dialog.server_combo.setItemData(index, flag, ServerComboData.LwcBranchStatus.value)

    def update_lwc_releases(self, released_versions: dict):
        """ Update labels about latest releases. """
        template = (
            '<a href="https://github.com/3liz/lizmap-web-client/releases/tag/{tag}">'
            '{tag}   -    {date}'
            '</a>')

        self.dialog.lwc_version_latest_changelog.setVisible(False)
        self.dialog.lwc_version_oldest_changelog.setVisible(False)

        i = 0
        for json_version in released_versions:
            qdate = QDate.fromString(
                json_version['latest_release_date'],
                "yyyy-MM-dd")
            date_string = qdate.toString(QLocale().dateFormat(QLocale.ShortFormat))
            status = ReleaseStatus.find(json_version['status'])

            changelog = json_version.get('changelog')
            if changelog:
                changelog = json_version.get('changelog')
                link = changelog.get(current_locale())
                if not link:
                    link = changelog.get('en')

                link = '<a href="{}">{}</a>'.format(link, tr("What's new in {} ?").format(json_version['branch']))
            else:
                link = None

            if status == ReleaseStatus.Stable:
                if i == 0:
                    text = template.format(
                        tag=json_version['latest_release_version'],
                        date=date_string,
                    )
                    self.dialog.lwc_version_latest.setText(text)
                    self.date_newest_release_branch = qdate
                    self.newest_release_branch = json_version['latest_release_version']

                    if link:
                        self.dialog.lwc_version_latest_changelog.setVisible(True)
                        self.dialog.lwc_version_latest_changelog.setText(link)

                elif i == 1:
                    text = template.format(
                        tag=json_version['latest_release_version'],
                        date=date_string,
                    )
                    self.dialog.lwc_version_oldest.setText(text)
                    self.date_oldest_release_branch = qdate
                    self.oldest_release_branche = json_version['latest_release_version']

                    if link:
                        self.dialog.lwc_version_oldest_changelog.setVisible(True)
                        self.dialog.lwc_version_oldest_changelog.setText(link)

                i += 1
            elif status == ReleaseStatus.Retired:
                lwc_version = LwcVersions.find(json_version['branch'])
                if qdate.daysTo(QDate.currentDate()) > DAYS_BEING_OUTDATED:
                    self.outdated.append(lwc_version)

    def check_outdated_version(self, lwc_version: LwcVersions, with_gui: True):
        """ Display a warning about outdated LWC version. """
        if lwc_version not in self.outdated:
            return

        if with_gui:
            title = tr('Outdated branch of Lizmap Web Client')
            description = tr(
                "This branch of Lizmap Web Client {} is already outdated for more than {} days.").format(
                lwc_version.value, DAYS_BEING_OUTDATED)
            details = tr(
                'We encourage you strongly to upgrade to the latest {} or {} as soon as possible. A possible '
                'update of the plugin in a few months will remove the support for writing CFG file to this '
                'version.'.format(self.newest_release_branch, self.oldest_release_branche)
            )
            self.dialog.display_message_bar(title, description, Qgis.Warning, 10, details)
            return

        LOGGER.warning(
            "This branch of Lizmap Web Client {} is already outdated for more than {} days. We encourage you "
            "to upgrade to the latest {} or {}. A possible update of the plugin in a few months will remove "
            "the support for writing CFG file to this version".format(
                lwc_version.value,
                DAYS_BEING_OUTDATED,
                self.newest_release_branch,
                self.oldest_release_branche
            )
        )
