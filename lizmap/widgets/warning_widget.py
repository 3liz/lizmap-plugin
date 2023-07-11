__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from qgis.PyQt.QtGui import QPixmap
from qgis.PyQt.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget


class WarningWidget(QWidget):

    """ Widget to show a warning sign with a text. """

    def __init__(self, flags, *args, **kwargs):
        """ Constructor. """
        super().__init__(flags, *args, **kwargs)

        layout = QHBoxLayout(self)
        image_widget = QLabel()
        warning_icon = QPixmap(":images/themes/default/mIconWarning.svg")
        image_widget.setPixmap(warning_icon)
        image_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)

        # noinspection PyArgumentList
        layout.addWidget(image_widget)

        self.text_widget = QLabel()
        # self.text_widget.setText(text)
        self.text_widget.setWordWrap(True)

        # noinspection PyArgumentList
        layout.addWidget(self.text_widget)

        self.setLayout(layout)

    def set_text(self, text: str):
        """ Set text in the label. """
        self.text_widget.setText(text)
