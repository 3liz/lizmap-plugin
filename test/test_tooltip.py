"""Test tooltip."""

from qgis.core import (
    QgsVectorLayer,
    QgsProject,
    QgsEditFormConfig,
    QgsEditorWidgetSetup)
from qgis.testing import unittest, start_app


start_app()


from ..qgis_plugin_tools.tools.resources import plugin_test_data_path
from ..tooltip import Tooltip

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


class TestToolTip(unittest.TestCase):


    def test_tooltip(self):
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
                        hstore_to_map('a=>A, b=>B, c=>C, {2839923C-8B7D-419E-B84B-CA2FE9B80EC7}=><NULL>'),
                        "name"
                    )
                , '</div>',
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
                        hstore_to_map('a=>A, b=>B, c=>C, {2839923C-8B7D-419E-B84B-CA2FE9B80EC7}=><NULL>'),
                        "name"
                    )
                , '</div>',
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
                        hstore_to_map('a=>A, b=>B, c=>C, {2839923C-8B7D-419E-B84B-CA2FE9B80EC7}=><NULL>'),
                        "name"
                    )
                , '</div>',
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
                        hstore_to_map('a=>A, b=>B, c=>C, {2839923C-8B7D-419E-B84B-CA2FE9B80EC7}=><NULL>'),
                        "name"
                    )
                , '</div>',
                    '</p>'
                )
                ELSE ''
            END %]
            
  </div>
</div>'''.strip()

        self.assertEqual(html_content, expected)
