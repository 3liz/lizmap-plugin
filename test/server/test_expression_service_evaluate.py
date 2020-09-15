import json

from urllib.parse import quote

__copyright__ = 'Copyright 2019, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


def test_layer_error(client):
    """  Test Expression Evaluate request with Layer parameter error
    """
    projectfile = "france_parts.qgs"

    # Make a request without layer
    qs = "?SERVICE=EXPRESSION&REQUEST=Evaluate&MAP=france_parts.qgs"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 400

    assert rv.headers.get('Content-Type', '').find('application/json') == 0

    # Make a request with an unknown layer
    qs = "?SERVICE=EXPRESSION&REQUEST=Evaluate&MAP=france_parts.qgs&LAYER=UNKNOWN_LAYER"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 400
    assert rv.headers.get('Content-Type', '').find('application/json') == 0


def test_expression_error(client):
    """  Test Expression Evaluate request with Expression parameter error
    """
    projectfile = "france_parts.qgs"

    # Make a request without expression
    qs = "?SERVICE=EXPRESSION&REQUEST=Evaluate&MAP=france_parts.qgs&LAYER=france_parts"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 400
    assert rv.headers.get('Content-Type', '').find('application/json') == 0


def test_features_error(client):
    """  Test Expression Evaluate request with Feature or Features parameter error
    """
    projectfile = "france_parts.qgs"

    # Make a request
    qs = "?SERVICE=EXPRESSION&REQUEST=Evaluate&MAP=france_parts.qgs&LAYER=france_parts"
    qs += "&EXPRESSIONS={\"a\":\"%s\", \"b\":\"%s\", \"c\":\"%s\", \"d\":\"%s\"}" % (
        quote('1', safe=''), quote('1 + 1', safe=''), quote('prop0', safe=''), quote('$x', safe=''))
    qs += "&FEATURE={\"type\":\"Feature\", \"geometry\": {\"type\": \"Point\", \"coordinates\": [102.0, 0.5]}, \"properties\": {\"prop0\": \"value0\"}"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 400
    assert rv.headers.get('Content-Type', '').find('application/json') == 0

    # Make a request
    qs = "?SERVICE=EXPRESSION&REQUEST=Evaluate&MAP=france_parts.qgs&LAYER=france_parts"
    qs += "&EXPRESSIONS={\"a\":\"%s\", \"b\":\"%s\", \"c\":\"%s\", \"d\":\"%s\"}" % (
        quote('1', safe=''), quote('1 + 1', safe=''), quote('prop0', safe=''), quote('$x', safe=''))
    qs += "&FEATURE={\"type\":\"feature\", \"geometry\": {\"type\": \"Point\", \"coordinates\": [102.0, 0.5]}, \"properties\": {\"prop0\": \"value0\"}}"
    # type feature and not Feature error
    rv = client.get(qs, projectfile)
    assert rv.status_code == 400
    assert rv.headers.get('Content-Type', '').find('application/json') == 0

    # Make a request
    qs = "?SERVICE=EXPRESSION&REQUEST=Evaluate&MAP=france_parts.qgs&LAYER=france_parts"
    qs += "&EXPRESSIONS={\"a\":\"%s\", \"b\":\"%s\", \"c\":\"%s\", \"d\":\"%s\"}" % (
        quote('1', safe=''), quote('1 + 1', safe=''), quote('prop0', safe=''), quote('$x', safe=''))
    qs += "&FEATURES=["
    qs += "{\"type\":\"Feature\", \"geometry\": {\"type\": \"Point\", \"coordinates\": [102.0, 0.5]}, \"properties\": {\"prop0\": \"value0\"}}"
    qs += ", "
    qs += "{\"type\":\"Feature\", \"geometry\": {\"type\": \"Point\", \"coordinates\": [105.0, 0.5]}, \"properties\": {\"prop0\": \"value1\"}}"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 400
    assert rv.headers.get('Content-Type', '').find('application/json') == 0


def test_request_without_features(client):
    """  Test Expression Evaluate request without Feature or Features parameter
    """
    projectfile = "france_parts.qgs"

    # Make a request
    qs = "?SERVICE=EXPRESSION&REQUEST=Evaluate&MAP=france_parts.qgs&LAYER=france_parts&EXPRESSION=%s" % (
        quote('1 + 1', safe=''))
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('application/json') == 0

    b = json.loads(rv.content.decode('utf-8'))

    assert 'status' in b
    assert b['status'] == 'success'

    assert 'results' in b
    assert len(b['results']) == 1
    assert '0' in b['results'][0]
    assert b['results'][0]['0'] == 2

    qs = "?SERVICE=EXPRESSION&REQUEST=Evaluate&MAP=france_parts.qgs&LAYER=france_parts&EXPRESSIONS=[\"%s\", \"%s\"]" % (
        quote('1', safe=''), quote('1 + 1', safe=''))
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('application/json') == 0

    b = json.loads(rv.content.decode('utf-8'))

    assert 'status' in b
    assert b['status'] == 'success'

    assert 'results' in b
    assert len(b['results']) == 1
    assert '0' in b['results'][0]
    assert b['results'][0]['0'] == 1
    assert '1' in b['results'][0]
    assert b['results'][0]['1'] == 2

    qs = "?SERVICE=EXPRESSION&REQUEST=Evaluate&MAP=france_parts.qgs&LAYER=france_parts&EXPRESSIONS={\"a\":\"%s\", \"b\":\"%s\"}" % (
        quote('1', safe=''), quote('1 + 1', safe=''))
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('application/json') == 0

    b = json.loads(rv.content.decode('utf-8'))

    assert 'status' in b
    assert b['status'] == 'success'

    assert 'results' in b
    assert len(b['results']) == 1
    assert 'a' in b['results'][0]
    assert b['results'][0]['a'] == 1
    assert 'b' in b['results'][0]
    assert b['results'][0]['b'] == 2


