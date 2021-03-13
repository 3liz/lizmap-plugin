"""Test tools."""

import os
import unittest

from lizmap.server.core import (
    config_value_to_boolean,
    get_lizmap_config,
    get_lizmap_layer_login_filter,
    get_lizmap_layers_config,
)

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


class TestTools(unittest.TestCase):

    def test_config_value_to_boolean(self):
        """ Test convert lizmap config value to boolean """

        trueValues = ['True', 'true', 'Yes', 'yes', 'T', 't', '1',
                      1, 1.0, [''], {'a': 'b'}]
        for v in trueValues:
            self.assertTrue(config_value_to_boolean(v))

        falseValues = ['False', 'false', 'NO', 'no', 'F', 'f', '0', 'foobar',
                       0, 0.0, None, [], {}]
        for v in falseValues:
            self.assertFalse(config_value_to_boolean(v))

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
