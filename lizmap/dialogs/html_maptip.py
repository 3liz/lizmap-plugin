__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


from qgis.core import QgsVectorLayer
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox

from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.qgis_plugin_tools.tools.resources import load_ui

FORM_CLASS = load_ui('ui_html_maptip.ui')


class HtmlMapTipDialog(QDialog, FORM_CLASS):

    def __init__(self, layer: QgsVectorLayer):
        QDialog.__init__(self)
        self.setupUi(self)
        self.layer = layer

        accept_button = self.button_box.button(QDialogButtonBox.Ok)
        accept_button.clicked.connect(self.accept)
        cancel_button = self.button_box.button(QDialogButtonBox.Cancel)
        cancel_button.clicked.connect(self.reject)

    def map_tip(self) -> str:
        table_template = """<table class="table table-condensed table-striped table-bordered lizmapPopupTable">
          <thead>
            <tr>
              <th>{field}</th>
              <th>{value}</th>
            </tr>
          </thead>
          <tbody>
        {fields_template}
          </tbody>
        </table>"""

        if self.show_null.isChecked():
            field_template = """    <tr>
                  <th>{display}</th>
                  <td>[% "{name}" %]</td>
                </tr>
            """
        else:
            field_template = """
            [% with_variable(
                'content',
                '<tr><th>{display}</th><td>' || "{name}" || '</td></tr>',
                if( "{name}" is not NULL or "{name}" <> '',@content,'')
            )
            %]
            """

        fields = ""
        for field in self.layer.fields():
            name = field.name()
            if name in self.layer.excludeAttributesWms():
                fields += "<!-- Field {} excluded from WMS in the layer properties -->\n".format(name)
            else:
                fields += field_template.format(display=field.displayName(), name=name)

        result = table_template.format(field=tr("Field"), value=tr("Value"), fields_template=fields)

        return result
