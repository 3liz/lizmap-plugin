"""Definitions for dataviz."""

from enum import Enum, unique

from qgis.core import QgsVectorLayer

from lizmap.definitions.base import BaseDefinitions, InputType
from lizmap.definitions.definitions import LwcVersions
from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.qgis_plugin_tools.tools.resources import resources_path
from lizmap.tools import random_string

__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


def generate_uuid(layer: QgsVectorLayer, plot_type: str) -> str:
    """ Generate a UUID for the given layer. """
    uuid = '{}_plot_{}_{}'.format(layer.name(), plot_type, random_string())
    return uuid


@unique
class Theme(Enum):
    Dark = {
        'data': 'dark',
        'label': tr('Dark'),
    }
    Light = {
        'data': 'light',
        'label': tr('Light'),
    }


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
        'version': LwcVersions.Lizmap_3_4,
    }
    HtmlTemplate = {
        'data': 'html',
        'label': tr('HTML Template'),
        'icon': resources_path('icons', 'plots', 'html_template.png'),
        'version': LwcVersions.Lizmap_3_4,
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
    No = {
        'data': 'no',
        'label': tr('No'),
    }


def represent_traces(data) -> str:
    """Generate HTMl string for the tooltip instead of JSON representation."""
    # Nice to have : color in a small square
    html = '<ul>'
    for trace in data:
        y_field = trace.get('y_field')
        if y_field:
            html += '<li>{}: '.format(y_field)

            color_field = trace.get('colorfield')
            if color_field:
                html += color_field

            color = trace.get('color')
            if color:
                html += color

            html += '</li>\n'

    html += '</ul>\n'
    return html


class DatavizDefinitions(BaseDefinitions):

    def __init__(self):
        super().__init__()
        self._layer_config['type'] = {
            'type': InputType.List,
            'header': tr('Type'),
            'items': GraphType,
            'default': GraphType.Scatter,
            'tooltip': tr('Type of chart to add'),
            'items_depend_on_lwc_version': True,
        }
        self._layer_config['title'] = {
            'type': InputType.Text,
            'header': tr('Title'),
            'default': '',
            'tooltip': tr('The title of the plot, when displayed in the dataviz dock')
        }
        self._layer_config['title_popup'] = {
            'type': InputType.Text,
            'header': tr('Title in popup'),
            'default': '',
            'tooltip': tr('The title of the plot, when displayed in a popup'),
            'version': LwcVersions.Lizmap_3_7,
        }
        self._layer_config['description'] = {
            'type': InputType.HtmlWysiwyg,
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
            'tooltip': tr(
                'For a few types of charts like "bar" or "pie", you can choose to aggregate the data in the '
                'graph.')
        }
        self._layer_config['traces'] = {
            'type': InputType.Collection,
            'header': tr('Traces'),
            'tooltip': tr('Textual representations of traces'),
            'items': [
                'y_field',
                'color',
                'colorfield',
                'z_field',
            ],
            'represent_value': represent_traces,
        }
        self._layer_config['y_field'] = {
            'plural': 'y{}_field',
            'type': InputType.Field,
            'header': tr('Y field'),
            'default': '',
            'tooltip': tr('The Y field of your graph.')
        }
        self._layer_config['color'] = {
            'plural': 'color{}',
            'type': InputType.Color,
            'header': tr('Color'),
            'default': '#086FA1',
            'tooltip': tr('The color for Y.')
        }
        self._layer_config['colorfield'] = {
            'plural': 'colorfield{}',
            'type': InputType.Field,
            'header': tr('Color field'),
            'default': '',
            'tooltip': tr(
                'You can choose or not a color field to customize the color of each category of your chart. '
                'Choose the field of your layer which contains the colors you want to use. The color can be written '
                'like "red" or "blue" but it can be an HTML color code like "#01DFD7" for example.')
        }
        self._layer_config['z_field'] = {
            'plural': 'z_field_{}',
            'type': InputType.Field,
            'header': tr('Z field'),
            'default': '',
            'tooltip': tr('The Z field of your graph.'),
            'version': LwcVersions.Lizmap_3_4,
        }
        self._layer_config['html_template'] = {
            'type': InputType.HtmlWysiwyg,
            'header': tr('HTML template'),
            'default': '',
            'tooltip': tr('The HTML template.'),
            'version': LwcVersions.Lizmap_3_4,
        }
        self._layer_config['layout'] = {
            'type': InputType.Json,
            'header': tr('Layout'),
            'default': '',
            'tooltip': tr(
                'You can add here a JSON configuration to override the default layout object created by Lizmap.'),
            'version': LwcVersions.Lizmap_3_4,
        }
        self._layer_config['popup_display_child_plot'] = {
            'type': InputType.CheckBox,
            'header': tr('Popup for children'),
            'default': False,
            'tooltip': tr(
                'If you check this checkbox, the graph will be shown in the pop-up of the parent layer, '
                'with data filtered according to a QGIS relation between the graph layer and the parent layer. '
                'For example show the repartition between men and women employment rate filtered by the town selected '
                'in the pop-up.')
        }
        self._layer_config['trigger_filter'] = {
            'type': InputType.CheckBox,
            'header': tr('Filterable'),
            'default': True,
            'tooltip': tr(
                'By default, a plot is refreshed if the data is filtered. By unchecking this option, the plot '
                'will not be refreshed when the data is filtered in the layer.'
            ),
            'use_json': True,
        }
        self._layer_config['stacked'] = {
            'type': InputType.CheckBox,
            'header': tr('If the chart is stacked'),
            'default': False,
            'tooltip': tr('If the bar chart is stacked.'),
            'version': LwcVersions.Lizmap_3_4,
        }
        self._layer_config['horizontal'] = {
            'type': InputType.CheckBox,
            'header': tr('If the chart is horizontal'),
            'default': False,
            'tooltip': tr('If the bar chart is horizontal.'),
            'version': LwcVersions.Lizmap_3_4,
        }
        self._layer_config['only_show_child'] = {
            'type': InputType.CheckBox,
            'header': tr('Only show child'),
            'default': False,
            'tooltip': tr(
                'The main graph will not be shown in the main container and only the filtered graph of the relation of '
                'the layer will be displayed in the popup when you select the element.')
        }
        self._layer_config['display_legend'] = {
            'type': InputType.CheckBox,
            'header': tr('Display legend'),
            'default': True,
            'tooltip': tr('If the legend must be displayed with the graph.'),
            'version': LwcVersions.Lizmap_3_4,
        }
        self._layer_config['display_when_layer_visible'] = {
            'type': InputType.CheckBox,
            'header': tr('Display chart only when the layer is visible'),
            'default': False,
            'tooltip': tr(
                'If checked, the chart will be shown only if the source layer is visible in the map (checked '
                'in the legend panel)'),
            'version': LwcVersions.Lizmap_3_4,
        }
        self._layer_config['uuid'] = {
            'type': InputType.Text,
            'header': tr('UUID'),
            'tooltip': tr('The UUID of the plot'),
            'default': generate_uuid,
            'read_only': True,
            'visible': True,
            'update_on_saving': False,
        }

        self._general_config['datavizLocation'] = {
            'type': InputType.List,
            # 'default': False,
            'tooltip': tr('Position of the Dataviz panel in the web interface.'),
            'version': LwcVersions.Lizmap_3_2,
        }

        self._general_config['datavizTemplate'] = {
            'type': InputType.HtmlWysiwyg,
            'tooltip': tr('You can write our own HTML layout. Follow the documentation online to have an example.'),
            'version': LwcVersions.Lizmap_3_2,
        }

        self._general_config['theme'] = {
            'type': InputType.List,
            'items': Theme,
            # If the default value is changed, must be changed in the commands python file as well
            'default': Theme.Dark,
            'tooltip': tr('The theme for the dataviz panel.'),
            'version': LwcVersions.Lizmap_3_4,
        }

    @staticmethod
    def primary_keys() -> tuple:
        return tuple()

    def key(self) -> str:
        return 'datavizLayers'

    def help_path(self) -> str:
        return 'publish/lizmap_plugin/dataviz.html'
