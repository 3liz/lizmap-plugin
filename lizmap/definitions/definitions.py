"""Definitions used in Lizmap"""

from enum import Enum, unique

__copyright__ = 'Copyright 2022, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from functools import total_ordering


@unique
@total_ordering
class LwcVersions(Enum):
    Lizmap_3_1 = '3.1'
    Lizmap_3_2 = '3.2'
    Lizmap_3_3 = '3.3'
    Lizmap_3_4 = '3.4'
    Lizmap_3_5 = '3.5'
    Lizmap_3_6 = '3.6'

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented


@unique
class LayerProperties(Enum):
    DataUrl = 'DataUrl'


DOMAIN = 'https://docs.lizmap.com'
VERSION = 'current'
DOC_URL = '{domain}/{version}/'.format(domain=DOMAIN, version=VERSION)
ONLINE_HELP_LANGUAGES = ('en', 'es', 'it', 'ja', 'pt', 'fi', 'fr')
