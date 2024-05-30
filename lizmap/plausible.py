__copyright__ = 'Copyright 2024, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import json
import os
import platform

from qgis.core import Qgis, QgsNetworkAccessManager, QgsSettings
from qgis.PyQt.QtCore import QByteArray, QDateTime, QLocale, QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest

from lizmap.definitions.definitions import (
    PLAUSIBLE_DOMAIN_PROD,
    PLAUSIBLE_DOMAIN_TEST,
    PLAUSIBLE_URL_PROD,
    PLAUSIBLE_URL_TEST,
    LwcVersions,
    ServerComboData,
)
from lizmap.definitions.lizmap_cloud import EXCLUDED_DOMAINS, WORKSHOP_DOMAINS
from lizmap.saas import is_lizmap_cloud
from lizmap.toolbelt.convert import to_bool
from lizmap.toolbelt.version import version

MIN_SECONDS = 3600
ENV_SKIP_STATS = "LIZMAP_SKIP_STATS"


# For testing purpose, to test.
# Similar to QGIS dashboard https://feed.qgis.org/metabase/public/dashboard/df81071d-4c75-45b8-a698-97b8649d7228
# We only collect data listed in the list below
# and the country according to IP address.
# The IP is not stored by Plausible Community Edition https://github.com/plausible/analytics
# Plausible is GDPR friendly https://plausible.io/data-policy
# The User-Agent is set by QGIS Desktop itself

class Plausible:

    def __init__(self, dlg):
        """ Constructor. """
        self.dialog = dlg
        self.previous_date = None
        self.locale = QgsSettings().value("locale/userLocale", "")
        if self.locale == "":
            self.locale = QLocale().name()
        self.locale = self.locale[0:2].lower()

    def request_stat_event(self) -> bool:
        """ Request to send an event to the API. """
        if not to_bool(os.getenv(ENV_SKIP_STATS)):
            # Disabled by environment variable
            return False

        if self.dialog.table_server.rowCount() == 0:
            # At least one server in the table
            return False

        if to_bool(os.getenv("CI"), default_value=False):
            # If running on CI, do not send stats
            return False

        current = QDateTime().currentDateTimeUtc()
        if self.previous_date and self.previous_date.secsTo(current) < MIN_SECONDS:
            # Not more than one request per hour
            return False

        if not self.dialog.current_lwc_version(default_value=False):
            # Let's wait to have the JSON in the combobox
            return False

        metadata = self.dialog.current_server_info(ServerComboData.JsonMetadata.value)
        if not metadata:
            return False

        qgis_server_info = metadata.get('qgis_server_info')
        if not qgis_server_info:
            return False

        qgis_metadata = qgis_server_info.get('metadata')
        if not qgis_metadata:
            return False

        qgis_server_version = qgis_metadata.get('version')
        if not qgis_server_version:
            return False

        if self._send_stat_event(metadata, qgis_server_version):
            self.previous_date = current
            return True

        return False

    def _send_stat_event(self, current_metadata: dict, qgis_server_version: str) -> bool:
        """ Send stats event to the API. """
        # Only turn ON for debug purpose, temporary !
        debug = False
        extra_debug = False

        lizmap_plugin_version = version()
        if lizmap_plugin_version in ('master', 'dev'):
            # Dev versions of the plugin, it's a kind of debug
            debug = True

        lizmap_cloud_instances = []
        for row in range(self.dialog.server_combo.count()):
            metadata = self.dialog.server_combo.itemData(row, ServerComboData.JsonMetadata.value)
            url = self.dialog.server_combo.itemData(row, ServerComboData.ServerUrl.value)
            if bool([domain for domain in EXCLUDED_DOMAINS if (domain in url)]):
                # We do not want to count for dev
                debug = True

            if bool([domain for domain in WORKSHOP_DOMAINS if (domain in url)]):
                # Workshop are temporary servers, for a month usually, let's not count them
                continue

            lizmap_cloud_instances.append(is_lizmap_cloud(metadata))

        if len(lizmap_cloud_instances) == 0:
            # Because of workshop servers
            return False

        if all(lizmap_cloud_instances):
            lizmap_cloud = 'all'
        elif any(lizmap_cloud_instances):
            lizmap_cloud = 'mixed'
        else:
            lizmap_cloud = 'no'

        plausible_url = PLAUSIBLE_URL_TEST if debug else PLAUSIBLE_URL_PROD

        request = QNetworkRequest()
        # noinspection PyArgumentList
        request.setUrl(QUrl(plausible_url))
        if extra_debug:
            request.setRawHeader(b"X-Debug-Request", b"true")
            request.setRawHeader(b"X-Forwarded-For", b"127.0.0.1")
        request.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")

        # Qgis.QGIS_VERSION → 3.34.6-Prizren
        # noinspection PyUnresolvedReferences
        qgis_version_full = Qgis.QGIS_VERSION.split('-')[0]
        # qgis_version_full → 3.34.6
        qgis_version_branch = '.'.join(qgis_version_full.split('.')[0:2])
        # qgis_version_branch → 3.34

        python_version_full = platform.python_version()
        # python_version_full → 3.10.12
        python_version_branch = '.'.join(python_version_full.split('.')[0:2])
        # python_version_branch → 3.10

        # Current selected metadata
        lwc_version_full = current_metadata.get("info").get("version")
        # lwc_version_full → 3.7.7-pre.7357
        lwc_version_light = lwc_version_full.split('-')[0]
        # lwc_version_light → 3.7.7
        lwc_version_branch = LwcVersions.find_from_metadata(current_metadata)
        # lwc_version_branch → 3.7 as Python enum

        # qgis_server_version → 3.34.6
        qgis_server_branch = '.'.join(qgis_server_version.split('.')[0:2])
        # qgis_server_branch → 3.34

        # QGIS version diff between desktop and server
        # QGIS Server 3.34, QGIS Desktop 3.30 → 6
        # QGIS Server 3.28, QGIS Desktop 3.36 → -8
        # Positive number are better
        qgis_diff = int(qgis_server_branch.split('.')[1]) - int(qgis_version_branch.split('.')[1])

        data = {
            "name": "plugin",
            "props": {
                # Lizmap Desktop version
                "lizmap-plugin-version": lizmap_plugin_version,
                "lizmap-plugin-desktop": 'yes',
                # Current server LWC and linked QGIS server
                "client-version-full": lwc_version_full,
                "client-version-light": lwc_version_light,
                "client-version-branch": lwc_version_branch.value,
                "qgis-server-full": qgis_server_version,
                "qgis-server-branch": qgis_server_branch,
                # Lizmap Cloud
                "lizmap-cloud-instances": lizmap_cloud,
                "lizmap-cloud": 'yes' if any(lizmap_cloud_instances) else 'no',
                # QGIS
                "qgis-version-full": qgis_version_full,
                "qgis-version-branch": qgis_version_branch,
                # Diff between desktop and server
                "qgis-version-diff": qgis_diff,
                # Python
                "python-version-full": python_version_full,
                "python-version-branch": python_version_branch,
                # Locale
                "locale-qgis": self.locale,
                # OS
                "os-name": platform.system(),
                "os-version": platform.release(),
            },
            "url": plausible_url,
            "domain": PLAUSIBLE_DOMAIN_TEST if debug else PLAUSIBLE_DOMAIN_PROD,
        }
        # noinspection PyArgumentList
        reply = QgsNetworkAccessManager.instance().post(request, QByteArray(str.encode(json.dumps(data))))
        _ = reply
        # return reply.attribute(QNetworkRequest.HttpStatusCodeAttribute).startswith(('1', '2', '3'))
        return True
