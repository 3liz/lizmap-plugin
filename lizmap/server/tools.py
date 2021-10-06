__copyright__ = 'Copyright 2021, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from typing import Union

"""
Tools for Lizmap.
"""


def to_bool(val: Union[str, int, float, bool]) -> bool:
    """ Convert lizmap config value to boolean """
    if isinstance(val, str):
        # For string, compare lower value to True string
        return val.lower() in ('yes', 'true', 't', '1')
    elif not val:
        # For value like False, 0, 0.0, None, empty list or dict returns False
        return False
    else:
        return True
