"""Test group wizard."""

__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from qgis.PyQt.QtCore import Qt
from qgis.testing import unittest

from lizmap.dialogs.wizard_group import WizardGroupDialog


class TestWizardGroupAclDialog(unittest.TestCase):

    def test_ui(self):
        """ Test the UI."""
        dialog = WizardGroupDialog(
            "Helper",  # Helper not needed in test
            "foo,admins,bar",  # Existing string in the config
            {
                "admins": {
                    "label": "admins"
                },
                "group_a": {
                    "label": "group_a"
                }
            }
        )

        self.assertEqual(2, dialog.list.count())
        selection = dialog.list.selectedItems()
        self.assertEqual(1, len(selection))
        self.assertEqual("admins", selection[0].data(Qt.UserRole))
        self.assertEqual("foo,bar", dialog.additional.text())
        self.assertEqual("admins,foo,bar", dialog.preview.text())

        # Set empty the custom CSV list
        dialog.additional.setText("")
        self.assertEqual("admins", dialog.preview.text())
