""" Test version info. """

import unittest

from pathlib import Path

from qgis.core import Qgis

from lizmap.qgis_plugin_tools.tools.resources import plugin_test_data_path
from lizmap.server_lwc import ServerManager

__copyright__ = 'Copyright 2022, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


class TestVersionInfo(unittest.TestCase):

    def test_split_lizmap_version(self):
        """ Test to split the LWC version. """
        self.assertTupleEqual(ServerManager._split_lizmap_version("3.5.2"), (3, 5, 2))
        self.assertTupleEqual(ServerManager._split_lizmap_version("3.5.2-pre"), (3, 5, 2, 'pre'))
        self.assertTupleEqual(ServerManager._split_lizmap_version("3.5.2-pre.5204"), (3, 5, 2, 'pre', 5204))

    def test_version_info_lizmap_status(self):
        """ Test version info according to LWC version and QGIS version.

        With the given JSON file, 3.6 was on development and login was not required.
        See the second test for a more up-to-date version file with 3.6 and server login required.
        """

        # Test file with
        # 3.6.0 active dev
        # 3.5.1 latest 3.5.X
        # 3.5.0 critical
        # 3.4.9 latest 3.4.X
        # 3.3.X deprecated
        json_path = Path(plugin_test_data_path('version_info_15022022.json'))

        # 3.6.0 without login
        self.assertEqual(
            ServerManager._messages_for_version('3.6.0', '', '', json_path),
            (
                Qgis.Critical,
                [
                    'No administrator/publisher login provided',
                    'A dev version, warrior ! 👍'
                ],
                False,
            )
        )

        # 3.6.0 with login
        self.assertEqual(
            ServerManager._messages_for_version('3.6.0', '', 'bob_is_admin', json_path),
            (
                Qgis.Success,
                [
                    'A dev version, warrior ! 👍'
                ],
                True,
            )
        )

        # 3.5.1 with error
        self.assertEqual(
            ServerManager._messages_for_version('3.5.1', '', 'bob_is_admin', json_path, error='HTTP_ERROR'),
            (
                Qgis.Critical,
                [
                    'Please check your "Server Information" panel in the Lizmap administration interface. There is an '
                    'error reading the QGIS Server configuration.',
                ],
                True,
            )
        )

        # 3.5.1 with login denied
        # Starting with the QGIS plugin version 3.9.2, login is required
        self.assertEqual(
            ServerManager._messages_for_version('3.5.1', '', 'bob_is_not_admin', json_path, error='NO_ACCESS'),
            (
                Qgis.Critical,
                [
                    'The login is not a publisher/administrator'
                ],
                True,
            )
        )

        # 3.5.1
        self.assertEqual(
            ServerManager._messages_for_version('3.5.1', '', 'bob_is_admin', json_path),
            (
                Qgis.Success,
                [
                    '👍'
                ],
                True,
            )
        )

        # 3.5.1-pre
        self.assertEqual(
            ServerManager._messages_for_version('3.5.1-pre', '', '', json_path),
            (
                Qgis.Critical,
                [
                    '⚠ Upgrade to 3.5.1 as soon as possible, some critical issues were detected with this version.'
                ],
                False,
            )
        )

        # 3.5.1-pre.5110
        self.assertEqual(
            ServerManager._messages_for_version('3.5.1-pre.5110', '', '', json_path),
            (
                Qgis.Critical,
                [
                    '⚠ Upgrade to 3.5.1 as soon as possible, some critical issues were detected with this version.'
                ],
                False,
            )
        )

        # 3.5.0
        self.assertEqual(
            ServerManager._messages_for_version('3.5.0', '', '', json_path),
            (
                Qgis.Critical,
                [
                    '⚠ Upgrade to 3.5.1 as soon as possible, some critical issues were detected with this version.'
                ],
                False,
            )
        )

        # 3.4.10-rc.4
        self.assertEqual(
            ServerManager._messages_for_version('3.4.9', '', '', json_path),
            (
                Qgis.Success,
                [
                    '👍'
                ],
                True,
            )
        )

        # Latest 3.4.9 without login
        self.assertEqual(
            ServerManager._messages_for_version('3.4.9', '', '', json_path),
            (
                Qgis.Success,
                [
                    '👍'
                ],
                True,
            )
        )

        # Latest 3.4.9-pre
        self.assertEqual(
            ServerManager._messages_for_version('3.4.9-pre', '', '', json_path),
            (
                Qgis.Warning,
                [
                    'Not latest bugfix release, 3.4.9 is available',
                    '. This version is not based on a tag.'
                ],
                True,
            )
        )

        # 3.4.8
        self.assertEqual(
            ServerManager._messages_for_version('3.4.8', '', '', json_path),
            (
                Qgis.Warning,
                [
                    'Not latest bugfix release, 3.4.9 is available'
                ],
                True,
            )
        )

        # 3.4.5, critical because more than 2 releases late
        self.assertEqual(
            ServerManager._messages_for_version('3.4.5', '', '', json_path),
            (
                Qgis.Critical,
                [
                    'Not latest bugfix release, 3.4.9 is available'
                ],
                True,
            )
        )

        # 3.3.16
        self.assertEqual(
            ServerManager._messages_for_version('3.3.16', '', '', json_path),
            (
                Qgis.Critical,
                [
                    'Version 3.3 not maintained anymore'
                ],
                True,
            )
        )

        # 3.2.0
        self.assertEqual(
            ServerManager._messages_for_version('3.2.0', '', '', json_path),
            (
                Qgis.Critical,
                [
                    'Version 3.2 not maintained anymore',
                ],
                True,
            )
        )

    def test_version_info_qgis_server_status(self):
        """ Test a valid QGIS server status."""
        # Test file with
        # 3.7.0 active dev
        # 3.6.2 latest 3.6.X, QGIS server must be valid
        # 3.5.11 latest 3.5.X, QGIS server is not needed
        # 3.4.X deprecated
        json_path = Path(plugin_test_data_path('version_info_27032023.json'))

        data = {
            'lizmap_version': '3.5.11',
            'qgis_version': "",
            'login': 'simple_lambda',
            'json_path': json_path,
            'error': "NO_ACCESS",
        }

        # 3.5.11 with simple login
        self.assertEqual(
            ServerManager._messages_for_version(**data),
            (
                Qgis.Critical,
                [
                    'The login is not a publisher/administrator',
                ],
                True,
            )
        )

        data['lizmap_version'] = '3.6.2'

        # 3.6.2 with simple login
        self.assertEqual(
            ServerManager._messages_for_version(**data),
            (
                Qgis.Critical,
                [
                    'The login is not a publisher/administrator',
                ],
                False,
            )
        )
