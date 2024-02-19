"""Test webdav protocol and custom HTTP requests."""

import random
import string
import unittest

from pathlib import Path

from lizmap.toolbelt.version import qgis_version

if qgis_version() >= 32200:
    from lizmap.server_dav import WebDav

from lizmap.toolbelt.resources import plugin_test_data_path

try:
    from lizmap.test.credentials import (
        LIZMAP_HOST_DAV,
        LIZMAP_HOST_WEB,
        LIZMAP_PASSWORD,
        LIZMAP_USER,
    )
    CREDENTIALS = True
    from webdav3.client import Client
    from webdav3.exceptions import RemoteResourceNotFound
except ImportError:
    CREDENTIALS = False
    Client = None
    RemoteResourceNotFound = None
    LIZMAP_USER = ''
    LIZMAP_HOST_WEB = ''
    LIZMAP_HOST_DAV = ''
    LIZMAP_PASSWORD = ''


__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

# To run these tests:
# * copy credentials.py.example to credentials.py
# * edit info credentials.py


def skip_test():
    if not CREDENTIALS:
        return True
    if qgis_version() < 32200:
        return True
    if not LIZMAP_HOST_DAV:
        return True
    if not LIZMAP_USER:
        return True
    if not LIZMAP_PASSWORD:
        return True

    return False

#
# Important note, we are not using our own webdav library to create/remove fixtures.
# We rely on the Python package webdavclient3
# So we are sure that fixtures are cleaned and set properly (because I trust more this library :) )
#


class TestHttpProtocol(unittest.TestCase):

    @unittest.skipIf(skip_test(), "Missing credentials")
    def setUp(self) -> None:
        self.prefix = 'unit_test_plugin_'
        self.directory_name = self.prefix + ''.join(random.choice(string.ascii_lowercase) for _ in range(5))
        self.dav = WebDav(LIZMAP_HOST_DAV)
        options = {
            'webdav_hostname': LIZMAP_HOST_DAV,
            'webdav_login': LIZMAP_USER,
            'webdav_password': LIZMAP_PASSWORD,
        }
        self.client = Client(options)

    def tearDown(self) -> None:
        try:
            self.client.clean(self.directory_name)
        except RemoteResourceNotFound:
            pass

    def test_create_directory(self):
        """ Test to create a directory with webdav. """
        # Create directory
        result, msg = self.dav.make_dir_basic(
            self.directory_name, LIZMAP_USER, LIZMAP_PASSWORD
        )
        self.assertEqual(msg, '')
        self.assertTrue(result)

        # Check it exists using external library
        self.assertTrue(self.client.check(self.directory_name))

        # Check already existing directory
        result, msg = self.dav.make_dir_basic(
            self.directory_name, LIZMAP_USER, LIZMAP_PASSWORD
        )
        self.assertEqual(msg, 'The resource you tried to create already exists')
        self.assertFalse(result)

    def test_qgs_exists(self):
        """ Test to check if a file exists. """
        # Create the directory using external library
        self.client.mkdir(self.directory_name)

        project = Path(plugin_test_data_path('legend_image_option.qgs'))

        # It doesn't exist yet
        result, msg = self.dav.check_qgs_exists_basic(
            self.directory_name, LIZMAP_USER, LIZMAP_PASSWORD, project.name
        )
        self.assertEqual(msg, '')
        self.assertFalse(result)

        # Upload with external library
        self.client.upload_sync(local_path=str(project), remote_path=self.directory_name + '/' + project.name)

        # It exists now
        result, msg = self.dav.check_qgs_exists_basic(
            self.directory_name, LIZMAP_USER, LIZMAP_PASSWORD, project.name
        )
        self.assertEqual(msg, '')
        self.assertTrue(result)

    def test_backup_qgs(self):
        """ Test to back up a QGS file. """
        project = Path(plugin_test_data_path('legend_image_option.qgs'))
        # Create the directory using external library
        self.client.mkdir(self.directory_name)
        self.client.upload_sync(local_path=str(project), remote_path=self.directory_name + '/' + project.name)

        result, msg = self.dav.backup_qgs_basic(self.directory_name, LIZMAP_USER, LIZMAP_PASSWORD, project.name)
        self.assertEqual(msg, '')
        self.assertTrue(result)

    # @unittest.expectedFailure
    # def test_wizard(self):
    #     """ Test the wizard, because linked to webdav capabilities. """
    #     dialog = WizardNewComer(None, LIZMAP_HOST_WEB, LIZMAP_HOST_DAV, LIZMAP_USER, LIZMAP_PASSWORD)
    #     # dialog.exec_()


if __name__ == "__main__":
    from qgis.testing import start_app
    start_app()
