"""Test tooltip.

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
"""
from pathlib import Path

import pytest

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

from lizmap.tooltip import Tooltip

from .compat import TestCase


class TestToolTip(TestCase):

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
                    [%
                    concat(
                        '<div class="control-group ',
                        CASE
                            WHEN "field_a" IS NULL OR trim("field_a") = ''
                                THEN ' control-has-empty-value '
                            ELSE ''
                        END,
                        '">',
                        '    <label ',
                        '       id="dd_jforms_view_edition_field_a_label" ',
                        '       class="control-label jforms-label" ',
                        '       for="dd_jforms_view_edition_field_a" >',
                        '    Field Name',
                        '    </label>',
                        '    <div class="controls">',
                        '        <span ',
                        '            id="dd_jforms_view_edition_field_a" ',
                        '            class="jforms-control-input" ',
                        '        >',
                                    'foo',
                        '        </span>',
                        '    </div>',
                        '</div>'
                    )
                    %]'''
        self.assertEqual(expected, template, template)

        layer = QgsVectorLayer('None?field=field_a:string', 'table', 'memory')
        sub_context = QgsExpressionContext()
        # noinspection PyCallByClass,PyArgumentList
        sub_context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(layer))
        feature = QgsFeature()
        feature.setAttributes(['a'])
        layer.dataProvider().addFeatures([feature])
        sub_context.setFeature(next(layer.getFeatures()))
        expression = QgsExpression().replaceExpressionText(template, sub_context)
        self.assertEqual('\n                    <div class="control-group ">    <label        id="dd_jforms_view_edition_field_a_label"        class="control-label jforms-label"        for="dd_jforms_view_edition_field_a" >    Field Name    </label>    <div class="controls">        <span             id="dd_jforms_view_edition_field_a"             class="jforms-control-input"         >foo        </span>    </div></div>', expression, expression)

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

    def test_represent_value(self):
        """Test we can generate a represent_value."""
        result = Tooltip._generate_represent_value('name' )
        expected = 'represent_value("name")'
        self.assertEqual(expected, result)

    def test_checkbox(self):
        """Test we can generate checkbox."""
        # Here, we have nothing to do, it's working by default in QGIS.
        field_view = Tooltip._generate_field_view('is_ok')
        self.assertEqual('"is_ok"', field_view)

        template = Tooltip._generate_field_name('is_ok', 'Is ok ?', field_view)
        expected = '''
                    [%
                    concat(
                        '<div class="control-group ',
                        CASE
                            WHEN "is_ok" IS NULL OR trim("is_ok") = ''
                                THEN ' control-has-empty-value '
                            ELSE ''
                        END,
                        '">',
                        '    <label ',
                        '       id="dd_jforms_view_edition_is_ok_label" ',
                        '       class="control-label jforms-label" ',
                        '       for="dd_jforms_view_edition_is_ok" >',
                        '    Is ok ?',
                        '    </label>',
                        '    <div class="controls">',
                        '        <span ',
                        '            id="dd_jforms_view_edition_is_ok" ',
                        '            class="jforms-control-input" ',
                        '        >',
                                    "is_ok",
                        '        </span>',
                        '    </div>',
                        '</div>'
                    )
                    %]'''
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
        self.assertEqual('\n                    <div class="control-group ">    <label        id="dd_jforms_view_edition_is_ok_label"        class="control-label jforms-label"        for="dd_jforms_view_edition_is_ok" >    Is ok ?    </label>    <div class="controls">        <span             id="dd_jforms_view_edition_is_ok"             class="jforms-control-input"         >true        </span>    </div></div>', expression, expression)

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
            'DocumentViewer': QgsExternalResourceWidget.DocumentViewerContent.Web,
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
                       </a>'''  # noqa W293
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
            'DocumentViewer': QgsExternalResourceWidget.DocumentViewerContent.Image,
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
            'DocumentViewer': QgsExternalResourceWidget.DocumentViewerContent.NoContent,
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

    def test_layer_non_existing_field(self):
        """Test we do not generate for non-existing fields."""
        layer = QgsVectorLayer('None?field=field_a:string', 'table', 'memory')

        feature = QgsFeature()
        feature.setAttributes(['a'])
        layer.dataProvider().addFeatures([feature])

        config = layer.editFormConfig()
        config.setLayout(QgsEditFormConfig.EditorLayout.TabLayout)
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

    @pytest.mark.skip()
    def test_display_group(self):
        """Test we can hide some groups."""
        layer = QgsVectorLayer('None?field=field_a:string', 'table', 'memory')

        config = layer.editFormConfig()
        config.setLayout(QgsEditFormConfig.EditorLayout.TabLayout)
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

    def test_tooltip_layer(self, data: Path):
        """Test tooltip on a layer."""
        layer = QgsVectorLayer(str(data.joinpath('complex_form.geojson')), 'form', 'ogr')
        # noinspection PyArgumentList
        QgsProject.instance().addMapLayer(layer)
        self.assertTrue(layer.isValid())

        config = layer.editFormConfig()
        self.assertEqual(QgsEditFormConfig.EditorLayout.TabLayout, config.layout())

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
    
                    [%
                    concat(
                        '<div class="control-group ',
                        CASE
                            WHEN "name" IS NULL OR trim("name") = ''
                                THEN ' control-has-empty-value '
                            ELSE ''
                        END,
                        '">',
                        '    <label ',
                        '       id="dd_jforms_view_edition_name_label" ',
                        '       class="control-label jforms-label" ',
                        '       for="dd_jforms_view_edition_name" >',
                        '    name',
                        '    </label>',
                        '    <div class="controls">',
                        '        <span ',
                        '            id="dd_jforms_view_edition_name" ',
                        '            class="jforms-control-input" ',
                        '        >',
                                    
                    map_get(
                        hstore_to_map('"a"=>"A","b"=>"B","c"=>"C"'),
                        replace("name", '\\'', '’')
                    ),
                        '        </span>',
                        '    </div>',
                        '</div>'
                    )
                    %]
  </div>

  <div id="popup_dd_[% $id %]_tab2" class="tab-pane ">
  </div>

  <div id="popup_dd_[% $id %]_invisible" class="tab-pane ">
    
                    [%
                    concat(
                        '<div class="control-group ',
                        CASE
                            WHEN "name" IS NULL OR trim("name") = ''
                                THEN ' control-has-empty-value '
                            ELSE ''
                        END,
                        '">',
                        '    <label ',
                        '       id="dd_jforms_view_edition_name_label" ',
                        '       class="control-label jforms-label" ',
                        '       for="dd_jforms_view_edition_name" >',
                        '    name',
                        '    </label>',
                        '    <div class="controls">',
                        '        <span ',
                        '            id="dd_jforms_view_edition_name" ',
                        '            class="jforms-control-input" ',
                        '        >',
                                    
                    map_get(
                        hstore_to_map('"a"=>"A","b"=>"B","c"=>"C"'),
                        replace("name", '\\'', '’')
                    ),
                        '        </span>',
                        '    </div>',
                        '</div>'
                    )
                    %]
  </div>
</div>'''  # noqa W293

        self.assertEqual(expected, html_content, html_content)
        self.assertFalse('data-bs-toggle="tab"' in html_content)

        # Same but with Bootstrap 5
        html_content = Tooltip.create_popup_node_item_from_form(
            layer, root, 0, [], '', QgsProject.instance().relationManager(), bootstrap_5=True)
        self.assertTrue('data-bs-toggle="tab"' in html_content)
