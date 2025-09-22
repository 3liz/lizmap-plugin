__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import sys

# Both colors MUST be synchronized
NEW_FEATURE_COLOR = '#aaffff'
NEW_FEATURE_CSS = 'background-color:rgb(170, 255, 255);'

STYLESHEET = (
    '''
QGroupBox::title {{
    background-color: transparent;
    subcontrol-origin: margin;
    margin-left: 6px;
    subcontrol-position: top left;
}}
QGroupBox {{
    background-color: rgba({}, {}, {}, {});
    border: 1px solid rgba(0,0,0,20%);
    border-radius: 5px;
    font-weight: bold;
    margin-top: {}ex;
}}
''')

if sys.platform.startswith('win'):
    style = ['0', '0', '0', '5%']
    margin = '4.0'
else:
    style = ['225', '225', '225', '90%']
    margin = '2.5'

COMPLETE_STYLE_SHEET = STYLESHEET.format(*style, margin)
