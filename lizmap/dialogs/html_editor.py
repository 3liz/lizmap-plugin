__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import logging

from qgis.core import QgsVectorLayer
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout

from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.widgets.html_editor import HtmlEditorWidget

LOGGER = logging.getLogger('Lizmap')


class HtmlEditorDialog(QDialog):

    def __init__(self):
        # noinspection PyArgumentList
        QDialog.__init__(self)

        self.editor = HtmlEditorWidget(self)

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

    def set_layer(self, layer: QgsVectorLayer):
        self.setWindowTitle(tr("HTML maptip for the layer '{}'").format(layer.name()))
        self.editor.set_layer(layer)
