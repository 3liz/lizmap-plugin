"""Test Traces."""
from collections import OrderedDict

from qgis.core import QgsVectorLayer, QgsProject
from qgis.testing import unittest

from lizmap.qgis_plugin_tools.tools.resources import plugin_test_data_path
from lizmap.forms.trace_dataviz_edition import TraceDatavizEditionDialog

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


class TestTraceDialog(unittest.TestCase):

    def test_trace_dialog(self):
        """Test trace dialog."""
        layer = QgsVectorLayer(plugin_test_data_path('lines.geojson'), 'lines', 'ogr')
        QgsProject.instance().addMapLayer(layer)
        self.assertTrue(layer.isValid())

        dialog = TraceDatavizEditionDialog(None, layer)
        self.assertFalse(dialog.error.isVisible())

        self.assertEqual('Field is required.', dialog.validate())
        self.assertEqual('#086fa1', dialog.color.color().name())
        self.assertEqual('', dialog.color_field.currentField())
        self.assertTrue(dialog.color.isEnabled())
        self.assertTrue(dialog.color_field.allowEmptyFieldName())

        dialog.color_field.setCurrentIndex(1)
        self.assertNotEqual('', dialog.color_field.currentField())
        self.assertFalse(dialog.color.isEnabled())

        dialog.color_field.setCurrentIndex(0)
        self.assertEqual('', dialog.color_field.currentField())
        self.assertTrue(dialog.color.isEnabled())

        dialog.field.setCurrentIndex(0)
        self.assertIsNone(dialog.validate())

        data = dialog.save_form()
        expected = OrderedDict()
        expected['y_field'] = 'id'
        expected['color'] = '#086fa1'
        expected['colorfield'] = ''
        self.assertEqual(expected, data)

        data = OrderedDict()
        data['y_field'] = 'name'
        data['color'] = '#aabbcc'
        data['colorfield'] = ''
        dialog.load_form(data)
        self.assertEqual(data, dialog.save_form())
