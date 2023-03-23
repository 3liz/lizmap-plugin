import logging
import os

from pathlib import Path
from typing import Optional, Tuple

from qgis.core import QgsProject
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QDialog, QMessageBox

from lizmap.qgis_plugin_tools.tools.resources import resources_path

try:
    from ftplib import FTP, FTP_TLS, error_perm, socket
    IS_FTP_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    IS_FTP_AVAILABLE = False


__copyright__ = 'Copyright 2022, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

LOGGER = logging.getLogger("Lizmap")


class FtpServer:

    @classmethod
    def is_ftp_available(cls) -> bool:
        """ Check if the FTP lib is available. """
        if not IS_FTP_AVAILABLE:
            LOGGER.warning("FTP library is not available.")
        return IS_FTP_AVAILABLE

    def __init__(self, dialog: QDialog):
        """ Constructor. """
        self.dialog = dialog
        self.host = None
        self.user = None
        self.password = None
        self.port = None
        self.directory = None
        self.project = QgsProject.instance()
        self.project_name = None
        self.set_project_name()

        # For easier debug only, it will be removed later
        self.dialog.input_ftp_host.setText(os.getenv("LIZMAP_FTP_HOST", ""))
        self.dialog.input_ftp_user.setText(os.getenv("LIZMAP_FTP_USER", ""))
        self.dialog.input_ftp_password.setText(os.getenv("LIZMAP_FTP_PASSWORD", ""))
        self.dialog.input_ftp_directory.setText(os.getenv("LIZMAP_FTP_DIRECTORY", ""))

        # self.dialog.input_ftp_port.setReadOnly(True)

        # self.dialog.button_ftp_save.setIcon(QIcon(":images/themes/default/mActionFileSave.svg"))
        # self.dialog.button_ftp_save.setVisible(False)
        self.dialog.button_ftp_check.setIcon(QIcon(":images/themes/default/algorithms/mAlgorithmCheckGeometry.svg"))

        self.dialog.button_ftp_reset.clicked.connect(self.reset_dialog)
        self.dialog.button_ftp_check.clicked.connect(self.check_server)
        self.dialog.checkbox_save_project.toggled.connect(self.enable_checkbox)

        self.enable_checkbox()

        if not self.is_ftp_available():
            self.dialog.button_ftp_reset.setEnabled(False)
            self.dialog.button_ftp_check.setEnabled(False)
            # self.dialog.input_ftp_port.setEnabled(False)
            self.dialog.input_ftp_host.setEnabled(False)
            self.dialog.input_ftp_user.setEnabled(False)
            self.dialog.input_ftp_password.setEnabled(False)
            self.dialog.input_ftp_directory.setEnabled(False)

    def set_project_name(self):
        """ Reset the FTP credentials if the project is not the same. """
        current = Path(self.project.fileName()).name
        if self.set_project_name != current:
            self.reset_dialog(prompt=False)
            self.project_name = current

    def reset_dialog(self, prompt=True):
        """ To reset all fields with empty values. """
        if prompt:
            box = QMessageBox(self.dialog)
            box.setIcon(QMessageBox.Question)
            box.setWindowIcon(QIcon(resources_path('icons', 'icon.png')), )
            box.setWindowTitle('Reset all fields')
            box.setText('Are you sure you want to reset all fields about the FTP ?')
            box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            box.setDefaultButton(QMessageBox.No)
            result = box.exec_()
            if result == QMessageBox.No:
                return

        # self.dialog.input_ftp_port.setValue(21)
        self.dialog.input_ftp_host.setText('')
        self.dialog.input_ftp_user.setText('')
        self.dialog.input_ftp_password.setText('')
        self.dialog.input_ftp_directory.setText('')

    def fetch_inputs(self) -> bool:
        """ Fetch inputs from fields and check."""
        # self.port = self.dialog.input_ftp_port.value()
        self.host = self.dialog.input_ftp_host.text()
        self.user = self.dialog.input_ftp_user.text()
        self.password = self.dialog.input_ftp_password.text()
        self.directory = self.dialog.input_ftp_directory.text()

        if not self.port:
            self.port = 21

        if not self.host:
            QMessageBox.critical(self.dialog, 'FTP Error', "Host is required", QMessageBox.Ok)
            return False

        if not self.user:
            QMessageBox.critical(self.dialog, 'FTP Error', "User is required", QMessageBox.Ok)
            return False

        if not self.password:
            QMessageBox.critical(self.dialog, 'FTP Error', "Password is required", QMessageBox.Ok)
            return False

        if not self.directory:
            self.directory = self.dialog.input_ftp_directory.placeholderText()

        return True

    def check_server(self):
        """ Check if the given user can connect to this FTP and display a message if needed. """
        if not self.fetch_inputs():
            return False

        valid, message = self.connect(False)
        if not valid:
            QMessageBox.critical(
                self.dialog,
                'FTP Error',
                message,
                QMessageBox.Ok
            )
            return False

        QMessageBox.information(
            self.dialog,
            'Success',
            "Host, login and password is successful",
            QMessageBox.Ok
        )
        return True

    def enable_checkbox(self):
        """ Enable the FTP transfer or not. """
        if self.dialog.checkbox_save_project.isChecked():
            self.dialog.checkbox_ftp_transfer.setEnabled(True)
        else:
            self.dialog.checkbox_ftp_transfer.setEnabled(False)
            self.dialog.checkbox_ftp_transfer.setChecked(False)

    def connect(self, send_files: bool = False) -> Tuple[bool, Optional[str]]:
        """ Send the QGS and the CFG file over FTP. """
        if not self.is_ftp_available():
            return False, "The FTP is not installed."

        try:
            self.with_tls(send_files)
        except socket.gaierror:
            return False, 'Host is not correct'
        except ConnectionResetError as e:
            LOGGER.critical("Connection reset error")
            return False, str(e)
        except error_perm:
            # The directory does not exist or no rights.
            msg = (
                "The directory {} does not exist or not enough permission to move in this directory."
            ).format(self.directory)
            return False, msg

        except Exception as e:
            LOGGER.critical(f"Unknown exception while using FTP : {str(e)}")
            return False, str(e)

        LOGGER.info("Both QGS and CFG files have been send on {}".format(self.host))
        return True, None

    def with_tls(self, send_files):
        with FTP_TLS(self.host) as session:
            session.login(user=self.user, passwd=self.password)
            session.prot_p()
            session.set_pasv(False)
            session.cwd(self.directory)

            if send_files:
                session.set_pasv(True)

                cfg_path = Path(self.project.fileName() + '.cfg')
                # CFG file
                with open(cfg_path, 'rb') as file:
                    session.storbinary(f'STOR {cfg_path.name}', file)

                # QGS file
                with open(self.project.fileName(), 'rb') as file:
                    session.storbinary(f'STOR {Path(self.project.fileName()).name}', file)

                try:
                    session.close()
                except Exception as e:
                    # It shouldn't be necessary as we are in a context
                    LOGGER.critical("Error while closing the FTP connection : {}".format(str(e)))

    def without_tls(self, send_files):
        try:
            with FTP(self.host, self.user, self.password) as ftp:
                ftp.cwd(self.directory)
                if send_files:
                    self._send_files(ftp)

        except socket.gaierror:
            return False, 'Host is not correct'
        except error_perm as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)

        LOGGER.info("Both QGS and CFG files have been send on {}".format(self.host))
        return True, None
