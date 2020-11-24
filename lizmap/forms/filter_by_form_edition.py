"""Dialog for filter by form."""

from qgis.core import QgsMapLayerProxyModel, QgsProject

from lizmap.definitions.filter_by_form import FilterByFormDefinitions
from lizmap.forms.base_edition_dialog import BaseEditionDialog
from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.qgis_plugin_tools.tools.resources import load_ui

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


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
        self.config.add_layer_widget('min_date', self.min_date)
        self.config.add_layer_widget('max_date', self.max_date)
        self.config.add_layer_widget('format', self.filter_format)
        self.config.add_layer_widget('splitter', self.splitter)

        self.config.add_layer_label('layerId', self.label_layer)
        self.config.add_layer_label('title', self.label_title)
        self.config.add_layer_label('type', self.label_type)
        self.config.add_layer_label('field', self.label_field)
        self.config.add_layer_label('min_date', self.label_min_date)
        self.config.add_layer_label('max_date', self.label_max_date)
        self.config.add_layer_label('format', self.label_format)
        self.config.add_layer_label('splitter', self.label_splitter)

        self.type.addItem(tr('Text'), 'text')
        self.type.addItem(tr('Unique values'), 'uniquevalues')
        self.type.addItem(tr('Numeric'), 'numeric')
        self.type.addItem(tr('Date'), 'date')

        self.filter_format.addItem(tr('Checkboxes'), 'checkboxes')
        self.filter_format.addItem(tr('Combobox'), 'select')

        self.layer.setFilters(QgsMapLayerProxyModel.VectorLayer)

        self.layer.layerChanged.connect(self.field.setLayer)
        self.layer.layerChanged.connect(self.min_date.setLayer)
        self.layer.layerChanged.connect(self.max_date.setLayer)

        self.field.setLayer(self.layer.currentLayer())
        self.min_date.setLayer(self.layer.currentLayer())
        self.max_date.setLayer(self.layer.currentLayer())

        self.field.setAllowEmptyFieldName(False)
        self.min_date.setAllowEmptyFieldName(False)
        self.max_date.setAllowEmptyFieldName(True)

        block_list = []
        for layer in QgsProject().instance().mapLayers().values():
            if layer.providerType() not in ('ogr', 'postgres', 'spatialite'):
                block_list.append(layer)
            if layer.providerType() == 'ogr':
                if '|layername=' not in layer.dataProvider().dataSourceUri():
                    block_list.append(layer)
        self.layer.setExceptedLayerList(block_list)

        self.setup_ui()
        self.update_visibility()
        self.type.currentIndexChanged.connect(self.update_visibility)

    def update_visibility(self):
        """Show/Hide fields depending of chosen type."""
        index = self.type.currentIndex()
        data = self.type.itemData(index)

        if data == 'date':
            self.min_date.setVisible(True)
            self.min_date.setAllowEmptyFieldName(False)
            self.max_date.setVisible(True)
            self.label_min_date.setVisible(True)
            self.label_max_date.setVisible(True)
        else:
            self.min_date.setVisible(False)
            self.min_date.setAllowEmptyFieldName(True)
            self.min_date.setField('')
            self.max_date.setVisible(False)
            self.max_date.setField('')
            self.label_min_date.setVisible(False)
            self.label_max_date.setVisible(False)

        if data == 'uniquevalues':
            self.filter_format.setVisible(True)
            index = self.filter_format.findData('')
            self.filter_format.removeItem(index)
            self.splitter.setVisible(True)
            self.label_format.setVisible(True)
            self.label_splitter.setVisible(True)
        else:
            self.filter_format.setVisible(False)
            self.filter_format.addItem('', '')
            index = self.filter_format.findData('')
            self.filter_format.setCurrentIndex(index)
            self.splitter.setVisible(False)
            self.splitter.setText('')
            self.label_format.setVisible(False)
            self.label_splitter.setVisible(False)

        if data in ['text', 'uniquevalues', 'numeric']:
            self.field.setVisible(True)
            self.field.setAllowEmptyFieldName(False)
            self.label_field.setVisible(True)
        else:
            self.field.setVisible(False)
            self.field.setAllowEmptyFieldName(True)
            self.field.setField('')
            self.label_field.setVisible(False)

    def validate(self) -> str:
        upstream = super().validate()
        if upstream:
            return upstream

        layer = self.layer.currentLayer()
        wfs_layers_list = QgsProject.instance().readListEntry('WFSLayers', '')[0]
        for wfs_layer in wfs_layers_list:
            if layer.id() == wfs_layer:
                break
        else:
            msg = tr(
                'The layers you have chosen for this tool must be checked in the "WFS Capabilities"\n'
                ' option of the QGIS Server tab in the "Project Properties" dialog.')
            return msg

        index = self.type.currentIndex()
        data = self.type.itemData(index)

        if data == 'date':
            if not self.min_date.currentField():
                return tr('Field min date is mandatory.')
        elif data in ['text', 'uniquevalues', 'numeric']:
            if not self.field.currentField():
                return tr('Field is mandatory.')
        else:
            raise Exception('Unknown option')
