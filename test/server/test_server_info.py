import json
import os

__copyright__ = 'Copyright 2021, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


def test_lizmap_server_info(client):
    """Test the Lizmap API for server settings"""
    query = "/lizmap/server.json"
    key = 'QGIS_SERVER_LIZMAP_REVEAL_SETTINGS'

    # The environment variable is already there
    assert os.getenv(key) == 'TRUE'

    # The query must work
    rv = client.get(query)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('application/json') == 0

    json_content = json.loads(rv.content.decode('utf-8'))
    assert 'qgis_server' in json_content

    # Remove the security environment variable, the query mustn't work
    del os.environ[key]
    rv = client.get(query)
    assert rv.status_code == 400

    assert rv.headers.get('Content-Type', '').find('application/json') == 0

    json_content = json.loads(rv.content.decode('utf-8'))
    assert [{'code': 'Bad request error', 'description': 'Invalid request'}] == json_content

    # Reset the environment variable
    os.environ[key] = 'TRUE'
