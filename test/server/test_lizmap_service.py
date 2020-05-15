import json
import logging
import warnings

LOGGER = logging.getLogger('server')

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
    assert 'version' in b['lizmap']
    assert 'name' in b['lizmap']

    assert 'services' in b
    assert 'WMS' in b['services']
    assert 'LIZMAP' in b['services']
    assert 'EXPRESSION' in b['services']
