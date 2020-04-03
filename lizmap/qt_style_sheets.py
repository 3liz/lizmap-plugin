NEW_FEATURE = 'background-color:rgb(170, 255, 255);'

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
