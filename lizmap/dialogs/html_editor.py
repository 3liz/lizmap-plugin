__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import logging

from qgis.core import QgsVectorLayer
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout

from lizmap.widgets.html_editor import HtmlEditorWidget

LOGGER = logging.getLogger('Lizmap')


class HtmlEditorDialog(QDialog):

    def __init__(self, layer: QgsVectorLayer = None):
        # noinspection PyArgumentList
        QDialog.__init__(self)
        self.editor = HtmlEditorWidget(layer)

        layout = QVBoxLayout()
        # noinspection PyArgumentList
        layout.addWidget(self.editor)

        self.button_box = QDialogButtonBox()
        self.button_box.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        # noinspection PyArgumentList
        layout.addWidget(self.button_box)

        self.setLayout(layout)

        accept_button = self.button_box.button(QDialogButtonBox.Ok)
        accept_button.clicked.connect(self.accept)
        cancel_button = self.button_box.button(QDialogButtonBox.Cancel)
        cancel_button.clicked.connect(self.reject)
