"""Create QGIS tooltip from Drag&Drop designer form."""

import logging
import re

from typing import Union

from qgis.core import (
    Qgis,
    QgsAttributeEditorContainer,
    QgsAttributeEditorElement,
    QgsAttributeEditorField,
    QgsHstoreUtils,
    QgsProject,
    QgsRelationManager,
    QgsVectorLayer,
)
from qgis.gui import QgsExternalResourceWidget

LOGGER = logging.getLogger('Lizmap')
SPACES = '  '

__copyright__ = 'Copyright 2021, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


class Tooltip:

    @staticmethod
    def create_popup(html: str) -> str:
        template = '''<div class="container popup_lizmap_dd" style="width:100%;">
    {}
</div>\n'''
        return template.format(html)

    @staticmethod
    def create_popup_node_item_from_form(
            layer: QgsVectorLayer,
            node: QgsAttributeEditorElement,
            level: int,
            headers: list,
            html: str,
            relation_manager: QgsRelationManager,
            ) -> str:
        regex = re.compile(r"[^a-zA-Z0-9_]", re.IGNORECASE)
        a = ''
        h = ''
        if isinstance(node, QgsAttributeEditorField):
            if node.idx() < 0:
                # The form might have been imported from QML with some not existing fields
                LOGGER.warning(
                    'Layer {} does not have a valid editor field'.format(layer.id()))
                return html

            field = layer.fields()[node.idx()]

            # display field name or alias if filled
            alias = field.alias()
            name = field.name()
            fname = alias if alias else name
            fname = fname.replace("'", "’")

            # adapt the view depending on the field type
            field_widget_setup = field.editorWidgetSetup()
            widget_type = field_widget_setup.type()
            widget_config = field_widget_setup.config()

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

                field_view = Tooltip._generate_value_relation(widget_config, name)

            if widget_type == 'RelationReference':
                relation = relation_manager.relation(widget_config['Relation'])
                referenced_layer = relation.referencedLayer()

                if not referenced_layer:
                    # Issue #287
                    LOGGER.warning(
                        'Layer {} does not have a valid relation reference layer for field {}'.format(
                            layer.id(), fname))
                    return html

                display = referenced_layer.displayExpression()
                layer_id = relation.referencedLayerId()
                parent_pk = relation.resolveReferencedField(name)
                field_view = Tooltip._generate_relation_reference(name, parent_pk, layer_id, display)

            if widget_type == 'ValueMap':
                field_view = Tooltip._generate_value_map(widget_config, name)

            if widget_type == 'DateTime':
                field_view = Tooltip._generate_date(widget_config, name)

            a += '\n' + SPACES * level
            a += Tooltip._generate_field_name(name, fname, field_view)

        if isinstance(node, QgsAttributeEditorContainer):

            visibility = ''
            if node.visibilityExpression().enabled():
                visibility = Tooltip._generate_eval_visibility(node.visibilityExpression().data().expression())

            l = level
            # create div container
            if l == 1:
                active = ''
                if not headers:
                    active = 'active'

                a += '\n' + SPACES + '<div id="popup_dd_[% $id %]_{}" class="tab-pane {}">'.format(
                    regex.sub('_', node.name()), active)

                if visibility and active:
                    active = '{} {}'.format(active, visibility)
                if visibility and not active:
                    active = visibility
                h += '\n' + SPACES + '<li class="{}"><a href="#popup_dd_[% $id %]_{}" data-toggle="tab">{}</a></li>'.format(
                    active, regex.sub('_', node.name()), node.name())
                headers.append(h)

            if l > 1:
                a += '\n' + SPACES * l + '<fieldset class="{}">'.format(visibility)
                a += '\n' + SPACES * l + '<legend>{}</legend>'.format(node.name())
                a += '\n' + SPACES * l + '<div>'

            # In case of root children
            before_tabs = []
            content_tabs = []
            after_tabs = []

            level += 1
            for n in node.children():
                h = Tooltip.create_popup_node_item_from_form(layer, n, level, headers, html, relation_manager)
                # If it is not root children, add html
                if l > 0:
                    a += h
                    continue
                # If it is root children, store html in the right list
                if isinstance(n, QgsAttributeEditorField):
                    if not headers:
                        before_tabs.append(h)
                    else:
                        after_tabs.append(h)
                else:
                    content_tabs.append(h)

            if l == 0:
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
            elif l == 1:
                a += '\n' + SPACES * l + '</div>'
            elif l > 1:
                a += '\n' + SPACES * l + '</div>'
                a += '\n' + SPACES * l + '</fieldset>'

        html += a
        return html

    @staticmethod
    def _generate_field_view(name: str):
        return '"{}"'.format(name)

    @staticmethod
    def _generate_eval_visibility(expression: str):
        return "[% if ({}, '', 'hidden') %]".format(expression)

    @staticmethod
    def _generate_relation_reference(name: str, parent_pk: str, layer_id: str, display_expression: str):
        expression = '''
                    "{}" = attribute(@parent, '{}')
                '''.format(parent_pk, name)

        field_view = '''
                    aggregate(
                        layer:='{0}',
                        aggregate:='concatenate',
                        expression:={1},
                        filter:={2}
                    )'''.format(
            layer_id,
            display_expression,
            expression
        )
        return field_view

    @staticmethod
    def _generate_field_name(name: str, fname: str, expression: str):
        text = '''
                    [% CASE
                        WHEN "{0}" IS NOT NULL OR trim("{0}") != ''
                        THEN concat(
                            '<p>', '<b>{1}</b>',
                            '<div class="field">', {2}, '</div>',
                            '</p>'
                        )
                        ELSE ''
                    END %]'''.format(
            name,
            fname,
            expression
        )
        return text

    @staticmethod
    def _generate_value_map(widget_config: Union[list, dict], name: str):
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
            if values.get('<NULL>'):
                del values['<NULL>']
            values = {escape_value(y): escape_value(x) for x, y in values.items()}

        # noinspection PyCallByClass,PyArgumentList
        hstore = QgsHstoreUtils.build(values)
        field_view = '''
                    map_get(
                        hstore_to_map('{}'),
                        replace("{}", '\\'', '’')
                    )'''.format(hstore, name)
        return field_view

    @staticmethod
    def _generate_external_resource(widget_config: dict, name: str, fname: str):
        dview = widget_config['DocumentViewer']

        if dview == QgsExternalResourceWidget.Image:
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

        elif dview == QgsExternalResourceWidget.Web:
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

        elif dview == QgsExternalResourceWidget.NoContent:
            if Qgis.QGIS_VERSION_INT >= 30800:
                field_view = '''
                    concat(
                        '<a href="',
                        "{0}",
                        '" target="_blank">',
                        base_file_name({0}),
                        '</a>'
                    )'''.format(name)
            else:
                field_view = '''
                    concat(
                        '<a href="',
                        "{}",
                        '" target="_blank">{}</a>'
                    )'''.format(name, fname)

        else:
            raise Exception('Unknown external resource widget')

        return field_view

    @staticmethod
    def _generate_date(widget_config: dict, name: str):
        dfor = widget_config['display_format']
        field_view = '''
                    format_date(
                        "{}",
                        '{}'
                    )'''.format(name, dfor)
        return field_view

    @staticmethod
    def _generate_value_relation(widget_config: dict, name: str):
        vlid = widget_config['Layer']

        expression = '''"{}" = attribute(@parent, '{}')'''.format(
            widget_config['Key'],
            name
        )

        filter_exp = widget_config['FilterExpression'].strip()
        if filter_exp:
            expression += ' AND {}'.format(filter_exp)

        field_view = '''
                    aggregate(
                        layer:='{0}',
                        aggregate:='concatenate',
                        expression:="{1}",
                        filter:={2}
                    )'''.format(
                                vlid,
                                widget_config['Value'],
                                expression
                            )
        return field_view

    @staticmethod
    def css() -> str:
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
