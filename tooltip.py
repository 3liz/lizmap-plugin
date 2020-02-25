"""Create QGIS tooltip from Drag&Drop designer form."""

import re

from qgis.gui import QgsExternalResourceWidget
from qgis.core import (
    QgsAttributeEditorField,
    QgsAttributeEditorContainer,
    QgsVectorLayer,
    QgsAttributeEditorElement,
    QgsHstoreUtils)

from .html_and_expressions import HTML_POPUP_BASE


__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


class Tooltip:

    @staticmethod
    def create_popup(html):
        return HTML_POPUP_BASE.format(html)

    @staticmethod
    def create_popup_node_item_from_form(layer: QgsVectorLayer, node: QgsAttributeEditorElement, level, headers, html, relation_manager):
        regex = re.compile(r"[^a-zA-Z0-9_]", re.IGNORECASE)
        a = ''
        h = ''
        if isinstance(node, QgsAttributeEditorField):
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
            field_view = '"{}"'.format(name)

            # If hidden field, do nothing
            if widget_type == 'Hidden':
                return html

            # External ressource: file, url, photo, iframe
            if widget_type == 'ExternalResource':
                field_view = Tooltip._generate_external_resource(widget_config, name, fname)

            # Value relation
            if widget_type == 'ValueRelation':
                field_view = Tooltip._generate_value_relation(widget_config, name)

            # Value relation
            if widget_type == 'RelationReference':
                rel = relation_manager.relation(widget_config['Relation'])
                vlay = rel.referencedLayer()
                vlid = rel.referencedLayerId()
                parent_pk = rel.resolveReferencedField(name)
                fexp = '''
                    "{0}" = attribute(@parent, '{1}')
                '''.format(
                    parent_pk,
                    name
                )
                field_view = '''
                    aggregate(
                        layer:='{0}',
                        aggregate:='concatenate',
                        expression:={1},
                        filter:={2}
                    )
                '''.format(
                    vlid,
                    vlay.displayExpression(),
                    fexp
                )

            # Value map
            if widget_type == 'ValueMap':
                field_view = Tooltip._generate_value_map(widget_config, name)

            # Date
            if widget_type == 'DateTime':
                field_view = Tooltip._generate_date(widget_config, name)

            # field_view = '''
            # represent_value("{0}")
            # '''.format(
            # name
            # )

            a += '\n' + '  ' * level
            a += '''
            [% CASE
                WHEN "{0}" IS NOT NULL OR trim("{0}") != ''
                THEN concat(
                    '<p>', '<b>{1}</b>',
                    '<div class="field">', {2}, '</div>',
                    '</p>'
                )
                ELSE ''
            END %]
            '''.format(
                name,
                fname,
                field_view
            )

        if isinstance(node, QgsAttributeEditorContainer):
            l = level
            # create div container
            if l == 1:
                act = ''
                if not headers:
                    act = 'active'
                a += '\n' + '  ' * l + '<div id="popup_dd_%s" class="tab-pane %s">' % (
                    regex.sub('_', node.name()),
                    act
                )
                h += '\n    ' + '<li class="%s"><a href="#popup_dd_%s" data-toggle="tab">%s</a></li>' % (
                    act,
                    regex.sub('_', node.name()),
                    node.name()
                )
                headers.append(h)
            if l > 1:
                a += '\n' + '  ' * l + '<fieldset>'
                a += '\n' + '  ' * l + '<legend>%s</legend>' % node.name()
                a += '\n' + '  ' * l + '<div>'

            # In cas of root children
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
                    a += '\n<div class="before-tabs">' + '\n'.join(before_tabs) + '\n</div>'
                if headers:
                    a += '<ul class="nav nav-tabs">\n' + '\n'.join(headers) + '\n</ul>'
                    a += '\n<div class="tab-content">' + '\n'.join(content_tabs) + '\n</div>'
                if after_tabs:
                    a += '\n<div class="after-tabs">' + '\n'.join(after_tabs) + '\n</div>'
            elif l == 1:
                a += '\n' + '  ' * l + '</div>'
            elif l > 1:
                a += '\n' + '  ' * l + '</div>'
                a += '\n' + '  ' * l + '</fieldset>'

        html += a
        return html

    @staticmethod
    def _generate_value_map(widget_config, name):
        hstore = QgsHstoreUtils.build(widget_config['map'][0])
        field_view = '''
map_get(
    hstore_to_map('{}'),
    "{}"
)'''.format(hstore, name)
        return field_view

    @staticmethod
    def _generate_external_resource(widget_config, name, fname):
        dview = widget_config['DocumentViewer']
        field_view = '''
concat(
   '<a href="',
   "{}",
   '" target="_blank">{}</a>'
)'''.format(name, fname)

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

        if dview == QgsExternalResourceWidget.Web:
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

        return field_view

    @staticmethod
    def _generate_date(widget_config, name):
        dfor = widget_config['display_format']
        field_view = '''
format_date(
    "{}",
    '{}'
)'''.format(name, dfor)
        return field_view

    @staticmethod
    def _generate_value_relation(widget_config, name):
        vlid = widget_config['Layer']

        fexp = '''"{}" = attribute(@parent, '{}')'''.format(
            widget_config['Key'],
            name
        )

        filter_exp = widget_config['FilterExpression'].strip()
        if filter_exp:
            fexp += ' AND %s' % filter_exp

        field_view = '''
aggregate(
    layer:='{0}',
    aggregate:='concatenate',
    expression:="{1}",
    filter:={2}
)
        '''.format(
            vlid,
            widget_config['Value'],
            fexp
        )
        return field_view
