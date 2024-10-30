"""Dialog for tooltip edition."""

from qgis.core import QgsMapLayerProxyModel
from qgis.PyQt.QtGui import QColor, QIcon
from qgis.PyQt.QtWidgets import QMessageBox

from lizmap.definitions.definitions import LwcVersions
from lizmap.definitions.tooltip import ToolTipDefinitions
from lizmap.dialogs.html_maptip import HtmlMapTipDialog
from lizmap.forms.base_edition_dialog import BaseEditionDialog
from lizmap.toolbelt.i18n import tr
from lizmap.toolbelt.resources import load_ui, resources_path

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


CLASS = load_ui('ui_form_tooltip.ui')


class ToolTipEditionDialog(BaseEditionDialog, CLASS):

    def __init__(self, parent=None, unicity=None, lwc_version: LwcVersions = None):
        super().__init__(parent, unicity, lwc_version)
        self.setupUi(self)
        self.config = ToolTipDefinitions()
        self.config.add_layer_widget('layerId', self.layer)
        self.config.add_layer_widget('fields', self.fields)
        self.config.add_layer_widget('template', self.html_template)
        self.config.add_layer_widget('displayGeom', self.display_geometry)
        self.config.add_layer_widget('colorGeom', self.color)

        self.config.add_layer_label('layerId', self.label_layer)
        self.config.add_layer_label('fields', self.label_fields)
        self.config.add_layer_label('template', self.label_html_template)
        self.config.add_layer_label('displayGeom', self.label_display_geometry)
        self.config.add_layer_label('colorGeom', self.label_color)

        # TODO when 3.8 will be the default, change the default tab according to the LWC version

        self.layer.setFilters(QgsMapLayerProxyModel.Filter.VectorLayer)
        self.layer.layerChanged.connect(self.check_layer_wfs)
        self.layer.layerChanged.connect(self.fields.set_layer)
        self.layer.layerChanged.connect(self.html_template.set_layer)
        self.fields.set_layer(self.layer.currentLayer())
        self.html_template.set_layer(self.layer.currentLayer())

        self.display_geometry.toggled.connect(self.enable_color)
        self.enable_color()

        self.generate_table.clicked.connect(self.generate_table_clicked)

        self.lwc_versions[LwcVersions.Lizmap_3_8] = [
            self.label_html_template,
        ]

        self.setup_ui()
        self.check_layer_wfs()

    def check_layer_wfs(self):
        """ When the layer has changed in the combobox, check if the layer is published as WFS. """
        layer = self.layer.currentLayer()
        if not layer:
            self.show_error(tr('A layer is mandatory.'))
            return

        not_in_wfs = self.is_layer_in_wfs(layer)
        self.show_error(not_in_wfs)

    def post_load_form(self):
        """ When the data has been loaded, check which tab to display. """
        if self.fields.selection():
            self.tab.setCurrentIndex(0)
        else:
            self.tab.setCurrentIndex(1)

    def generate_table_clicked(self):
        """ Template about HTML table. """
        layer = self.layer.currentLayer()
        if not layer:
            return

        html_maptip_dialog = HtmlMapTipDialog(layer)
        if not html_maptip_dialog.exec():
            return

        if self.html_template.html_content():
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Question)
            box.setWindowIcon(QIcon(resources_path('icons', 'icon.png')),)
            box.setWindowTitle(tr('Replace existing HTML with the template'))
            box.setText(tr('This will erase your previous HTML.'))
            box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            box.setDefaultButton(QMessageBox.StandardButton.No)
            result = box.exec()
            if result == QMessageBox.StandardButton.No:
                return

        result = html_maptip_dialog.map_tip()
        self.html_template.set_html_content(result)

    def enable_color(self):
        if self.display_geometry.isChecked():
            self.color.setEnabled(True)
            self.color.setColor(QColor('blue'))
        else:
            self.color.setEnabled(False)
            self.color.setToNull()

    def validate(self) -> str:
        upstream = super().validate()
        if upstream:
            return upstream

        layer = self.layer.currentLayer()
        not_in_wfs = self.is_layer_in_wfs(layer)
        if not_in_wfs:
            return not_in_wfs

        if self.fields.selection() and self.html_template.html_content() != '':
            return tr("It's not possible to use both 'fields' and 'HTML template'. Please choose only one.")

        if not self.fields.selection() and not self.html_template.html_content():
            return tr('Either an HTML template or a field must be set.')
