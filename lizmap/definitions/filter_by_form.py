"""Definitions for filter by form."""

from lizmap.definitions.base import BaseDefinitions, InputType
from lizmap.definitions.definitions import LwcVersions
from lizmap.qgis_plugin_tools.tools.i18n import tr

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


class FilterByFormDefinitions(BaseDefinitions):

    def __init__(self):
        super().__init__()
        self._layer_config['layerId'] = {
            'type': InputType.Layer,
            'header': tr('Layer'),
            'default': None,
            'tooltip': tr('The vector layer for the filter.')
        }
        self._layer_config['title'] = {
            'type': InputType.Text,
            'header': tr('Title'),
            'default': '',
            'tooltip': tr(
                'The title to give to the input, which will be displayed above the form input. '
                'For example "Choose a category" for a layer field called "category".')
        }
        # TODO switch to enum for the list with icons
        self._layer_config['type'] = {
            'type': InputType.List,
            'header': tr('Type'),
            'default': None,
            'tooltip': tr('The type of the form input.')
        }
        self._layer_config['field'] = {
            'type': InputType.Field,
            'header': tr('Field'),
            'default': '',
            'tooltip': tr(
                'The field name to apply the filter on.')
        }
        # In a near future, we should merge min_date into start_field
        # LWC 3.7 is able to read it already
        self._layer_config['min_date'] = {
            'type': InputType.Field,
            'header': tr('Date minimum'),
            'default': '',
            'tooltip': tr(
                'The field containing the start date of your feature (ex: "start_date" of an event).')
        }
        # In a near future, we should merge max_date into end_field
        # LWC 3.7 is able to read it already
        self._layer_config['max_date'] = {
            'type': InputType.Field,
            'header': tr('Date maximum'),
            'default': '',
            'tooltip': tr(
                'The field containing the end date of your data. If you have 2 fields containing dates, '
                'one for the start date and another for the end date, you can differentiate them. '
                'If not, you need to use the same field name for Min date and Max date.'
            )
        }
        self._layer_config['start_field'] = {
            'type': InputType.Field,
            'header': tr('Start field'),
            'default': '',
            'tooltip': tr('The field containing the minimum/start value'),
            # 'version': LwcVersions.Lizmap_3_7, # This field is kinda not new, used for legacy CFG from < 3.7
        }
        self._layer_config['end_field'] = {
            'type': InputType.Field,
            'header': tr('End field'),
            'default': '',
            'tooltip': tr('The field containing the maximum/end value of your data.'),
            'version': LwcVersions.Lizmap_3_7,
        }
        self._layer_config['format'] = {
            'type': InputType.List,
            'header': tr('Format'),
            'default': '',
            'tooltip': tr(
                'It can be select, which will show a combo box, or checkboxes which will show one checkbox for each distinct value. '
                'The distinct values are dynamically queried by Lizmap Web Client.')
        }
        self._layer_config['splitter'] = {
            'type': InputType.Text,
            'header': tr('Splitter'),
            'default': '',
            'tooltip': tr(
                'Use if you want to split the field values by a separator. '
                'Ex: "culture, environment" can be split into "culture" and "environment" with the splitter ", ".'
            )
        }

    @staticmethod
    def primary_keys() -> tuple:
        return tuple()

    def key(self) -> str:
        return 'formFilterLayers'

    def help_path(self) -> str:
        return 'publish/lizmap_plugin/form_filtering.html'
