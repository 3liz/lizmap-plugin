__copyright__ = 'Copyright 2022, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


from enum import Enum, unique


@unique
class Warnings(Enum):
    OgcNotValid = 'ogc_not_valid'
    UseLayerIdAsName = 'use_layer_id_as_name'
    SaasLizmapCloud = 'saas_lizmap_cloud_invalid'
    InvalidFieldType = 'invalid_field_type'
    DuplicatedLayersWithFilters = 'duplicated_layers_with_filters'
