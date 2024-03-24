"""Test the instance wizard."""
import os
import unittest

from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtWidgets import QWizard

from lizmap.dialogs.server_wizard import (
    NamePage,
    ServerWizard,
    UrlPage,
    WizardPages,
)
from lizmap.toolbelt.version import qgis_version

try:
    from lizmap.test.credentials import (
        LIZMAP_HOST_WEB,
        LIZMAP_PASSWORD,
        LIZMAP_USER,
    )
    CREDENTIALS = True
except ImportError:
    CREDENTIALS = False
    LIZMAP_HOST_WEB = ''
    LIZMAP_PASSWORD = ''
    LIZMAP_USER = ''

# from qgis.testing import start_app
# start_app()


__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


def skip_test():
    """ Check conditions for running tests. """
    return not all((
        CREDENTIALS, LIZMAP_USER, LIZMAP_HOST_WEB, LIZMAP_PASSWORD, os.getenv('CI'), 'lizmap.local' in LIZMAP_HOST_WEB))


class TestWizardServer(unittest.TestCase):

    def test_url(self):
        """ Test the validity of the URL. """
        self.assertFalse(UrlPage.url_valid(QUrl("https://demo.lizmap.com/lizmap/index.php")))
        self.assertFalse(UrlPage.url_valid(QUrl("https://demo.lizmap.com/lizmap/index.php/")))
        self.assertFalse(UrlPage.url_valid(QUrl("bourbon")))

        self.assertTrue(UrlPage.url_valid(QUrl("http://lizmap.local:8130/")))

    @unittest.skipIf(qgis_version() < 34000, "Always failing, do not use unexpectedSuccess as well")
    def test_server_creation_wrong_data(self):
        """ Test to create a new server with wrong data only. """
        dialog = ServerWizard(None, [])
        dialog.show()

        #
        # URL page
        #
        self.assertEqual(WizardPages.UrlPage, dialog.currentId())
        self.assertFalse(dialog.button(QWizard.NextButton).isEnabled())
        # Not a JSON content when appending index.php/view/app/metadata
        dialog.currentPage().url_edit.setText('https://foo.org')
        dialog.button(QWizard.NextButton).click()

        #
        # Login and password page
        #

        self.assertEqual(WizardPages.LoginPasswordPage, dialog.currentId())
        self.assertFalse(dialog.button(QWizard.NextButton).isEnabled())

        # Wrong credentials
        dialog.currentPage().login_edit.setText('admin')
        dialog.currentPage().password_edit.setText('admin')

        self.assertTrue(dialog.button(QWizard.NextButton).isEnabled())
        dialog.button(QWizard.NextButton).click()

        # Back to the first panel because of the URL is not a JSON reply
        self.assertEqual(WizardPages.UrlPage, dialog.currentId())
        self.assertEqual(
            "The URL was not valid : https://foo.org", dialog.page(WizardPages.UrlPage).result_url.text())
        self.assertEqual("", dialog.page(WizardPages.LoginPasswordPage).result_login_password.text())

        dialog.currentPage().url_edit.setText("https://demo.snap.lizmap.com/lizmap_3_6")
        dialog.button(QWizard.NextButton).click()

        dialog.currentPage().login_edit.setText('admin_WRONG')
        dialog.currentPage().password_edit.setText('admin_WRONG')

        dialog.button(QWizard.NextButton).click()

        # Still on the same page because of the login & password now...

        self.assertEqual("", dialog.page(WizardPages.UrlPage).result_url.text())
        self.assertEqual(
            "Either the login or the password is wrong. It must be your login you use in your web-browser.",
            dialog.page(WizardPages.LoginPasswordPage).result_login_password.text())
        self.assertEqual(WizardPages.LoginPasswordPage, dialog.currentId())

    @unittest.skipIf(skip_test(), "Missing credentials")
    def X_test_server_creation_real_data(self):
        """ Test to create a new server with correct data. """
        dialog = ServerWizard(None, [])
        dialog.show()

        #
        # URL page
        #
        self.assertEqual(WizardPages.UrlPage, dialog.currentId())
        dialog.currentPage().url_edit.setText(LIZMAP_HOST_WEB)
        dialog.button(QWizard.NextButton).click()

        #
        # Login and password page
        #

        self.assertEqual(WizardPages.LoginPasswordPage, dialog.currentId())
        self.assertFalse(dialog.button(QWizard.NextButton).isEnabled())

        dialog.currentPage().login_edit.setText(LIZMAP_USER)
        dialog.currentPage().password_edit.setText(LIZMAP_PASSWORD)
        dialog.button(QWizard.NextButton).click()

        #
        # Name page
        #

        self.assertEqual(WizardPages.NamePage, dialog.currentId())
        self.assertNotEqual('', dialog.page(WizardPages.LoginPasswordPage).result_login_password.text())

        self.assertEqual(NamePage.automatic_name(LIZMAP_HOST_WEB), dialog.currentPage().name_edit.text())
        dialog.button(QWizard.NextButton).click()

        #
        # Saving credentials page
        #
