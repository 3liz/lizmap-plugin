
from qgis.core import QgsVectorLayer
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox

from lizmap.toolbelt.i18n import tr
from lizmap.toolbelt.resources import load_ui
from lizmap.tooltip import Tooltip

FORM_CLASS = load_ui('ui_html_maptip.ui')


class HtmlMapTipDialog(QDialog, FORM_CLASS):

    def __init__(self, layer: QgsVectorLayer):
        QDialog.__init__(self)
        self.setupUi(self)
        self.layer = layer

        accept_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        accept_button.clicked.connect(self.accept)
        cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_button.clicked.connect(self.reject)

    @staticmethod
    def table_row(display: str, name: str) -> str:
        """ Table row, including NULL values. """
        return f"""    <tr>
              <th>{display}</th>
              <td>[% "{name}" %]</td>
            </tr>
        """

    @staticmethod
    def table_row_html(display: str, cell: str) -> str:
        """ Table row with an expression. """
        return f"""    <tr>
              <th>{display}</th>
              <td>{cell}</td>
            </tr>
        """

    @staticmethod
    def table_row_not_null(display: str, name: str) -> str:
        """ Table row, hidden if NULL. """
        return f"""
        [% with_variable(
            'content',
            '<tr><th>{display}</th><td>' || "{name}" || '</td></tr>',
            if( "{name}" is not NULL or "{name}" <> '',@content,'')
        )
        %]
        """

    @staticmethod
    def image(field: str) -> str:
        return f'<img src=\'[% "{field}" %]\' />'

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

        fields = ""
        for field in self.layer.fields():
            name = field.name()
            if name in self.layer.excludeAttributesWms():
                fields += "<!-- Field '{}' was excluded from WMS in the layer properties -->\n".format(name)
            else:

                field_widget_setup = field.editorWidgetSetup()
                widget_type = field_widget_setup.type()
                widget_config = field_widget_setup.config()
                widget_config = Tooltip.remove_none(widget_config)
                display = field.displayName()
                if self.use_widget_config.isChecked() and widget_type == 'ExternalResource':
                    # External resource: file, url, photo, iframe
                    fields += self.table_row_html(display, self.image(name))
                # TODO add more
                else:
                    if self.show_null.isChecked():
                        fields += self.table_row(display, name)
                    else:
                        fields += self.table_row_not_null(display, name)

        return table_template.format(field=tr("Field"), value=tr("Value"), fields_template=fields)
