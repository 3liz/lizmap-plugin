from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QIcon, QPixmap
from qgis.PyQt.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from lizmap.toolbelt.i18n import tr
from lizmap.toolbelt.resources import resources_path

__copyright__ = 'Copyright 2024, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


class ConfirmationTextMessageBox(QDialog):

    def __init__(self, number: int, confirmation_text: str, *__args):
        """ Constructor. """
        super().__init__(*__args)

        self.setWindowTitle(tr("Error(s) on the project"))
        self.setWindowIcon(QIcon(resources_path('icons', 'icon.png')), )

        # Text to use for enabling the OK button
        self.confirmation_text = confirmation_text

        self.main_layout = QVBoxLayout(self)
        self.horizontal_layout = QHBoxLayout(self)

        # Left side
        self.icon = QLabel()
        self.icon.setPixmap(QPixmap(":images/themes/default/mIconWarning.svg"))
        self.icon.setMinimumSize(QSize(150, 150))
        self.horizontal_layout.addWidget(self.icon)

        # Right side, text and line edit
        self.right_side_layout = QVBoxLayout(self)

        self.text = QLabel(self)
        self.text.setWordWrap(True)

        message = tr('The project has at least one important issue :')
        message += "<strong>"
        message += " " + tr("{count} error(s)").format(count=number)
        message += "</strong><br><br>"
        message += tr(
            'You should really consider fixing these "<strong>important</strong>" issues to avoid technical problems '
            'on Lizmap later.'
        )
        message += "<br><br>"
        message += tr(
            'You can decide to skip fixing these "important" issues but you must write the name of the project with '
            'the number of error in the input text below so as to generate the Lizmap configuration file.'
        )
        message += "<br><br>"
        message += tr("Please type :")
        message += f"<br><strong>{self.confirmation_text}</strong>"
        self.text.setText(message)

        self.input_text = QLineEdit(self)

        self.right_side_layout.addWidget(self.text)
        self.right_side_layout.addWidget(self.input_text)
        self.horizontal_layout.addLayout(self.right_side_layout)
        self.main_layout.addLayout(self.horizontal_layout)

        self.button_box = QDialogButtonBox(self)
        self.button_box.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).clicked.connect(self.close)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).clicked.connect(self.accept)
        self.main_layout.addWidget(self.button_box)

        self.input_text.textEdited.connect(self.check_input_text)
        self.check_input_text()

    def check_input_text(self):
        """ Check the input text to enable or not the OK button."""
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            self.confirmation_text == self.input_text.text())
