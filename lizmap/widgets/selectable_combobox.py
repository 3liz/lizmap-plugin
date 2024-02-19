"""QCombobox with checkbox for selecting multiple items."""

from qgis.core import QgsMapLayer
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QStandardItem, QStandardItemModel
from qgis.PyQt.QtWidgets import QStyledItemDelegate

__copyright__ = "Copyright 2019, 3Liz"
__license__ = "GPL version 3"
__email__ = "info@3liz.org"
__revision__ = "$Format:%H$"


class CheckableComboBox:

    """Basic QCombobox with selectable items."""

    def __init__(self, combobox, select_all=None):
        """Constructor."""
        self.combo = combobox
        self.combo.setEditable(True)
        self.combo.lineEdit().setReadOnly(True)
        self.model = QStandardItemModel(self.combo)
        self.combo.setModel(self.model)
        self.combo.setItemDelegate(QStyledItemDelegate())
        self.model.itemChanged.connect(self.combo_changed)
        self.combo.lineEdit().textChanged.connect(self.text_changed)
        if select_all:
            self.select_all = select_all
            self.select_all.clicked.connect(self.select_all_clicked)

    def select_all_clicked(self):
        for item in self.model.findItems("*", Qt.MatchWildcard):
            item.setCheckState(Qt.Checked)

    def append_row(self, item: QStandardItem):
        """Add an item to the combobox."""
        item.setEnabled(True)
        item.setCheckable(True)
        item.setSelectable(False)
        self.model.appendRow(item)

    def combo_changed(self):
        """Slot when the combo has changed."""
        self.text_changed(None)

    def selected_items(self) -> list:
        checked_items = []
        for item in self.model.findItems("*", Qt.MatchWildcard):
            if item.checkState() == Qt.Checked:
                checked_items.append(item.data())
        return checked_items

    def set_selected_items(self, items):
        for item in self.model.findItems("*", Qt.MatchWildcard):
            checked = item.data() in items
            item.setCheckState(Qt.Checked if checked else Qt.Unchecked)

    def text_changed(self, text):
        """Update the preview with all selected items, separated by a comma."""
        label = ", ".join(self.selected_items())
        if text != label:
            self.combo.setEditText(label)


class CheckableFieldComboBox(CheckableComboBox):
    def __init__(self, combobox, select_all=None):
        self.layer = None
        super().__init__(combobox, select_all)

    def set_layer(self, layer):
        self.model.clear()

        if not layer:
            return
        if layer.type() != QgsMapLayer.VectorLayer:
            return

        self.layer = layer

        for i, field in enumerate(self.layer.fields()):
            alias = field.alias()
            if alias:
                name = "{} ({})".format(field.name(), alias)
            else:
                name = field.name()
            item = QStandardItem(name)
            item.setData(field.name())
            item.setIcon(self.layer.fields().iconForField(i))
            self.append_row(item)
