__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import json
import logging

from qgis.core import Qgis, QgsNetworkContentFetcher
from qgis.PyQt.QtCore import QDate, QLocale, QUrl

from lizmap.definitions.definitions import (
    LwcVersions,
    ReleaseStatus,
    ServerComboData,
)
from lizmap.definitions.online_help import current_locale
from lizmap.dialogs.main import LizmapDialog
from lizmap.dialogs.news import NewVersionDialog
from lizmap.toolbelt.i18n import tr
from lizmap.toolbelt.plugin import lizmap_user_folder

LOGGER = logging.getLogger('Lizmap')
DAYS_BEING_OUTDATED = 90


class VersionChecker:

    def __init__(self, dialog: LizmapDialog, url: str, is_dev: bool):
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
        self.is_dev = is_dev

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

                flag = ReleaseStatus.find(json_version.get('status'))
                self.dialog.server_combo.setItemData(index, flag, ServerComboData.LwcBranchStatus.value)

    def update_lwc_releases(self, released_versions: dict):
        """ Update labels about latest releases. """
        template = (
            '<a href="https://github.com/3liz/lizmap-web-client/releases/tag/{tag}">'
            '{tag}   -    {date}'
            '</a>'
        )

        self.dialog.lwc_version_latest_changelog.setVisible(False)
        self.dialog.lwc_version_oldest_changelog.setVisible(False)

        # The variable "i" is a counter of stable versions
        i = 0

        # During a few months, we can have two stable versions
        # But, we might have as well now a single one
        single_stable_version_release = True
        self.dialog.lwc_version_feature_freeze.setVisible(False)
        for json_version in released_versions:

            # The is_dev flag is to raise an exception only for developers
            # if the Python source code is missing a version
            lwc_version = LwcVersions.find(json_version['branch'], self.is_dev)

            qdate = QDate.fromString(
                json_version['latest_release_date'],
                "yyyy-MM-dd")
            date_string = qdate.toString(QLocale().dateFormat(QLocale.FormatType.ShortFormat))
            status = ReleaseStatus.find(json_version['status'])

            changelog = json_version.get('changelog')
            if changelog:
                changelog = json_version.get('changelog')
                changelog_url = changelog.get(current_locale())
                if not changelog_url:
                    changelog_url = changelog.get('en')

                link = '<a href="{}">{}</a>'.format(
                    changelog_url, tr("What's new in {} ?").format(json_version['branch']))
            else:
                link = None
                changelog_url = None

            text = template.format(
                tag=json_version['latest_release_version'],
                date=date_string,
            )

            if status == ReleaseStatus.ReleaseCandidate:
                if not json_version.get('first_release_date'):
                    # TODO, remove in a few months
                    text = (
                        '<a href="https://github.com/3liz/lizmap-web-client/releases/">'
                        '{tag}   -    {version}'
                        '</a>'
                    ).format(tag=tr("Release candidate"), version=lwc_version.value)
                self.dialog.lwc_version_feature_freeze.setText(text)
                self.dialog.lwc_version_feature_freeze.setVisible(True)

            if status == ReleaseStatus.Stable:
                if i == 0:
                    self.dialog.lwc_version_latest.setText(text)
                    self.date_newest_release_branch = qdate
                    self.newest_release_branch = json_version['latest_release_version']

                    if link:
                        self.dialog.lwc_version_latest_changelog.setVisible(True)
                        self.dialog.lwc_version_latest_changelog.setText(link)

                        # Only call the new version dialog for i == 0, the newest branch
                        # If the changelog link has been published
                        if NewVersionDialog.check_version(lwc_version, self.dialog.table_server.rowCount):
                            new_version = NewVersionDialog(lwc_version, changelog_url)
                            new_version.exec()
                        else:
                            NewVersionDialog.append_version(lwc_version)

                elif i == 1:
                    single_stable_version_release = False
                    self.dialog.lwc_version_oldest.setText(text)
                    self.date_oldest_release_branch = qdate
                    self.oldest_release_branche = json_version['latest_release_version']

                    if link:
                        self.dialog.lwc_version_oldest_changelog.setVisible(True)
                        self.dialog.lwc_version_oldest_changelog.setText(link)

                i += 1
            elif status == ReleaseStatus.Retired:
                if qdate.daysTo(QDate.currentDate()) > DAYS_BEING_OUTDATED:
                    self.outdated.append(lwc_version)

        if single_stable_version_release:
            # We have only one single branch maintained, hide the oldest one.
            self.dialog.lwc_version_oldest_changelog.setVisible(False)
            self.dialog.lwc_version_oldest.setVisible(False)

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
                'update of the plugin in a few months will remove the support for writing the Lizmap configuration '
                'file to this version.'.format(self.newest_release_branch, self.oldest_release_branche)
            )
            self.dialog.display_message_bar(title, description, Qgis.MessageLevel.Warning, 10, details)
            return

        LOGGER.warning(
            "This branch of Lizmap Web Client {} is already outdated for more than {} days. We encourage you "
            "to upgrade to the latest {} or {}. A possible update of the plugin in a few months will remove "
            "the support for writing the Lizmap configuration file to this version".format(
                lwc_version.value,
                DAYS_BEING_OUTDATED,
                self.newest_release_branch,
                self.oldest_release_branche
            )
        )
