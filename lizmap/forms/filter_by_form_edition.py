"""Dialog for filter by form."""

from qgis.core import QgsFields, QgsMapLayerProxyModel, QgsProject
from qgis.PyQt.QtGui import QIcon

from lizmap import LwcVersions
from lizmap.definitions.filter_by_form import FilterByFormDefinitions
from lizmap.forms.base_edition_dialog import BaseEditionDialog
from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.qgis_plugin_tools.tools.resources import load_ui
from lizmap.tools import is_database_layer

__copyright__ = 'Copyright 2022, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


CLASS = load_ui('ui_form_filter_by_form.ui')


class FilterByFormEditionDialog(BaseEditionDialog, CLASS):

    def __init__(self, parent=None, unicity=None):
        super().__init__(parent, unicity)
        self.setupUi(self)
        self.config = FilterByFormDefinitions()
        self.config.add_layer_widget('layerId', self.layer)
        self.config.add_layer_widget('title', self.title)
        self.config.add_layer_widget('type', self.type)
        self.config.add_layer_widget('field', self.field)
        self.config.add_layer_widget('start_field', self.start_field)
        self.config.add_layer_widget('end_field', self.end_field)
        self.config.add_layer_widget('format', self.filter_format)
        self.config.add_layer_widget('splitter', self.splitter)

        self.config.add_layer_label('layerId', self.label_layer)
        self.config.add_layer_label('title', self.label_title)
        self.config.add_layer_label('type', self.label_type)
        self.config.add_layer_label('field', self.label_field)
        self.config.add_layer_label('start_field', self.label_start_field)
        self.config.add_layer_label('end_field', self.label_end_field)
        self.config.add_layer_label('format', self.label_format)
        self.config.add_layer_label('splitter', self.label_splitter)

        # TODO this shouldn't be here but in the definitions package
        self.type.addItem(
            QIcon(":images/themes/default/mIconFieldText.svg"),
            tr('Text'),
            'text'
        )
        self.type.addItem(
            QIcon(":images/themes/default/algorithms/mAlgorithmUniqueValues.svg"),
            tr('Unique values'),
            'uniquevalues'
        )
        self.type.addItem(
            QIcon(":images/themes/default/mIconFieldInteger.svg"),
            tr('Numeric'),
            'numeric',
        )
        self.type.addItem(
            QIcon(":images/themes/default/mIconFieldDateTime.svg"),
            tr('Date'),
            'date',
        )

        self.filter_format.addItem(
            QIcon(":images/themes/default/mIconDeselected.svg"),
            tr('Checkboxes'),
            'checkboxes'
        )
        self.filter_format.addItem(
            QIcon(":images/themes/default/mIconDropDownMenu.svg"),
            tr('Combobox'),
            'select'
        )

        self.layer.setFilters(QgsMapLayerProxyModel.VectorLayer)

        self.layer.layerChanged.connect(self.check_layer_wfs)
        self.layer.layerChanged.connect(self.field.setLayer)
        self.layer.layerChanged.connect(self.start_field.setLayer)
        self.layer.layerChanged.connect(self.end_field.setLayer)

        self.field.setLayer(self.layer.currentLayer())
        self.start_field.setLayer(self.layer.currentLayer())
        self.end_field.setLayer(self.layer.currentLayer())

        self.lwc_versions[LwcVersions.Lizmap_3_7] = [
            # self.label_end_field, this one, it depends on the type of filter : date versus numeric
        ]

        block_list = []
        for layer in QgsProject().instance().mapLayers().values():
            if not is_database_layer(layer):
                block_list.append(layer)
        self.layer.setExceptedLayerList(block_list)

        self.setup_ui()
        self.update_visibility()
        self.type.currentIndexChanged.connect(self.update_visibility)
        self.check_layer_wfs()

    def check_layer_wfs(self):
        """ When the layer has changed in the combobox, check if the layer is published as WFS. """
        layer = self.layer.currentLayer()
        if not layer:
            self.show_error(tr('A layer is mandatory.'))
            return

        not_in_wfs = self.is_layer_in_wfs(layer)
        self.show_error(not_in_wfs)

    def update_visibility(self):
        """Show/Hide fields depending on chosen type."""
        index = self.type.currentIndex()
        data = self.type.itemData(index)

        # Make all not common fields not visible by default
        # And enable them one per one
        # Field
        self.label_field.setVisible(False)
        self.field.setVisible(False)
        self.field.setAllowEmptyFieldName(True)

        # Start field
        self.label_start_field.setVisible(False)
        self.start_field.setVisible(False)
        self.start_field.setAllowEmptyFieldName(True)

        # End field
        self.label_end_field.setVisible(False)
        self.end_field.setVisible(False)
        self.end_field.setAllowEmptyFieldName(True)

        # Format
        self.filter_format.setVisible(False)
        self.label_format.setVisible(False)

        # Splitter
        self.splitter.setVisible(False)
        self.label_splitter.setVisible(False)

        if data == 'date':
            self.start_field.setVisible(True)
            self.start_field.setAllowEmptyFieldName(False)
            self.end_field.setVisible(True)
            self.label_start_field.setVisible(True)
            self.label_end_field.setVisible(True)
            if self.label_end_field in self.lwc_versions[LwcVersions.Lizmap_3_7]:
                self.lwc_versions[LwcVersions.Lizmap_3_7].remove(self.label_end_field)
        elif data == 'uniquevalues':
            self.label_field.setVisible(True)
            self.field.setVisible(True)
            self.field.setAllowEmptyFieldName(False)
            self.filter_format.setVisible(True)
            index = self.filter_format.findData('')
            self.filter_format.removeItem(index)
            self.splitter.setVisible(True)
            self.label_format.setVisible(True)
            self.label_splitter.setVisible(True)
        elif data == 'numeric':
            self.label_start_field.setVisible(True)
            self.label_end_field.setVisible(True)
            self.start_field.setVisible(True)
            self.start_field.setAllowEmptyFieldName(False)
            self.end_field.setVisible(True)
            if self.label_end_field not in self.lwc_versions[LwcVersions.Lizmap_3_7]:
                self.lwc_versions[LwcVersions.Lizmap_3_7].append(self.label_end_field)
        elif data == 'text':
            self.label_field.setVisible(True)
            self.field.setVisible(True)
            self.field.setAllowEmptyFieldName(False)
            self.filter_format.addItem('', '')
            index = self.filter_format.findData('')
            self.filter_format.setCurrentIndex(index)
            self.splitter.setText('')
        else:
            raise Exception('Unknown type')

        # Let's repaint colors on widgets because of the numeric versus date type
        self.version_lwc()

    def validate(self) -> str:
        upstream = super().validate()
        if upstream:
            return upstream

        layer = self.layer.currentLayer()
        not_in_wfs = self.is_layer_in_wfs(layer)
        if not_in_wfs:
            return not_in_wfs

        index = self.type.currentIndex()
        data = self.type.itemData(index)

        field_required = tr('Field is mandatory.')
        if data in ('numeric', 'date'):
            if not self.start_field.currentField():
                return field_required
        elif data in ('text', 'uniquevalues'):
            if not self.field.currentField():
                return field_required
        else:
            raise Exception('Unknown option')

        # Check for join, or virtual fields
        field_origin = tr(
            'The field "{}" is not provided by the underlying table. It can not come from a join or be a virtual '
            'field. This tool is using plain SQL query on the underlying table.')
        forbidden = (QgsFields.FieldOrigin.OriginJoin, QgsFields.FieldOrigin.OriginExpression)
        widget_fields = (
            self.field,
            self.start_field,
            self.end_field,
        )
        for widget in widget_fields:
            if not widget.isVisible():
                # Deeper bug, do we save this value ?
                continue

            if not widget.currentField():
                continue

            index = self.layer.currentLayer().fields().indexFromName(widget.currentField())
            if self.layer.currentLayer().fields().fieldOrigin(index) in forbidden:
                return field_origin.format(widget.currentField())
