import json
import logging
import warnings

LOGGER = logging.getLogger('server')

__copyright__ = 'Copyright 2019, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


def test_no_lizmap_config(client):
    """
    Test Access Control response with a project without
    lizmap config
    """
    projectfile = "france_parts.qgs"

    # Make a request without LIZMAP_USER_GROUPS
    qs = "?SERVICE=WMS&REQUEST=GetCapabilities&MAP=france_parts.qgs"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    layers = rv.xpath('//wms:Layer')
    assert layers is not None
    assert len(layers) == 2

    # Make a request with LIZMAP_USER_GROUPS with 1 group
    qs = "?SERVICE=WMS&REQUEST=GetCapabilities&MAP=france_parts.qgs&LIZMAP_USER_GROUPS=test1"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    layers = rv.xpath('//wms:Layer')
    assert layers is not None
    assert len(layers) == 2

    # Make a request with LIZMAP_USER_GROUPS with 2 groups
    qs = "?SERVICE=WMS&REQUEST=GetCapabilities&MAP=france_parts.qgs&LIZMAP_USER_GROUPS=test1,test2"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    layers = rv.xpath('//wms:Layer')
    assert layers is not None
    assert len(layers) == 2



def test_no_group_visibility(client):
    """
    Test Access Control response with a project with
    lizmap config without a group visibility
    """
    projectfile = "france_parts_liz.qgs"

    # Make a request with LIZMAP_USER_GROUPS
    qs = "?SERVICE=WMS&REQUEST=GetCapabilities&MAP=france_parts_liz.qgs"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    layers = rv.xpath('//wms:Layer')
    assert layers is not None
    assert len(layers) == 2

    # Make a request with LIZMAP_USER_GROUPS with 1 group
    qs = "?SERVICE=WMS&REQUEST=GetCapabilities&MAP=france_parts_liz.qgs&LIZMAP_USER_GROUPS=test1"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    layers = rv.xpath('//wms:Layer')
    assert layers is not None
    assert len(layers) == 2

    # Make a request without LIZMAP_USER_GROUPS with 2 groups
    qs = "?SERVICE=WMS&REQUEST=GetCapabilities&MAP=france_parts_liz.qgs&LIZMAP_USER_GROUPS=test1,test2"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    layers = rv.xpath('//wms:Layer')
    assert layers is not None
    assert len(layers) == 2



def test_group_visibility(client):
    """
    Test Access Control response with a project with
    lizmap config with a group visibility
    """
    projectfile = "france_parts_liz_grp_v.qgs"

    # Make a request with LIZMAP_USER_GROUPS
    qs = "?SERVICE=WMS&REQUEST=GetCapabilities&MAP=france_parts_liz_grp_v.qgs"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    layers = rv.xpath('//wms:Layer')
    assert layers is not None
    assert len(layers) == 2

    # Make a request with LIZMAP_USER_GROUPS with 1 group not authorized
    qs = "?SERVICE=WMS&REQUEST=GetCapabilities&MAP=france_parts_liz_grp_v.qgs&LIZMAP_USER_GROUPS=test1"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    layers = rv.xpath('//wms:Layer')
    assert layers is not None
    assert len(layers) == 1

    # Make a request with LIZMAP_USER_GROUPS with 1 group authorized
    qs = "?SERVICE=WMS&REQUEST=GetCapabilities&MAP=france_parts_liz_grp_v.qgs&LIZMAP_USER_GROUPS=test2"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    layers = rv.xpath('//wms:Layer')
    assert layers is not None
    assert len(layers) == 2

    # Make a request without LIZMAP_USER_GROUPS with 2 groups which 1 is authorized
    qs = "?SERVICE=WMS&REQUEST=GetCapabilities&MAP=france_parts_liz_grp_v.qgs&LIZMAP_USER_GROUPS=test1,test2"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    layers = rv.xpath('//wms:Layer')
    assert layers is not None
    assert len(layers) == 2

    # Make a request with LIZMAP_USER_GROUPS with anonymous group not authorized
    qs = "?SERVICE=WMS&REQUEST=GetCapabilities&MAP=france_parts_liz_grp_v.qgs&LIZMAP_USER_GROUPS="
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    layers = rv.xpath('//wms:Layer')
    assert layers is not None
    assert len(layers) == 1


