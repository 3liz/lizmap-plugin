"""Definitions for portfolio."""

from enum import Enum, unique

from lizmap.definitions.base import BaseDefinitions, InputType
from lizmap.toolbelt.i18n import tr


def represent_folios(data: dict) -> str:
    """Generate HTMl string for the tooltip instead of JSON representation."""
    html = '<ul>'

    for folio in data:
        layout = folio.get('layout')
        theme = folio.get('theme')
        zoom_method = folio.get('zoom_method')
        scale = folio.get('fixed_scale')
        margin = folio.get('margin')
        html += f'<li>{layout} - {theme}'
        for z in ZoomMethodType:
            if z.value['data'] == zoom_method:
                label = z.value['label']
                html += f' - {label}'
                if z == ZoomMethodType.FixedScale:
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
    FixedScale = {
        'data': 'fixed_scale',
        'label': tr('Fixed scale'),
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
        self._layer_config['folios'] = {
            'type': InputType.Collection,
            'header': tr('Folioss'),
            'tooltip': tr('Textual representations of folios as tuples'),
            'items': [
                'layout',
                'theme',
                'zoom_method',
                'fixed_scale',
                'margin',
            ],
            'represent_value': represent_folios,
        }
        self._layer_config['layout'] = {
            'plural': 'layout_{}',
            'type': InputType.List,
            'header': tr('Layout'),
            'tooltip': tr('The QGIS print layout.')
        }
        self._layer_config['theme'] = {
            'plural': 'theme_{}',
            'type': InputType.List,
            'header': tr('Theme'),
            'tooltip': tr('The QGIS theme to be applied.')
        }
        self._layer_config['zoom_method'] = {
            'plural': 'zoom_method_{}',
            'type': InputType.List,
            'header': tr('Zoom method'),
            'items': ZoomMethodType,
            'default': ZoomMethodType.FixedScale,
            'tooltip': tr('The zoom to geometry method, depends on the geometry type.')
        }
        self._layer_config['fixed_scale'] = {
            'plural': 'fixed_scale_{}',
            'type': InputType.Scale,
            'header': tr('Fixed scale'),
            'default': 5000,
            'tooltip': tr('The fixed scale of the portfolio for point geometry.')
        }
        self._layer_config['margin'] = {
            'plural': 'margin_{}',
            'type': InputType.SpinBox,
            'header': tr('Margin'),
            'default': 10,
            'tooltip': tr('The margin around the line or polygon geometry.')
        }

    @staticmethod
    def primary_keys() -> tuple:
        return ()

    def key(self) -> str:
        return 'portfolioLayers'

    def help_path(self) -> str:
        return 'publish/lizmap_plugin/portfolio.html'
