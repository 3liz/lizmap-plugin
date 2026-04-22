from __future__ import annotations

import re

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from qgis.core import QgsVectorLayer


def convert_lizmap_popup(content: str, layer: QgsVectorLayer) -> tuple[str, list[str]]:
    """Convert an HTML Lizmap popup to QGIS HTML Maptip.

    If one or more field couldn't be found in the layer fields/alias, returned in errors.
    If all fields could be converted, an empty list is returned.
    """
    # An alias can have accent, space etc...
    pattern = re.compile(r"(\{\s?\$([_\w\s]+)\s?\})")
    lizmap_variables = pattern.findall(content)
    fields = layer.fields()

    translations = {}
    for field in fields:
        translations[field.name()] = field.alias()

    errors = []

    for variable in lizmap_variables:
        for field, alias in translations.items():
            if variable[1].strip() in (alias, field):
                content = content.replace(variable[0], f'[% "{field}" %]')
                break
        else:
            errors.append(variable[1])

    return content, errors


def sidecar_media_dirs(file_path: Path) -> list[Path]:
    """Look for all side-car dirs in "media" directory.

    Like a Lizmap theme or a JavaScript.
    """
    media_root = file_path.parent.joinpath("media")
    if not media_root.exists():
        return []

    results = []
    for one_media in ("js", "theme"):
        folder = media_root.joinpath(one_media)
        if not folder.exists():
            continue

        default_media = folder.joinpath("default")
        if default_media.exists():
            results.append(default_media)

        project_media = folder.joinpath(file_path.stem)
        if project_media.exists():
            results.append(project_media)
            continue

    results.sort()
    return results
