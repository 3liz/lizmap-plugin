from pathlib import Path

from qgis.core import (
    QgsProject,
    QgsRuleBasedRenderer,
    QgsSymbol,
    QgsVectorLayer,
    QgsWkbTypes,
)

from lizmap.project_checker_tools import (
    _duplicated_label_legend_layer,
    _split_layer_uri,
    authcfg_url_parameters,
    duplicated_layer_with_filter,
    duplicated_layer_with_filter_legend,
    duplicated_rule_key_legend,
    french_geopf_authcfg_url_parameters,
    trailing_layer_group_name,
)
from lizmap.widgets.check_project import Error

from .compat import TestCase


class TestProjectTable(TestCase):
    def test_trailing_spaces(self):
        """Test about trailing spaces in the table."""
        layer = QgsVectorLayer("None?field=field_a:string", " table", "memory")
        project = QgsProject()
        project.addMapLayer(layer)

        results = trailing_layer_group_name(project.layerTreeRoot(), project, [])
        self.assertEqual(1, len(results))
        self.assertIsInstance(results[0], Error)
        self.assertEqual(" table", results[0].source)

    def test_split_uri(self):
        """Test to split a vector layer URI with its filter if needed."""
        self.assertTupleEqual(
            ("/home/path/lines.geojson", "\"name\" = '2 Name'"),
            _split_layer_uri("ogr", "/home/path/lines.geojson|subset=\"name\" = '2 Name'"),
        )

        self.assertTupleEqual(
            ("/home/path/lines.geojson", None), _split_layer_uri("ogr", "/home/path/lines.geojson")
        )

        self.assertTupleEqual(
            (
                "service='lizmapdb' key='gid' estimatedmetadata=true srid=2154 type=Point "
                'checkPrimaryKeyUnicity=\'1\' table="tests_projects"."filter_layer_by_user" (geom)',
                "\"user\" = 'admin'",
            ),
            _split_layer_uri(
                "postgres",
                "service='lizmapdb' key='gid' estimatedmetadata=true srid=2154 type=Point "
                'checkPrimaryKeyUnicity=\'1\' table="tests_projects"."filter_layer_by_user" (geom) '
                "sql=\"user\" = 'admin'",
            ),
        )

        self.assertTupleEqual(
            (
                "service='lizmapdb' key='gid' estimatedmetadata=true srid=2154 type=Point "
                'checkPrimaryKeyUnicity=\'1\' table="tests_projects"."filter_layer_by_user" (geom)',
                None,
            ),
            _split_layer_uri(
                "postgres",
                "service='lizmapdb' key='gid' estimatedmetadata=true srid=2154 type=Point "
                'checkPrimaryKeyUnicity=\'1\' table="tests_projects"."filter_layer_by_user" (geom)',
            ),
        )

    def test_legend_filter_duplicated_layers(self, data: Path):
        """Test duplicated layers with different filters."""
        project_file = str(data.joinpath("duplicated_filter.qgs"))
        project = QgsProject.instance()
        project.read(project_file)
        data = duplicated_layer_with_filter(project)
        self.assertIsInstance(data, dict)
        # We have a single datasource
        self.assertEqual(1, len(data.keys()))
        layer = next(iter(data.keys()))
        self.assertDictEqual(
            {
                "\"name\" = '5 Name'": "half lines filter 5",
                "\"name\" = '4 Name'": "half lines filter 4",
                "\"name\" = '3 Name'": "half lines filter 3",
                "\"name\" = '2 Name'": "half lines filter 2",
                "\"name\" = '1 Name'": "half lines filter 1",
            },
            data[layer],
            data[layer],
        )

    def test_legend_filter_duplicated_layers_legend(self, data: Path):
        """Test duplicated layers with different filters using the legend."""
        project_file = str(data.joinpath("duplicated_filter.qgs"))
        project = QgsProject.instance()
        project.read(project_file)
        data = duplicated_layer_with_filter_legend(project)
        self.assertIsInstance(data, list)
        # We have 3 groups of duplicated layers, even if it is the same datasource
        # +3 icons
        self.assertEqual(3, len(data), data)

        layer = next(iter(data[0].keys()))
        self.assertDictEqual(
            {
                "\"name\" = '1 Name'": "detected lines filter 1",
                "\"name\" = '2 Name'": "detected lines filter 2",
                "_wkb_type": 2,
            },
            data[0][layer],
            data[0][layer],
        )
        layer = next(iter((data[1].keys())))
        self.assertDictEqual(
            {
                "\"name\" = '1 Name'": "half lines filter 1",
                "\"name\" = '2 Name'": "half lines filter 2",
                "_wkb_type": 2,
            },
            data[1][layer],
            data[1][layer],
        )
        layer = next(iter((data[2].keys())))
        self.assertDictEqual(
            {
                "\"name\" = '4 Name'": "half lines filter 4",
                "\"name\" = '5 Name'": "half lines filter 5",
                "_wkb_type": 2,
            },
            data[2][layer],
            data[2][layer],
        )

    def test_rule_key_legend(self, data: Path):
        """Test duplicated rule key in the legend."""
        project_file = str(data.joinpath("rule_key_duplicated.qgs"))
        project = QgsProject.instance()
        project.read(project_file)

        self.assertDictEqual(
            {
                "points_b7228e3a_5092_4ee2_b9e7_e1da96f8a395": {
                    "{007c67f1-3e25-479d-b33b-fac4a0a705b0}": 1,
                    "{cdee1fdb-874c-4265-aa26-5e915d69563f}": 2,
                }
            },
            duplicated_rule_key_legend(project, filter_data=False),
        )

    def test_french_raster_datasource_authcfg(self):
        """Check for authcfg in raster datasource."""
        # other.url.fr
        raster = (
            "contextualWMSLegend=0&amp;crs=EPSG:2154&amp;dpiMode=7&amp;featureCount=10&amp;format=image/jpeg&amp;"
            "layers=SCAN25TOUR_PYR-JPEG_WLD_WM&amp;styles&amp;url=https://other.url.fr/private/wms-r?VERSION%3D1.3.0"
            "&amp;authCFG=x3rzac9"
        )
        self.assertFalse(french_geopf_authcfg_url_parameters(raster))
        self.assertTrue(authcfg_url_parameters(raster))

        # data.GEOPF.fr
        raster = (
            "contextualWMSLegend=0&amp;crs=EPSG:2154&amp;dpiMode=7&amp;featureCount=10&amp;format=image/jpeg&amp;"
            "layers=SCAN25TOUR_PYR-JPEG_WLD_WM&amp;styles&amp;url=https://data.GEOPF.fr/private/wms-r?VERSION%3D1.3.0"
            "&amp;authCFG=x3rzac9"
        )
        self.assertTrue(french_geopf_authcfg_url_parameters(raster))
        self.assertTrue(authcfg_url_parameters(raster))

        # Correct
        raster = (
            "contextualWMSLegend=0&amp;crs=EPSG:2154&amp;dpiMode=7&amp;featureCount=10&amp;format=image/jpeg&amp;"
            "layers=SCAN25TOUR_PYR-JPEG_WLD_WM&amp;styles&amp;url=https://data.geopf.fr/private/wms-r?VERSION%3D1.3.0"
        )
        self.assertFalse(french_geopf_authcfg_url_parameters(raster))
        self.assertFalse(authcfg_url_parameters(raster))

        # http-header
        # raster = (
        #     "IgnoreGetMapUrl=1&amp;crs=CRS:84&amp;dpiMode=7&amp;format=image/png&amp;"
        #     "layers=SCAN25TOUR_PYR-JPEG_WLD_WM&amp;styles&amp;"
        #     "url=https://data.geopf.fr/private/wms-r?VERSION%3D1.3.0&amp;http-header:custom-header"
        # )
        # self.assertTrue(french_geopf_authcfg_url_parameters(raster))

    def test_duplicated_sub_rule(self):
        """Test to detect duplicated sub rules."""
        # noinspection PyTypeChecker
        root_rule = QgsRuleBasedRenderer.Rule(None)

        label = "label"

        # Rule 1 with symbol
        # noinspection PyUnresolvedReferences
        rule_1 = QgsRuleBasedRenderer.Rule(
            QgsSymbol.defaultSymbol(QgsWkbTypes.GeometryType.PointGeometry), label=label + "-1"
        )
        root_rule.appendChild(rule_1)

        # Sub-rule to rule 1
        # noinspection PyTypeChecker
        rule_1_1 = QgsRuleBasedRenderer.Rule(
            QgsSymbol.defaultSymbol(QgsWkbTypes.GeometryType.PointGeometry), label=label
        )
        rule_1.appendChild(rule_1_1)

        # Rule 2 with symbol
        # noinspection PyUnresolvedReferences
        rule_2 = QgsRuleBasedRenderer.Rule(
            QgsSymbol.defaultSymbol(QgsWkbTypes.GeometryType.PointGeometry), label=label + "-2"
        )
        root_rule.appendChild(rule_2)

        # Sub-rule to rule 2
        # noinspection PyTypeChecker
        rule_2_1 = QgsRuleBasedRenderer.Rule(
            QgsSymbol.defaultSymbol(QgsWkbTypes.GeometryType.PointGeometry), label=label
        )
        rule_2.appendChild(rule_2_1)

        # Useful for debugging
        # layer = QgsVectorLayer("Point?field=fldtxt:string", "layer1", "memory")
        # layer.setRenderer(QgsRuleBasedRenderer(root_rule))

        data = _duplicated_label_legend_layer(QgsRuleBasedRenderer(root_rule))
        self.assertDictEqual({"label-1": 1, "label": 2, "label-2": 1}, data)
