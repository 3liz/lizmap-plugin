__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from qgis.core import QgsDataSourceUri, QgsVectorLayer

""" Some checks which can be done on a layer. """

# https://github.com/3liz/lizmap-web-client/issues/3692


def invalid_tid_field(layer: QgsVectorLayer) -> bool:
    """ If the primary key has been detected as tid but the field does not exist. """
    # Example
    # CREATE TABLE IF NOT EXISTS public.test_tid
    # (
    #     id bigint,
    #     label text
    # )
    # In QGIS source code, look for "Primary key is ctid"
    uri = QgsDataSourceUri(layer.source())
    # QgsVectorLayer.primaryKeyAttributes is returning a list.
    # TODO check, but with QgsDataSourceUri, we have a single field
    if uri.keyColumn() != 'tid':
        return False

    if 'tid' in layer.fields().names():
        return False

    # The layer has "tid" as a primary key, but the field is not found.
    return True


def invalid_int8_primary_key(layer: QgsVectorLayer) -> bool:
    """ If the layer has a primary key as int8, alias bigint. """
    # Example
    # CREATE TABLE IF NOT EXISTS france.test_bigint
    # (
    #     id bigint PRIMARY KEY,
    #     label text
    # )
    # QgsVectorLayer.primaryKeyAttributes is returning a list.
    if len(layer.primaryKeyAttributes()) != 1:
        # We might have either no primary key,
        # or a composite primary key
        return False

    uri = QgsDataSourceUri(layer.source())
    primary_key = uri.keyColumn()
    if not primary_key:
        return False

    field_type = layer.fields().field(primary_key).typeName()
    return field_type.lower() == 'int8'
