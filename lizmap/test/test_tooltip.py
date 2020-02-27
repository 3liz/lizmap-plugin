"""Test tooltip."""
from qgis.core import (
    QgsVectorLayer,
    QgsProject,
    QgsEditFormConfig,
    QgsExpression,
    QgsFeature,
    QgsExpressionContext,
    QgsExpressionContextUtils,
    QgsAttributeEditorContainer,
    QgsOptionalExpression,
    QgsAttributeEditorField)
from qgis.gui import QgsExternalResourceWidget
from qgis.testing import unittest, start_app


start_app()


from .qgis_plugin_tools import plugin_test_data_path
from .tooltip import Tooltip

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


class TestToolTip(unittest.TestCase):

    def check_layer_context(self, field_value, expression, expected):
        layer = QgsVectorLayer('None?field=field_a:string', 'table', 'memory')

        feature = QgsFeature()
        feature.setAttributes([field_value])

        context = QgsExpressionContext()
        context.appendScope(QgsExpressionContextUtils.layerScope(layer))
        context.setFeature(feature)

        expression = QgsExpression(expression)
        self.assertFalse(expression.hasParserError())

        expression.prepare(context)
        self.assertFalse(expression.hasEvalError())
        self.assertEqual(expected, expression.evaluate(context))

    def test_field_name(self):
        """Test we can generate the field name correctly."""
        template = Tooltip._generate_field_name('field_a', 'Field Name', '\'foo\'')

        expected = '''
                    [% CASE
                        WHEN "field_a" IS NOT NULL OR trim("field_a") != ''
                        THEN concat(
                            '<p>', '<b>Field Name</b>',
                            '<div class="field">', 'foo', '</div>',
                            '</p>'
                        )
                        ELSE ''
                    END %]'''
        self.assertEqual(expected, template)

        layer = QgsVectorLayer('None?field=field_a:string', 'table', 'memory')
        sub_context = QgsExpressionContext()
        sub_context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(layer))
        feature = QgsFeature()
        feature.setAttributes(['a'])
        layer.dataProvider().addFeatures([feature])
        sub_context.setFeature(next(layer.getFeatures()))
        expression = QgsExpression().replaceExpressionText(template, sub_context)
        self.assertEqual('\n                    <p><b>Field Name</b><div class="field">foo</div></p>', expression)

    def test_relation_reference(self):
        """Test we can generate a relation reference."""
        result = Tooltip._generate_relation_reference('name', 'parent_pk', 'layer_id', 'display_expression')
        expected = '''
                    aggregate(
                        layer:='layer_id',
                        aggregate:='concatenate',
                        expression:=display_expression,
                        filter:=
                    "parent_pk" = attribute(@parent, 'name')
                
                    )'''
        self.assertEqual(expected, result)

    def test_value_map(self):
        """Test we can generate value map."""
        widget_config = {
            'map': [
                {
                    'a': 'A',
                }, {
                    'b': 'B',
                }, {
                    '<NULL>': '{2839923C-8B7D-419E-B84B-CA2FE9B80EC7}',
                }
            ]
        }
        expression = Tooltip._generate_value_map(widget_config, 'field_a')
        expected = '''
                    map_get(
                        hstore_to_map('"a"=>"A","b"=>"B"'),
                        "field_a"
                    )'''
        self.assertEqual(expected, expression)
        self.check_layer_context('a', expression, 'A')

    def test_date(self):
        """Test we can generate date."""
        widget_config = {
            'display_format': 'yyyy',
        }
        expression = Tooltip._generate_date(widget_config, 'field_a')
        expected = '''
                    format_date(
                        "field_a",
                        'yyyy'
                    )'''
        self.assertEqual(expected, expression)
        self.check_layer_context('2012-05-15', expression, '2012')

    def test_external_resource_web(self):
        """Test we can generate external resource for web."""
        widget_config = {
            'DocumentViewer': QgsExternalResourceWidget.Web,
        }
        expression = Tooltip._generate_external_resource(widget_config, 'field_a', 'fname')
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
        self.assertEqual(expression, expected)

        expected = '''<a href="test.pdf" target="_blank">
                       
                       <iframe src="test.pdf" width="100%" height="300" title="fname"/>
                       </a>'''
        self.check_layer_context('test.pdf', expression, expected)

    def test_external_resource_image(self):
        """Test we can generate external resource for an image."""
        widget_config = {
            'DocumentViewer': QgsExternalResourceWidget.Image,
        }
        expression = Tooltip._generate_external_resource(widget_config, 'field_a', 'fname')
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
        self.assertEqual(expression, expected)

        expected = '''<a href="test.png" target="_blank">
                       <img src="test.png" width="100%" title="fname">
                       </a>'''
        self.check_layer_context('test.png', expression, expected)

    def test_external_resource_no_content(self):
        """Test we can generate external resource for no content."""
        widget_config = {
            'DocumentViewer': QgsExternalResourceWidget.NoContent,
        }
        expression = Tooltip._generate_external_resource(widget_config, 'field_a', 'fname')
        expected = '''
                    concat(
                        '<a href="',
                        "field_a",
                        '" target="_blank">fname</a>'
                    )'''
        self.assertEqual(expected, expression)

        expected = '<a href="test.png" target="_blank">fname</a>'
        self.check_layer_context('test.png', expression, expected)

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
                    )'''
        self.assertEqual(expected, result)
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
                    )'''
        self.assertEqual(expected, result)
        expression = QgsExpression(result)
        self.assertFalse(expression.hasParserError())

    def test_layer_non_existing_field(self):
        """Test we do not generate for non existing fields."""
        layer = QgsVectorLayer('None?field=field_a:string', 'table', 'memory')

        feature = QgsFeature()
        feature.setAttributes(['a'])
        layer.dataProvider().addFeatures([feature])

        config = layer.editFormConfig()
        config.setLayout(QgsEditFormConfig.TabLayout)
        config.clearTabs()

        root = config.invisibleRootContainer()

        tab_1 = QgsAttributeEditorContainer('tab1', root)
        config.addTab(tab_1)

        html_content = Tooltip.create_popup_node_item_from_form(
            layer, root, 0, [], '', QgsProject.instance().relationManager())

        expected = '''<ul class="nav nav-tabs">

    <li class="active"><a href="#popup_dd_tab1" data-toggle="tab">tab1</a></li>
</ul>
<div class="tab-content">
  <div id="popup_dd_tab1" class="tab-pane active">
  </div>
</div>'''
        self.assertEqual(expected, html_content)

        tab_1.addChildElement(QgsAttributeEditorField('fake_field', -1, tab_1))

        html_content = Tooltip.create_popup_node_item_from_form(
            layer, root, 0, [], '', QgsProject.instance().relationManager())

        self.assertEqual(expected, html_content)

    @unittest.skip
    def test_display_group(self):
        """Test we can hide some groups."""
        layer = QgsVectorLayer('None?field=field_a:string', 'table', 'memory')

        config = layer.editFormConfig()
        config.setLayout(QgsEditFormConfig.TabLayout)
        config.clearTabs()

        root = config.invisibleRootContainer()

        tab_1 = QgsAttributeEditorContainer('tab1', root)
        config.addTab(tab_1)

        tab_2 = QgsAttributeEditorContainer('tab2', root)
        config.addTab(tab_2)

        html_content = Tooltip.create_popup_node_item_from_form(
            layer, root, 0, [], '', QgsProject.instance().relationManager())

        expected = '''<ul class="nav nav-tabs">

    <li class="active"><a href="#popup_dd_tab1" data-toggle="tab">tab1</a></li>

    <li class=""><a href="#popup_dd_tab2" data-toggle="tab">tab2</a></li>
</ul>
<div class="tab-content">
  <div id="popup_dd_tab1" class="tab-pane active">
  </div>

  <div id="popup_dd_tab2" class="tab-pane ">
  </div>
</div>'''
        self.assertEqual(expected, html_content)

        tab_1.setVisibilityExpression(QgsOptionalExpression(QgsExpression('True')))
        tab_2.setVisibilityExpression(QgsOptionalExpression(QgsExpression('False')))

        expected = '''<ul class="nav nav-tabs">

        <li class="active"><a href="#popup_dd_tab1" data-toggle="tab">tab1</a></li>

        <li class=""><a href="#popup_dd_tab2" data-toggle="tab">tab2</a></li>
    </ul>
    <div class="tab-content">
      <div id="popup_dd_tab1" class="tab-pane active">
      </div>

      <div id="popup_dd_tab2" class="tab-pane ">
      </div>
    </div>'''
        self.assertEqual(expected, html_content)

    def test_tooltip_layer(self):
        """Test tooltip on a layer."""
        layer = QgsVectorLayer(plugin_test_data_path('complex_form.geojson'), 'form', 'ogr')
        QgsProject.instance().addMapLayer(layer)
        self.assertTrue(layer.isValid())

        config = layer.editFormConfig()
        self.assertEqual(QgsEditFormConfig.TabLayout, config.layout())

        root = config.invisibleRootContainer()
        html_content = Tooltip.create_popup_node_item_from_form(
            layer, root, 0, [], '', QgsProject.instance().relationManager())

        self.maxDiff = None
        expected = '''<ul class="nav nav-tabs">

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
                        hstore_to_map('"A"=>"a","B"=>"b","C"=>"c"'),
                        "name"
                    ), '</div>',
                            '</p>'
                        )
                        ELSE ''
                    END %]
  </div>

  <div id="popup_dd_tab2" class="tab-pane ">
  </div>
</div>'''

        self.assertEqual(expected, html_content)
