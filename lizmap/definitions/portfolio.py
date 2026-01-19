"""Definitions for portfolio."""

from lizmap.definitions.base import BaseDefinitions, InputType
from lizmap.toolbelt.i18n import tr


def represent_templates(data: Dict) -> str:
    """Generate HTMl string for the tooltip instead of JSON representation."""
    html = '<ul>'

    for template in data:
        layout = template.get('layout')
        theme = template.get('theme')
        html += f'<li>{layout} - {theme}</li>\n'

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
        self._layer_config['geometry'] = {
            'type': InputType.List,
            'header': tr('Geometry'),
            'items': GeometryType,
            'default': GeometryType.Point,
            'tooltip': tr('The geometry type of the portfolio.')
        }
        self._layer_config['margin'] = {
            'type': InputType.SpinBox,
            'header': tr('Margin'),
            'default': 10,
            'tooltip': tr('The margin around line or polygon geometry.')
        }
        self._layer_config['scale'] = {
            'type': InputType.Scale,
            'header': tr('Scale'),
            'default': 5000,
            'tooltip': tr('The scale of the portfolio for point geometry.')
        }
        self._layer_config['templates'] = {
            'type': InputType.Collection,
            'header': tr('Templates'),
            'tooltip': tr('Textual representations of templates'),
            'items': [
                'layout',
                'theme',
            ],
            'represent_value': represent_templates,
        }

    @staticmethod
    def primary_keys() -> tuple:
        return tuple()

    def key(self) -> str:
        return 'portfolioLayers'

    def help_path(self) -> str:
        return 'publish/lizmap_plugin/portfolio.html'
