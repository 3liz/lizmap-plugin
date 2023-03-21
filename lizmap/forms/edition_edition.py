"""Dialog for edition layer edition."""

from qgis.core import (
    QgsMapLayerProxyModel,
    QgsProject,
    QgsProviderRegistry,
    QgsWkbTypes,
)
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QMessageBox

from lizmap.definitions.definitions import LwcVersions
from lizmap.definitions.edition import EditionDefinitions, layer_provider
from lizmap.forms.base_edition_dialog import BaseEditionDialog
from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.qgis_plugin_tools.tools.resources import load_ui, resources_path

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


CLASS = load_ui('ui_form_edition.ui')


class EditionLayerDialog(BaseEditionDialog, CLASS):

    def __init__(self, parent=None, unicity=None):
        super().__init__(parent, unicity)
        self.setupUi(self)
        self.config = EditionDefinitions()
        self.config.add_layer_widget('layerId', self.layer)
        self.config.add_layer_widget('createFeature', self.create_feature)
        self.config.add_layer_widget('allow_without_geom', self.without_geom)
        self.config.add_layer_widget('modifyAttribute', self.edit_attributes)
        self.config.add_layer_widget('modifyGeometry', self.edit_geometry)
        self.config.add_layer_widget('deleteFeature', self.delete_feature)
        self.config.add_layer_widget('acl', self.allowed_groups)
        self.config.add_layer_widget('snap_layers', self.layers)
        self.config.add_layer_widget('snap_vertices', self.snap_node)
        self.config.add_layer_widget('snap_segments', self.snap_segments)
        self.config.add_layer_widget('snap_intersections', self.snap_intersection)
        self.config.add_layer_widget('snap_vertices_tolerance', self.vertices_tolerance)
        self.config.add_layer_widget('snap_segments_tolerance', self.segments_tolerance)
        self.config.add_layer_widget('snap_intersections_tolerance', self.intersections_tolerance)
        self.config.add_layer_widget('provider', self.provider)

        self.config.add_layer_label('layerId', self.label_layer)
        self.config.add_layer_label('createFeature', self.label_create)
        self.config.add_layer_label('allow_without_geom', self.label_without_geom)
        self.config.add_layer_label('modifyAttribute', self.label_edit_attributes)
        self.config.add_layer_label('modifyGeometry', self.label_edit_geometry)
        self.config.add_layer_label('deleteFeature', self.label_delete)
        self.config.add_layer_label('acl', self.label_allowed_groups)
        self.config.add_layer_label('snap_layers', self.label_layers_snapping)
        self.config.add_layer_label('provider', self.label_provider)

        self.layer.layerChanged.connect(self.layer_changed)
        self.layer.layerChanged.connect(self.check_layer_wfs)
        self.layer.setFilters(QgsMapLayerProxyModel.VectorLayer)
        providers = QgsProviderRegistry.instance().providerList()
        providers.remove('postgres')
        self.layer.setExcludedProviders(providers)
        self.layers.set_project(QgsProject.instance())

        self.lwc_versions[LwcVersions.Lizmap_3_4] = [
            self.group_box_snapping
        ]
        self.lwc_versions[LwcVersions.Lizmap_3_6] = [
            self.button_wizard_group,
        ]

        # Wizard ACL group
        icon = QIcon(resources_path('icons', 'user_group.svg'))
        self.button_wizard_group.setText('')
        self.button_wizard_group.setIcon(icon)
        self.button_wizard_group.clicked.connect(self.open_wizard_group)
        self.button_wizard_group.setToolTip(tr("Open the group wizard"))

        self.setup_ui()
        self.check_layer_wfs()
        self.layer_changed()

    def check_layer_wfs(self):
        """ When the layer has changed in the combobox, check if the layer is published as WFS. """
        layer = self.layer.currentLayer()
        if not layer:
            self.show_error(tr('A layer is mandatory.'))
            return

        not_in_wfs = self.is_layer_in_wfs(layer)
        self.show_error(not_in_wfs)

    def post_load_form(self):
        self.layer_changed()

    def layer_changed(self):
        layer = self.layer.currentLayer()
        self.provider.setText(layer_provider(layer))

        if not layer:
            return

        if layer.isSpatial():
            self.without_geom.setEnabled(True)
            self.edit_geometry.setEnabled(True)
            self.label_edit_geometry.setEnabled(True)
            self.label_without_geom.setEnabled(True)
        else:
            self.without_geom.setEnabled(False)
            self.edit_geometry.setEnabled(False)
            self.label_edit_geometry.setEnabled(False)
            self.label_without_geom.setEnabled(False)
            self.without_geom.setChecked(False)
            self.edit_geometry.setChecked(False)

    def open_wizard_group(self):
        """ When the user clicks on the group wizard. """
        layer = self.layer.currentLayer()
        if not layer:
            return

        helper = tr("Setting groups for the layer editing capabilities '{}'").format(layer.name())
        super().open_wizard_dialog(helper)

    def validate(self) -> str:
        layer = self.layer.currentLayer()
        if not layer:
            return tr('A layer is mandatory.')

        upstream = super().validate()
        if upstream:
            return upstream

        not_in_wfs = self.is_layer_in_wfs(layer)
        if not_in_wfs:
            return not_in_wfs

        create_feature = self.create_feature.isChecked()
        modify_attribute = self.edit_attributes.isChecked()
        modify_geometry = self.edit_geometry.isChecked()
        delete_feature = self.delete_feature.isChecked()
        if not create_feature and not modify_attribute and not modify_geometry and not delete_feature:
            return tr('At least one action is mandatory.')

        # Check Z or M values which will be lost when editing
        geometry_type = layer.wkbType()
        # noinspection PyArgumentList
        has_m_values = QgsWkbTypes.hasM(geometry_type)
        # noinspection PyArgumentList
        has_z_values = QgsWkbTypes.hasZ(geometry_type)
        if has_z_values or has_m_values:
            QMessageBox.warning(
                self,
                tr('Editing Z/M Values'),
                tr('Be careful, editing this layer with Lizmap will set the Z and M to 0.'),
            )

        has_snap = self.snap_node.isChecked() or self.snap_segments.isChecked() or self.snap_intersection.isChecked()
        layers = self.layers.selection()
        if len(layers) == 0 and has_snap:
            return tr('One snapping checkbox is checked, so at least one layer is mandatory in the list.')

        if len(layers) > 0 and not has_snap:
            return tr('One layer is selected in the list, so at least one snapping mode is mandatory.')

        missing_layers = []
        for layer in layers:
            wfs_layers_list = QgsProject.instance().readListEntry('WFSLayers', '')[0]
            for wfs_layer in wfs_layers_list:
                if layer == wfs_layer:
                    break
            else:
                missing_layers.append(layer)
        if missing_layers:
            missing_layers = [QgsProject.instance().mapLayer(layer_id).name() for layer_id in missing_layers]
            msg = tr(
                'The layer "{}" for the snapping must be checked in the "WFS Capabilities"\n'
                ' option of the QGIS Server tab in the "Project Properties" dialog.').format(', '.join(missing_layers))
            return msg
