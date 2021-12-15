import json

__copyright__ = 'Copyright 2021, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


def test_lizmap_server_info(client):
    """Test the Lizmap API for server settings"""
    qs = "/lizmap/server.json"
    rv = client.get(qs)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('application/json') == 0

    json_content = json.loads(rv.content.decode('utf-8'))
    assert 'qgis_server' in json_content
