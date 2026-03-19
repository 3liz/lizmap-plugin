
from typing import (
    TYPE_CHECKING,
)

from qgis.core import QgsProject

from lizmap.definitions.online_help import Panels
from lizmap.server_dav import WebDav

if TYPE_CHECKING:
    from ..dialogs.main import LizmapDialog


class WebDavManager:

    def __init__(
        self,
        dlg: "LizmapDialog",
        project: QgsProject,
    ):
        self.dlg = dlg
        self.project = project
        self.webdav = WebDav()
        self.webdav.setup_webdav_dialog(dlg)

    def check_webdav(self):
        """ Check if we can enable or the webdav, according to the current selected server. """

        def disable_upload_panel():
            self.dlg.mOptionsListWidget.item(Panels.Upload).setHidden(True)
            if self.dlg.mOptionsListWidget.currentRow() == Panels.Upload:
                self.dlg.mOptionsListWidget.setCurrentRow(Panels.Information)

        if not self.webdav:
            self.dlg.webdav_frame.setVisible(False)
            self.dlg.button_upload_thumbnail.setVisible(False)
            self.dlg.button_upload_action.setVisible(False)
            self.dlg.button_upload_media.setVisible(False)
            self.dlg.button_create_media_remote.setVisible(False)
            disable_upload_panel()
            return

        self.webdav.config_project()

        # The dialog is already given.
        # We can check if WebDAV is supported.
        if self.webdav.setup_webdav_dialog():
            # self.dlg.group_upload.setVisible(True)
            # self.dlg.send_webdav.setEnabled(True)
            # self.dlg.send_webdav.setVisible(True)
            self.dlg.webdav_frame.setVisible(True)
            self.dlg.button_upload_thumbnail.setVisible(True)
            self.dlg.button_upload_action.setVisible(True)
            self.dlg.button_upload_media.setVisible(True)
            self.dlg.button_create_media_remote.setVisible(True)
            self.dlg.mOptionsListWidget.item(Panels.Upload).setHidden(False)
        else:
            # self.dlg.group_upload.setVisible(False)
            # self.dlg.send_webdav.setChecked(False)
            # self.dlg.send_webdav.setEnabled(False)
            # self.dlg.send_webdav.setVisible(False)
            self.dlg.webdav_frame.setVisible(False)
            self.dlg.button_upload_thumbnail.setVisible(False)
            self.dlg.button_upload_action.setVisible(False)
            self.dlg.button_upload_media.setVisible(False)
            self.dlg.button_create_media_remote.setVisible(False)
            disable_upload_panel()
