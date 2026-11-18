"""Read, write and validate the Lizmap actions configuration file."""

from __future__ import annotations

import json

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Union

from qgis.core import QgsProject, QgsVectorLayer

from lizmap.actions.definitions import (
    ACTION_FILE_SUFFIX,
    ACTION_NAME_REGEX,
    ICON_MEDIA_REGEX,
    ICON_PREFIX,
    OPTION_KEY_REGEX,
    RESERVED_OPTION_KEYS,
    ActionGeometry,
    ActionScope,
    CallbackMethod,
    StyleKey,
)
from lizmap.toolbelt.i18n import tr

__copyright__ = "Copyright 2026, 3Liz"
__license__ = "GPL version 3"
__email__ = "info@3liz.org"

# A scalar value in the JSON file, used for the options and the style
JsonScalar = Union[str, int, float]


class ActionFormatError(Exception):
    """The action configuration file cannot be read."""


class LegacyActionFormatError(ActionFormatError):
    """The action configuration file uses the format for Lizmap Web Client older than 3.7, not supported."""


@dataclass
class ActionCallback:
    """A method run by Lizmap Web Client after the action has returned some features."""

    method: CallbackMethod
    layer_id: str | None = None

    @classmethod
    def from_json(cls, data: Any) -> ActionCallback | None:
        """Build a callback from its JSON object.

        Lizmap Web Client ignores a callback with an unknown method, so it does not prevent reading the file.

        :param data: The JSON object of the callback.
        :return: The callback, or None if the method is unknown.
        :raises ActionFormatError: If the JSON object is not a valid callback.
        """
        if not isinstance(data, dict):
            raise ActionFormatError(tr("A callback must be a JSON object."))

        # The method must be known by Lizmap Web Client
        try:
            method = CallbackMethod(data.get("method"))
        except ValueError:
            return None

        layer_id = data.get("layerId")
        return cls(method=method, layer_id=str(layer_id) if layer_id else None)

    def to_json(self) -> dict[str, str]:
        """Export the callback as a JSON object.

        The layer ID is only written for the methods using a layer.

        :return: The JSON object of the callback.
        """
        data = {"method": self.method.value}
        if self.method.needs_layer() and self.layer_id:
            data["layerId"] = self.layer_id
        return data


@dataclass
class Action:
    """A Lizmap action, running the PostgreSQL function lizmap_get_data."""

    name: str
    title: str
    scope: ActionScope
    icon: str
    description: str = ""
    confirm: str = ""
    layers: list[str] = field(default_factory=list)
    geometry: ActionGeometry | None = None
    options: dict[str, JsonScalar] = field(default_factory=dict)
    style: dict[StyleKey, JsonScalar] = field(default_factory=dict)
    callbacks: list[ActionCallback] = field(default_factory=list)
    # Methods of the callbacks ignored while reading the file, because they are unknown by Lizmap Web Client.
    # They are not written back in the file.
    ignored_callbacks: list[str] = field(default_factory=list, compare=False)

    @classmethod
    def from_json(cls, data: Any) -> Action:
        """Build an action from its JSON object.

        Keys unknown by the plugin are not kept.

        :param data: The JSON object of the action.
        :return: The action.
        :raises ActionFormatError: If the JSON object is not a valid action.
        """
        if not isinstance(data, dict):
            raise ActionFormatError(tr("An action must be a JSON object."))

        # Mandatory name and scope
        name = data.get("name")
        if not name or not isinstance(name, str):
            raise ActionFormatError(tr("An action does not have a name."))

        try:
            scope = ActionScope(data.get("scope"))
        except ValueError:
            raise ActionFormatError(
                tr("Unknown scope '{}' for the action '{}'.").format(data.get("scope"), name)
            ) from None

        # Optional geometry to draw
        geometry = None
        if data.get("geometry"):
            try:
                geometry = ActionGeometry(data["geometry"])
            except ValueError:
                raise ActionFormatError(
                    tr("Unknown geometry '{}' for the action '{}'.").format(data["geometry"], name)
                ) from None

        # Lists and objects must have the right JSON type
        layers = data.get("layers", [])
        options = data.get("options", {})
        style = data.get("style", {})
        callbacks = data.get("callbacks", [])
        if not isinstance(layers, list):
            raise ActionFormatError(tr("The layers of the action '{}' must be a list.").format(name))
        if not isinstance(options, dict):
            raise ActionFormatError(tr("The options of the action '{}' must be a JSON object.").format(name))
        if not isinstance(style, dict):
            raise ActionFormatError(tr("The style of the action '{}' must be a JSON object.").format(name))
        if not isinstance(callbacks, list):
            raise ActionFormatError(tr("The callbacks of the action '{}' must be a list.").format(name))

        # Callbacks with an unknown method are ignored, but remembered to warn the user
        known_callbacks = []
        ignored_callbacks = []
        for item in callbacks:
            callback = ActionCallback.from_json(item)
            if callback:
                known_callbacks.append(callback)
            else:
                ignored_callbacks.append(str(item.get("method")))

        # Only the style keys handled by the plugin are kept
        known_style = {}
        for key, value in style.items():
            try:
                known_style[StyleKey(key)] = value
            except ValueError:
                continue

        return cls(
            name=name,
            title=str(data.get("title") or ""),
            scope=scope,
            icon=str(data.get("icon") or ""),
            description=str(data.get("description") or ""),
            confirm=str(data.get("confirm") or ""),
            layers=[str(layer_id) for layer_id in layers],
            geometry=geometry,
            options=dict(options),
            style=known_style,
            callbacks=known_callbacks,
            ignored_callbacks=ignored_callbacks,
        )

    def to_json(self) -> dict[str, Any]:
        """Export the action as a JSON object, as expected by Lizmap Web Client.

        Empty optional values are not written, except options and callbacks,
        always read by Lizmap Web Client.

        :return: The JSON object of the action.
        """
        data: dict[str, Any] = {
            "name": self.name,
            "title": self.title,
        }
        if self.description:
            data["description"] = self.description
        data["scope"] = self.scope.value

        # Layers only for the layer and feature scopes, geometry only for the project and layer scopes
        if self.scope.has_layers():
            data["layers"] = list(self.layers)
        if self.geometry and self.scope.allows_geometry():
            data["geometry"] = self.geometry.value

        data["icon"] = self.icon
        if self.confirm:
            data["confirm"] = self.confirm
        data["options"] = dict(self.options)

        # Style keys are written in the order of the enum, for a stable file
        style = {key.value: self.style[key] for key in StyleKey if key in self.style}
        if style:
            data["style"] = style

        data["callbacks"] = [callback.to_json() for callback in self.callbacks]
        return data


