"""Test tooltip."""
from qgis.core import (
    QgsAttributeEditorContainer,
    QgsAttributeEditorField,
    QgsEditFormConfig,
    QgsExpression,
    QgsExpressionContext,
    QgsExpressionContextUtils,
    QgsFeature,
    QgsField,
    QgsOptionalExpression,
    QgsProject,
    QgsVectorLayer,
)
from qgis.gui import QgsExternalResourceWidget
from qgis.PyQt.QtCore import QVariant
from qgis.testing import unittest

from lizmap.toolbelt.resources import plugin_test_data_path
from lizmap.tooltip import Tooltip

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


class TestToolTip(unittest.TestCase):

    def check_layer_context(self, field_value, expression, expected):
        layer = QgsVectorLayer('None?field=field_a:string', 'table', 'memory')

        feature = QgsFeature()
        feature.setAttributes([field_value])

        context = QgsExpressionContext()
        # noinspection PyCallByClass,PyArgumentList
        context.appendScope(QgsExpressionContextUtils.layerScope(layer))
        context.setFeature(feature)

        error = 'Expression : {}\nError : {}'

        expression = QgsExpression(expression)
        self.assertFalse(
            expression.hasParserError(),
            error.format(
                expression.expression(),
                expression.parserErrorString()))

        expression.prepare(context)
        self.assertFalse(
            expression.hasEvalError(),
            error.format(
                expression.expression(),
                expression.evalErrorString()))
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
        # noinspection PyCallByClass,PyArgumentList
        sub_context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(layer))
        feature = QgsFeature()
        feature.setAttributes(['a'])
        layer.dataProvider().addFeatures([feature])
        sub_context.setFeature(next(layer.getFeatures()))
        expression = QgsExpression().replaceExpressionText(template, sub_context)
        self.assertEqual('\n                    <p><b>Field Name</b><div class="field">foo</div></p>', expression)

    def test_visibility_expression(self):
        """Test the visibility expression."""
        expression = Tooltip._generate_eval_visibility(str(True))
        self.assertEqual("[% if (True, '', 'hidden') %]", expression)
        expression = QgsExpression().replaceExpressionText(expression, QgsExpressionContext())
        self.assertEqual('', expression)

        expression = Tooltip._generate_eval_visibility(str(False))
        self.assertEqual("[% if (False, '', 'hidden') %]", expression)
        expression = QgsExpression().replaceExpressionText(expression, QgsExpressionContext())
        self.assertEqual('hidden', expression)

    def test_relation_reference(self):
        """Test we can generate a relation reference."""
        result = Tooltip._generate_relation_reference('name', 'parent_pk', 'layer_id', 'display_expression')
        expected = '''
                    aggregate(
                        layer:='layer_id',
                        aggregate:='concatenate',
                        expression:=to_string(display_expression),
                        filter:=
                    "parent_pk" = attribute(@parent, 'name')
                
                    )'''
        self.assertEqual(expected, result)

    def test_checkbox(self):
        """Test we can generate checkbox."""
        # Here, we have nothing to do, it's working by default in QGIS.
        field_view = Tooltip._generate_field_view('is_ok')
        self.assertEqual('"is_ok"', field_view)

        template = Tooltip._generate_field_name('is_ok', 'Is ok ?', field_view)
        expected = '''
                    [% CASE
                        WHEN "is_ok" IS NOT NULL OR trim("is_ok") != ''
                        THEN concat(
                            '<p>', '<b>Is ok ?</b>',
                            '<div class="field">', "is_ok", '</div>',
                            '</p>'
                        )
                        ELSE ''
                    END %]'''
        self.assertEqual(expected, template, template)

        layer = QgsVectorLayer('Point', 'temporary_points', 'memory')
        provider = layer.dataProvider()
        provider.addAttributes([QgsField('is_ok', QVariant.Bool)])
        layer.updateFields()
        sub_context = QgsExpressionContext()
        # noinspection PyCallByClass,PyArgumentList
        sub_context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(layer))
        feature = QgsFeature()
        feature.setAttributes([True])
        layer.dataProvider().addFeatures([feature])
        sub_context.setFeature(next(layer.getFeatures()))
        expression = QgsExpression().replaceExpressionText(template, sub_context)
        self.assertEqual('\n                    <p><b>Is ok ?</b><div class="field">true</div></p>', expression, expression)

        # FIXME On memory layers, we can't custom config on checkbox widget
        # config = {
        #     'CheckedState': 'Good',
        #     'UncheckedState': 'Not good',
        # }
        # layer.setEditorWidgetSetup(1, QgsEditorWidgetSetup('CheckBox', config))
        # sub_context.setFeature(next(layer.getFeatures()))
        # expression = QgsExpression().replaceExpressionText(template, sub_context)
        # self.assertEqual('\n                    <p><b>Is ok ?</b><div class="field">true</div></p>', expression, expression)

    def test_value_map(self):
        """Test we can generate value map."""
        widget_config = {
            'map': [
                {
                    'A': 'a',
                }, {
                    'B': 'b',
                }, {
                    '<NULL>': '{2839923C-8B7D-419E-B84B-CA2FE9B80EC7}',
                }
            ]
        }
        expression = Tooltip._generate_value_map(widget_config, 'field_a')
        expected = '''
                    map_get(
                        hstore_to_map('"a"=>"A","b"=>"B"'),
                        replace("field_a", '\\'', '’')
                    )'''
        self.assertEqual(expected, expression)
        self.check_layer_context('a', expression, 'A')

        widget_config = {
            'map': {
                'A': 'a',
                'B': 'b',
                '<NULL>': '{2839923C-8B7D-419E-B84B-CA2FE9B80EC7}',
            }
        }
        expression = Tooltip._generate_value_map(widget_config, 'field_a')
        expected = '''
                    map_get(
                        hstore_to_map('"a"=>"A","b"=>"B"'),
                        replace("field_a", '\\'', '’')
                    )'''
        self.assertEqual(expected, expression)
        self.check_layer_context('a', expression, 'A')

    def test_empty_value_map(self):
        """ Test empty value map. """
        # This test is a special one, the widget is not fully configured in the QGIS UI.
        widget_config = {
            'map': None
        }
        expression = Tooltip._generate_value_map(widget_config, 'field_a')
        self.assertEqual("''", expression)
        self.check_layer_context('a', expression, '')

    def test_value_map_with_quote(self):
        """Test we can generate a value map with some quotes."""
        widget_config = {
            'map': [
                {
                    'L\'eau c\'est bon': 'a',
                }, {
                    'B': 'b',
                }
            ]
        }
        expression = Tooltip._generate_value_map(widget_config, 'field_a')
        expected = '''
                    map_get(
                        hstore_to_map('"a"=>"L’eau c’est bon","b"=>"B"'),
                        replace("field_a", '\\'', '’')
                    )'''
        self.assertEqual(expected, expression)
        self.check_layer_context('a', expression, 'L’eau c’est bon')

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

    def test_attribute_editor_relation(self):
        """Test to generate the attribute editor relation."""
        expression = Tooltip._generate_attribute_editor_relation('a country', 'a_relation_id', 'a_layer_id')
        expected = '''
  <p><b>a country</b></p>
  <div id="popup_relation_a_relation_id" data-relation-id="a_relation_id" data-referencing-layer-id="a_layer_id" class="popup_lizmap_dd_relation">
  </div>'''
        self.assertEqual(expected, expression)

    def test_text_widget(self):
        """Test to check the text widget."""
        expression = Tooltip._generate_text_label('a label', 'a text widget')
        expected = '''
                    <p><strong>a label</strong>
                    <div class="field">a text widget</div>
                    </p>
                    '''
        self.assertEqual(expected, expression)

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
                        '" target="_blank">',
                        base_file_name(field_a),
                        '</a>'
                    )'''
        self.assertEqual(expected, expression)

        expected = '<a href="test.png" target="_blank">test</a>'
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
                        expression:=to_string("value"),
                        filter:="key" = attribute(@parent, 'foo') AND filter_expression
                    )'''
        self.assertEqual(expected, result)
        expression = QgsExpression(result)
        self.assertFalse(expression.hasParserError())

        # https://github.com/3liz/lizmap-web-client/issues/4307
        widget_config['FilterExpression'] = None
        widget_config = Tooltip.remove_none(widget_config)
        result = Tooltip._generate_value_relation(widget_config, 'foo')
        expected = '''
                    aggregate(
                        layer:='layer_id',
                        aggregate:='concatenate',
                        expression:=to_string("value"),
                        filter:="key" = attribute(@parent, 'foo')
                    )'''
        self.assertEqual(expected, result)
        expression = QgsExpression(result)
        self.assertFalse(expression.hasParserError())

    def test_value_relation_current_geometry(self):
        """Test a value relation with @current_geometry in widget config FilterExpression."""
        widget_config = {
            'Key': 'key',
            'Layer': 'layer_id',
            'FilterExpression': 'intersects(@current_geometry, $geometry)',
            'Value': 'value',
        }
        result = Tooltip._generate_value_relation(widget_config, 'foo')
        expected = '''
                    aggregate(
                        layer:='layer_id',
                        aggregate:='concatenate',
                        expression:=to_string("value"),
                        filter:="key" = attribute(@parent, 'foo') AND intersects(geometry(@parent), $geometry)
                    )'''
        self.assertEqual(expected, result)
        expression = QgsExpression(result)
        self.assertFalse(expression.hasParserError())

    def test_value_relation_current_value(self):
        """Test a value relation with current_value in widget config FilterExpression."""
        widget_config = {
            'Key': 'key',
            'Layer': 'layer_id',
            'FilterExpression': '''"fkey" = current_value('bar')''',
            'Value': 'value',
        }
        result = Tooltip._generate_value_relation(widget_config, 'foo')
        expected = '''
                    aggregate(
                        layer:='layer_id',
                        aggregate:='concatenate',
                        expression:=to_string("value"),
                        filter:="key" = attribute(@parent, 'foo') AND "fkey" = attribute(@parent, 'bar')
                    )'''
        self.assertEqual(expected, result)
        expression = QgsExpression(result)
        self.assertFalse(expression.hasParserError())

    def test_layer_non_existing_field(self):
        """Test we do not generate for non-existing fields."""
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

        # noinspection PyArgumentList
        html_content = Tooltip.create_popup_node_item_from_form(
            layer, root, 0, [], '', QgsProject.instance().relationManager())

        expected = '''<ul class="nav nav-tabs">

  <li class="active"><a href="#popup_dd_[% $id %]_tab1" data-toggle="tab">tab1</a></li>
</ul>
<div class="tab-content">
  <div id="popup_dd_[% $id %]_tab1" class="tab-pane active">
  </div>
</div>'''
        self.assertEqual(expected, html_content, html_content)

        tab_1.addChildElement(QgsAttributeEditorField('fake_field', -1, tab_1))

        # noinspection PyArgumentList
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

        # noinspection PyArgumentList
        html_content = Tooltip.create_popup_node_item_from_form(
            layer, root, 0, [], '', QgsProject.instance().relationManager())

        expected = '''<ul class="nav nav-tabs">

    <li class="active"><a href="#popup_dd_[% $id %]_tab1" data-toggle="tab">tab1</a></li>

    <li class=""><a href="#popup_dd_[% $id %]_tab2" data-toggle="tab">tab2</a></li>
</ul>
<div class="tab-content">
  <div id="popup_dd_[% $id %]_tab1" class="tab-pane active">
  </div>

  <div id="popup_dd_[% $id %]_tab2" class="tab-pane ">
  </div>
</div>'''
        self.assertEqual(expected, html_content)

        tab_1.setVisibilityExpression(QgsOptionalExpression(QgsExpression(str(True))))
        tab_2.setVisibilityExpression(QgsOptionalExpression(QgsExpression(str(False))))

        expected = '''<ul class="nav nav-tabs">

        <li class="active"><a href="#popup_dd_[% $id %]_tab1" data-toggle="tab">tab1</a></li>

        <li class=""><a href="#popup_dd_[% $id %]_tab2" data-toggle="tab">tab2</a></li>
    </ul>
    <div class="tab-content">
      <div id="popup_dd_[% $id %]_tab1" class="tab-pane active">
      </div>

      <div id="popup_dd_[% $id %]_tab2" class="tab-pane ">
      </div>
    </div>'''
        self.assertEqual(expected, html_content)

    def test_tooltip_layer(self):
        """Test tooltip on a layer."""
        layer = QgsVectorLayer(plugin_test_data_path('complex_form.geojson'), 'form', 'ogr')
        # noinspection PyArgumentList
        QgsProject.instance().addMapLayer(layer)
        self.assertTrue(layer.isValid())

        config = layer.editFormConfig()
        self.assertEqual(QgsEditFormConfig.TabLayout, config.layout())

        root = config.invisibleRootContainer()
        # noinspection PyArgumentList
        html_content = Tooltip.create_popup_node_item_from_form(
            layer, root, 0, [], '', QgsProject.instance().relationManager(), bootstrap_5=False)

        self.maxDiff = None
        expected = '''<ul class="nav nav-tabs">

  <li class="active"><a href="#popup_dd_[% $id %]_tab_1" data-toggle="tab">tab 1</a></li>

  <li class=""><a href="#popup_dd_[% $id %]_tab2" data-toggle="tab">tab2</a></li>

  <li class="[% if (False, '', 'hidden') %]"><a href="#popup_dd_[% $id %]_invisible" data-toggle="tab">invisible</a></li>
</ul>
<div class="tab-content">
  <div id="popup_dd_[% $id %]_tab_1" class="tab-pane active">
    
                    [% CASE
                        WHEN "name" IS NOT NULL OR trim("name") != ''
                        THEN concat(
                            '<p>', '<b>name</b>',
                            '<div class="field">', 
                    map_get(
                        hstore_to_map('"a"=>"A","b"=>"B","c"=>"C"'),
                        replace("name", '\\'', '’')
                    ), '</div>',
                            '</p>'
                        )
                        ELSE ''
                    END %]
  </div>

  <div id="popup_dd_[% $id %]_tab2" class="tab-pane ">
  </div>

  <div id="popup_dd_[% $id %]_invisible" class="tab-pane ">
    
                    [% CASE
                        WHEN "name" IS NOT NULL OR trim("name") != ''
                        THEN concat(
                            '<p>', '<b>name</b>',
                            '<div class="field">', 
                    map_get(
                        hstore_to_map('"a"=>"A","b"=>"B","c"=>"C"'),
                        replace("name", '\\'', '’')
                    ), '</div>',
                            '</p>'
                        )
                        ELSE ''
                    END %]
  </div>
</div>'''

        self.assertEqual(expected, html_content, html_content)
        self.assertFalse('data-bs-toggle="tab"' in html_content)

        # Same but with Bootstrap 5
        html_content = Tooltip.create_popup_node_item_from_form(
            layer, root, 0, [], '', QgsProject.instance().relationManager(), bootstrap_5=True)
        self.assertTrue('data-bs-toggle="tab"' in html_content)
