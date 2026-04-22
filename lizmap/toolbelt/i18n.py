"""I18N tools."""
from __future__ import annotations

from typing import TYPE_CHECKING

from qgis.core import QgsSettings
from qgis.PyQt.QtCore import QLocale
from qgis.PyQt.QtWidgets import QApplication

from lizmap.toolbelt.resources import resources_path

if TYPE_CHECKING:
    from pathlib import Path


def setup_translation(
    file_pattern: str = "{}.qm",
    folder: Path | None = None,
) -> tuple[str, Path | None]:
    """Find the translation file according to locale.

    :param file_pattern: Custom file pattern to use to find QM files.
    :type file_pattern: basestring

    :param folder: Optional folder to look in if it's not the default.
    :type folder: basestring

    :return: The locale and the file path to the QM file, or None.
    :rtype: (basestring, basestring)
    """
    locale = QgsSettings().value("locale/userLocale", QLocale().name())

    if folder:
        ts_file = folder.joinpath(file_pattern.format(locale))
    else:
        ts_file = resources_path("i18n", file_pattern.format(locale))
    if ts_file.exists():
        return locale, ts_file

    if folder:
        ts_file = folder.joinpath(file_pattern.format(locale[0:2]))
    else:
        ts_file = resources_path("i18n", file_pattern.format(locale[0:2]))
    if ts_file.exists():
        return locale, ts_file

    return locale, None


def tr(text, context="@default"):
    return QApplication.translate(context, text)