@dataclass
class ActionIssue:
    """An issue found in an action while validating the configuration.

    An error makes the action fail or not displayed in Lizmap Web Client.
    A warning is about a configuration which works, but which may not be the expected one.
    """

    action: str
    message: str
    warning: bool = False

    def __str__(self) -> str:
        """Human-readable issue, with the action name.

        :return: The issue message prefixed by the action name.
        """
        return f"{self.action} : {self.message}"


def action_file_path(project_file: str | Path) -> Path:
    """Path of the action configuration file for a QGS file.

    :param project_file: Path of the QGS file.
    :return: The path of the action file, next to the QGS file.
    """
    return Path(f"{project_file}{ACTION_FILE_SUFFIX}")


def actions_from_json(content: str) -> list[Action]:
    """Read the actions from the content of the action configuration file.

    :param content: The JSON content.
    :return: The list of actions, in the file order.
    :raises LegacyActionFormatError: If the content uses the format for Lizmap Web Client older than 3.7.
    :raises ActionFormatError: If the content is not a valid action configuration.
    """
    try:
        data = json.loads(content)
    except ValueError as e:
        raise ActionFormatError(tr("The action file is not a valid JSON document : {}").format(e)) from None

    # The format for LWC < 3.7 was an object, with layer IDs as keys
    if isinstance(data, dict):
        raise LegacyActionFormatError(
            tr(
                "The action file uses the format for Lizmap Web Client older than 3.7, which is not supported "
                "anymore. The actions must be created again."
            )
        )

    if not isinstance(data, list):
        raise ActionFormatError(tr("The action file must contain a list of actions."))

    return [Action.from_json(item) for item in data]


def actions_to_json(actions: list[Action]) -> str:
    """Export the actions as the content of the action configuration file.

    :param actions: The list of actions.
    :return: The indented JSON content.
    """
    return json.dumps([action.to_json() for action in actions], indent=4, ensure_ascii=False) + "\n"


def read_actions(path: Path) -> list[Action]:
    """Read the action configuration file.

    :param path: Path of the action file.
    :return: The list of actions, empty if the file does not exist.
    :raises LegacyActionFormatError: If the file uses the format for Lizmap Web Client older than 3.7.
    :raises ActionFormatError: If the file is not a valid action configuration.
    """
    if not path.is_file():
        return []
    return actions_from_json(path.read_text(encoding="utf8"))


def write_actions(path: Path, actions: list[Action]) -> bool:
    """Write the action configuration file.

    The file is removed if there is no action.

    :param path: Path of the action file.
    :param actions: The list of actions.
    :return: True if the file has been written, False if there is no action.
    """
    if not actions:
        path.unlink(missing_ok=True)
        return False

    path.write_text(actions_to_json(actions), encoding="utf8")
    return True


