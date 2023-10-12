"""Definitions for layouts."""
from enum import Enum, unique

from lizmap.definitions.base import BaseDefinitions, InputType
from lizmap.qgis_plugin_tools.tools.i18n import tr

__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


@unique
class FormatType(Enum):
    Pdf = {
        'data': 'pdf',
        'label': tr('PDF'),
    }
    Svg = {
        'data': 'svg',
        'label': tr('SVG'),
    }
    Png = {
        'data': 'png',
        'label': tr('PNG'),
    }
    Jpeg = {
        'data': 'jpeg',
        'label': tr('JPEG'),
    }


@unique
class Dpi(Enum):
    Dpi100 = {
        'data': '100',
        'label': '100',
    }
    Dpi200 = {
        'data': '200',
        'label': '200',
    }
    Dpi300 = {
        'data': '300',
        'label': '300',
    }


class LayoutsDefinitions(BaseDefinitions):

    def __init__(self):
        super().__init__()
        self._layer_config['layout'] = {
            'type': InputType.Text,
            'header': tr('Layout'),
            'tooltip': tr('The name of the layout, read-only because it\'s inherited from the QGIS project.')
        }
        self._layer_config['enabled'] = {
            'type': InputType.CheckBox,
            'header': tr('Enabled'),
            'default': True,
            'use_json': True,
            'tooltip': tr('If the layout is enabled.')
        }
        self._layer_config['allowed_groups'] = {
            'type': InputType.Text,
            'header': tr('Allowed groups'),
            'default': '',
            'separator': ',',
            'use_json': True,
            'tooltip': tr(
                'Use a comma separated list of Lizmap groups ids to restrict access '
                'to this layer edition.')
        }
        self._layer_config['formats_available'] = {
            'type': InputType.List,
            'multiple_selection': True,
            'header': tr('Formats'),
            'items': FormatType,
            'default': ('pdf', ),  # This value is overriden if the legacy checkbox was used adding all other formats.
            'tooltip': tr("The list of formats to be displayed in the interface.")
        }
        self._layer_config['default_format'] = {
            'type': InputType.List,
            'header': tr('Default format'),
            'items': FormatType,
            'default': FormatType.Pdf,
            'tooltip': tr("The default format.")
        }
        self._layer_config['dpi_available'] = {
            'type': InputType.List,
            'multiple_selection': True,
            'header': tr('DPI'),
            'items': Dpi,
            'default': ('100', ),  # This value is overriden if the legacy checkbox was used adding all other formats.
            'tooltip': tr("The list of DPI to be displayed.")
        }
        self._layer_config['default_dpi'] = {
            'type': InputType.List,
            'header': tr('Default DPI'),
            'items': Dpi,
            'default': Dpi.Dpi100,
            'tooltip': tr("The default DPI")
        }
        self._layer_config['icon'] = {
            'type': InputType.File,
            'header': tr('Icon'),
            'tooltip': tr('The icon to use, stored in a "media" folder.'),
            'default': '',
        }

        self._general_config['default_popup_print'] = {
            'type': InputType.CheckBox,
            'default': True,
        }

    def key(self) -> str:
        return 'layouts'

    def help_path(self) -> str:
        return 'publish/lizmap_plugin/layouts.html'
