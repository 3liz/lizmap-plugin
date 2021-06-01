import logging

LOGGER = logging.getLogger('server')

__copyright__ = 'Copyright 2021, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

PROJECT = "get_feature_info.qgs"
BBOX = "48.331869%2C-2.847776%2C48.971191%2C-0.659558"
BASE_QUERY = (
    f"?MAP={PROJECT}&"
    f"STYLES=d%C3%A9faut&"
    f"SERVICE=WMS&"
    f"VERSION=1.3.0"
    f"&REQUEST=GetFeatureInfo&"
    f"EXCEPTIONS=application%2Fvnd.ogc.se_inimage&"
    f"BBOX={BBOX}&"
    f"FI_POINT_TOLERANCE=25&"
    f"FI_LINE_TOLERANCE=10&"
    f"FI_POLYGON_TOLERANCE=5&"
    f"FEATURE_COUNT=10&"
    f"HEIGHT=537&"
    f"WIDTH=1838&"
    f"FORMAT=image%2Fpng&"
    f"CRS=EPSG%3A4326&"
    f"INFO_FORMAT=text%2Fhtml&"
)

# Points
NO_FEATURE = "I=817&J=87&"
SINGLE_FEATURE = "I=1435&J=398&"

# Layers
LAYER_DEFAULT_POPUP = "default_popup"
DEFAULT_POPUP = f"LAYERS={LAYER_DEFAULT_POPUP}&QUERY_LAYERS={LAYER_DEFAULT_POPUP}&"

LAYER_QGIS_POPUP = "qgis_popup"
QGIS_POPUP = f"LAYERS={LAYER_QGIS_POPUP}&QUERY_LAYERS={LAYER_QGIS_POPUP}&"


def test_no_get_feature_info_default_popup(client):
    """ Test the get feature info without a feature with default layer. """
    qs = BASE_QUERY + NO_FEATURE + DEFAULT_POPUP
    rv = client.get(qs, PROJECT)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type', '').find('text/html') == 0
    expected = f'''<HEAD>
<TITLE> GetFeatureInfo results </TITLE>
<META http-equiv="Content-Type" content="text/html;charset=utf-8"/>
</HEAD>
<BODY>
<TABLE border=1 width=100%>
<TR><TH width=25%>Layer</TH><TD>{LAYER_DEFAULT_POPUP}</TD></TR>
</BR></TABLE>
<BR></BR>
</BODY>
'''
    assert rv.content.decode('utf-8') == expected


def test_single_get_feature_info_default_popup(client):
    """ Test the get feature info with a single feature with default layer. """
    qs = BASE_QUERY + SINGLE_FEATURE + DEFAULT_POPUP
    rv = client.get(qs, PROJECT)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type', '').find('text/html') == 0
    expected = f'''<HEAD>
<TITLE> GetFeatureInfo results </TITLE>
<META http-equiv="Content-Type" content="text/html;charset=utf-8"/>
</HEAD>
<BODY>
<TABLE border=1 width=100%>
<TR><TH width=25%>Layer</TH><TD>{LAYER_DEFAULT_POPUP}</TD></TR>
</BR><TABLE border=1 width=100%>
<TR><TH>Feature</TH><TD>1</TD></TR>
<TR><TH>OBJECTID</TH><TD>2662</TD></TR>
<TR><TH>NAME_0</TH><TD>France</TD></TR>
<TR><TH>VARNAME_1</TH><TD>Bretaa|Brittany</TD></TR>
<TR><TH>Region</TH><TD>Bretagne</TD></TR>
<TR><TH>Shape_Leng</TH><TD>18.39336934850</TD></TR>
<TR><TH>Shape_Area</TH><TD>3.30646936365</TD></TR>
</TABLE>
</BR>
</TABLE>
<BR></BR>
</BODY>
'''
    assert rv.content.decode('utf-8') == expected


def test_single_get_feature_info_qgis_popup(client):
    """ Test the get feature info with a single feature with QGIS maptip. """
    qs = BASE_QUERY + SINGLE_FEATURE + QGIS_POPUP + "WITH_MAPTIP=true&"
    rv = client.get(qs, PROJECT)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type', '').find('text/html') == 0

    # Note the line <TH>maptip</TH>
    expected = f'''<HEAD>
<TITLE> GetFeatureInfo results </TITLE>
<META http-equiv="Content-Type" content="text/html;charset=utf-8"/>
</HEAD>
<BODY>
<TABLE border=1 width=100%>
<TR><TH width=25%>Layer</TH><TD>{LAYER_QGIS_POPUP}</TD></TR>
</BR><TABLE border=1 width=100%>
<TR><TH>Feature</TH><TD>1</TD></TR>
<TR><TH>OBJECTID</TH><TD>2662</TD></TR>
<TR><TH>NAME_0</TH><TD>France</TD></TR>
<TR><TH>VARNAME_1</TH><TD>Bretaa|Brittany</TD></TR>
<TR><TH>Region</TH><TD>Bretagne</TD></TR>
<TR><TH>Shape_Leng</TH><TD>18.39336934850</TD></TR>
<TR><TH>Shape_Area</TH><TD>3.30646936365</TD></TR>
<TR><TH>maptip</TH><TD><p>France</p></TD></TR>
</TABLE>
</BR>
</TABLE>
<BR></BR>
</BODY>
'''
    assert rv.content.decode('utf-8') == expected
