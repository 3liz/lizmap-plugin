"""Definitions for portfolio."""

from enum import Enum, unique
from typing import (
    Dict,
)

from lizmap.definitions.base import BaseDefinitions, InputType
from lizmap.toolbelt.i18n import tr


def represent_layouts(data: Dict) -> str:
    """Generate HTMl string for the tooltip instead of JSON representation."""
    html = '<ul>'

    for template in data:
        layout = template.get('layout')
        theme = template.get('theme')
        zoom_method = template.get('zoom_method')
        scale = template.get('fix_scale')
        margin = template.get('margin')
        html += f'<li>{layout} - {theme}'
        for z in ZoomMethodType:
            if z.value['data'] == zoom_method:
                label = z.value['label']
                html += f' - {label}'
                if z == ZoomMethodType.FixScale:
                    html += f' - 1:{scale}'
                elif z == ZoomMethodType.Margin:
                    html += f' - {margin}%'
                break
        html += '</li>\n'

    html += '</ul>\n'
    return html


@unique
class GeometryType(Enum):
    Point = {
        'data': 'point',
        'label': tr('Point'),
    }
    Line = {
        'data': 'line',
        'label': tr('Line'),
    }
    Polygon = {
        'data': 'polygon',
        'label': tr('Polygon'),
    }


@unique
class ZoomMethodType(Enum):
    FixScale = {
        'data': 'fix_scale',
        'label': tr('Fix scale'),
    }
    Margin = {
        'data': 'margin',
        'label': tr('Margin (%)'),
    }
    BestScale = {
        'data': 'best_scale',
        'label': tr('Best scale'),
    }


class PortfolioDefinitions(BaseDefinitions):

    def __init__(self):
        super().__init__()
        self._layer_config['title'] = {
            'type': InputType.Text,
            'header': tr('Title'),
            'default': '',
            'tooltip': tr('The title of the portfolio, when displayed in the portfolio dock'),
        }
        self._layer_config['description'] = {
            'type': InputType.HtmlWysiwyg,
            'header': tr('Description'),
            'default': '',
            'tooltip': tr('The description of the portfolio. HTML is supported.'),
        }
        self._layer_config['drawing_geometry'] = {
            'type': InputType.List,
            'header': tr('Geometry'),
            'items': GeometryType,
            'default': GeometryType.Point,
            'tooltip': tr('The geometry type of the portfolio.')
        }
        self._layer_config['layouts'] = {
            'type': InputType.Collection,
            'header': tr('Layouts'),
            'tooltip': tr('Textual representations of layout tuples'),
            'items': [
                'layout',
                'theme',
                'zoom_method',
                'fix_scale',
                'margin',
            ],
            'represent_value': represent_layouts,
        }
        self._layer_config['layout'] = {
            'plural': 'layout_{}',
            'type': InputType.List,
            'header': tr('Layout'),
            'tooltip': tr('The zoom to geometry method, depends on the geometry type.')
        }
        self._layer_config['theme'] = {
            'plural': 'theme_{}',
            'type': InputType.List,
            'header': tr('Theme'),
            'tooltip': tr('The zoom to geometry method, depends on the geometry type.')
        }
        self._layer_config['zoom_method'] = {
            'plural': 'zoom_method_{}',
            'type': InputType.List,
            'header': tr('Zoom method'),
            'items': ZoomMethodType,
            'default': ZoomMethodType.FixScale,
            'tooltip': tr('The zoom to geometry method, depends on the geometry type.')
        }
        self._layer_config['fix_scale'] = {
            'plural': 'fix_scale_{}',
            'type': InputType.Scale,
            'header': tr('Fix scale'),
            'default': 5000,
            'tooltip': tr('The scale of the portfolio for point geometry.')
        }
        self._layer_config['margin'] = {
            'plural': 'margin_{}',
            'type': InputType.SpinBox,
            'header': tr('Margin'),
            'default': 10,
            'tooltip': tr('The margin around line or polygon geometry.')
        }

    @staticmethod
    def primary_keys() -> tuple:
        return tuple()

    def key(self) -> str:
        return 'portfolioLayers'

    def help_path(self) -> str:
        return 'publish/lizmap_plugin/portfolio.html'
