import logging

LOGGER = logging.getLogger('server')

__copyright__ = 'Copyright 2019, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


def test_no_lizmap_config(client):
    """
    Test Filter response with a project without
    lizmap config
    """
    projectfile = "france_parts.qgs"

    # Make a request without LIZMAP_USER_GROUPS
    qs = "?SERVICE=WMS&REQUEST=GetCapabilities&MAP=france_parts.qgs"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    # Make a request with LIZMAP_USER_GROUPS with 1 group
    qs = "?SERVICE=WMS&REQUEST=GetCapabilities&MAP=france_parts.qgs&LIZMAP_USER_GROUPS=test1"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('text/xml') == 0


def test_no_acl(client):
    """
    Test Filter response with a project with
    a lizmap config without acl
    """
    projectfile = "france_parts_liz.qgs"

    # Make a request without LIZMAP_USER_GROUPS
    qs = "?SERVICE=WMS&REQUEST=GetCapabilities&MAP=france_parts_liz.qgs"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    # Make a request with LIZMAP_USER_GROUPS with 1 group
    qs = "?SERVICE=WMS&REQUEST=GetCapabilities&MAP=france_parts.qgs&LIZMAP_USER_GROUPS=test1"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('text/xml') == 0


def test_acl(client):
    """
    Test Filter response with a project wit
    a lizmap config with acl
    """
    projectfile = "france_parts_liz_acl.qgs"

    # Make a request without LIZMAP_USER_GROUPS
    qs = "?SERVICE=WMS&REQUEST=GetCapabilities&MAP=france_parts_liz_acl.qgs"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    # Make a request with LIZMAP_USER_GROUPS with 1 group not authorized
    qs = "?SERVICE=WMS&REQUEST=GetCapabilities&MAP=france_parts.qgs&LIZMAP_USER_GROUPS=test1"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 403

    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    # Make a request with LIZMAP_USER_GROUPS with 1 group authorized
    qs = "?SERVICE=WMS&REQUEST=GetCapabilities&MAP=france_parts.qgs&LIZMAP_USER_GROUPS=test2"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    # Make a request with LIZMAP_USER_GROUPS with 2 groups which 1 is authorized
    qs = "?SERVICE=WMS&REQUEST=GetCapabilities&MAP=france_parts.qgs&LIZMAP_USER_GROUPS=test1,test2"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    # Make a request with LIZMAP_USER_GROUPS with anonymous group not authorized
    qs = "?SERVICE=WMS&REQUEST=GetCapabilities&MAP=france_parts.qgs&LIZMAP_USER_GROUPS="
    rv = client.get(qs, projectfile)
    assert rv.status_code == 403

    assert rv.headers.get('Content-Type', '').find('text/xml') == 0


def test_acl_headers(client):
    """
    Test Filter response with a project wit
    a lizmap config with acl and Lizmap groups in request headers
    """
    projectfile = "france_parts_liz_acl.qgs"

    # Make a request without LIZMAP_USER_GROUPS
    qs = "?SERVICE=WMS&REQUEST=GetCapabilities&MAP=france_parts_liz_acl.qgs"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    # Make a request with LIZMAP_USER_GROUPS with 1 group not authorized
    headers = {'X-Lizmap-User-Groups': 'test1'}
    rv = client.get(qs, projectfile, headers)
    assert rv.status_code == 403

    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    # Make a request with LIZMAP_USER_GROUPS with 1 group authorized
    headers = {'X-Lizmap-User-Groups': 'test2'}
    rv = client.get(qs, projectfile, headers)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    # Make a request with LIZMAP_USER_GROUPS with 2 groups which 1 is authorized
    headers = {'X-Lizmap-User-Groups': 'test1,test2'}
    rv = client.get(qs, projectfile, headers)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    # Make a request with LIZMAP_USER_GROUPS with anonymous group not authorized
    headers = {'X-Lizmap-User-Groups': ''}
    rv = client.get(qs, projectfile, headers)
    assert rv.status_code == 403

    assert rv.headers.get('Content-Type', '').find('text/xml') == 0
