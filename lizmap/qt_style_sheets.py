__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

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
