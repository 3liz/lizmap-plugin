
from typing import TYPE_CHECKING

from qgis.PyQt.QtWidgets import (
    QMessageBox,
)

from lizmap.toolbelt.i18n import tr

if TYPE_CHECKING:
    from ..dialogs.main import LizmapDialog


def display_error(dlg: "LizmapDialog" , message: str):
    QMessageBox.critical(
        dlg,
        tr('Lizmap Error'),
        message,
        QMessageBox.StandardButton.Ok)


def string_to_list(text):
    """ Format a string to a list. """
    data = text.split(',') if len(text) > 0 else []
    return [item.strip() for item in data]