def test_group_visibility_headers(client):
    """
    Test Access Control response with a project with
    lizmap config with a group visibility
    and groups provided in headers
    """
    projectfile = "france_parts_liz_grp_v.qgs"

    # Make a request without LIZMAP_USER_GROUPS
    qs = "?SERVICE=WMS&REQUEST=GetCapabilities&MAP=france_parts_liz_grp_v.qgs"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    layers = rv.xpath('//wms:Layer')
    assert layers is not None
    assert len(layers) == 2

    # Make a request with LIZMAP_USER_GROUPS with 1 group not authorized
    headers = {'X-Lizmap-User-Groups': 'test1'}
    rv = client.get(qs, projectfile, headers)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    layers = rv.xpath('//wms:Layer')
    assert layers is not None
    assert len(layers) == 1

    # Make a request with LIZMAP_USER_GROUPS with 1 group authorized
    headers = {'X-Lizmap-User-Groups': 'test2'}
    rv = client.get(qs, projectfile, headers)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    layers = rv.xpath('//wms:Layer')
    assert layers is not None
    assert len(layers) == 2

    # Make a request with LIZMAP_USER_GROUPS with 2 groups which 1 is authorized
    headers = {'X-Lizmap-User-Groups': 'test1,test2'}
    rv = client.get(qs, projectfile, headers)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    layers = rv.xpath('//wms:Layer')
    assert layers is not None
    assert len(layers) == 2

    # Make a request with LIZMAP_USER_GROUPS with anonymous group not authorized
    headers = {'X-Lizmap-User-Groups': ''}
    rv = client.get(qs, projectfile, headers)
    assert rv.status_code == 200

    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    layers = rv.xpath('//wms:Layer')
    assert layers is not None
    assert len(layers) == 1


def test_layer_filter_login(client):

    # Project without config
    projectfile = "france_parts.qgs"

    qs = "?SERVICE=WFS&REQUEST=GetCapabilities&MAP=france_parts.qgs"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200

    qs = "?SERVICE=WFS&REQUEST=GetFeature&MAP=france_parts.qgs&TYPENAME=france_parts"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    layers = rv.xpath('//gml:featureMember')
    assert layers is not None
    assert len(layers) == 4

    headers = {'X-Lizmap-User-Groups': 'Bretagne'}
    rv = client.get(qs, projectfile, headers)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    layers = rv.xpath('//gml:featureMember')
    assert layers is not None
    assert len(layers) == 4

    headers = {'X-Lizmap-User-Groups': 'test1', 'X-Lizmap-User': 'Bretagne'}
    rv = client.get(qs, projectfile, headers)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    layers = rv.xpath('//gml:featureMember')
    assert layers is not None
    assert len(layers) == 4

    # Project with config but without login filter
    projectfile = "france_parts_liz.qgs"

    qs = "?SERVICE=WFS&REQUEST=GetFeature&MAP=france_parts_liz.qgs&TYPENAME=france_parts"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    layers = rv.xpath('//gml:featureMember')
    assert layers is not None
    assert len(layers) == 4

    headers = {'X-Lizmap-User-Groups': 'Bretagne'}
    rv = client.get(qs, projectfile, headers)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    layers = rv.xpath('//gml:featureMember')
    assert layers is not None
    assert len(layers) == 4

    headers = {'X-Lizmap-User-Groups': 'test1', 'X-Lizmap-User': 'Bretagne'}
    rv = client.get(qs, projectfile, headers)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    layers = rv.xpath('//gml:featureMember')
    assert layers is not None
    assert len(layers) == 4

    # Project with config with group filter
    projectfile = "france_parts_liz_filter_group.qgs"

    qs = "?SERVICE=WFS&REQUEST=GetFeature&MAP=france_parts_liz_filter_group.qgs&TYPENAME=france_parts"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    layers = rv.xpath('//gml:featureMember')
    assert layers is not None
    assert len(layers) == 4

    headers = {'X-Lizmap-User-Groups': 'Bretagne'}
    rv = client.get(qs, projectfile, headers)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    layers = rv.xpath('//gml:featureMember')
    assert layers is not None
    assert len(layers) == 1

    headers = {'X-Lizmap-User-Groups': 'Bretagne, Centre, test1'}
    rv = client.get(qs, projectfile, headers)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    layers = rv.xpath('//gml:featureMember')
    assert layers is not None
    assert len(layers) == 2

    headers = {'X-Lizmap-User-Groups': 'test1', 'X-Lizmap-User': 'Bretagne'}
    rv = client.get(qs, projectfile, headers)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    layers = rv.xpath('//gml:featureMember')
    assert layers is not None
    assert len(layers) == 0

    # Project with config with login filter
    projectfile = "france_parts_liz_filter_login.qgs"

    qs = "?SERVICE=WFS&REQUEST=GetFeature&MAP=france_parts_liz_filter_login.qgs&TYPENAME=france_parts"
    rv = client.get(qs, projectfile)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    layers = rv.xpath('//gml:featureMember')
    assert layers is not None
    assert len(layers) == 4

    headers = {'X-Lizmap-User-Groups': 'test1', 'X-Lizmap-User': 'Bretagne'}
    rv = client.get(qs, projectfile, headers)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    layers = rv.xpath('//gml:featureMember')
    assert layers is not None
    assert len(layers) == 1

    headers = {'X-Lizmap-User-Groups': 'Bretagne, Centre, test1', 'X-Lizmap-User': 'test'}
    rv = client.get(qs, projectfile, headers)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type', '').find('text/xml') == 0

    layers = rv.xpath('//gml:featureMember')
    assert layers is not None
    assert len(layers) == 0
