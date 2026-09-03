__copyright__ = "Copyright 2024, 3Liz"
__license__ = "GPL version 3"
__email__ = "info@3liz.org"

from pathlib import Path

from qgis._core import QgsMapLayerModel
from qgis.PyQt.QtWidgets import QDialog, QPushButton

from lizmap.definitions.lizmap_cloud import UPLOAD_EXTENSIONS, UPLOAD_MAX_SIZE
from lizmap.widgets.table_files import TableFiles

from .. import logger
from ..toolbelt.layer_files import scan_layer_files


class TableFilesManager:
    def __init__(self, parent: QDialog, table: TableFiles, button_scan_files: QPushButton):
        """Constructor."""
        self.parent = parent
        self.table = table
        self.button_scan = button_scan_files

        self.button_scan.clicked.connect(self.scan_files)

    def scan_files(self):
        """Scan all files"""
        self.table.setRowCount(0)

        project = self.parent.project

        project_home = Path(project.absolutePath())
        self.parent.label_current_folder.setText(f"<strong>{project_home}</strong>")

        files = {}

        for layer, layer_path, sidecar_files in scan_layer_files(project):
            if layer_path in files:
                # A layer can be used many times, with different filters
                continue

            if not layer_path.is_relative_to(project_home):
                # Discard files outside of project path
                logger.warning(
                    "%s is outside project path (%s) and will not be uploaded", layer_path, project_home
                )
                continue

            if layer_path.suffix.lower().replace(".", "") not in UPLOAD_EXTENSIONS:
                # Not supported for now
                logger.warning("%s is not supported for uploading", layer_path)
                continue

            if layer_path.stat().st_size > UPLOAD_MAX_SIZE:
                # Not supported for now
                # FIXME: This must by dynamic and definitely not set in the client !!!!!
                logger.warning("%s exceed the allowed UPLOAD_MAX_SIZE ", layer_path)
                continue

            if sidecar_files:
                # FIXME: ATM sidecar files are not supported !!!!!
                logger.warning("File %s has sidecars files: %s, this is not supported ATM")

            files[layer_path] = QgsMapLayerModel.iconForLayer(layer)

        # Add to table
        for file_path, icon in files.items():
            self.table.add_file(file_path, icon)
