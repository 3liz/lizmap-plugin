"""Definitions for dataviz."""

from enum import Enum, unique

from .base import BaseDefinitions, InputType
from ..qgis_plugin_tools.tools.i18n import tr

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


@unique
class GraphType(Enum):
    Scatter = 'scatter'
    Box = 'box'
    Bar = 'bar'
    Histogram = 'histogram'
    Pie = 'pie'
    Histogram2D = 'histogram2d'
    Polar = 'polar'


@unique
class AggregationType(Enum):
    Sum = 'sum'
    Count = 'count'
    Avg = 'avg'
    Median = 'median'
    Stddev = 'stddev'
    Min = 'min'
    Max = 'max'
    First = 'first'
    Last = 'last'


class DatavizDefinitions(BaseDefinitions):

    def __init__(self):
        super().__init__()
        self._layer_config['type'] = {
            'type': InputType.List,
            'header': tr('Type'),
            'default': None,
            'tooltip': tr('Type of chart to add')
        }
        self._layer_config['title'] = {
            'type': InputType.Text,
            'header': tr('Title'),
            'default': '',
            'tooltip': tr('The title of the graph')
        }
        self._layer_config['layerId'] = {
            'type': InputType.Layer,
            'header': tr('Layer'),
            'default': None,
            'tooltip': tr('The vector layer for the graph.')
        }
        self._layer_config['x_field'] = {
            'type': InputType.Field,
            'header': tr('X field'),
            'default': '',
            'tooltip': tr('X field of your graph, it might be empty according to the kind of graph (box).')
        }
        self._layer_config['aggregation'] = {
            'type': InputType.List,
            'header': tr('Aggregation'),
            'default': AggregationType.Sum.value,
            'tooltip': tr('For a few types of charts like ‘bar’ or ‘pie’, you can choose to aggregate the data in the graph.')
        }
        self._layer_config['y_field'] = {
            'type': InputType.Field,
            'header': tr('Y field'),
            'default': '',
            'tooltip': tr('The Y field of your graph.')
        }
        self._layer_config['color'] = {
            'type': InputType.Color,
            'header': tr('Color'),
            'default': '#086FA1',
            'tooltip': tr('The color for Y.')
        }
        self._layer_config['colorfield'] = {
            'type': InputType.Field,
            'header': tr('Color field'),
            'default': '',
            'tooltip': tr(
                'You can choose or not a color field to customize the color of each category of your chart. '
                'If you want to do it, you need to check the checkbox, then choose the field of your layer which contains the colors you want to use. The color can be written like ‘red’ or ‘blue’ but it can be an HTML color code like ‘#01DFD7’ for example.')
        }
        self._layer_config['y2_field'] = {
            'type': InputType.Field,
            'header': tr('Y field 2'),
            'default': '',
            'tooltip': tr('You can add a second Y field.')
        }
        self._layer_config['colorfield2'] = {
            'type': InputType.Field,
            'header': tr('Color field 2'),
            'default': '',
            'tooltip': tr('You can choose the color of the second Y field the same way you choose the one for his first Y field.')
        }
        self._layer_config['color2'] = {
            'type': InputType.Color,
            'header': tr('Color 2'),
            'default': '#FF8900',
            'tooltip': tr('The second color')
        }
        self._layer_config['popup_display_child_plot'] = {
            'type': InputType.CheckBox,
            'header': tr('Popup for children'),
            'default': False,
            'tooltip': tr(
                'If you check this checkbox, the graph will be shown in the pop-up of the parent layer, '
                'with data filtered according to a QGIS relation between the graph layer and the parent layer. '
                'For example show the repartition between men and women employment rate filtered by the town selected in the pop-up.')
        }
        self._layer_config['only_show_child'] = {
            'type': InputType.CheckBox,
            'header': tr('Only show child'),
            'default': False,
            'tooltip': tr('The main graph will not be shown in the main container and only the filtered graph of the relation of the layer will be displayed in the popup when you select the element.')
        }

        self._general_config['datavizLocation'] = {
            # 'type': InputType.CheckBox,
            # 'default': False,
        }

        self._general_config['datavizTemplate'] = {
            # 'type': InputType.CheckBox,
            # 'default': False,
        }

    @staticmethod
    def primary_keys() -> tuple:
        return tuple()

    def key(self) -> str:
        return 'datavizLayers'