def _is_postgresql_layer(project: QgsProject, layer_id: str) -> bool:
    """Check if a layer is a PostgreSQL vector layer in the project.

    :param project: The QGIS project.
    :param layer_id: The layer ID.
    :return: True if the layer exists and is a PostgreSQL vector layer.
    """
    layer = project.mapLayer(layer_id)
    return isinstance(layer, QgsVectorLayer) and layer.providerType() == "postgres"


def _validate_style_value(key: StyleKey, value: JsonScalar) -> bool:
    """Check a style value.

    :param key: The style key.
    :param value: The style value.
    :return: True if the value is a non-empty string for a color, or a positive number otherwise.
    """
    if key.is_color():
        return isinstance(value, str) and bool(value.strip())
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0


def _validate_action(action: Action, project: QgsProject) -> list[ActionIssue]:
    """Validate one action against the rules of Lizmap Web Client and the current project.

    The uniqueness of the name is checked by validate_actions.

    :param action: The action.
    :param project: The QGIS project, to check the layers.
    :return: The list of issues, empty if the action is valid.
    """
    issues = []

    def error(message: str) -> None:
        """Add an error for the action.

        :param message: The error message.
        """
        issues.append(ActionIssue(action.name, message))

    def warning(message: str) -> None:
        """Add a warning for the action.

        :param message: The warning message.
        """
        issues.append(ActionIssue(action.name, message, warning=True))

    # Name: mandatory, without special characters
    if not ACTION_NAME_REGEX.match(action.name):
        error(tr("The name must only contain letters, digits, '_' or '-'."))

    # Title and icon are displayed in the web interface
    if not action.title.strip():
        error(tr("The title is mandatory."))
    if not action.icon.startswith(ICON_PREFIX) and not ICON_MEDIA_REGEX.match(action.icon):
        error(
            tr(
                "The icon must be either a Lizmap icon starting with '{}' or a file in the media folder."
            ).format(ICON_PREFIX)
        )

    # Layers: only for the layer and feature scopes, PostgreSQL layers in the project
    if action.scope.has_layers():
        if not action.layers:
            error(tr("At least one layer is mandatory for the '{}' scope.").format(action.scope.value))
        for layer_id in action.layers:
            if not _is_postgresql_layer(project, layer_id):
                error(tr("The layer '{}' is not a PostgreSQL layer in the project.").format(layer_id))

    # Geometry to draw: not available for the feature scope
    if action.geometry and not action.scope.allows_geometry():
        error(tr("A geometry to draw is not possible for the '{}' scope.").format(action.scope.value))

    # Options: default values of parameters, which can be overridden by a JavaScript script calling the action.
    # Keys are written in the SQL query, values are sent as text.
    for key, value in action.options.items():
        if not OPTION_KEY_REGEX.match(key):
            error(
                tr(
                    "The option '{}' must start with a letter and only contain letters, digits or '_'."
                ).format(key)
            )
        elif key in RESERVED_OPTION_KEYS:
            error(tr("The option '{}' is a reserved parameter sent by Lizmap Web Client.").format(key))
        if isinstance(value, bool) or not isinstance(value, (str, int, float)):
            error(tr("The value of the option '{}' must be a text or a number.").format(key))

    # Style values
    for style_key, style_value in action.style.items():
        if _validate_style_value(style_key, style_value):
            continue
        if style_key.is_color():
            error(tr("The style '{}' must be a color.").format(style_key.value))
        else:
            error(tr("The style '{}' must be a positive number.").format(style_key.value))

    # Callbacks: a layer in the project is needed for select and redraw
    for method in action.ignored_callbacks:
        warning(tr("The callback '{}' is unknown by Lizmap Web Client, it will be removed.").format(method))
    for callback in action.callbacks:
        if not callback.method.needs_layer():
            continue
        if not callback.layer_id:
            error(tr("The callback '{}' needs a layer.").format(callback.method.value))
        elif not project.mapLayer(callback.layer_id):
            error(
                tr("The layer '{}' of the callback '{}' is not in the project.").format(
                    callback.layer_id, callback.method.value
                )
            )

    return issues


def validate_actions(actions: list[Action], project: QgsProject) -> list[ActionIssue]:
    """Validate the actions against the rules of Lizmap Web Client and the current project.

    :param actions: The list of actions.
    :param project: The QGIS project, to check the layers.
    :return: The list of errors and warnings, empty if all actions are valid.
    """
    issues = []
    names: set[str] = set()

    for action in actions:
        # Lizmap Web Client finds a project action by its name only, so the name must be unique in the file
        if action.name in names:
            issues.append(ActionIssue(action.name, tr("The name is used by another action.")))
        names.add(action.name)

        issues.extend(_validate_action(action, project))

    return issues
