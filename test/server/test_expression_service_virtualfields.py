import json

from urllib.parse import quote


__copyright__ = 'Copyright 2019, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


def test_layer_error(client):
    """  Test Expression VirtualFields request with Layer parameter error
    """
    projectfile = "france_parts.qgs"

    # Make a request without layer
    qs = "?SERVICE=EXPRESSION&REQUEST=GetFeatureWithFormScope&MAP=france_parts.qgs"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 400
    assert rv.headers.get('Content-Type', '').find('application/json') == 0

    # Make a request with an unknown layer
    qs = "?SERVICE=EXPRESSION&REQUEST=GetFeatureWithFormScope&MAP=france_parts.qgs&LAYER=UNKNOWN_LAYER"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 400
    assert rv.headers.get('Content-Type', '').find('application/json') == 0


def test_virtuals_error(client):
    """  Test Expression VirtualFields request with Virtuals parameter error
    """
    projectfile = "france_parts.qgs"

    # Make a request without filter
    qs = "?SERVICE=EXPRESSION&REQUEST=Evaluate&MAP=france_parts.qgs&LAYER=france_parts"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 400
    assert rv.headers.get('Content-Type', '').find('application/json') == 0

    # Make a request
    qs = "?SERVICE=EXPRESSION&REQUEST=VirtualFields&MAP=france_parts.qgs&LAYER=france_parts"
    qs+= "&VIRTUALS={\"a\":\"%s\", \"b\":\"%s\"" % (
        quote('1', safe=''), quote('1 + 1', safe=''))
    rv = client.get(qs, projectfile)
    assert rv.status_code == 400
    assert rv.headers.get('Content-Type', '').find('application/json') == 0


def test_request(client):
    """  Test Expression VirtualFields request
    """
    projectfile = "france_parts.qgs"

    # Make a request
    qs = "?SERVICE=EXPRESSION&REQUEST=VirtualFields&MAP=france_parts.qgs&LAYER=france_parts"
    qs+= "&VIRTUALS={\"a\":\"%s\", \"b\":\"%s\"}" % (
        quote('1', safe=''), quote('1 + 1', safe=''))
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type', '').find('application/json') == 0

    b = json.loads(rv.content.decode('utf-8'))

    assert 'type' in b
    assert b['type'] == 'FeatureCollection'

    assert 'features' in b
    assert len(b['features']) == 4

    assert 'type' in b['features'][0]
    assert b['features'][0]['type'] == 'Feature'

    assert 'geometry' in b['features'][0]
    assert b['features'][0]['geometry'] is None

    assert 'properties' in b['features'][0]
    assert 'NAME_1' in b['features'][0]['properties']
    assert 'Region' in b['features'][0]['properties']

    assert 'a' in b['features'][0]['properties']
    assert b['features'][0]['properties']['a'] == 1
    assert 'b' in b['features'][0]['properties']
    assert b['features'][0]['properties']['b'] == 2


def test_request_with_filter(client):
    """  Test Expression VirtualFields request with Filter parameter
    """
    projectfile = "france_parts.qgs"

    # Make a request
    qs = "?SERVICE=EXPRESSION&REQUEST=VirtualFields&MAP=france_parts.qgs&LAYER=france_parts"
    qs+= "&VIRTUALS={\"a\":\"%s\", \"b\":\"%s\"}" % (
        quote('1', safe=''), quote('1 + 1', safe=''))
    qs+= "&FILTER=%s" % (
        quote("NAME_1 = 'Bretagne'", safe=''))
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type', '').find('application/json') == 0

    b = json.loads(rv.content.decode('utf-8'))

    assert 'type' in b
    assert b['type'] == 'FeatureCollection'

    assert 'features' in b
    assert len(b['features']) == 1

    assert 'type' in b['features'][0]
    assert b['features'][0]['type'] == 'Feature'

    assert 'geometry' in b['features'][0]
    assert b['features'][0]['geometry'] is None

    assert 'properties' in b['features'][0]
    assert 'NAME_1' in b['features'][0]['properties']
    assert b['features'][0]['properties']['NAME_1'] == 'Bretagne'
    assert 'Region' in b['features'][0]['properties']
    assert b['features'][0]['properties']['Region'] == 'Bretagne'

    assert 'a' in b['features'][0]['properties']
    assert b['features'][0]['properties']['a'] == 1
    assert 'b' in b['features'][0]['properties']
    assert b['features'][0]['properties']['b'] == 2


def test_request_with_filter_fields(client):
    """  Test Expression VirtualFields request with Filter and Fields parameters
    """
    projectfile = "france_parts.qgs"

    # Make a request
    qs = "?SERVICE=EXPRESSION&REQUEST=VirtualFields&MAP=france_parts.qgs&LAYER=france_parts"
    qs+= "&VIRTUALS={\"a\":\"%s\", \"b\":\"%s\"}" % (
        quote('1', safe=''), quote('1 + 1', safe=''))
    qs+= "&FILTER=%s" % (
        quote("NAME_1 = 'Bretagne'", safe=''))
    qs+= "&FIELDS=ISO,NAME_1"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type', '').find('application/json') == 0

    b = json.loads(rv.content.decode('utf-8'))

    assert 'type' in b
    assert b['type'] == 'FeatureCollection'

    assert 'features' in b
    assert len(b['features']) == 1

    assert 'type' in b['features'][0]
    assert b['features'][0]['type'] == 'Feature'

    assert 'geometry' in b['features'][0]
    assert b['features'][0]['geometry'] is None

    assert 'properties' in b['features'][0]
    assert 'NAME_1' in b['features'][0]['properties']
    assert b['features'][0]['properties']['NAME_1'] == 'Bretagne'
    assert 'Region' not in b['features'][0]['properties']

    assert 'a' in b['features'][0]['properties']
    assert b['features'][0]['properties']['a'] == 1
    assert 'b' in b['features'][0]['properties']
    assert b['features'][0]['properties']['b'] == 2


def test_request_with_filter_fields_geometry(client):
    """  Test Expression VirtualFields request with Filter, Fields and With_Geometry parameters
    """
    projectfile = "france_parts.qgs"

    # Make a request
    qs = "?SERVICE=EXPRESSION&REQUEST=VirtualFields&MAP=france_parts.qgs&LAYER=france_parts"
    qs+= "&VIRTUALS={\"a\":\"%s\", \"b\":\"%s\"}" % (
        quote('1', safe=''), quote('1 + 1', safe=''))
    qs+= "&FILTER=%s" % (
        quote("NAME_1 = 'Bretagne'", safe=''))
    qs+= "&FIELDS=ISO,NAME_1"
    qs+= "&WITH_GEOMETRY=true"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type', '').find('application/json') == 0

    b = json.loads(rv.content.decode('utf-8'))

    assert 'type' in b
    assert b['type'] == 'FeatureCollection'

    assert 'features' in b
    assert len(b['features']) == 1

    assert 'type' in b['features'][0]
    assert b['features'][0]['type'] == 'Feature'

    assert 'geometry' in b['features'][0]
    assert b['features'][0]['geometry'] is not None

    assert 'properties' in b['features'][0]
    assert 'NAME_1' in b['features'][0]['properties']
    assert b['features'][0]['properties']['NAME_1'] == 'Bretagne'
    assert 'Region' not in b['features'][0]['properties']

    assert 'a' in b['features'][0]['properties']
    assert b['features'][0]['properties']['a'] == 1
    assert 'b' in b['features'][0]['properties']
    assert b['features'][0]['properties']['b'] == 2
