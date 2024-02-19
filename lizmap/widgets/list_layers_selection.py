"""QListWidget with layers selection."""

from qgis.core import QgsMapLayer, QgsMapLayerModel, QgsProject
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QAbstractItemView, QListWidget, QListWidgetItem

__copyright__ = "Copyright 2019, 3Liz"
__license__ = "GPL version 3"
__email__ = "info@3liz.org"
__revision__ = "$Format:%H$"


class ListLayersSelection(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.MultiSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.project = None

    def set_project(self, project: QgsProject):
        self.project = project

        self.clear()

        for layer in self.project.mapLayers().values():
            if layer.type() != QgsMapLayer.VectorLayer:
                continue

            if not layer.isSpatial():
                continue

            cell = QListWidgetItem()
            cell.setText(layer.name())
            cell.setData(Qt.UserRole, layer.id())
            cell.setIcon(QgsMapLayerModel.iconForLayer(layer))
            self.addItem(cell)

    def set_selection(self, layers: tuple):
        for i in range(self.count()):
            item = self.item(i)
            item.setSelected(item.data(Qt.UserRole) in layers)

    def selection(self) -> list:
        selection = []
        for i in range(self.count()):
            item = self.item(i)
            if item.isSelected():
                selection.append(item.data(Qt.UserRole))
        return selection
