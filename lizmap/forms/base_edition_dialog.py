"""Base class for the edition dialog."""

import json
import re

from collections import OrderedDict
from typing import Union

from qgis.core import QgsProject, QgsVectorLayer
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QBrush, QColor, QDesktopServices, QIcon
from qgis.PyQt.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QMessageBox,
    QPlainTextEdit,
)

from lizmap import DEFAULT_LWC_VERSION
from lizmap.definitions.base import InputType
from lizmap.definitions.definitions import LwcVersions, ServerComboData
from lizmap.definitions.online_help import online_lwc_help
from lizmap.dialogs.wizard_group import WizardGroupDialog
from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.qt_style_sheets import NEW_FEATURE_COLOR, NEW_FEATURE_CSS

__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from lizmap.tools import is_database_layer


class BaseEditionDialog(QDialog):

    """ Class managing the edition form, either creation or editing. """

    def __init__(self, parent: QDialog = None, unicity=None):
        """ Constructor. """
        # parent is the main UI of the plugin
        # noinspection PyArgumentList
        super().__init__(parent)
        self.parent = parent
        self.config = None
        self.unicity = unicity

        # Most edition dialogs are based on a layer as input. Only the layout dialog is not.
        self.layer = None
        self.primary_key = None
        self.primary_key_valid = None

        self.lwc_versions = OrderedDict()
        self.lwc_versions[LwcVersions.Lizmap_3_1] = []
        self.lwc_versions[LwcVersions.Lizmap_3_2] = []
        self.lwc_versions[LwcVersions.Lizmap_3_3] = []
        self.lwc_versions[LwcVersions.Lizmap_3_4] = []
        self.lwc_versions[LwcVersions.Lizmap_3_5] = []
        self.lwc_versions[LwcVersions.Lizmap_3_6] = []
        self.lwc_versions[LwcVersions.Lizmap_3_7] = []

    def setup_ui(self):
        """ Build the UI. """
        self.button_box.button(QDialogButtonBox.Help).setToolTip(
            tr('Open the online documentation for this feature.'))
        self.error.setTextInteractionFlags(Qt.TextSelectableByMouse)

        if not self.config.help_path():
            self.button_box.button(QDialogButtonBox.Help).setVisible(False)

        self.button_box.button(QDialogButtonBox.Help).clicked.connect(self.open_help)
        self.button_box.button(QDialogButtonBox.Cancel).clicked.connect(self.close)
        self.button_box.button(QDialogButtonBox.Ok).clicked.connect(self.accept)
        self.error.setVisible(False)

        for layer_config in self.config.layer_config.values():
            widget = layer_config.get('widget')

            tooltip = layer_config.get('tooltip')
            if tooltip:
                label = layer_config.get('label')
                if label:
                    label.setToolTip(tooltip)
                if widget:
                    widget.setToolTip(tooltip)

            if layer_config['type'] in (InputType.List, InputType.CheckBoxAsDropdown):
                if widget is not None:
                    items = layer_config.get('items')
                    if items:
                        for item in items:
                            icon = item.value.get('icon')
                            if icon:
                                widget.addItem(QIcon(icon), item.value['label'], item.value['data'])
                            else:
                                widget.addItem(item.value['label'], item.value['data'])
                            index = widget.findData(item.value['data'])
                            tooltip = item.value.get('tooltip')
                            if tooltip:
                                widget.setItemData(index, tooltip, Qt.ToolTipRole)
                        default = layer_config.get('default')
                        if default and not isinstance(default, (list, tuple)):
                            index = widget.findData(default.value['data'])
                            widget.setCurrentIndex(index)

            if layer_config['type'] == InputType.CheckBox:
                default_value = layer_config['default']
                if widget is not None and not hasattr(default_value, '__call__'):
                    widget.setChecked(default_value)

            if layer_config['type'] == InputType.SpinBox:
                if widget is not None:
                    unit = layer_config.get('unit')
                    if unit:
                        widget.setSuffix(unit)

                    default = layer_config.get('default')
                    if unit:
                        widget.setValue(default)

            if layer_config['type'] == InputType.Color:
                if widget is not None:
                    if layer_config['default'] == '':
                        widget.setShowNull(True)
                        widget.setToNull()
                    else:
                        widget.setDefaultColor(QColor(layer_config['default']))
                        widget.setToDefaultColor()

            if layer_config.get('read_only'):
                if widget is not None:
                    if layer_config['type'] == InputType.Text:
                        widget.setReadOnly(True)
                    elif layer_config['type'] == InputType.CheckBox:
                        # Some UX issues #338
                        # The disabled is not possible somehow ?
                        # The tooltip is not showing
                        widget.setText(tr('Read only, check the tooltip on the label'))
                        widget.setStyleSheet("font: italic;")
                        widget.setAttribute(Qt.WA_TransparentForMouseEvents)
                        widget.setFocusPolicy(Qt.NoFocus)

            if not layer_config.get('visible', True):
                if widget is not None:
                    widget.setVisible(False)
                label = layer_config.get('label')
                if label is not None:
                    label.setVisible(False)

        self.version_lwc()

    def open_help(self):
        """ Open the online documentation for the panel. """
        # noinspection PyArgumentList
        QDesktopServices.openUrl(online_lwc_help(self.config.help_path()))

    def version_lwc(self):
        """ Make all colors about widgets if it is available or not. """
        if self.parent:
            current_version = self.parent.current_lwc_version()
        else:
            current_version = DEFAULT_LWC_VERSION

        # For labels in the UI files, which are not part of the definitions.
        found = False
        for lwc_version, items in self.lwc_versions.items():
            if found:
                for item in items:
                    item.setStyleSheet(NEW_FEATURE_CSS)

            else:
                for item in items:
                    item.setStyleSheet('')

            if lwc_version == current_version:
                found = True

        # For definition properties
        found = False
        for lwc_version in self.lwc_versions.keys():
            if found:
                for layer_config in self.config.layer_config.values():
                    version = layer_config.get('version')
                    if version == lwc_version:
                        label = layer_config.get('label')
                        if label:
                            label.setStyleSheet(NEW_FEATURE_CSS)
                        if layer_config['type'] == InputType.CheckBox:
                            layer_config.get('widget').setStyleSheet(NEW_FEATURE_CSS)
            else:
                for layer_config in self.config.layer_config.values():
                    version = layer_config.get('version')
                    if version == lwc_version:
                        label = layer_config.get('label')
                        if label:
                            label.setStyleSheet('')
                        if layer_config['type'] == InputType.CheckBox:
                            layer_config.get('widget').setStyleSheet('')

            if lwc_version == current_version:
                found = True

        # For items in combobox
        found = False
        for lwc_version in self.lwc_versions.keys():
            if found:
                for layer_config in self.config.layer_config.values():
                    widget_type = layer_config.get('type')
                    if not layer_config.get('items_depend_on_lwc_version'):
                        continue

                    if widget_type != InputType.List:
                        continue

                    for item in layer_config['items']:
                        if item.value.get('version'):
                            item_combo = layer_config['widget'].model().item(
                                layer_config['widget'].findData(item.value.get('data'))
                            )
                            brush = QBrush()
                            brush.setStyle(Qt.SolidPattern)
                            brush.setColor(QColor(NEW_FEATURE_COLOR))
                            item_combo.setBackground(brush)

            else:
                for layer_config in self.config.layer_config.values():
                    widget_type = layer_config.get('type')
                    if not layer_config.get('items_depend_on_lwc_version'):
                        continue

                    if widget_type != InputType.List:
                        continue

                    for item in layer_config['items']:
                        if item.value.get('version'):
                            item_combo = layer_config['widget'].model().item(
                                layer_config['widget'].findData(item.value.get('data'))
                            )
                            item_combo.setBackground(QBrush())

            if lwc_version == current_version:
                found = True

    @staticmethod
    def is_layer_in_wfs(layer: QgsVectorLayer) -> Union[None, str]:
        """ Check if the layer in the WFS capabilities. """
        # noinspection PyArgumentList
        for wfs_layer in QgsProject.instance().readListEntry('WFSLayers', '')[0]:
            if layer.id() == wfs_layer:
                return None

        msg = tr(
            'The layers you have chosen for this tool must be checked in the "WFS Capabilities"\n'
            ' option of the QGIS Server tab in the "Project Properties" dialog.')
        return msg

    def validate(self):
        """ Validate the form or not.

        It returns None if it's OK otherwise a message to be displayed.
        """
        if self.unicity:
            for key in self.unicity:
                for k, layer_config in self.config.layer_config.items():
                    if key == k:
                        if layer_config['type'] == InputType.Layer:
                            if layer_config['widget'].currentLayer().id() in self.unicity[key]:
                                msg = tr(
                                    'A duplicated "{}"="{}" is already in the table.'.format(
                                        key, layer_config['widget'].currentLayer().name()))
                                return msg
                        else:
                            raise Exception('InputType "{}" not implemented'.format(layer_config['type']))

        if self.primary_key_valid is not None:
            if not self.primary_key_valid:
                msg = tr(
                    "The primary key defined in your datasource for the layer '{}' is not valid. The layer is stored "
                    "in a database and must have a valid primary key defined in the project."
                ).format(self.layer.currentLayer().name())
                return msg

        for k, layer_config in self.config.layer_config.items():
            if layer_config['type'] in (InputType.Field, InputType.PrimaryKeyField):
                widget = layer_config.get('widget')

                if widget is None:
                    # Dataviz does not have widget for Y, Z
                    continue

                if not widget.allowEmptyFieldName():
                    if widget.currentField() == '':
                        names = re.findall('.[^A-Z]*', k)
                        names = [n.lower().replace('_', ' ') for n in names]
                        msg = tr('The field "{}" is mandatory.').format(' '.join(names))
                        return msg

        return None

    def accept(self):
        """ The "accept" slot to close the dialog. """
        message = self.validate()
        if message:
            self.error.setVisible(True)
            self.error.setText(message)
            self.error.setWordWrap(True)
        else:
            super().accept()

    def show_error(self, message):
        """ Show the error bar or not. """
        if message:
            self.error.setVisible(True)
            self.error.setText(message)
        else:
            self.error.setVisible(False)
            self.error.setText("")

    def load_collection(self, value):
        """Load a collection to JSON."""
        # This function is implemented in child class.
        pass

    def save_collection(self) -> dict:
        """Save a collection into JSON."""
        # This function is implemented in child class.
        pass

    def primary_keys_collection(self) -> list:
        """List of unique keys in the collection."""
        # This function is implemented in child class.
        pass

    def post_load_form(self):
        """Function executed after the form with data has been loaded."""
        # This function is implemented in child class.
        pass

    def load_form(self, data: OrderedDict) -> None:
        """A dictionary to load in the UI.

        If this function is called, it means we are editing an existing row.
        """
        layer_properties = OrderedDict()
        for key, definition in self.config.layer_config.items():
            if definition.get('plural') is None:
                layer_properties[key] = definition

        for key, definition in layer_properties.items():
            value = data.get(key)

            if definition['type'] == InputType.Layer:
                # noinspection PyArgumentList
                layer = QgsProject.instance().mapLayer(value)
                definition['widget'].setLayer(layer)
            elif definition['type'] == InputType.Layers:
                definition['widget'].set_selection(value)
            elif definition['type'] in (InputType.Field, InputType.PrimaryKeyField):
                definition['widget'].setField(value)
            elif definition['type'] == InputType.Fields:
                definition['widget'].set_selection(value.split(','))
            elif definition['type'] == InputType.File:
                definition['widget'].setFilePath(value)
            elif definition['type'] == InputType.CheckBox:
                definition['widget'].setChecked(value)
            elif definition['type'] == InputType.Color:
                color = QColor(value)
                if color.isValid():
                    definition['widget'].setDefaultColor(color)
                    definition['widget'].setColor(color)
                else:
                    definition['widget'].setToNull()
            elif definition['type'] in (InputType.List, InputType.CheckBoxAsDropdown):
                if definition.get('multiple_selection', False):
                    for val in value:
                        index = definition['widget'].findData(val)
                        definition['widget'].setItemCheckState(index, Qt.Checked)
                else:
                    index = definition['widget'].findData(value)
                    definition['widget'].setCurrentIndex(index)
            elif definition['type'] == InputType.SpinBox:
                definition['widget'].setValue(value)
            elif definition['type'] == InputType.Text:
                definition['widget'].setText(value)
            elif definition['type'] == InputType.Json:
                if value:
                    definition['widget'].setText(json.dumps(value))
            elif definition['type'] == InputType.MultiLine:
                widget = definition['widget']
                if isinstance(widget, QPlainTextEdit):
                    widget.setPlainText(value)
                else:
                    widget.setText(value)
            elif definition['type'] == InputType.HtmlWysiwyg:
                definition['widget'].set_html_content(value)
            elif definition['type'] == InputType.Collection:
                self.load_collection(value)
            else:
                raise Exception('InputType "{}" not implemented'.format(definition['type']))

        self.post_load_form()
        self.enable_primary_key_field()

    def save_form(self) -> OrderedDict:
        """Save the UI in the dictionary with QGIS objects"""
        layer_properties = OrderedDict()
        for key, definition in self.config.layer_config.items():
            if definition.get('plural') is None:
                layer_properties[key] = definition

        data = OrderedDict()

        for key, definition in layer_properties.items():

            if definition['type'] == InputType.Layer:
                value = definition['widget'].currentLayer().id()
            elif definition['type'] == InputType.Layers:
                value = definition['widget'].selection()
            elif definition['type'] in (InputType.Field, InputType.PrimaryKeyField):
                value = definition['widget'].currentField()
            elif definition['type'] == InputType.Fields:
                value = ','.join(definition['widget'].selection())
            elif definition['type'] == InputType.File:
                value = definition['widget'].filePath()
            elif definition['type'] == InputType.Color:
                widget = definition['widget']
                if widget.isNull():
                    value = ''
                else:
                    value = widget.color().name()
            elif definition['type'] == InputType.CheckBox:
                value = definition['widget'].isChecked()
            elif definition['type'] in (InputType.List, InputType.CheckBoxAsDropdown):
                if definition.get('multiple_selection', False):
                    value = definition['widget'].checkedItemsData()
                else:
                    value = definition['widget'].currentData()
            elif definition['type'] == InputType.SpinBox:
                value = definition['widget'].value()
            elif definition['type'] == InputType.Text:
                value = definition['widget'].text().strip(' \t')
            elif definition['type'] == InputType.MultiLine:
                widget = definition['widget']
                if isinstance(widget, QPlainTextEdit):
                    value = definition['widget'].toPlainText()
                else:
                    value = definition['widget'].text()
                value = value.strip(' \t')
            elif definition['type'] == InputType.HtmlWysiwyg:
                value = definition['widget'].html_content()
            elif definition['type'] == InputType.Json:
                text = definition['widget'].text()
                if text:
                    value = json.loads(text)
                else:
                    value = ''
            elif definition['type'] == InputType.Collection:
                value = self.save_collection()
            else:
                raise Exception('InputType "{}" not implemented'.format(definition['type']))

            data[key] = value
        return data

    def enable_primary_key_field(self):
        """ Enable or not the primary key widget.

        For a database based layer (PG, SQLite, GPKG) the widget is disabled."""
        if not self.layer:
            self.primary_key_valid = None
            return
        if not self.primary_key:
            self.primary_key_valid = None
            return

        tooltip = self.primary_key.toolTip()
        extra_tooltip = tr('The primary key is defined by the dataprovider only for layer stored in a database.')
        self.primary_key.setToolTip('{} {}'.format(tooltip, extra_tooltip))

        layer = self.layer.currentLayer()
        if not is_database_layer(layer):
            self.primary_key.setEnabled(True)
            self.primary_key.setAllowEmptyFieldName(False)
            self.primary_key_valid = None
            return

        # We trust the datasource
        # And we do not trust the legacy CFG
        self.primary_key.setEnabled(False)
        self.primary_key.setAllowEmptyFieldName(True)
        pks = layer.primaryKeyAttributes()
        if len(pks) == 0:
            # Must be an issue for the user to validate the form, because the widget is disabled
            # The datasource must be fixed
            self.primary_key_valid = False
            return

        if len(pks) >= 2:
            # As well, the user must add a PK and an unicity constraint
            # Not possible to validate the form
            self.primary_key_valid = False
            return

        # Single field as a primary key
        # We do not trust the CFG anymore, let's go datasource
        name = layer.fields().at(pks[0]).name()
        self.primary_key.setField(name)
        self.primary_key_valid = True

    def open_wizard_dialog(self, helper: str):
        """ Internal function to open the wizard ACL. """
        # Duplicated in plugin.py, _open_wizard_group()
        json_metadata = self.parent.current_server_info(ServerComboData.JsonMetadata.value)
        acl = json_metadata.get('acl')
        if not acl:
            # noinspection PyArgumentList
            QMessageBox.critical(
                self,
                tr('Upgrade your Lizmap instance'),
                tr(
                    "Your current Lizmap instance, running version {}, is not providing the needed information. "
                    "You should upgrade your Lizmap instance to at least 3.6.1 to use this wizard."
                ).format(json_metadata["info"]["version"]),
                QMessageBox.Ok
            )
            return None
        # End of duplicated

        wizard_dialog = WizardGroupDialog(helper, self.allowed_groups.text(), acl['groups'])
        if not wizard_dialog.exec_():
            return

        text = wizard_dialog.preview.text()
        if not text:
            return

        self.allowed_groups.setText(text)
