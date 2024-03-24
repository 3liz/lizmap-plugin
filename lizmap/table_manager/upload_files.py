__copyright__ = 'Copyright 2024, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from os.path import relpath
from pathlib import Path

from qgis._core import QgsMapLayerModel
from qgis.core import QgsProviderRegistry
from qgis.PyQt.QtWidgets import QDialog, QPushButton

from lizmap.definitions.lizmap_cloud import UPLOAD_EXTENSIONS, UPLOAD_MAX_SIZE
from lizmap.widgets.table_files import TableFiles


class TableFilesManager:

    def __init__(self, parent: QDialog, table: TableFiles, button_scan_files: QPushButton):
        """ Constructor. """
        self.parent = parent
        self.table = table
        self.button_scan = button_scan_files

        self.button_scan.clicked.connect(self.scan_files)

    def scan_files(self):
        """ Scan all files"""
        self.table.setRowCount(0)

        unique_files = []
        unique_icons = {}

        project_home = Path(self.parent.project.absolutePath())
        self.parent.label_current_folder.setText(f"<strong>{project_home}</strong>")

        # QGIS_VERSION_INT 32200 :
        # Use QgsOgrProviderMetadata::sidecarFilesForUri
        for layer in self.parent.project.mapLayers().values():

            components = QgsProviderRegistry.instance().decodeUri(layer.dataProvider().name(), layer.source())
            if 'path' not in components.keys():
                # The layer is not file base.
                continue

            layer_path = Path(components['path'])
            try:
                if not layer_path.exists():
                    # Let's skip, QGIS is already warning this layer
                    # Or the file might be a COG on Linux :
                    # /vsicurl/https://demo.snap.lizmap.com/lizmap_3_6/cog/...
                    continue
            except OSError:
                # Ticket https://github.com/3liz/lizmap-plugin/issues/541
                # OSError: [WinError 123] La syntaxe du nom de fichier, de répertoire ou de volume est incorrecte:
                # '\\vsicurl\\https:\\XXX.lizmap.com\\YYY\\cog\\ZZZ.tif'
                continue

            try:
                relative_path = relpath(layer_path, project_home)
            except ValueError:
                # https://docs.python.org/3/library/os.path.html#os.path.relpath
                # On Windows, ValueError is raised when path and start are on different drives.
                # For instance, H: and C:

                # Not sure what to do for now...
                # We can't compute a relative path, but the user didn't enable the safety check, so we must still skip
                continue

            if '..' in relative_path:
                # Not supported for now
                continue

            if layer_path.stat().st_size > UPLOAD_MAX_SIZE:
                # Not supported for now
                continue

            if layer_path.suffix.lower().replace('.', '') not in UPLOAD_EXTENSIONS:
                # Not supported for now
                continue

            if layer_path in unique_files:
                # A layer can be used many times, with different filters
                continue

            # TODO check if number of sub-folder ?

            # TODO switch the other method
            # try:
            #     relative_path = layer_path.relative_to(project_home)
            # except ValueError:
            #     # It shouldn't happen at this stage
            #     continue

            # print(type(relative_path))
            # for dir_parent in relative_path.parents:
            #     print(dir_parent)

            unique_icons[layer_path] = QgsMapLayerModel.iconForLayer(layer)
            # unique_files.append(layer_path)

        for file_path, icon in unique_icons.items():
            self.table.add_file(file_path, icon)
