import json

import pytest

__copyright__ = 'Copyright 2019, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


def test_lizmap_request_unknown(client):
    """  Test getserversettings response
    """
    projectfile = "france_parts.qgs"

    # Make a request
    qs = "?SERVICE=LIZMAP&REQUEST=UNKNOWN_REQUEST&MAP=france_parts.qgs"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 400

    assert rv.headers.get('Content-Type', '').find('application/json') == 0

    b = json.loads(rv.content.decode('utf-8'))

    assert 'status' in b
    assert b['status'] == 'fail'

    assert 'code' in b
    assert 'message' in b


def test_lizmap_getserversettings(client):
    """  Test getserversettings response
    """
    projectfile = "france_parts.qgs"

    # Make a request
    qs = "?SERVICE=LIZMAP&REQUEST=GetServerSettings&MAP=france_parts.qgs"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('application/json') == 0

    b = json.loads(rv.content.decode('utf-8'))

    assert 'qgis' in b
    assert 'version' in b['qgis']
    assert 'version_int' in b['qgis']
    assert 'name' in b['qgis']

    assert 'gdalogr' in b
    assert 'version_int' in b['gdalogr']
    assert 'name' in b['gdalogr']

    assert 'lizmap' in b
    assert b['lizmap']['version'] in ['master', 'dev']
    assert b['lizmap']['name'] == 'Lizmap'

    assert 'services' in b
    assert 'WMS' in b['services']
    assert 'LIZMAP' in b['services']
    assert 'EXPRESSION' in b['services']


@pytest.mark.skip(reason="crash ?")
def test_lizmap_service_filter_polygon_with_user(client):
    """  Test get polygon filter with the Lizmap service with a user. """
    project_file = "test_filter_layer_data_by_polygon_for_groups.qgs"

    qs = (
        "?"
        "SERVICE=LIZMAP&"
        "REQUEST=GETSUBSETSTRING&"
        "MAP=france_parts.qgs&"
        "LAYER=shop_bakery&"
        "LIZMAP_USER_GROUPS=montferrier-sur-lez"
    )
    rv = client.get(qs, project_file)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('application/json') == 0

    b = json.loads(rv.content.decode('utf-8'))

    assert b['filter'] == '"id" IN ( 68 )'
    assert b['status'] == 'success'
    assert b['polygons'].startswith('SRID=3857;MultiPolygon')


@pytest.mark.skip(reason="crash ?")
def test_lizmap_service_filter_polygon_without_user(client):
    """  Test get polygon filter with the Lizmap service without a user. """
    project_file = "test_filter_layer_data_by_polygon_for_groups.qgs"

    qs = (
        "?"
        "SERVICE=LIZMAP&"
        "REQUEST=GETSUBSETSTRING&"
        "MAP=france_parts.qgs&"
        "LAYER=shop_bakery&"
        # "LIZMAP_USER_GROUPS=montferrier-sur-lez"
    )
    rv = client.get(qs, project_file)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('application/json') == 0

    b = json.loads(rv.content.decode('utf-8'))

    assert b == {'filter': '1 = 0', 'polygons': '', 'status': 'success'}
