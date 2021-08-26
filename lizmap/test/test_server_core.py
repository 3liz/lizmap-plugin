"""Test tools."""

import os
import unittest
import xml.etree.ElementTree as ET

from qgis.core import QgsField, QgsFields
from qgis.PyQt.QtCore import QVariant

from lizmap.server.core import (
    get_lizmap_config,
    get_lizmap_layer_login_filter,
    get_lizmap_layers_config,
    server_feature_id_expression,
    to_bool,
)
from lizmap.server.get_feature_info import GetFeatureInfoFilter

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


class TestServerCore(unittest.TestCase):

    def test_config_value_to_boolean(self):
        """ Test convert lizmap config value to boolean """
        true_values = [
            'True', 'true', 'Yes', 'yes', 'T', 't', '1', 1, 1.0, [''], {'a': 'b'}]
        for v in true_values:
            self.assertTrue(to_bool(v), v)

        false_values = [
            'False', 'false', 'NO', 'no', 'F', 'f', '0', 'foobar', 0, 0.0, None, [], {}]
        for v in false_values:
            self.assertFalse(to_bool(v), v)

    def test_get_lizmap_config(self):
        """ Test get the lizmap config based on QGIS project path """
        data_path = os.path.join(os.path.dirname(__file__), 'data')

        qgis_project_path = os.path.join(data_path, 'foobar.qgs')
        self.assertIsNone(get_lizmap_config(qgis_project_path))

        qgis_project_path = os.path.join(data_path, 'lizmap_3_3.qgs')
        self.assertIsNotNone(get_lizmap_config(qgis_project_path))

    def test_get_lizmap_layers_config(self):
        """ Test get layers Lizmap config """

        self.assertIsNone(get_lizmap_layers_config(None))
        self.assertIsNone(get_lizmap_layers_config({}))
        self.assertIsNone(get_lizmap_layers_config({'foo': 'bar'}))

        self.assertIsNone(get_lizmap_layers_config({'layers': 'bar'}))

        cfg_layers = get_lizmap_layers_config({'layers': {'lines-geojson': {'id': 'lines_7ddd81b1_8307_4aa2_8b7a_a0b7983f33e3'}}})
        self.assertIsNotNone(cfg_layers)
        self.assertDictEqual(cfg_layers, {'lines-geojson': {'id': 'lines_7ddd81b1_8307_4aa2_8b7a_a0b7983f33e3'}})

    def test_get_lizmap_layer_login_filter(self):
        """ Test get loginFilteredLayers for layer """

        self.assertIsNone(get_lizmap_layer_login_filter(None, 'lines-geojson'))
        self.assertIsNone(get_lizmap_layer_login_filter({}, 'lines-geojson'))
        self.assertIsNone(get_lizmap_layer_login_filter({'foo': 'bar'}, 'lines-geojson'))

        self.assertIsNone(get_lizmap_layer_login_filter(
            {'loginFilteredLayers': 'bar'},
            'lines-geojson'))
        self.assertIsNone(get_lizmap_layer_login_filter(
            {'loginFilteredLayers': {}},
            'lines-geojson'))
        self.assertIsNone(get_lizmap_layer_login_filter(
            {'loginFilteredLayers': {'lines-geojson': {}}},
            'lines-geojson'))
        self.assertIsNone(get_lizmap_layer_login_filter(
            {
                'loginFilteredLayers': {
                    'lines-geojson': {
                        'layerId': 'lines_7ddd81b1_8307_4aa2_8b7a_a0b7983f33e3'
                    }
                }
            },
            'lines-geojson'))
        self.assertIsNone(get_lizmap_layer_login_filter(
            {
                'loginFilteredLayers': {
                    'lines-geojson': {
                        'layerId': 'lines_7ddd81b1_8307_4aa2_8b7a_a0b7983f33e3',
                        'filterAttribute': 'name'
                    }
                }
            },
            'lines-geojson'))
        self.assertIsNone(get_lizmap_layer_login_filter(
            {
                'loginFilteredLayers': {
                    'lines-geojson': {
                        'layerId': 'lines_7ddd81b1_8307_4aa2_8b7a_a0b7983f33e3',
                        'filterPrivate': 'False'
                    }
                }
            },
            'lines-geojson'))
        self.assertIsNone(get_lizmap_layer_login_filter(
            {
                'loginFilteredLayers': {
                    'lines-geojson': {
                        'filterAttribute': 'name',
                        'filterPrivate': 'False'
                    }
                }
            },
            'lines-geojson'))

        goodDict = {
            'loginFilteredLayers': {
                'lines-geojson': {
                    'layerId': 'lines_7ddd81b1_8307_4aa2_8b7a_a0b7983f33e3',
                    'filterAttribute': 'name',
                    'filterPrivate': 'False',
                    'order': 0
                }
            }
        }

        self.assertIsNone(get_lizmap_layer_login_filter(goodDict, 'foobar'))
        self.assertIsNone(get_lizmap_layer_login_filter(goodDict, None))
        self.assertIsNone(get_lizmap_layer_login_filter(goodDict, 10))

        cfg_layer_login_filter = get_lizmap_layer_login_filter(goodDict, 'lines-geojson')
        self.assertIsNotNone(cfg_layer_login_filter)
        self.assertDictEqual(
            cfg_layer_login_filter,
            {
                'layerId': 'lines_7ddd81b1_8307_4aa2_8b7a_a0b7983f33e3',
                'filterAttribute': 'name',
                'filterPrivate': 'False',
                'order': 0
            })

    def test_parse_xml_get_feature_info(self):
        """ Test to GetFeatureInfo XML. """
        string = '''<GetFeatureInfoResponse>
         <Layer name="qgis_popup">
          <Feature id="1">
           <Attribute name="OBJECTID" value="2662"/>
           <Attribute name="NAME_0" value="France"/>
           <Attribute name="VARNAME_1" value="Bretaa|Brittany"/>
           <Attribute name="Region" value="Bretagne"/>
           <Attribute name="Shape_Leng" value="18.39336934850"/>
           <Attribute name="Shape_Area" value="3.30646936365"/>
           <Attribute name="maptip" value="&lt;p>France&lt;/p>"/>
          </Feature>
         </Layer>
        </GetFeatureInfoResponse>
        '''

        for layer, feature in GetFeatureInfoFilter.parse_xml(string):
            self.assertEqual(layer, 'qgis_popup')
            self.assertEqual(feature, '1')

    def test_edit_xml_get_feature_info_without_maptip(self):
        """ Test to edit a GetFeatureInfo xml without maptip. """
        string = '''<GetFeatureInfoResponse>
         <Layer name="qgis_popup">
          <Feature id="1">
           <Attribute name="OBJECTID" value="2662"/>
           <Attribute name="NAME_0" value="France"/>
           <Attribute name="VARNAME_1" value="Bretaa|Brittany"/>
           <Attribute name="Region" value="Bretagne"/>
           <Attribute name="Shape_Leng" value="18.39336934850"/>
           <Attribute name="Shape_Area" value="3.30646936365"/>
          </Feature>
         </Layer>
        </GetFeatureInfoResponse>
        '''

        response = GetFeatureInfoFilter.append_maptip(string, "qgis_popup", 1, "<b>foo</b>")

        # ElementTree adds a space at the end " />" instead of "/>"
        # maptip line is un-indented from 1 space, with feature on the same line. !!
        expected = '''<GetFeatureInfoResponse>
         <Layer name="qgis_popup">
          <Feature id="1">
           <Attribute name="OBJECTID" value="2662" />
           <Attribute name="NAME_0" value="France" />
           <Attribute name="VARNAME_1" value="Bretaa|Brittany" />
           <Attribute name="Region" value="Bretagne" />
           <Attribute name="Shape_Leng" value="18.39336934850" />
           <Attribute name="Shape_Area" value="3.30646936365" />
          <Attribute name="maptip" value="&lt;b&gt;foo&lt;/b&gt;" /></Feature>
         </Layer>
        </GetFeatureInfoResponse>
        '''
        self.assertEqual(
            ET.tostring(ET.fromstring(expected)).decode("utf-8"),
            ET.tostring(ET.fromstring(response)).decode("utf-8")
        )

    def test_edit_xml_get_feature_info_with_maptip(self):
        """ Test to edit a GetFeatureInfo xml with maptip. """
        string = '''<GetFeatureInfoResponse>
         <Layer name="qgis_popup">
          <Feature id="1">
           <Attribute name="OBJECTID" value="2662"/>
           <Attribute name="NAME_0" value="France"/>
           <Attribute name="VARNAME_1" value="Bretaa|Brittany"/>
           <Attribute name="Region" value="Bretagne"/>
           <Attribute name="Shape_Leng" value="18.39336934850"/>
           <Attribute name="Shape_Area" value="3.30646936365"/>
           <Attribute name="maptip" value="Hello"/>
          </Feature>
         </Layer>
        </GetFeatureInfoResponse>
        '''

        response = GetFeatureInfoFilter.append_maptip(string, "qgis_popup", 1, "<b>foo</b>")

        expected = '''<GetFeatureInfoResponse>
         <Layer name="qgis_popup">
          <Feature id="1">
           <Attribute name="OBJECTID" value="2662" />
           <Attribute name="NAME_0" value="France" />
           <Attribute name="VARNAME_1" value="Bretaa|Brittany" />
           <Attribute name="Region" value="Bretagne" />
           <Attribute name="Shape_Leng" value="18.39336934850" />
           <Attribute name="Shape_Area" value="3.30646936365" />
           <Attribute name="maptip" value="&lt;b&gt;foo&lt;/b&gt;" />
          </Feature>
         </Layer>
        </GetFeatureInfoResponse>
        '''
        self.assertEqual(
            ET.tostring(ET.fromstring(expected)).decode("utf-8"),
            ET.tostring(ET.fromstring(response)).decode("utf-8")
        )

    def test_feature_id_expression(self):
        """ Test the QgsServerFeatureId port from CPP into Python. """
        fields = QgsFields()
        fields.append(QgsField('field_1', type=QVariant.Double))
        fields.append(QgsField('field_2', type=QVariant.Double))

        self.assertEqual(
            "",
            server_feature_id_expression("1", [], fields)
        )
        self.assertEqual(
            "\"field_1\" = '1'",
            server_feature_id_expression("1", ['field_1'], fields)
        )
        self.assertEqual(
            "\"field_1\" = '1' AND \"field_2\" = '2'",
            server_feature_id_expression("1@@2", ['field_1', 'field_2'], fields)
        )
