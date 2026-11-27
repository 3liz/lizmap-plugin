"""Checks of the open QGIS project before a synchronisation."""

from __future__ import annotations

import sqlite3

from pathlib import Path
from typing import TYPE_CHECKING

from qgis.core import QgsVectorLayer

from lizmap.toolbelt.layer_files import scan_layer_files

if TYPE_CHECKING:
    from qgis.core import QgsProject

# SQLite based formats, which may have a write-ahead log not written yet in the main file
SQLITE_SUFFIXES = (".gpkg", ".sqlite", ".db")


def project_files(project: QgsProject, root: Path) -> dict[str, Path]:
    """List the files used by the layers of the project, inside the local directory.

    :param project: The project.
    :param root: The local directory.
    :return: Absolute paths of the files, by path relative to the local directory, sidecar files included.
    """
    root = root.resolve()
    files = {}
    for _layer, path, sidecars in scan_layer_files(project):
        for file_path in (path, *sidecars):
            try:
                relative = file_path.resolve().relative_to(root)
            except ValueError:
                # Outside the local directory, not synchronised
                continue
            files[relative.as_posix()] = file_path
    return files


def layers_with_pending_edits(project: QgsProject) -> list[str]:
    """List the layers having edits not saved yet.

    :param project: The project.
    :return: The names of the layers.
    """
    return sorted(
        layer.name()
        for layer in project.mapLayers().values()
        if isinstance(layer, QgsVectorLayer) and layer.isEditable() and layer.isModified()
    )


def checkpoint_sqlite(files: list[Path]) -> dict[str, str]:
    """Write the write-ahead log of SQLite and GeoPackage files into the main files.

    QGIS opens GeoPackage files in WAL mode: recent edits can be only in the "-wal" file, which is
    never synchronised. A checkpoint writes them in the main file before the comparison.

    :param files: The files, only SQLite based formats are handled.
    :return: Error messages, by file.
    """
    errors = {}
    for file_path in files:
        if file_path.suffix.lower() not in SQLITE_SUFFIXES:
            continue
        if not Path(f"{file_path}-wal").exists():
            continue
        try:
            connection = sqlite3.connect(str(file_path))
            try:
                busy, _log, _done = connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
            finally:
                connection.close()
            if busy:
                errors[str(file_path)] = "The file is busy, the checkpoint is not complete."
        except sqlite3.Error as e:
            errors[str(file_path)] = str(e)
    return errors
