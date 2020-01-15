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

CSS_TOOLTIP_FORM = (
    '''
<style>
    div.popup_lizmap_dd {
        margin: 2px;
    }
    div.popup_lizmap_dd div {
        padding: 5px;
    }
    div.popup_lizmap_dd div.tab-content{
        border: 1px solid rgba(150,150,150,0.5);
    }
    div.popup_lizmap_dd ul.nav.nav-tabs li a {
        border: 1px solid rgba(150,150,150,0.5);
        border-bottom: none;
        color: grey;
    }
    div.popup_lizmap_dd ul.nav.nav-tabs li.active a {
        color: #333333;
    }
    div.popup_lizmap_dd div.tab-content div.tab-pane div {
        border: 1px solid rgba(150,150,150,0.5);
        border-radius: 5px;
        background-color: rgba(150,150,150,0.5);
    }
    div.popup_lizmap_dd div.tab-content div.tab-pane div.field,
    div.popup_lizmap_dd div.field,
    div.popup_lizmap_dd div.tab-content div.field {
        background-color: white;
        border: 1px solid white;
    }
    div.popup_lizmap_dd div.tab-content legend {
        font-weight: bold;
        font-size: 1em !important;
        color: #333333;
        border-bottom: none;
        margin-top: 15px !important;
    }

</style>
''')
