"""Test webdav protocol and custom HTTP requests."""

from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree

import pytest

from qgis.PyQt.QtWidgets import QWizard

from lizmap.dialogs.server_wizard import THUMBS, CreateFolderWizard
from lizmap.server_dav import PropFindDirResponse, PropFindFileResponse, WebDav
from lizmap.toolbelt.strings import random_string

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
    LIZMAP_USER = ""
    LIZMAP_HOST_WEB = ""
    LIZMAP_HOST_DAV = ""
    LIZMAP_PASSWORD = ""


from .compat import TestCase

# To run these tests:
# * copy credentials.py.example to credentials.py
# * edit info credentials.py about WebDav

#
# Important note, we are not using our own webdav library to create/remove fixtures.
# We rely on the Python package webdavclient3
# So we are sure that fixtures are cleaned and set properly (because I trust more this library :) )
#


@dataclass(frozen=True)
class Dav:
    directory_name: str
    local_dir_path: Path
    dav: WebDav
    client: Client


@pytest.fixture(scope="class")
def webdav(data: Path) -> Dav:
    prefix = "unit_test_plugin_"
    options = {
        "webdav_hostname": LIZMAP_HOST_DAV,
        "webdav_login": LIZMAP_USER,
        "webdav_password": LIZMAP_PASSWORD,
    }

    dav = Dav(
        directory_name=prefix + random_string(),
        local_dir_path=data.joinpath(webdav.directory_name),
        dav=WebDav(LIZMAP_HOST_DAV),
        client=Client(options),
    )

    yield dav

    try:
        dav.client.clean(dav.directory_name)
    except RemoteResourceNotFound:
        pass

    # Clean on local
    rmtree(dav.local_dir_path, ignore_errors=True)


