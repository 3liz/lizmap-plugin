import json

from urllib.parse import quote

__copyright__ = 'Copyright 2019, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


def test_layer_error(client):
    """  Test Expression GetFeatureFormScope request with Layer parameter error
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


def test_filter_error(client):
    """  Test Expression GetFeatureFormScope request with Filter parameter error
    """
    projectfile = "france_parts.qgs"

    # Make a request without filter
    qs = "?SERVICE=EXPRESSION&REQUEST=Evaluate&MAP=france_parts.qgs&LAYER=france_parts"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 400
    assert rv.headers.get('Content-Type', '').find('application/json') == 0


def test_formfeature_error(client):
    """  Test Expression GetFeatureFormScope request with Form_Feature parameter error
    """
    projectfile = "france_parts.qgs"

    # Make a request without form_feature
    qs = "?SERVICE=EXPRESSION&REQUEST=Evaluate&MAP=france_parts.qgs&LAYER=france_parts"
    qs += "&FILTER=%s" % (
        quote("NAME_1 = current_value('prop0')", safe=''))
    rv = client.get(qs, projectfile)
    assert rv.status_code == 400
    assert rv.headers.get('Content-Type', '').find('application/json') == 0

    # Make a request without well formed form_feature
    qs = "?SERVICE=EXPRESSION&REQUEST=GetFeatureWithFormScope&MAP=france_parts.qgs&LAYER=france_parts"
    qs += "&FILTER=%s" % (
        quote("NAME_1 = current_value('prop0')", safe=''))
    qs += "&FORM_FEATURE={\"type\":\"Feature\", \"geometry\": {\"type\": \"Point\", \"coordinates\": [102.0, 0.5]}, \"properties\": {\"prop0\": \"Bretagne\"}"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 400
    assert rv.headers.get('Content-Type', '').find('application/json') == 0

    # Make a request without well formed form_feature
    qs = "?SERVICE=EXPRESSION&REQUEST=GetFeatureWithFormScope&MAP=france_parts.qgs&LAYER=france_parts"
    qs += "&FILTER=%s" % (
        quote("NAME_1 = current_value('prop0')", safe=''))
    qs += "&FORM_FEATURE={\"type\":\"feature\", \"geometry\": {\"type\": \"Point\", \"coordinates\": [102.0, 0.5]}, \"properties\": {\"prop0\": \"Bretagne\"}}"
    # type feature and not Feature error
    rv = client.get(qs, projectfile)
    assert rv.status_code == 400
    assert rv.headers.get('Content-Type', '').find('application/json') == 0


def test_request(client):
    """  Test Expression GetFeatureFormScope request
    """
    projectfile = "france_parts.qgs"

    # Make a request
    qs = "?SERVICE=EXPRESSION&REQUEST=GetFeatureWithFormScope&MAP=france_parts.qgs&LAYER=france_parts"
    qs += "&FILTER=%s" % (
        quote("NAME_1 = current_value('prop0')", safe=''))
    qs += "&FORM_FEATURE={\"type\":\"Feature\", \"geometry\": {\"type\": \"Point\", \"coordinates\": [102.0, 0.5]}, \"properties\": {\"prop0\": \"Bretagne\"}}"
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

    assert 'properties' in b['features'][0]
    assert 'NAME_1' in b['features'][0]['properties']
    assert b['features'][0]['properties']['NAME_1'] == 'Bretagne'

    assert 'geometry' in b['features'][0]
    assert b['features'][0]['geometry'] is None

    assert 'id' in b['features'][0]
    assert b['features'][0]['id'] == 'france_parts.1'  # should be 4

    # Make a request with geometry
    qs = "?SERVICE=EXPRESSION&REQUEST=GetFeatureWithFormScope&MAP=france_parts.qgs&LAYER=france_parts"
    qs += "&FILTER=%s" % (
        quote("NAME_1 = current_value('prop0')", safe=''))
    qs += "&FORM_FEATURE={\"type\":\"Feature\", \"geometry\": {\"type\": \"Point\", \"coordinates\": [102.0, 0.5]}, \"properties\": {\"prop0\": \"Bretagne\"}}"
    qs += "&WITH_GEOMETRY=True"
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

    assert 'properties' in b['features'][0]
    assert 'NAME_1' in b['features'][0]['properties']
    assert b['features'][0]['properties']['NAME_1'] == 'Bretagne'

    assert 'geometry' in b['features'][0]
    assert b['features'][0]['geometry'] is not None
    assert 'type' in b['features'][0]['geometry']
    assert b['features'][0]['geometry']['type'] == 'MultiPolygon'

    # Make a request with fields
    qs = "?SERVICE=EXPRESSION&REQUEST=GetFeatureWithFormScope&MAP=france_parts.qgs&LAYER=france_parts"
    qs += "&FILTER=%s" % (
        quote("NAME_1 = current_value('prop0')", safe=''))
    qs += "&FORM_FEATURE={\"type\":\"Feature\", \"geometry\": {\"type\": \"Point\", \"coordinates\": [102.0, 0.5]}, \"properties\": {\"prop0\": \"Bretagne\"}}"
    qs += "&FIELDS=ISO,NAME_1"
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

    assert 'properties' in b['features'][0]
    assert 'NAME_1' in b['features'][0]['properties']
    assert b['features'][0]['properties']['NAME_1'] == 'Bretagne'
    assert 'NAME_0' not in b['features'][0]['properties']

    assert 'geometry' in b['features'][0]
    assert b['features'][0]['geometry'] is None

    # Make a request with spatial filter
    qs = "?SERVICE=EXPRESSION&REQUEST=GetFeatureWithFormScope&MAP=france_parts.qgs&LAYER=france_parts"
    qs += "&FILTER=%s" % (
        quote("intersects($geometry, @current_geometry)", safe=''))
    qs += "&FORM_FEATURE={\"type\":\"Feature\", \"geometry\": {\"type\": \"Point\", \"coordinates\": [-3.0, 48.0]}, \"properties\": {\"prop0\": \"Bretagne\"}}"
    qs += "&WITH_GEOMETRY=True"
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

    assert 'properties' in b['features'][0]
    assert 'NAME_1' in b['features'][0]['properties']
    assert b['features'][0]['properties']['NAME_1'] == 'Bretagne'

    assert 'geometry' in b['features'][0]
    assert b['features'][0]['geometry'] is not None
    assert 'type' in b['features'][0]['geometry']
    assert b['features'][0]['geometry']['type'] == 'MultiPolygon'
