__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from typing import Optional

from qgis.core import QgsDataSourceUri, QgsProject, QgsVectorLayer

from lizmap.qgis_plugin_tools.tools.i18n import tr

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


def duplicated_layer_with_filter(project: QgsProject) -> Optional[str]:
    """ Check for duplicated layers with the same datasource but different filters. """
    unique_datasource = {}
    for layer in project.mapLayers().values():
        uri = QgsDataSourceUri(layer.source())
        uri_filter = uri.sql()
        if uri_filter == '':
            continue

        uri.setSql('')

        uri_string = uri.uri(True)

        if uri_string not in unique_datasource.keys():
            unique_datasource[uri_string] = {}

        if uri_filter not in unique_datasource[uri_string]:
            unique_datasource[uri_string][uri_filter] = layer.name()

    if len(unique_datasource.keys()) == 0:
        return None

    text = ''
    for datasource, filters in unique_datasource.items():
        layer_names = ','.join([f"'{k}'" for k in filters.values()])
        uri_filter = ','.join([f"'{k}'" for k in filters.keys()])
        text += tr(
            "Review layers {layers} having the same datasource '{datasource}' with these filters {uri_filter}."
        ).format(
            layers=layer_names,
            datasource=QgsDataSourceUri.removePassword(QgsDataSourceUri(datasource).uri(False)),
            uri_filter=uri_filter
        )
        text += '<br>'

    return text
