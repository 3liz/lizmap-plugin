__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QDialog,
    QGridLayout,
    QLabel,
    QMessageBox,
    QScrollArea,
)


class ScrollMessageBox(QMessageBox):

    def __init__(self, parent: QDialog, *args, **kwargs):
        QMessageBox.__init__(self, *args, **kwargs)
        if parent:
            self.parent = parent
        children = self.children()
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        grid = self.findChild(QGridLayout)
        label = QLabel(children[1].text(), self)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        scroll.setWidget(label)
        scroll.setMinimumSize(400, 200)
        grid.addWidget(scroll, 0, 1)
        children[1].setText('')
        self.exec_()
