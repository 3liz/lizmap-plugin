""" Dataviz container dialog. """
from typing import Optional

from qgis.PyQt.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
)

from lizmap.qgis_plugin_tools.tools.resources import load_ui

FORM_CLASS = load_ui('ui_drag_drop_dataviz.ui')

__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


class ContainerDatavizDialog(QDialog, FORM_CLASS):

    def __init__(self, parent: QDialog, existing: list):
        """ Constructor. """
        # noinspection PyArgumentList
        QDialog.__init__(self)
        self.parent = parent
        self.setupUi(self)

        accept_button = self.button_box.button(QDialogButtonBox.Ok)
        accept_button.clicked.connect(self.accept)
        cancel_button = self.button_box.button(QDialogButtonBox.Cancel)
        cancel_button.clicked.connect(self.reject)

        self.button_group = QButtonGroup()
        self.button_group.setExclusive(True)
        self.button_group.addButton(self.radio_tab)
        self.button_group.addButton(self.radio_group)

        # By default
        self.radio_tab.setChecked(True)

        if len(existing) >= 1:
            self.widget_container.setEnabled(True)
        else:
            self.widget_container.setEnabled(False)

        for item in existing:
            self.combo_tab: QComboBox
            self.combo_tab.addItem(item, item)

    # def radio_toggled(self):
    #     self.radio_tab.blockSignals(True)
    #     self.radio_group.blockSignals(True)
    #     if self.radio_tab.isChecked():
    #         self.radio
    #
    #
    #     self.radio_tab.blockSignals(False)
    #     self.radio_group.blockSignals(False)

    def name(self):
        """ Name of the container. """
        return self.edit_container_name.text()

    def parent_name(self) -> Optional[str]:
        """ Return the parent : either None if it's a tab, or the parent container. """
        if self.radio_tab.isChecked():
            return None

        return self.combo_tab.currentData()