def test_request_with_features(client):
    """  Test Expression Evaluate request with Feature or Features parameter
    """
    projectfile = "france_parts.qgs"

    # Make a request
    qs = "?SERVICE=EXPRESSION&REQUEST=Evaluate&MAP=france_parts.qgs&LAYER=france_parts"
    qs += "&EXPRESSIONS={\"a\":\"%s\", \"b\":\"%s\", \"c\":\"%s\", \"d\":\"%s\"}" % (
        quote('1', safe=''), quote('1 + 1', safe=''), quote('prop0', safe=''), quote('$x', safe=''))
    qs += "&FEATURE={\"type\":\"Feature\", \"geometry\": {\"type\": \"Point\", \"coordinates\": [102.0, 0.5]}, \"properties\": {\"prop0\": \"value0\"}}"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('application/json') == 0

    b = json.loads(rv.content.decode('utf-8'))

    assert 'status' in b
    assert b['status'] == 'success'

    assert 'results' in b
    assert len(b['results']) == 1
    assert 'a' in b['results'][0]
    assert b['results'][0]['a'] == 1
    assert 'b' in b['results'][0]
    assert b['results'][0]['b'] == 2
    assert 'c' in b['results'][0]
    assert b['results'][0]['c'] == 'value0'
    assert 'd' in b['results'][0]
    assert b['results'][0]['d'] == 102.0

    # Make a second request
    qs = "?SERVICE=EXPRESSION&REQUEST=Evaluate&MAP=france_parts.qgs&LAYER=france_parts"
    qs += "&EXPRESSIONS={\"a\":\"%s\", \"b\":\"%s\", \"c\":\"%s\", \"d\":\"%s\"}" % (
        quote('1', safe=''), quote('1 + 1', safe=''), quote('prop0', safe=''), quote('$x', safe=''))
    qs += "&FEATURES=["
    qs += "{\"type\":\"Feature\", \"geometry\": {\"type\": \"Point\", \"coordinates\": [102.0, 0.5]}, \"properties\": {\"prop0\": \"value0\"}}"
    qs += ", "
    qs += "{\"type\":\"Feature\", \"geometry\": {\"type\": \"Point\", \"coordinates\": [105.0, 0.5]}, \"properties\": {\"prop0\": \"value1\"}}"
    qs += "]"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('application/json') == 0

    b = json.loads(rv.content.decode('utf-8'))

    assert 'status' in b
    assert b['status'] == 'success'

    assert 'results' in b
    assert len(b['results']) == 2
    assert 'a' in b['results'][0]
    assert b['results'][0]['a'] == 1
    assert 'b' in b['results'][0]
    assert b['results'][0]['b'] == 2
    assert 'c' in b['results'][0]
    assert b['results'][0]['c'] == 'value0'
    assert 'd' in b['results'][0]
    assert b['results'][0]['d'] == 102.0

    assert 'c' in b['results'][1]
    assert b['results'][1]['c'] == 'value1'
    assert 'd' in b['results'][1]
    assert b['results'][1]['d'] == 105.0


def test_request_with_formscope(client):
    """  Test Expression Evaluate request without Feature or Features and Form_Scope parameters
    """
    projectfile = "france_parts.qgs"

    # Make a request
    qs = "?SERVICE=EXPRESSION&REQUEST=Evaluate&MAP=france_parts.qgs&LAYER=france_parts"
    qs += "&EXPRESSIONS={\"a\":\"%s\", \"b\":\"%s\", \"c\":\"%s\", \"d\":\"%s\"}" % (
        quote('1', safe=''), quote('1 + 1', safe=''), quote("current_value('prop0')", safe=''), quote('$x', safe=''))
    qs += "&FEATURE={\"type\":\"Feature\", \"geometry\": {\"type\": \"Point\", \"coordinates\": [102.0, 0.5]}, \"properties\": {\"prop0\": \"value0\"}}"
    qs += "&FORM_SCOPE=true"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('application/json') == 0

    b = json.loads(rv.content.decode('utf-8'))

    assert 'status' in b
    assert b['status'] == 'success'

    assert 'results' in b
    assert len(b['results']) == 1
    assert 'a' in b['results'][0]
    assert b['results'][0]['a'] == 1
    assert 'b' in b['results'][0]
    assert b['results'][0]['b'] == 2
    assert 'c' in b['results'][0]
    assert b['results'][0]['c'] == 'value0'
    assert 'd' in b['results'][0]
    assert b['results'][0]['d'] == 102.0

    # Make a request without form scope but with current_value function
    qs = "?SERVICE=EXPRESSION&REQUEST=Evaluate&MAP=france_parts.qgs&LAYER=france_parts"
    qs += "&EXPRESSIONS={\"a\":\"%s\", \"b\":\"%s\", \"c\":\"%s\", \"d\":\"%s\"}" % (
        quote('1', safe=''), quote('1 + 1', safe=''), quote("current_value('prop0')", safe=''), quote('$x', safe=''))
    qs += "&FEATURE={\"type\":\"Feature\", \"geometry\": {\"type\": \"Point\", \"coordinates\": [102.0, 0.5]}, \"properties\": {\"prop0\": \"value0\"}}"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('application/json') == 0

    b = json.loads(rv.content.decode('utf-8'))

    assert 'status' in b
    assert b['status'] == 'success'

    assert 'results' in b
    assert len(b['results']) == 1

    assert 'c' in b['results'][0]
    assert b['results'][0]['c'] is None
