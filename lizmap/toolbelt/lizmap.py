__copyright__ = "Copyright 2024, 3Liz"
__license__ = "GPL version 3"
__email__ = "info@3liz.org"

import re

from typing import List, Tuple

from qgis.core import QgsVectorLayer


def convert_lizmap_popup(content: str, layer: QgsVectorLayer) -> Tuple[str, List[str]]:
    """ Convert an HTML Lizmap popup to QGIS HTML Maptip.

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
                content = content.replace(variable[0], '[% "{}" %]'.format(field))
                break
        else:
            errors.append(variable[1])

    return content, errors
