"""Dialog for layout edition."""
from qgis.core import QgsMasterLayoutInterface, QgsProject
from qgis.gui import QgsFileWidget
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon

from lizmap.definitions.layouts import Dpi, FormatType, LayoutsDefinitions
from lizmap.forms.base_edition_dialog import BaseEditionDialog
from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.qgis_plugin_tools.tools.resources import load_ui, resources_path

__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


CLASS = load_ui('ui_form_layout.ui')


class LayoutEditionDialog(BaseEditionDialog, CLASS):

    def __init__(self, parent=None, unicity=None):
        super().__init__(parent, unicity)
        self.setupUi(self)
        self.parent = parent
        self.config = LayoutsDefinitions()
        self.config.add_layer_widget('layout', self.layout)
        self.config.add_layer_widget('enabled', self.enabled)
        self.config.add_layer_widget('icon', self.icon)
        self.config.add_layer_widget('allowed_groups', self.allowed_groups)
        self.config.add_layer_widget('formats_available', self.formats)
        self.config.add_layer_widget('dpi_available', self.dpi)
        self.config.add_layer_widget('default_format', self.default_format)
        self.config.add_layer_widget('default_dpi', self.default_dpi)

        self.config.add_layer_label('layout', self.label_layout)
        self.config.add_layer_label('enabled', self.label_enabled)
        self.config.add_layer_label('icon', self.label_icon)
        self.config.add_layer_label('allowed_groups', self.allowed_groups)
        self.config.add_layer_label('formats_available', self.label_formats)
        self.config.add_layer_label('dpi_available', self.label_dpi)
        self.config.add_layer_label('default_format', self.label_default_format)
        self.config.add_layer_label('default_dpi', self.label_default_dpi)

        self.layout.setReadOnly(True)

        # Wizard ACL group
        icon = QIcon(resources_path('icons', 'user_group.svg'))
        self.button_wizard_group.setText('')
        self.button_wizard_group.setIcon(icon)
        self.button_wizard_group.clicked.connect(self.open_wizard_group)
        self.button_wizard_group.setToolTip(tr("Open the group wizard"))

        # Icon
        # TODO, this can be improved according to the hosting variable
        # "media" folder, SVG directory or absolute path
        self.icon: QgsFileWidget
        self.icon.setFilter("Images SVG, PNG, JPG (*.png *.jpg *.jpeg *.svg)")
        self.icon.setRelativeStorage(QgsFileWidget.RelativeProject)

        self.setup_ui()

    def post_load_form(self):
        """ When the form has been loaded. """
        manager = QgsProject.instance().layoutManager()
        layout = manager.layoutByName(self.layout.text())

        if layout.layoutType() == QgsMasterLayoutInterface.PrintLayout:
            for _print_layout in manager.printLayouts():
                if _print_layout.name() == self.layout.text():
                    atlas_layout = _print_layout
                    break

        if not atlas_layout:
            # The report shouldn't be loaded
            return

        is_atlas = atlas_layout.atlas().enabled()
        self.icon.setEnabled(is_atlas)
        self.label_icon.setEnabled(is_atlas)

        self.formats.setEnabled(not is_atlas)
        self.dpi.setEnabled(not is_atlas)
        self.default_format.setEnabled(not is_atlas)
        self.default_dpi.setEnabled(not is_atlas)
        self.label_formats.setEnabled(not is_atlas)
        self.label_dpi.setEnabled(not is_atlas)
        self.label_default_format.setEnabled(not is_atlas)
        self.label_default_dpi.setEnabled(not is_atlas)

        # Reset some values
        if is_atlas:
            # Formats options
            for index, item in enumerate(self.config.layer_config.get('formats_available')['items']):
                self.formats.setItemCheckState(index, Qt.Checked if item == FormatType.Pdf else Qt.Unchecked)

            # Default format
            index = self.default_format.findData(FormatType.Pdf.value['data'])
            self.default_format.setCurrentIndex(index)

            # DPI options
            for index, item in enumerate(self.config.layer_config.get('dpi_available')['items']):
                self.dpi.setItemCheckState(index, Qt.Checked if item == Dpi.Dpi100 else Qt.Unchecked)

            # Default DPI
            index = self.default_dpi.findData(Dpi.Dpi100.value['data'])
            self.default_dpi.setCurrentIndex(index)
        else:
            self.icon.setFilePath("")

    def validate(self) -> str:
        upstream = super().validate()
        if upstream:
            return upstream

        default_format = self.default_format.currentData()
        if default_format not in self.formats.checkedItemsData():
            return tr('The default format is not the available list.')

        default_dpi = self.default_dpi.currentData()
        if default_dpi not in self.dpi.checkedItemsData():
            return tr('The default DPI is not the available list.')

    def open_wizard_group(self):
        """ Open the wizard about ACL. """
        helper = tr("Setting groups for the layout print capabilities '{}'").format(self.layout.text())
        super().open_wizard_dialog(helper)
