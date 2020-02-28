"""Definitions for dataviz."""

from enum import Enum, unique

from .base import BaseDefinitions, InputType
from .definitions import LwcVersions
from ..qgis_plugin_tools.tools.i18n import tr
from ..qgis_plugin_tools.tools.resources import resources_path

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


@unique
class GraphType(Enum):
    Scatter = {
        'data': 'scatter',
        'label': tr('Scatter'),
        'icon': resources_path('icons', 'plots', 'scatterplot.svg'),
    }
    Box = {
        'data': 'box',
        'label': tr('Box'),
        'icon': resources_path('icons', 'plots', 'boxplot.svg'),
    }
    Bar = {
        'data': 'bar',
        'label': tr('Bar'),
        'icon': resources_path('icons', 'plots', 'barplot.svg'),
    }
    Histogram = {
        'data': 'histogram',
        'label': tr('Histogram'),
        'icon': resources_path('icons', 'plots', 'histogram.svg'),
    }
    Pie = {
        'data': 'pie',
        'label': tr('Pie'),
        'icon': resources_path('icons', 'plots', 'pie.svg'),
    }
    Histogram2D = {
        'data': 'histogram2d',
        'label': tr('Histogram 2D'),
        'icon': resources_path('icons', 'plots', '2dhistogram.svg'),
    }
    Polar = {
        'data': 'polar',
        'label': tr('Polar'),
        'icon': resources_path('icons', 'plots', 'polar.svg'),
    }
    Sunburst = {
        'data': 'sunburst',
        'label': tr('Sunburst'),
        'icon': resources_path('icons', 'plots', 'sunburst.svg'),
    }


@unique
class AggregationType(Enum):
    Sum = {
        'data': 'sum',
        'label': tr('Sum'),
    }
    Count = {
        'data': 'count',
        'label': tr('Count'),
    }
    Avg = {
        'data': 'avg',
        'label': tr('Average'),
    }
    Median = {
        'data': 'median',
        'label': tr('Median'),
    }
    Stddev = {
        'data': 'stddev',
        'label': tr('Standard deviation'),
    }
    Min = {
        'data': 'min',
        'label': tr('Min'),
    }
    Max = {
        'data': 'max',
        'label': tr('Max'),
    }
    First = {
        'data': 'first',
        'label': tr('First'),
    }
    Last = {
        'data': 'last',
        'label': tr('Last'),
    }


class DatavizDefinitions(BaseDefinitions):

    def __init__(self):
        super().__init__()
        self._layer_config['type'] = {
            'type': InputType.List,
            'header': tr('Type'),
            'items': GraphType,
            'default': GraphType.Scatter,
            'tooltip': tr('Type of chart to add')
        }
        self._layer_config['title'] = {
            'type': InputType.Text,
            'header': tr('Title'),
            'default': '',
            'tooltip': tr('The title of the graph')
        }
        self._layer_config['description'] = {
            'type': InputType.MultiLine,
            'header': tr('Description'),
            'default': '',
            'tooltip': tr('The description of the graph. HTML is supported.'),
            'version': LwcVersions.Lizmap_3_4,
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
            'items': AggregationType,
            'default': AggregationType.Sum,
            'tooltip': tr('For a few types of charts like "bar" or "pie", you can choose to aggregate the data in the graph.')
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
                'Choose the field of your layer which contains the colors you want to use. The color can be written like "red" or "blue" but it can be an HTML color code like "#01DFD7" for example.')
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
        self._layer_config['display_legend'] = {
            'type': InputType.CheckBox,
            'header': tr('Display legend'),
            'default': True,
            'tooltip': tr('If the legend must be displayed with the graph.'),
            'version': LwcVersions.Lizmap_3_4,
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
