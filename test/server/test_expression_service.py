import json


__copyright__ = 'Copyright 2019, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


def test_request_unknown(client):
    """  Test Expression service with an unknown request
    """
    projectfile = "france_parts.qgs"

    # Make a request
    qs = "?SERVICE=EXPRESSION&REQUEST=UNKNOWN_REQUEST&MAP=france_parts.qgs"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 400

    assert rv.headers.get('Content-Type', '').find('application/json') == 0

    b = json.loads(rv.content.decode('utf-8'))

    assert ('status' in b)
    assert b['status'] == 'fail'

    assert ('code' in b)
    assert ('message' in b)
