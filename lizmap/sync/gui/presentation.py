"""Labels, colors and icons of the statuses and actions of the synchronisation."""

from __future__ import annotations

from functools import cache

from qgis.core import QgsApplication, QgsFileUtils
from qgis.PyQt.QtCore import QDateTime, QLocale, Qt
from qgis.PyQt.QtGui import QColor, QIcon, QPainter, QPixmap

from lizmap.sync.model import Direction, FileStatus, SyncAction
from lizmap.toolbelt.i18n import tr

GREEN = "#2e7d32"
ORANGE = "#e65100"
RED = "#c62828"
GREY = "#757575"

_STATUS_COLORS = {
    FileStatus.Identical: GREY,
    FileStatus.Excluded: GREY,
    FileStatus.NewLocal: GREEN,
    FileStatus.NewRemote: GREEN,
    FileStatus.LocalModified: ORANGE,
    FileStatus.RemoteModified: ORANGE,
    FileStatus.Different: ORANGE,
    FileStatus.Unverified: ORANGE,
    FileStatus.Conflict: RED,
    FileStatus.DeletedLocal: RED,
    FileStatus.DeletedRemote: RED,
    FileStatus.CaseConflict: RED,
}

_ACTION_COLORS = {
    SyncAction.Nothing: GREY,
    SyncAction.Upload: GREEN,
    SyncAction.Download: GREEN,
    SyncAction.DeleteRemote: RED,
    SyncAction.DeleteLocal: RED,
}

_ACTION_ICONS = {
    SyncAction.Upload: "/mActionArrowUp.svg",
    SyncAction.Download: "/mActionArrowDown.svg",
    SyncAction.DeleteRemote: "/mActionDeleteSelected.svg",
    SyncAction.DeleteLocal: "/mActionDeleteSelected.svg",
}


def status_label(status: FileStatus) -> str:
    """Label of a status.

    :param status: The status.
    :return: The translated label.
    """
    labels = {
        FileStatus.Identical: tr("Identical"),
        FileStatus.NewLocal: tr("Missing on the server"),
        FileStatus.NewRemote: tr("Missing locally"),
        FileStatus.LocalModified: tr("Modified locally"),
        FileStatus.RemoteModified: tr("Modified on the server"),
        FileStatus.Different: tr("Different"),
        FileStatus.Unverified: tr("Same size, not verified"),
        FileStatus.Conflict: tr("Conflict"),
        FileStatus.DeletedLocal: tr("Deleted locally"),
        FileStatus.DeletedRemote: tr("Deleted on the server"),
        FileStatus.Excluded: tr("Excluded"),
        FileStatus.CaseConflict: tr("Name differing only by the case"),
    }
    return labels[status]


def status_tooltip(status: FileStatus) -> str:
    """Explanation of a status.

    :param status: The status.
    :return: The translated explanation.
    """
    tooltips = {
        FileStatus.Identical: tr("The file is the same on both sides."),
        FileStatus.NewLocal: tr("The file exists only on this computer."),
        FileStatus.NewRemote: tr("The file exists only on the server."),
        FileStatus.LocalModified: tr(
            "The file has been modified on this computer since the last synchronisation."
        ),
        FileStatus.RemoteModified: tr(
            "The file has been modified on the server since the last synchronisation."
        ),
        FileStatus.Different: tr(
            "The file has never been synchronised and its content is different on both sides. "
            "Choose which version to keep."
        ),
        FileStatus.Unverified: tr(
            "The file has never been synchronised. Both files have the same size, but they are too big "
            "to compare their content."
        ),
        FileStatus.Conflict: tr(
            "The file has been modified on both sides, or modified on one side and deleted on the other one, "
            "since the last synchronisation. Choose which version to keep."
        ),
        FileStatus.DeletedLocal: tr(
            "The file has been deleted on this computer since the last synchronisation."
        ),
        FileStatus.DeletedRemote: tr(
            "The file has been deleted on the server since the last synchronisation."
        ),
        FileStatus.Excluded: tr("The file is excluded by the filters of the synchronisation."),
        FileStatus.CaseConflict: tr(
            "Several files have the same name with a different case. They can't be synchronised, rename them."
        ),
    }
    return tooltips[status]


def action_label(action: SyncAction) -> str:
    """Label of an action.

    :param action: The action.
    :return: The translated label.
    """
    labels = {
        SyncAction.Nothing: tr("No action"),
        SyncAction.Upload: tr("Upload"),
        SyncAction.Download: tr("Download"),
        SyncAction.DeleteRemote: tr("Delete on the server"),
        SyncAction.DeleteLocal: tr("Delete locally"),
    }
    return labels[action]


def direction_label(direction: Direction) -> str:
    """Label of a direction.

    :param direction: The direction.
    :return: The translated label.
    """
    labels = {
        Direction.TwoWay: tr("Two-way"),
        Direction.PullOnly: tr("Download only"),
        Direction.PushOnly: tr("Upload only"),
    }
    return labels[direction]


def status_color(status: FileStatus) -> QColor:
    """Color of a status.

    :param status: The status.
    :return: The color.
    """
    return QColor(_STATUS_COLORS[status])


def action_color(action: SyncAction) -> QColor:
    """Color of an action.

    :param action: The action.
    :return: The color.
    """
    return QColor(_ACTION_COLORS[action])


@cache
def status_icon(status: FileStatus) -> QIcon:
    """Icon of a status: a disc with the color of the status.

    :param status: The status.
    :return: The icon.
    """
    pixmap = QPixmap(16, 16)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(status_color(status))
    painter.drawEllipse(3, 3, 10, 10)
    painter.end()
    return QIcon(pixmap)


def action_icon(action: SyncAction) -> QIcon:
    """Icon of an action.

    :param action: The action.
    :return: The icon, empty for no action.
    """
    name = _ACTION_ICONS.get(action)
    return QgsApplication.getThemeIcon(name) if name else QIcon()


def folder_icon() -> QIcon:
    """Icon of a directory.

    :return: The icon.
    """
    return QgsApplication.getThemeIcon("/mIconFolder.svg")


def file_size(size: int) -> str:
    """Size of a file, for the user.

    :param size: Size in bytes.
    :return: The size, such as "12.3 KB".
    """
    return QgsFileUtils.representFileSize(size)


def file_details(size: int, timestamp: float) -> str:
    """Describe a file with its size and its modification time.

    :param size: Size in bytes.
    :param timestamp: Modification time, in seconds since the epoch.
    :return: The description, such as "12 KB, 27/11/2026 10:12".
    """
    date = QDateTime.fromSecsSinceEpoch(int(timestamp))
    return f"{file_size(size)}, {QLocale().toString(date, QLocale.FormatType.ShortFormat)}"