@pytest.mark.skipif(
    not all((CREDENTIALS, LIZMAP_HOST_DAV, LIZMAP_USER, LIZMAP_PASSWORD)),
    reason="Missing WebDav credentials",
)
class TestHttpProtocol(TestCase):
    def test_mkdir_recursive(self, webdav: Dav):
        """Test to create recursive directories."""
        webdav.dav._for_test(LIZMAP_USER, LIZMAP_PASSWORD, webdav.directory_name, "")

        path = Path("a/b/c/d/")
        result, msg = webdav.dav.make_dirs_recursive_basic(
            path, True, user=LIZMAP_USER, password=LIZMAP_PASSWORD
        )
        self.assertEqual(msg, "")
        self.assertTrue(result)

        result, msg = webdav.dav.file_stats("a/b/c/d/")
        self.assertEqual("", msg)
        self.assertIsInstance(result, PropFindDirResponse)
        self.assertEqual(f"/dav.php/{webdav.directory_name}/{path}/", result.href)

    def test_mkdir_recursive_parent(self, webdav: Dav):
        """Test to create recursive directories from a file."""
        webdav.dav._for_test(LIZMAP_USER, LIZMAP_PASSWORD, webdav.directory_name, "")

        path = Path("a/b/c/d/e.txt")
        result, msg = webdav.dav.make_dirs_recursive_basic(
            path, True, user=LIZMAP_USER, password=LIZMAP_PASSWORD
        )
        self.assertEqual(msg, "")
        self.assertTrue(result)

        result, msg = webdav.dav.file_stats("a/b/c/d/")
        self.assertEqual("", msg)
        self.assertIsInstance(result, PropFindDirResponse)
        self.assertEqual(f"/dav.php/{webdav.directory_name}/a/b/c/d/", result.href)

        # Might be fragile, as we don't allow directories with a dot inside... (conf.d)
        result, msg = webdav.dav.file_stats("a/b/c/d/e.txt")
        self.assertEqual("", msg)
        self.assertIsNone(result)

    def test_create_directory(self, webdav: Dav):
        """Test to create a directory with webdav."""
        # Create directory
        result, msg = webdav.dav.make_dir_basic(
            webdav.directory_name, False, user=LIZMAP_USER, password=LIZMAP_PASSWORD
        )
        self.assertEqual(msg, "")
        self.assertTrue(result)

        # Check it exists using external library
        self.assertTrue(webdav.client.check(webdav.directory_name))

        # Check already existing directory
        result, msg = webdav.dav.make_dir_basic(
            webdav.directory_name, False, user=LIZMAP_USER, password=LIZMAP_PASSWORD
        )
        self.assertEqual(msg, "The resource you tried to create already exists")
        self.assertFalse(result)

        # Check already existing directory
        result, msg = webdav.dav.make_dir_basic(
            webdav.directory_name,
            True,
            user=LIZMAP_USER,
            password=LIZMAP_PASSWORD,
        )
        self.assertEqual(msg, "The resource you tried to create already exists")
        self.assertTrue(result)

    def test_stats_directory(self, webdav: Dav):
        """Test statistics on a directory."""
        webdav.dav._for_test(LIZMAP_USER, LIZMAP_PASSWORD, webdav.directory_name, "")

        result, msg = webdav.dav.file_stats_media()
        self.assertEqual("", msg)
        self.assertIsNone(result)

        result, msg = webdav.dav.make_dir_basic(
            webdav.directory_name + "/media", False, LIZMAP_USER, LIZMAP_PASSWORD
        )
        self.assertEqual("Parent node does not exist", msg)
        self.assertFalse(result)

        result, msg = webdav.dav.make_dir_basic(webdav.directory_name, False, LIZMAP_USER, LIZMAP_PASSWORD)
        self.assertEqual(msg, "")
        self.assertTrue(result)

        result, msg = webdav.dav.make_dir_basic(
            webdav.directory_name + "/media", False, LIZMAP_USER, LIZMAP_PASSWORD
        )
        self.assertEqual("", msg)
        self.assertTrue(result)

        result, msg = webdav.dav.make_dir_basic(
            webdav.directory_name + "/media", True, LIZMAP_USER, LIZMAP_PASSWORD
        )
        self.assertEqual("The resource you tried to create already exists", msg)
        self.assertTrue(result)

        result, msg = webdav.dav.file_stats_media()
        self.assertEqual("", msg)
        self.assertIsInstance(result, PropFindDirResponse)

    def test_qgs_exists(self, data: Path, webdav: Dav):
        """Test to check if a file exists."""
        # Create the directory using external library
        webdav.client.mkdir(webdav.directory_name)

        project_name = "legend_image_option.qgs"
        project = data.joinpath(project_name)

        webdav.dav._for_test(LIZMAP_USER, LIZMAP_PASSWORD, webdav.directory_name, project.name)

        # It doesn't exist yet
        result, msg = webdav.dav.check_exists_qgs()
        self.assertEqual("", msg)
        self.assertFalse(result)

        # Upload with external library
        webdav.client.upload_sync(
            local_path=str(project), remote_path=webdav.directory_name + "/" + project.name
        )

        # It exists now
        result, msg = webdav.dav.check_exists_qgs()
        self.assertEqual(msg, "")
        self.assertTrue(result)

        # Check file stats
        result, msg = webdav.dav.file_stats_qgs()
        self.assertEqual(msg, "")
        self.assertIsInstance(result, PropFindFileResponse)
        self.assertEqual(f"/dav.php/{webdav.directory_name}/{project_name}", result.href)

    def test_parse_propfind_file(self, webdav: Dav):
        """Test we can parse a PROPFIND file response."""
        xml_str = (
            '<?xml version="1.0"?>'
            '<d:multistatus xmlns:d="DAV:" xmlns:s="http://sabredav.org/ns">'
            "<d:response>"
            "<d:href>/dav.php/unit_test_plugin_upheq/legend_image_option.qgs</d:href>"
            "<d:propstat>"
            "<d:prop>"
            "<d:getlastmodified>Thu, 14 Mar 2024 14:16:29 GMT</d:getlastmodified>"
            "<d:getcontentlength>54512</d:getcontentlength>"
            "<d:resourcetype/>"
            "<d:getetag>&quot;bb814ac0a9bcbb42e4c7c3baf82f1fe3c48e2d91&quot;</d:getetag>"
            "</d:prop>"
            "<d:status>HTTP/1.1 200 OK</d:status>"
            "</d:propstat>"
            "</d:response>"
            "</d:multistatus>"
        )
        result = WebDav.parse_propfind_response(xml_str)
        self.assertEqual("Thu, 14 Mar 2024 14:16:29 GMT", result.last_modified)
        self.assertTrue("14" in result.last_modified_pretty)
        self.assertEqual("/dav.php/unit_test_plugin_upheq/legend_image_option.qgs", result.href)
        self.assertEqual("54512", result.content_length)
        self.assertEqual("bb814ac0a9bcbb42e4c7c3baf82f1fe3c48e2d91", result.etag)
        self.assertEqual("HTTP/1.1 200 OK", result.http_code)

    def test_parse_propfind_dir(self, webdav: Dav):
        """Test we can parse a PROPFIND dir response."""
        xml_str = (
            '<?xml version="1.0"?>'
            '<d:multistatus xmlns:d="DAV:" xmlns:s="http://sabredav.org/ns">'
            "<d:response>"
            "<d:href>/dav.php/unit_test_plugin_tobml/media/</d:href>"
            "<d:propstat>"
            "<d:prop>"
            "<d:getlastmodified>Thu, 14 Mar 2024 14:16:29 GMT</d:getlastmodified>"
            "<d:resourcetype><d:collection/></d:resourcetype>"
            "<d:quota-used-bytes>483604643840</d:quota-used-bytes>"
            "<d:quota-available-bytes>522049449984</d:quota-available-bytes>"
            "</d:prop>"
            "<d:status>HTTP/1.1 200 OK</d:status>"
            "</d:propstat>"
            "</d:response>"
            "</d:multistatus>"
        )
        result = WebDav.parse_propfind_response(xml_str)
        self.assertEqual("Thu, 14 Mar 2024 14:16:29 GMT", result.last_modified)
        self.assertEqual("483604643840", result.quota_used_bytes)
        self.assertEqual("522049449984", result.quota_available_bytes)
        self.assertTrue("14" in result.last_modified_pretty)
        self.assertEqual("/dav.php/unit_test_plugin_tobml/media/", result.href)
        self.assertEqual("HTTP/1.1 200 OK", result.http_code)

    def test_put_file(self, webdav: Dav):
        """Test to PUT a file."""
        webdav.client.mkdir(webdav.directory_name)

        # Create the local file to send, in some subdirectories
        file_path = "tmp/a/b/c/test.txt"
        local_file_path = webdav.local_dir_path.joinpath(file_path)
        local_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(local_file_path, "w") as f:
            f.write("Lizmap rocks !")
        self.assertTrue(local_file_path.exists())

        webdav.dav._for_test(LIZMAP_USER, LIZMAP_PASSWORD, webdav.directory_name, "")

        # remote_path = webdav.directory_name + "/" + file_path

        # It doesn't exist yet
        # For now, all path are relatives to the repository
        result, msg = webdav.dav.file_stats(file_path)
        self.assertEqual("", msg)
        self.assertFalse(result)

        relative_path = local_file_path.relative_to(webdav.local_dir_path)
        self.assertEqual(file_path, str(relative_path))

    def test_remove_file(self, data: Path, webdav: Dav):
        """Test we can remove a file."""
        webdav.client.mkdir(webdav.directory_name)

        project_name = "legend_image_option.qgs"
        project = data.joinpath(project_name)

        webdav.dav._for_test(LIZMAP_USER, LIZMAP_PASSWORD, webdav.directory_name, "")

        # File does not exist yet
        webdav.dav.file_stats(project_name)
        result, msg = webdav.dav.file_stats(project_name)
        self.assertEqual(msg, "")
        self.assertIsNone(result)

        # Send a file
        webdav.client.upload_sync(
            local_path=str(project), remote_path=webdav.directory_name + "/" + project.name
        )

        # Check
        result, msg = webdav.dav.file_stats(project_name)
        self.assertEqual(msg, "")
        self.assertIsInstance(result, PropFindFileResponse)
        self.assertEqual(f"/dav.php/{webdav.directory_name}/{project_name}", result.href)

        # Remove
        webdav.dav.remove_file(project_name)

        # Check
        webdav.dav.file_stats(project_name)
        result, msg = webdav.dav.file_stats(project_name)
        self.assertEqual(msg, "")
        self.assertIsNone(result)

    def test_wizard(self, webdav: Dav):
        """Test the wizard for folder creation."""
        dialog = CreateFolderWizard(
            None,
            webdav_server=LIZMAP_HOST_DAV,
            auth_id="",
            url=LIZMAP_HOST_WEB,
            user=LIZMAP_USER,
            password=LIZMAP_PASSWORD,
        )
        dialog.show()
        dialog.currentPage().custom_name.setText(webdav.directory_name)

        self.assertFalse(webdav.client.check(webdav.directory_name))
        dialog.currentPage().create_button.click()
        self.assertTrue(webdav.client.check(webdav.directory_name))

        self.assertTrue(THUMBS in dialog.currentPage().result.text())

        dialog.currentPage().create_button.click()
        # Message are always in English, hardcoded in source code
        self.assertEqual(
            "The resource you tried to create already exists", dialog.currentPage().result.text()
        )

        self.assertFalse(dialog.button(QWizard.WizardButton.FinishButton).isVisible())

        dialog.button(QWizard.WizardButton.NextButton).click()

        self.assertEqual(webdav.directory_name, dialog.field("folder_name"))

        dialog.currentPage().check_repository.click()

        self.assertFalse(THUMBS in dialog.currentPage().result.text())
        self.assertTrue(webdav.directory_name in dialog.currentPage().result.text())
        self.assertTrue(dialog.button(QWizard.WizardButton.FinishButton).isVisible())
