"""Test tooltip."""
from qgis.core import (
    QgsVectorLayer,
    QgsProject,
    QgsEditFormConfig,
    QgsExpression, QgsFeature, QgsExpressionContext, QgsExpressionContextUtils)
from qgis.gui import QgsExternalResourceWidget
from qgis.testing import unittest, start_app


start_app()


from ..qgis_plugin_tools.tools.resources import plugin_test_data_path
from ..tooltip import Tooltip

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


class TestToolTip(unittest.TestCase):

    def setUp(self) -> None:
        self.layer = QgsVectorLayer('None?field=field_a:string', 'table', 'memory')

        self.context = QgsExpressionContext()
        self.context.appendScope(QgsExpressionContextUtils.layerScope(self.layer))

    def test_value_map(self):
        """Test we can generate value map."""
        widget_config = {
            'map': [
                {
                    'a': 'A',
                    'b': 'B',
                }
            ]
        }
        result = Tooltip._generate_value_map(widget_config, 'field_a')
        expected = '''
map_get(
    hstore_to_map('"a"=>"A","b"=>"B"'),
    "field_a"
)'''
        self.assertEqual(result, expected)

        feature = QgsFeature()
        feature.setAttributes(['a'])
        self.layer.dataProvider().addFeatures([feature])

        expression = QgsExpression(result)
        self.assertFalse(expression.hasParserError())

        expression.prepare(self.context)
        self.context.setFeature(next(self.layer.getFeatures()))
        self.assertFalse(expression.hasEvalError())
        self.assertEqual(expression.evaluate(self.context), 'A')

    def test_date(self):
        """Test we can generate date."""
        widget_config = {
            'display_format': 'yyyy',
        }
        result = Tooltip._generate_date(widget_config, 'field_a')
        expected = '''
format_date(
    "field_a",
    'yyyy'
)'''

        self.assertEqual(result, expected)

        feature = QgsFeature()
        feature.setAttributes(['2012-05-15'])
        self.layer.dataProvider().addFeatures([feature])

        expression = QgsExpression(result)
        self.assertFalse(expression.hasParserError())

        expression.prepare(self.context)
        self.context.setFeature(next(self.layer.getFeatures()))
        self.assertFalse(expression.hasEvalError())
        self.assertEqual(expression.evaluate(self.context), '2012')

    def test_external_resource_web(self):
        """Test we can generate external resource for web."""
        widget_config = {
            'DocumentViewer': QgsExternalResourceWidget.Web,
        }
        result = Tooltip._generate_external_resource(widget_config, 'field_a', 'fname')
        expected = '''
concat(
   '<a href="',
   "field_a",
   '" target="_blank">
   ',
   '
   <iframe src="',
   "field_a",
   '" width="100%" height="300" title="fname"/>',
   '
   </a>'
)'''
        self.assertEqual(result, expected)

        feature = QgsFeature()
        feature.setAttributes(['test.pdf'])
        self.layer.dataProvider().addFeatures([feature])

        expression = QgsExpression(result)
        self.assertFalse(expression.hasParserError())

        expression.prepare(self.context)
        self.context.setFeature(next(self.layer.getFeatures()))
        self.assertFalse(expression.hasEvalError())
        expected = '<a href="test.pdf" target="_blank">      <iframe src="test.pdf" width="100%" height="300" title="fname"/>   </a>'
        result = expression.evaluate(self.context)
        result = result.replace('\n', '').replace('\r', '')
        self.assertEqual(expected, result)

    def test_external_resource_image(self):
        """Test we can generate external resource for an image."""
        widget_config = {
            'DocumentViewer': QgsExternalResourceWidget.Image,
        }
        result = Tooltip._generate_external_resource(widget_config, 'field_a', 'fname')
        expected = '''
concat(
   '<a href="',
   "field_a",
   '" target="_blank">',
   '
   <img src="',
   "field_a",
   '" width="100%" title="fname">',
   '
   </a>'
)'''
        self.assertEqual(result, expected)

        feature = QgsFeature()
        feature.setAttributes(['test.png'])
        self.layer.dataProvider().addFeatures([feature])

        expression = QgsExpression(result)
        self.assertFalse(expression.hasParserError())

        expression.prepare(self.context)
        self.context.setFeature(next(self.layer.getFeatures()))
        self.assertFalse(expression.hasEvalError())
        expected = '<a href="test.png" target="_blank">   <img src="test.png" width="100%" title="fname">   </a>'
        result = expression.evaluate(self.context)
        result = result.replace('\n', '').replace('\r', '')
        self.assertEqual(expected, result)

    def test_external_resource_no_content(self):
        """Test we can generate external resource for no content."""
        widget_config = {
            'DocumentViewer': QgsExternalResourceWidget.NoContent,
        }
        result = Tooltip._generate_external_resource(widget_config, 'field_a', 'fname')
        expected = '''
concat(
   '<a href="',
   "field_a",
   '" target="_blank">fname</a>'
)'''
        self.assertEqual(result, expected)

        feature = QgsFeature()
        feature.setAttributes(['test.png'])
        self.layer.dataProvider().addFeatures([feature])

        expression = QgsExpression(result)
        self.assertFalse(expression.hasParserError())

        expression.prepare(self.context)
        self.context.setFeature(next(self.layer.getFeatures()))
        self.assertFalse(expression.hasEvalError())
        expected = '<a href="test.png" target="_blank">fname</a>'
        result = expression.evaluate(self.context)
        result = result.replace('\n', '').replace('\r', '')
        self.assertEqual(expected, result)

    def test_value_relation(self):
        """Test we can generate a value relation."""
        widget_config = {
            'Key': 'key',
            'Layer': 'layer_id',
            'FilterExpression': 'filter_expression',
            'Value': 'value',
        }
        result = Tooltip._generate_value_relation(widget_config, 'foo')
        expected = '''
aggregate(
    layer:='layer_id',
    aggregate:='concatenate',
    expression:="value",
    filter:="key" = attribute(@parent, 'foo') AND filter_expression
)
        '''
        self.assertEqual(result, expected)
        expression = QgsExpression(result)
        self.assertFalse(expression.hasParserError())

        widget_config['FilterExpression'] = ''
        result = Tooltip._generate_value_relation(widget_config, 'foo')
        expected = '''
aggregate(
    layer:='layer_id',
    aggregate:='concatenate',
    expression:="value",
    filter:="key" = attribute(@parent, 'foo')
)
        '''
        self.assertEqual(result, expected)
        expression = QgsExpression(result)
        self.assertFalse(expression.hasParserError())

    def test_tooltip_layer(self):
        """Test tooltip on a layer."""
        layer = QgsVectorLayer(plugin_test_data_path('complex_form.geojson'), 'form', 'ogr')
        QgsProject.instance().addMapLayer(layer)
        self.assertTrue(layer.isValid())

        config = layer.editFormConfig()
        self.assertEqual(config.layout(), QgsEditFormConfig.TabLayout)

        root = config.invisibleRootContainer()
        html_content = Tooltip.create_popup_node_item_from_form(
            layer, root, 0, [], '', QgsProject.instance().relationManager())

        self.maxDiff = None
        expected = '''
<ul class="nav nav-tabs">

    <li class="active"><a href="#popup_dd_tab_1" data-toggle="tab">tab 1</a></li>

    <li class=""><a href="#popup_dd_tab2" data-toggle="tab">tab2</a></li>
</ul>
<div class="tab-content">
  <div id="popup_dd_tab_1" class="tab-pane active">
    
            [% CASE
                WHEN "name" IS NOT NULL OR trim("name") != ''
                THEN concat(
                    '<p>', '<b>name</b>',
                    '<div class="field">', 
map_get(
    hstore_to_map('"A"=>"a"'),
    "name"
), '</div>',
                    '</p>'
                )
                ELSE ''
            END %]
            
    
            [% CASE
                WHEN "name" IS NOT NULL OR trim("name") != ''
                THEN concat(
                    '<p>', '<b>name</b>',
                    '<div class="field">', 
map_get(
    hstore_to_map('"A"=>"a"'),
    "name"
), '</div>',
                    '</p>'
                )
                ELSE ''
            END %]
            
    
            [% CASE
                WHEN "name" IS NOT NULL OR trim("name") != ''
                THEN concat(
                    '<p>', '<b>name</b>',
                    '<div class="field">', 
map_get(
    hstore_to_map('"A"=>"a"'),
    "name"
), '</div>',
                    '</p>'
                )
                ELSE ''
            END %]
            
  </div>

  <div id="popup_dd_tab2" class="tab-pane ">
    
            [% CASE
                WHEN "name" IS NOT NULL OR trim("name") != ''
                THEN concat(
                    '<p>', '<b>name</b>',
                    '<div class="field">', 
map_get(
    hstore_to_map('"A"=>"a"'),
    "name"
), '</div>',
                    '</p>'
                )
                ELSE ''
            END %]
            
  </div>
</div>
'''.strip()

        self.assertEqual(expected, html_content)
