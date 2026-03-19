import os

from typing import TYPE_CHECKING

from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt.QtWidgets import QMessageBox, QPushButton

from ..definitions.definitions import ServerComboData
from ..definitions.online_help import (
    MAPPING_INDEX_DOC,
    online_cloud_help,
    online_lwc_help,
)
from ..saas import is_lizmap_cloud
from ..toolbelt.i18n import tr
from ..toolbelt.resources import window_icon

if TYPE_CHECKING:
    from ..dialogs.main import LizmapDialog


def display_error(dlg: "LizmapDialog", message: str):
    QMessageBox.critical(dlg, tr("Lizmap Error"), message, QMessageBox.StandardButton.Ok)


def string_to_list(text):
    """Format a string to a list."""
    data = text.split(",") if len(text) > 0 else []
    return [item.strip() for item in data]


def current_login() -> str:
    """Current login on the OS."""
    try:
        return os.getlogin()
    except OSError:
        return "repository"


def show_help_question(dlg: "LizmapDialog"):
    """According to the Lizmap server, ask the user which online help to open."""
    index = dlg.mOptionsListWidget.currentRow()
    page = MAPPING_INDEX_DOC.get(index)
    current_metadata = dlg.server_combo.currentData(ServerComboData.JsonMetadata.value)
    if not is_lizmap_cloud(current_metadata) and not page:
        show_help()
        return

    box = QMessageBox(dlg)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowIcon(window_icon())
    box.setWindowTitle(tr("Online documentation"))
    box.setText(
        tr("Different documentations are possible. Which online documentation would you like to open ?")
    )

    if is_lizmap_cloud(current_metadata):
        cloud_help = QPushButton("Lizmap Hosting")
        box.addButton(cloud_help, QMessageBox.ButtonRole.NoRole)

    if page:
        text = dlg.mOptionsListWidget.item(index).text()
        current_page = QPushButton(tr("Page '{}' in the plugin").format(text))
        box.addButton(current_page, QMessageBox.ButtonRole.NoRole)
    else:
        current_page = None

    lwc_help = QPushButton("Lizmap Web Client")
    box.addButton(lwc_help, QMessageBox.ButtonRole.YesRole)
    box.setStandardButtons(QMessageBox.StandardButton.Cancel)

    result = box.exec()

    if result == QMessageBox.StandardButton.Cancel:
        return

    if box.clickedButton() == lwc_help:
        show_help()
    elif box.clickedButton() == current_page:
        show_help(page)
    else:
        show_help_cloud()


def show_help(page=None):
    """Opens the HTML online help with default browser and language."""
    QDesktopServices.openUrl(online_lwc_help(page))


def show_help_cloud():
    """Opens the HTML online cloud help with default browser and language."""
    QDesktopServices.openUrl(online_cloud_help())
