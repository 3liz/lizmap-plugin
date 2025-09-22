""" Wizard for ACL group. """

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QListWidgetItem,
)

from lizmap.toolbelt.i18n import tr
from lizmap.toolbelt.resources import load_ui

FORM_CLASS = load_ui('ui_wizard_group.ui')

__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


class WizardGroupDialog(QDialog, FORM_CLASS):

    def __init__(self, helper: str, current_acl: str, server_groups: dict = None):
        """ Constructor. """
        QDialog.__init__(self)
        self.setupUi(self)

        self.helper.setText(helper)

        tooltip = tr("Additional list of group ID, separated by comma, which are not found on this specific server.")
        self.additional.setToolTip(tooltip)
        self.label_additional.setToolTip(tooltip)

        # Server groups
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.list.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.list.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.list.setAlternatingRowColors(True)
        self.list.itemSelectionChanged.connect(self.update_preview)

        # Additional groups
        self.additional.textChanged.connect(self.update_preview)

        accept_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        accept_button.clicked.connect(self.accept)
        cancel_button = self.buttons.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_button.clicked.connect(self.reject)

        self.populate_widgets(current_acl, server_groups)

    def update_preview(self):
        """ Update the preview string based on the selection and manual input. """
        selection = []
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item.isSelected():
                selection.append(item.data(Qt.ItemDataRole.UserRole))

        more = self.additional.text()
        more = more.strip()
        more = more.strip(',')
        if more:
            selection.extend(more.split(','))

        self.preview.setText(','.join(selection))

    def populate_widgets(self, existing: str, server_groups: dict):
        """ Populate widgets according to the data. """
        existing = existing.split(',')
        existing = [f.strip() for f in existing]

        for group_id, group_data in server_groups.items():
            cell = QListWidgetItem()
            cell.setText(group_data['label'])
            cell.setData(Qt.ItemDataRole.UserRole, group_id)
            cell.setData(Qt.ItemDataRole.ToolTipRole, group_id)
            self.list.addItem(cell)
            if group_id in existing:
                cell.setSelected(True)
                existing.remove(group_id)
            else:
                cell.setSelected(False)

        self.additional.setText(','.join(existing))

        self.update_preview()
