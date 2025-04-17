"""Create QGIS tooltip from Drag&Drop designer form."""

# BE CAREFUL
# This file MUST BE an exact copy between
# Desktop lizmap/tooltip.py
# Server lizmap_server/tooltip.py

import logging
import re

from typing import Union

from qgis.core import (
    QgsAttributeEditorContainer,
    QgsAttributeEditorElement,
    QgsAttributeEditorField,
    QgsAttributeEditorRelation,
    QgsHstoreUtils,
    QgsProject,
    QgsRelationManager,
    QgsVectorLayer,
)
from qgis.gui import QgsExternalResourceWidget
from qgis.PyQt.QtXml import QDomDocument

LOGGER = logging.getLogger('Lizmap')
SPACES = '  '

__copyright__ = 'Copyright 2021, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


class Tooltip:

    @staticmethod
    def create_popup(html: str) -> str:
        template = '''<div class="container popup_lizmap_dd form-horizontal" style="width:100%;">
    {}
</div>\n'''
        return template.format(html)

    @classmethod
    def remove_none(cls, data: dict) -> dict:
        """ Remove None values in the dictionary. """
        # Might be linked to QGIS 3.36 https://github.com/3liz/lizmap-web-client/issues/4307
        return {k: v for k, v in data.items() if v is not None}

    @classmethod
    def friendly_name(cls, name: str, alias: str) -> str:
        fname = alias if alias else name
        fname = fname.replace("'", "’")  # noqa RUF001
        return fname

    @staticmethod
    def create_popup_node_item_from_form(
            layer: QgsVectorLayer,
            node: QgsAttributeEditorElement,
            level: int,
            headers: list,
            html: str,
            relation_manager: QgsRelationManager,
            bootstrap_5: bool = False,
            ) -> str:
        regex = re.compile(r"[^a-zA-Z0-9_]", re.IGNORECASE)
        a = ''
        h = ''

        if isinstance(node, QgsAttributeEditorElement):
            # for text widgets
            # TODO QGIS_VERSION_INT 3.32 change to "Qgis.AttributeEditorType.TextElement"
            if node.type() == 6:
                label = node.name()
                expression = node.toDomElement(QDomDocument()).text()

                a += '\n' + SPACES * level
                a += Tooltip._generate_text_label(label, expression)

        if isinstance(node, QgsAttributeEditorField):
            if node.idx() < 0:
                # The form might have been imported from QML with some not existing fields
                LOGGER.warning(
                    f'Layer {layer.id()} does not have a valid editor field')
                return html

            field = layer.fields()[node.idx()]

            # display field name or alias if filled
            name = field.name()
            fname = Tooltip.friendly_name(name, field.alias())

            # adapt the view depending on the field type
            field_widget_setup = field.editorWidgetSetup()
            widget_type = field_widget_setup.type()
            widget_config = field_widget_setup.config()
            widget_config = Tooltip.remove_none(widget_config)

            field_view = Tooltip._generate_field_view(name)

            if widget_type == 'Hidden':
                # If hidden field, do nothing
                return html

            if widget_type == 'ExternalResource':
                # External resource: file, url, photo, iframe
                field_view = Tooltip._generate_external_resource(widget_config, name, fname)

            if widget_type == 'ValueRelation':
                if not QgsProject.instance().mapLayer(widget_config['Layer']):
                    # Issue #287
                    LOGGER.warning(
                        'Layer {} does not have a valid value relation layer for field {}'.format(
                            layer.id(), fname))
                    return html

                field_view = Tooltip._generate_represent_value(name)

            if widget_type == 'RelationReference':
                relation = relation_manager.relation(widget_config['Relation'])
                referenced_layer = relation.referencedLayer()

                if not referenced_layer:
                    # Issue #287
                    LOGGER.warning(
                        'Layer {} does not have a valid relation reference layer for field {}'.format(
                            layer.id(), fname))
                    return html

                field_view = Tooltip._generate_represent_value(name)

            if widget_type == 'ValueMap':
                field_view = Tooltip._generate_value_map(widget_config, name)

            if widget_type == 'DateTime':
                field_view = Tooltip._generate_date(widget_config, name)

            a += '\n' + SPACES * level
            a += Tooltip._generate_field_name(name, fname, field_view)

        if isinstance(node, QgsAttributeEditorRelation):
            # https://github.com/3liz/qgis-lizmap-server-plugin/issues/82
            node.init(relation_manager)  # Initializes the relation from the ID
            relation = node.relation()
            if relation:
                a += Tooltip._generate_attribute_editor_relation(
                    node.label(), relation.id(), relation.referencingLayerId())
            else:
                # Ticket https://github.com/3liz/qgis-lizmap-server-plugin/issues/82
                LOGGER.warning(
                    f"The node '{node.name()}::{node.label()}' cannot be processed for the tooltip "
                    f"because the relation has not been found.")

        if isinstance(node, QgsAttributeEditorContainer):

            visibility = ''
            if node.visibilityExpression().enabled():
                visibility = Tooltip._generate_eval_visibility(node.visibilityExpression().data().expression())

            lvl = level
            # create div container
            if lvl == 1:
                active = ''
                if not headers:
                    active = 'active'

                a += '\n' + SPACES + '<div id="popup_dd_[% $id %]_{}" class="tab-pane {}">'.format(
                    regex.sub('_', node.name()), active)

                if visibility and active:
                    active = f'{active} {visibility}'
                if visibility and not active:
                    active = visibility
                h += '\n' + SPACES
                id_tab = regex.sub('_', node.name())
                if bootstrap_5:
                    h += (
                        f'<li class="nav-item">'
                        f'<button class="nav-link {active}" data-bs-toggle="tab" '
                        f'data-bs-target="#popup_dd_[% $id %]_{id_tab}">'
                        f'{node.name()}'
                        f'</button>'
                        f'</li>'
                    )
                else:
                    h += (
                        f'<li class="{active}">'
                        f'<a href="#popup_dd_[% $id %]_{id_tab}" data-toggle="tab">{node.name()}</a>'
                        f'</li>'
                    )
                headers.append(h)

            if lvl > 1:
                a += '\n' + SPACES * lvl + f'<fieldset class="{visibility}">'
                a += '\n' + SPACES * lvl + f'<legend>{node.name()}</legend>'
                a += '\n' + SPACES * lvl + '<div>'

            # In case of root children
            before_tabs = []
            content_tabs = []
            after_tabs = []

            level += 1
            for n in node.children():
                h = Tooltip.create_popup_node_item_from_form(
                    layer, n, level, headers, html, relation_manager, bootstrap_5)
                # If it is not root children, add html
                if lvl > 0:
                    a += h
                    continue
                # TODO QGIS_VERSION_INT 3.30.0
                # Change the integer with the QGIS enum `Qgis.AttributeEditorType.TextElement`
                is_editor_element = isinstance(n, QgsAttributeEditorElement) and n.type() == 6
                # If it is root children, store html in the right list
                if isinstance(n, QgsAttributeEditorField) or is_editor_element:
                    if not headers:
                        before_tabs.append(h)
                    else:
                        after_tabs.append(h)
                else:
                    content_tabs.append(h)

            if lvl == 0:
                if before_tabs:
                    a += '\n<div class="before-tabs">'
                    a += '\n'.join(before_tabs)
                    a += '\n</div>'
                if headers:
                    a += '<ul class="nav nav-tabs">\n'
                    a += '\n'.join(headers)
                    a += '\n</ul>'
                    a += '\n<div class="tab-content">'
                    a += '\n'.join(content_tabs)
                    a += '\n</div>'
                if after_tabs:
                    a += '\n<div class="after-tabs">'
                    a += '\n'.join(after_tabs)
                    a += '\n</div>'
            elif lvl == 1:
                a += '\n' + SPACES * lvl + '</div>'
            elif lvl > 1:
                a += '\n' + SPACES * lvl + '</div>'
                a += '\n' + SPACES * lvl + '</fieldset>'

        html += a
        return html

    @staticmethod
    def _generate_field_view(name: str) -> str:
        return f'"{name}"'

    @staticmethod
    def _generate_eval_visibility(expression: str) -> str:
        return f"[% if ({expression}, '', 'hidden') %]"

    @staticmethod
    def _generate_attribute_editor_relation(label: str, relation_id: str, referencing_layer_id: str) -> str:
        """ Generate the div. LWC will manage to include children in the given div."""
        result = '\n' + SPACES + f'<p><b>{label}</b></p>'
        result += '\n' + SPACES
        result += (
            '<div id="popup_relation_{0}" data-relation-id="{0}" data-referencing-layer-id="{1}" '
            'class="popup_lizmap_dd_relation">'.format(relation_id, referencing_layer_id)
        )
        result += '\n' + SPACES + '</div>'
        return result

    @staticmethod
    def _generate_represent_value(name: str) -> str:
        """ Use represent_value which should cover many use cases about returning a human display string. """
        # https://github.com/3liz/lizmap-plugin/issues/241
        return f'represent_value("{name}")'

    @staticmethod
    def _generate_field_name(name: str, fname: str, expression: str) -> str:
        text = '''
                    [%
                    concat(
                        '<div class="control-group ',
                        CASE
                            WHEN "{0}" IS NULL OR trim("{0}") = ''
                                THEN ' control-has-empty-value '
                            ELSE ''
                        END,
                        '">',
                        '    <label ',
                        '       id="dd_jforms_view_edition_{0}_label" ',
                        '       class="control-label jforms-label" ',
                        '       for="dd_jforms_view_edition_{0}" >',
                        '    {1}',
                        '    </label>',
                        '    <div class="controls">',
                        '        <span ',
                        '            id="dd_jforms_view_edition_{0}" ',
                        '            class="jforms-control-input" ',
                        '        >',
                                    {2},
                        '        </span>',
                        '    </div>',
                        '</div>'
                    )
                    %]'''.format(
            name,
            fname,
            expression,
        )
        return text

    @staticmethod
    def _generate_value_map(widget_config: Union[list, dict], name: str) -> str:
        def escape_value(value: str) -> str:
            """Change ' to ’ for the HStore function. """
            return value.replace("'", "’")

        if isinstance(widget_config['map'], list):
            values = dict()
            for row in widget_config['map']:
                if '<NULL>' not in list(row.keys()):
                    reverted = {escape_value(y): escape_value(x) for x, y in row.items()}
                    values.update(reverted)
        else:
            # It's not a list, it's a dict.
            values = widget_config['map']

            if values is None:
                # The list is empty, the widget is not fully configured
                return "''"

            if values.get('<NULL>'):
                del values['<NULL>']
            values = {escape_value(y): escape_value(x) for x, y in values.items()}

        # noinspection PyCallByClass,PyArgumentList
        hstore = QgsHstoreUtils.build(values)
        field_view = f'''
                    map_get(
                        hstore_to_map('{hstore}'),
                        replace("{name}", '\\'', '’')
                    )'''
        return field_view

    @staticmethod
    def _generate_external_resource(widget_config: dict, name: str, fname: str) -> str:
        dview = widget_config['DocumentViewer']

        if dview == QgsExternalResourceWidget.DocumentViewerContent.Image:
            field_view = '''
                    concat(
                       '<a href="',
                       "{0}",
                       '" target="_blank">',
                       '
                       <img src="',
                       "{0}",
                       '" width="100%" title="{1}">',
                       '
                       </a>'
                    )'''.format(name, fname)

        elif dview == QgsExternalResourceWidget.DocumentViewerContent.Web:
            # web view
            field_view = '''
                    concat(
                       '<a href="',
                       "{0}",
                       '" target="_blank">
                       ',
                       '
                       <iframe src="',
                       "{0}",
                       '" width="100%" height="300" title="{1}"/>',
                       '
                       </a>'
                    )'''.format(name, fname)

        elif dview == QgsExternalResourceWidget.DocumentViewerContent.NoContent:
            field_view = '''
                    concat(
                        '<a href="',
                        "{0}",
                        '" target="_blank">',
                        base_file_name({0}),
                        '</a>'
                    )'''.format(name)

        else:
            raise Exception('Unknown external resource widget')

        return field_view

    @staticmethod
    def _generate_date(widget_config: dict, name: str) -> str:
        date_format = widget_config.get('display_format')

        if not date_format:
            # Fallback to ISO 8601, when the widget has not been configured yet
            date_format = "yyyy-MM-dd"

        field_view = f'''
                    format_date(
                        "{name}",
                        '{date_format}'
                    )'''
        return field_view

    @staticmethod
    def _generate_text_label(label: str, expression: str) -> str:
        text = f'''
                    <p><strong>{label}</strong>
                    <div class="field">{expression}</div>
                    </p>
                    '''
        return text

    @staticmethod
    def css() -> str:
        """ CSS for LWC <= 3.7. """
        css = '''<style>
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

</style>\n'''
        return css

    @staticmethod
    def css_3_8_6() -> str:
        """ CSS for LWC from 3.8.0 to 3.8.6. """
        css = '''<style>
/* Flat style for editing forms & drag-and-drop designed popup */
div.popup_lizmap_dd ul.nav-tabs {
  border-bottom: 1px solid var(--color-contrasted-elements);
}

div.popup_lizmap_dd .nav-tabs > li > a {
  color: var(--color-text-primary);
  padding: 5px;
  border: none;
}

div.popup_lizmap_dd .nav > li > a:hover,
div.popup_lizmap_dd .nav > li > a:focus {
  text-decoration: none;
}

div.popup_lizmap_dd .nav-tabs > li > a:hover,
div.popup_lizmap_dd .nav-tabs > li > a:focus {
  background: none;
  border: none;
  border-bottom: 3px solid var(--color-contrasted-elements);
  color: var(--color-text-primary);
  cursor: pointer;
}

div.popup_lizmap_dd .nav-tabs > li.active > a,
div.popup_lizmap_dd .nav-tabs > li.active > a:hover,
div.popup_lizmap_dd .nav-tabs > li.active > a:focus {
  background: none;
  border: none;
  border-bottom: 3px solid var(--color-contrasted-elements);
  color: var(--color-text-primary);
  cursor: auto;
}

div.popup_lizmap_dd div.tab-pane {
  border-left: 1px solid var(--color-contrasted-elements);
  border-right: 1px solid var(--color-contrasted-elements);
  border-bottom: 1px solid var(--color-contrasted-elements);
  padding: 5px;
  padding-bottom: 10px;
  margin-bottom: 5px;
}

div.popup_lizmap_dd div.tab-pane.attribute-layer-child-content {
  border: none;
}

div.popup_lizmap_dd #tabform {
  border: none;
}

div.popup_lizmap_dd legend {
  color: var(--color-text-primary);
  border-bottom: none;
  padding: 5px;
  width: unset;
  max-width: 100%;
  margin-bottom: 0;
}

div.popup_lizmap_dd fieldset {
  padding: 10px;
  padding-top: 0;
  margin: 0 5px;
  border: 1px solid var(--color-contrasted-elements-light);
  border-radius: 5px;
  background: rgb(255 255 255 / 20%);
}
/* Minor adaptation for popup compared to editing form */
div.popup_lizmap_dd {
  font-size: 12px;
}
div.popup_lizmap_dd .form-horizontal .control-group {
  margin-bottom: 0px !important;
}
div.popup_lizmap_dd label {
  padding-top: 0px !important;
  font-size: 12px !important;
  width: 130px !important;
}
div.popup_lizmap_dd .controls {
  margin-left: 140px !important;
}
</style>\n'''
        return css

# BE CAREFUL
# This file MUST BE an exact copy between
# Desktop lizmap/tooltip.py
# Server lizmap_server/tooltip.py
