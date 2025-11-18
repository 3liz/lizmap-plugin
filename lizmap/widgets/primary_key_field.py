__copyright__ = 'Copyright 2025, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from typing import Optional

from qgis.core import QgsVectorLayer
from qgis.gui import QgsFieldComboBox

from lizmap.toolbelt.i18n import tr
from lizmap.toolbelt.layer import is_database_layer


def enable_primary_key_field(primary_key: QgsFieldComboBox, layer: Optional[QgsVectorLayer]) -> Optional[bool]:
    """ Enable or not the primary key widget.
    For a database based layer (PG, SQLite, GPKG) the widget is disabled."""
    if not layer:
        return None

    tooltip = primary_key.toolTip()
    extra_tooltip = tr('The primary key is defined by the dataprovider only for layer stored in a database.')
    if extra_tooltip not in tooltip:
        primary_key.setToolTip('{} {}'.format(tooltip, extra_tooltip))

    if not is_database_layer(layer):
        primary_key.setEnabled(True)
        primary_key.setAllowEmptyFieldName(False)
        return None

    # We trust the datasource
    # And we do not trust the legacy CFG
    primary_key.setEnabled(False)
    primary_key.setAllowEmptyFieldName(True)
    pks = layer.primaryKeyAttributes()
    if len(pks) == 0:
        # Must be an issue for the user to validate the form, because the widget is disabled
        # The datasource must be fixed
        return False

    if len(pks) >= 2:
        # As well, the user must add a PK and an unicity constraint
        # Not possible to validate the form
        return False

    # Single field as a primary key
    # We do not trust the CFG anymore, let's go datasource
    name = layer.fields().at(pks[0]).name()
    primary_key.setField(name)
    return True
