"""Dialog to create or edit a Lizmap action."""

from __future__ import annotations

import re

from typing import TYPE_CHECKING

from qgis.core import QgsIconUtils, QgsMapLayerProxyModel, QgsProject, QgsSymbolLayerUtils, QgsVectorLayer
from qgis.gui import QgsColorButton, QgsMapLayerComboBox
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor, QIcon
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from lizmap.actions.config import Action, ActionCallback, JsonScalar, validate_action
from lizmap.actions.definitions import (
    LWC_ICONS,
    ActionGeometry,
    ActionScope,
    CallbackMethod,
    StyleKey,
)
from lizmap.toolbelt.i18n import tr

if TYPE_CHECKING:
    from collections.abc import Callable

__copyright__ = "Copyright 2026, 3Liz"
__license__ = "GPL version 3"
__email__ = "info@3liz.org"

# Value of a number spin box when the style is not set
STYLE_NUMBER_NOT_SET = -1

# Integer and decimal numbers, without leading zero, to convert an option value from the text
INTEGER_REGEX = re.compile(r"^-?(0|[1-9]\d*)$")
DECIMAL_REGEX = re.compile(r"^-?(0|[1-9]\d*)\.\d+$")


def option_value_from_text(text: str) -> JsonScalar:
    """Convert the text typed by the user to an option value.

    Lizmap Web Client sends all the values as text to PostgreSQL,
    numbers are only kept as numbers for a more readable JSON file.

    :param text: The text typed by the user.
    :return: An integer or a decimal number if the text is a number, the text otherwise.
    """
    if INTEGER_REGEX.match(text):
        return int(text)
    if DECIMAL_REGEX.match(text):
        return float(text)
    return text


def color_to_text(color: QColor) -> str:
    """Convert a color to a CSS color understood by OpenLayers.

    :param color: The color.
    :return: The color as 'rgb(r,g,b)', or as 'rgba(r,g,b,a)' if it is transparent.
    """
    if color.alpha() == 255:
        return f"rgb({color.red()},{color.green()},{color.blue()})"
    return f"rgba({color.red()},{color.green()},{color.blue()},{round(color.alphaF(), 2)})"


