"""Test webdav protocol and custom HTTP requests."""

import random
import string
import unittest

from pathlib import Path

from qgis.PyQt.QtWidgets import QWizard

from lizmap.dialogs.server_wizard import THUMBS, CreateFolderWizard
from lizmap.toolbelt.version import qgis_version

if qgis_version() >= 32200:
    from lizmap.server_dav import WebDav, PropFindFileResponse, PropFindDirResponse

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


__copyright__ = 'Copyright 2024, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

# To run these tests:
# * copy credentials.py.example to credentials.py
# * edit info credentials.py about WebDav


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

# from qgis.testing import start_app
#
# start_app()


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

    def test_stats_directory(self):
        """ Test statistics on a directory. """
        self.dav._for_test(LIZMAP_USER, LIZMAP_PASSWORD, self.directory_name, "")

        result, msg = self.dav.file_stats_media()
        self.assertEqual('', msg)
        self.assertIsNone(result)

        result, msg = self.dav.make_dir_basic(
            self.directory_name + '/media', LIZMAP_USER, LIZMAP_PASSWORD
        )
        self.assertEqual('Parent node does not exist', msg)
        self.assertFalse(result)

        result, msg = self.dav.make_dir_basic(
            self.directory_name, LIZMAP_USER, LIZMAP_PASSWORD
        )
        self.assertEqual(msg, '')
        self.assertTrue(result)

        result, msg = self.dav.make_dir_basic(
            self.directory_name + '/media', LIZMAP_USER, LIZMAP_PASSWORD
        )
        self.assertEqual('', msg)
        self.assertTrue(result)

        result, msg = self.dav.file_stats_media()
        self.assertEqual('', msg)
        self.assertIsInstance(result, PropFindDirResponse)

    def test_qgs_exists(self):
        """ Test to check if a file exists. """
        # Create the directory using external library
        self.client.mkdir(self.directory_name)

        project_name = 'legend_image_option.qgs'
        project = Path(plugin_test_data_path(project_name))

        self.dav._for_test(LIZMAP_USER, LIZMAP_PASSWORD, self.directory_name, project.name)

        # It doesn't exist yet
        result, msg = self.dav.check_exists_qgs()
        self.assertEqual('', msg)
        self.assertFalse(result)

        # Upload with external library
        self.client.upload_sync(local_path=str(project), remote_path=self.directory_name + '/' + project.name)

        # It exists now
        result, msg = self.dav.check_exists_qgs()
        self.assertEqual(msg, '')
        self.assertTrue(result)

        # Check file stats
        result, msg = self.dav.file_stats_qgs()
        self.assertEqual(msg, '')
        self.assertIsInstance(result, PropFindFileResponse)
        self.assertEqual(f'/dav.php/{self.directory_name}/{project_name}', result.href)

    # def test_backup_qgs(self):
    #     """ Test to back up a QGS file. """
    #     project = Path(plugin_test_data_path('legend_image_option.qgs'))
    #     # Create the directory using external library
    #     self.client.mkdir(self.directory_name)
    #     self.client.upload_sync(local_path=str(project), remote_path=self.directory_name + '/' + project.name)
    #
    #     result, msg = self.dav.backup_qgs_basic(self.directory_name, LIZMAP_USER, LIZMAP_PASSWORD, project.name)
    #     self.assertEqual(msg, '')
    #     self.assertTrue(result)

    def test_parse_propfind_file(self):
        """ Test we can parse a PROPFIND file response. """
        xml_str = (
            '<?xml version="1.0"?>'
            '<d:multistatus xmlns:d="DAV:" xmlns:s="http://sabredav.org/ns">'
            '<d:response>'
            '<d:href>/dav.php/unit_test_plugin_upheq/legend_image_option.qgs</d:href>'
            '<d:propstat>'
            '<d:prop>'
            '<d:getlastmodified>Thu, 14 Mar 2024 14:16:29 GMT</d:getlastmodified>'
            '<d:getcontentlength>54512</d:getcontentlength>'
            '<d:resourcetype/>'
            '<d:getetag>&quot;bb814ac0a9bcbb42e4c7c3baf82f1fe3c48e2d91&quot;</d:getetag>'
            '</d:prop>'
            '<d:status>HTTP/1.1 200 OK</d:status>'
            '</d:propstat>'
            '</d:response>'
            '</d:multistatus>'
        )
        result = WebDav.parse_propfind_response(xml_str)
        self.assertEqual("Thu, 14 Mar 2024 14:16:29 GMT", result.last_modified)
        self.assertTrue("14" in result.last_modified_pretty)
        self.assertEqual("/dav.php/unit_test_plugin_upheq/legend_image_option.qgs", result.href)
        self.assertEqual("54512", result.content_length)
        self.assertEqual("bb814ac0a9bcbb42e4c7c3baf82f1fe3c48e2d91", result.etag)
        self.assertEqual("HTTP/1.1 200 OK", result.http_code)

    def test_parse_propfind_dir(self):
        """ Test we can parse a PROPFIND dir response. """
        xml_str = (
            '<?xml version="1.0"?>'
            '<d:multistatus xmlns:d="DAV:" xmlns:s="http://sabredav.org/ns">'
            '<d:response>'
            '<d:href>/dav.php/unit_test_plugin_tobml/media/</d:href>'
            '<d:propstat>'
            '<d:prop>'
            '<d:getlastmodified>Thu, 14 Mar 2024 14:16:29 GMT</d:getlastmodified>'
            '<d:resourcetype><d:collection/></d:resourcetype>'
            '<d:quota-used-bytes>483604643840</d:quota-used-bytes>'
            '<d:quota-available-bytes>522049449984</d:quota-available-bytes>'
            '</d:prop>'
            '<d:status>HTTP/1.1 200 OK</d:status>'
            '</d:propstat>'
            '</d:response>'
            '</d:multistatus>'
        )
        result = WebDav.parse_propfind_response(xml_str)
        self.assertEqual("Thu, 14 Mar 2024 14:16:29 GMT", result.last_modified)
        self.assertEqual("483604643840", result.quota_used_bytes)
        self.assertEqual("522049449984", result.quota_available_bytes)
        self.assertTrue("14" in result.last_modified_pretty)
        self.assertEqual("/dav.php/unit_test_plugin_tobml/media/", result.href)
        self.assertEqual("HTTP/1.1 200 OK", result.http_code)

    def test_wizard(self):
        """ Test the wizard for folder creation. """
        dialog = CreateFolderWizard(
            None, webdav_server=LIZMAP_HOST_DAV, auth_id="", url=LIZMAP_HOST_WEB,
            user=LIZMAP_USER, password=LIZMAP_PASSWORD)
        dialog.show()
        dialog.currentPage().custom_name.setText(self.directory_name)

        self.assertFalse(self.client.check(self.directory_name))
        dialog.currentPage().create_button.click()
        self.assertTrue(self.client.check(self.directory_name))

        self.assertTrue(THUMBS in dialog.currentPage().result.text())

        dialog.currentPage().create_button.click()
        # Message are always in English, hardcoded in source code
        self.assertEqual("The resource you tried to create already exists", dialog.currentPage().result.text())

        self.assertFalse(dialog.button(QWizard.FinishButton).isVisible())

        dialog.button(QWizard.NextButton).click()

        self.assertEqual(self.directory_name, dialog.field("folder_name"))

        dialog.currentPage().check_repository.click()

        self.assertFalse(THUMBS in dialog.currentPage().result.text())
        self.assertTrue(self.directory_name in dialog.currentPage().result.text())
        self.assertTrue(dialog.button(QWizard.FinishButton).isVisible())


if __name__ == "__main__":
    from qgis.testing import start_app
    start_app()