def color_from_text(value: JsonScalar | None) -> QColor | None:
    """Convert a CSS color from the action file to a color.

    :param value: The CSS color, such as 'blue', 'rgb(0,0,255)' or 'rgba(0,0,255,0.5)'.
    :return: The color, or None if the value is not set or not a valid color.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    color = QgsSymbolLayerUtils.parseColor(value.strip())
    return color if color.isValid() else None


class ActionEditionDialog(QDialog):
    """Dialog to create or edit a Lizmap action.

    The action is validated when the user clicks OK, an action with errors cannot be saved.
    """

    def __init__(
        self,
        parent: QWidget | None,
        project: QgsProject,
        action: Action | None = None,
        other_names: list[str] | None = None,
    ):
        """Constructor.

        :param parent: The parent widget.
        :param project: The QGIS project, to list the layers.
        :param action: The action to edit, or None to create a new one.
        :param other_names: Names of the other actions in the file, the name must be unique.
        """
        super().__init__(parent)
        self.project = project
        self.other_names = other_names or []
        # Initial style values, kept as they are if the user does not change the color
        self._initial_style: dict[StyleKey, JsonScalar] = dict(action.style) if action else {}

        self.setWindowTitle(tr("Edit the action") if action else tr("Add a new action"))
        self.setMinimumWidth(600)

        # Tabs and error label above the buttons
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget(self)
        layout.addWidget(self.tabs)
        self.tabs.addTab(self._general_tab(), tr("General"))
        self.tabs.addTab(self._options_tab(), tr("Options"))
        self.tabs.addTab(self._style_tab(), tr("Style"))
        self.tabs.addTab(self._callbacks_tab(), tr("Callbacks"))

        self.error = QLabel(self)
        self.error.setWordWrap(True)
        self.error.setStyleSheet("QLabel { color : red; }")
        self.error.setVisible(False)
        layout.addWidget(self.error)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        # Fill the form, then enable the widgets according to the scope
        if action:
            self.load_action(action)
        self.scope_changed()

    # General

    def _general_tab(self) -> QWidget:
        """Build the tab with the main properties of the action.

        :return: The tab widget.
        """
        widget = QWidget(self)
        form = QFormLayout(widget)

        self.name = QLineEdit(widget)
        self.name.setToolTip(
            tr(
                "Unique name of the action, sent to the PostgreSQL function 'lizmap_get_data' as 'action_name'. "
                "Only letters, digits, '_' or '-'."
            )
        )
        form.addRow(tr("Name"), self.name)

        self.title = QLineEdit(widget)
        self.title.setToolTip(tr("Title of the action, displayed in the web interface."))
        form.addRow(tr("Title"), self.title)

        self.description = QLineEdit(widget)
        self.description.setToolTip(tr("Optional description, displayed when the action is selected."))
        form.addRow(tr("Description"), self.description)

        self.scope = QComboBox(widget)
        self.scope.addItem(tr("Project"), ActionScope.Project)
        self.scope.addItem(tr("Layer"), ActionScope.Layer)
        self.scope.addItem(tr("Feature"), ActionScope.Feature)
        self.scope.setToolTip(
            tr(
                "Project : in the action panel. "
                "Layer : in the layer information panel. "
                "Feature : in the popup of the feature."
            )
        )
        self.scope.currentIndexChanged.connect(self.scope_changed)
        form.addRow(tr("Scope"), self.scope)

        # PostgreSQL vector layers of the project, checkable
        self.layers = QListWidget(widget)
        self.layers.setToolTip(tr("PostgreSQL layers where the action is available."))
        for layer in sorted(self.project.mapLayers().values(), key=lambda lyr: lyr.name().lower()):
            if isinstance(layer, QgsVectorLayer) and layer.providerType() == "postgres":
                item = QListWidgetItem(layer.name(), self.layers)
                item.setIcon(QgsIconUtils.iconForLayer(layer))
                item.setData(Qt.ItemDataRole.UserRole, layer.id())
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
        form.addRow(tr("Layers"), self.layers)

        self.geometry = QComboBox(widget)
        self.geometry.addItem(tr("No geometry"), None)
        for geometry in ActionGeometry:
            self.geometry.addItem(geometry.value.capitalize(), geometry)
        self.geometry.setToolTip(
            tr("Geometry the user must draw before running the action. Not available for the feature scope.")
        )
        form.addRow(tr("Geometry to draw"), self.geometry)

        # Lizmap icons, or a path to a file in the media folder
        self.icon = QComboBox(widget)
        self.icon.setEditable(True)
        self.icon.addItems(LWC_ICONS)
        self.icon.setCurrentText("icon-star")
        self.icon.setToolTip(
            tr(
                "A Lizmap icon from the list, or the path to an image in the media folder, such as 'media/icon.svg'."
            )
        )
        form.addRow(tr("Icon"), self.icon)

        self.confirm = QLineEdit(widget)
        self.confirm.setToolTip(tr("Optional message, the user must confirm before running the action."))
        form.addRow(tr("Confirmation"), self.confirm)

        return widget

    def scope_changed(self):
        """Enable the layers and the geometry according to the scope."""
        scope = self.current_scope()
        self.layers.setEnabled(scope.has_layers())
        self.geometry.setEnabled(scope.allows_geometry())

    def current_scope(self) -> ActionScope:
        """The scope selected by the user.

        :return: The scope.
        """
        return self.scope.currentData()

    def _layer_item(self, layer_id: str) -> QListWidgetItem:
        """Find the item of a layer in the list, or add it if the layer is not a PostgreSQL layer of the project.

        :param layer_id: The layer ID.
        :return: The item.
        """
        for row in range(self.layers.count()):
            item = self.layers.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == layer_id:
                return item

        # Unknown layer, kept in the list to let the user uncheck it
        item = QListWidgetItem(tr("{} (not a PostgreSQL layer in the project)").format(layer_id), self.layers)
        item.setData(Qt.ItemDataRole.UserRole, layer_id)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setForeground(QColor("red"))
        return item

    # Options

    def _options_tab(self) -> QWidget:
        """Build the tab with the options of the action.

        :return: The tab widget.
        """
        widget = QWidget(self)
        layout = QVBoxLayout(widget)

        label = QLabel(
            tr(
                "Additional parameters sent to the PostgreSQL function 'lizmap_get_data'. The values are the "
                "default ones : a JavaScript script running the action can replace them. "
                "All values are sent as text."
            ),
            widget,
        )
        label.setWordWrap(True)
        layout.addWidget(label)

        self.options = QTableWidget(0, 2, widget)
        self.options.setHorizontalHeaderLabels([tr("Parameter"), tr("Default value")])
        self.options.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.options.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.options)

        layout.addLayout(self._add_remove_buttons(self.add_option, self.options))
        return widget

    def add_option(self, key: str = "", value: JsonScalar = ""):
        """Add a row in the option table.

        :param key: The parameter name.
        :param value: The default value.
        """
        row = self.options.rowCount()
        self.options.insertRow(row)
        self.options.setItem(row, 0, QTableWidgetItem(key))
        self.options.setItem(row, 1, QTableWidgetItem(str(value)))
        if not key:
            self.options.setCurrentCell(row, 0)
            self.options.editItem(self.options.item(row, 0))

    def current_options(self) -> dict[str, JsonScalar]:
        """The options typed by the user, rows without parameter name are ignored.

        :return: The options, with numbers converted.
        """
        options = {}
        for row in range(self.options.rowCount()):
            key_item = self.options.item(row, 0)
            value_item = self.options.item(row, 1)
            key = key_item.text().strip() if key_item else ""
            if not key:
                continue
            options[key] = option_value_from_text(value_item.text().strip() if value_item else "")
        return options

    # Style

    def _style_tab(self) -> QWidget:
        """Build the tab with the style of the features returned by the action.

        :return: The tab widget.
        """
        widget = QWidget(self)
        form = QFormLayout(widget)

        label = QLabel(
            tr("Style of the geometries returned by the action. A value not set is not written."), widget
        )
        label.setWordWrap(True)
        form.addRow(label)

        labels = {
            StyleKey.FillColor: tr("Fill color"),
            StyleKey.StrokeColor: tr("Stroke color"),
            StyleKey.StrokeWidth: tr("Stroke width"),
            StyleKey.CircleRadius: tr("Point radius"),
            StyleKey.CircleFillColor: tr("Point fill color"),
            StyleKey.CircleStrokeColor: tr("Point stroke color"),
            StyleKey.CircleStrokeWidth: tr("Point stroke width"),
        }

        # One color button or one spin box for each style key
        self.style_widgets: dict[StyleKey, QgsColorButton | QDoubleSpinBox] = {}
        for key in StyleKey:
            if key.is_color():
                button = QgsColorButton(widget)
                button.setAllowOpacity(True)
                button.setShowNull(True, tr("Not set"))
                button.setToNull()
                self.style_widgets[key] = button
            else:
                spin = QDoubleSpinBox(widget)
                spin.setMinimum(STYLE_NUMBER_NOT_SET)
                spin.setMaximum(100)
                spin.setDecimals(1)
                spin.setSpecialValueText(tr("Not set"))
                spin.setValue(STYLE_NUMBER_NOT_SET)
                self.style_widgets[key] = spin
            form.addRow(f"{labels[key]} ({key.value})", self.style_widgets[key])

        return widget

    def current_style(self) -> dict[StyleKey, JsonScalar]:
        """The style set by the user.

        A color not changed by the user keeps its initial text, such as 'blue'.

        :return: The style, without the values not set.
        """
        style: dict[StyleKey, JsonScalar] = {}
        for key, widget in self.style_widgets.items():
            if isinstance(widget, QgsColorButton):
                color = None if widget.isNull() else widget.color()
                initial = self._initial_style.get(key)
                if initial is not None and color == color_from_text(initial):
                    # Same color as in the file, or a value not understood but not changed by the user
                    style[key] = initial
                elif color is not None:
                    style[key] = color_to_text(color)
            elif widget.value() != STYLE_NUMBER_NOT_SET:
                value = widget.value()
                style[key] = int(value) if value.is_integer() else value
        return style

    # Callbacks

    def _callbacks_tab(self) -> QWidget:
        """Build the tab with the callbacks run after the action.

        :return: The tab widget.
        """
        widget = QWidget(self)
        layout = QVBoxLayout(widget)

        label = QLabel(
            tr(
                "Methods run in the web interface after the action has returned some geometries : zoom to them, "
                "select the features of a layer intersecting them, or refresh a layer."
            ),
            widget,
        )
        label.setWordWrap(True)
        layout.addWidget(label)

        self.callbacks = QTableWidget(0, 2, widget)
        self.callbacks.setHorizontalHeaderLabels([tr("Method"), tr("Layer")])
        self.callbacks.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.callbacks.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.callbacks)

        layout.addLayout(self._add_remove_buttons(self.add_callback, self.callbacks))
        return widget

    def add_callback(self, callback: ActionCallback | None = None):
        """Add a row in the callback table.

        :param callback: The callback, or None for a new zoom callback.
        """
        row = self.callbacks.rowCount()
        self.callbacks.insertRow(row)

        method = QComboBox(self.callbacks)
        method.addItem(tr("Zoom"), CallbackMethod.Zoom)
        method.addItem(tr("Select"), CallbackMethod.Select)
        method.addItem(tr("Redraw"), CallbackMethod.Redraw)

        layer = QgsMapLayerComboBox(self.callbacks)
        layer.setFilters(QgsMapLayerProxyModel.Filter.VectorLayer)
        layer.setAllowEmptyLayer(True)
        layer.setLayer(None)

        if callback:
            method.setCurrentIndex(method.findData(callback.method))
            if callback.layer_id:
                layer.setLayer(self.project.mapLayer(callback.layer_id))

        # The layer is only used by the select and redraw methods
        def method_changed():
            """Enable the layer according to the method."""
            layer.setEnabled(method.currentData().needs_layer())

        method.currentIndexChanged.connect(method_changed)
        method_changed()

        self.callbacks.setCellWidget(row, 0, method)
        self.callbacks.setCellWidget(row, 1, layer)

    def current_callbacks(self) -> list[ActionCallback]:
        """The callbacks set by the user.

        :return: The callbacks, in the table order.
        """
        callbacks = []
        for row in range(self.callbacks.rowCount()):
            method: CallbackMethod = self.callbacks.cellWidget(row, 0).currentData()
            layer = self.callbacks.cellWidget(row, 1).currentLayer()
            layer_id = layer.id() if layer and method.needs_layer() else None
            callbacks.append(ActionCallback(method, layer_id))
        return callbacks

    # Common

    def _add_remove_buttons(self, add_callable: Callable[[], None], table: QTableWidget) -> QHBoxLayout:
        """Build the buttons to add and remove rows in a table.

        :param add_callable: The method adding a row, called without argument.
        :param table: The table.
        :return: The layout with the buttons.
        """
        layout = QHBoxLayout()

        add_button = QPushButton(self)
        add_button.setIcon(QIcon(":images/themes/default/symbologyAdd.svg"))
        add_button.setToolTip(tr("Add"))
        add_button.clicked.connect(lambda: add_callable())
        layout.addWidget(add_button)

        remove_button = QPushButton(self)
        remove_button.setIcon(QIcon(":images/themes/default/symbologyRemove.svg"))
        remove_button.setToolTip(tr("Remove the selected row"))
        remove_button.clicked.connect(lambda: table.removeRow(table.currentRow()))
        layout.addWidget(remove_button)

        layout.addStretch()
        return layout

    def load_action(self, action: Action):
        """Fill the form with an action.

        :param action: The action.
        """
        self.name.setText(action.name)
        self.title.setText(action.title)
        self.description.setText(action.description)
        self.scope.setCurrentIndex(self.scope.findData(action.scope))
        for layer_id in action.layers:
            self._layer_item(layer_id).setCheckState(Qt.CheckState.Checked)
        self.geometry.setCurrentIndex(max(0, self.geometry.findData(action.geometry)))
        self.icon.setCurrentText(action.icon)
        self.confirm.setText(action.confirm)

        for key, value in action.options.items():
            self.add_option(key, value)

        for style_key, style_value in action.style.items():
            widget = self.style_widgets[style_key]
            if isinstance(widget, QgsColorButton):
                color = color_from_text(style_value)
                if color:
                    widget.setColor(color)
            elif isinstance(style_value, (int, float)) and not isinstance(style_value, bool):
                widget.setValue(style_value)

        for callback in action.callbacks:
            self.add_callback(callback)

    def action(self) -> Action:
        """The action built from the form.

        :return: The action.
        """
        scope = self.current_scope()

        # Checked layers, only for the scopes with layers
        layers = []
        if scope.has_layers():
            for row in range(self.layers.count()):
                item = self.layers.item(row)
                if item.checkState() == Qt.CheckState.Checked:
                    layers.append(item.data(Qt.ItemDataRole.UserRole))

        return Action(
            name=self.name.text().strip(),
            title=self.title.text().strip(),
            scope=scope,
            icon=self.icon.currentText().strip(),
            description=self.description.text().strip(),
            confirm=self.confirm.text().strip(),
            layers=layers,
            geometry=self.geometry.currentData() if scope.allows_geometry() else None,
            options=self.current_options(),
            style=self.current_style(),
            callbacks=self.current_callbacks(),
        )

    def validation_errors(self) -> list[str]:
        """Errors of the action built from the form, warnings are not included.

        :return: The error messages.
        """
        action = self.action()
        errors = [issue.message for issue in validate_action(action, self.project) if not issue.warning]
        if action.name in self.other_names:
            errors.insert(0, tr("The name is used by another action."))
        return errors

    def accept(self):
        """Close the dialog only if the action has no error."""
        errors = self.validation_errors()
        if errors:
            self.error.setText("<br>".join(errors))
            self.error.setVisible(True)
            return
        super().accept()
