"""Definitions for the Lizmap actions."""

from __future__ import annotations

import re

from enum import Enum, unique

__copyright__ = "Copyright 2026, 3Liz"
__license__ = "GPL version 3"
__email__ = "info@3liz.org"


# Suffix of the action configuration file, added to the QGS file name
ACTION_FILE_SUFFIX = ".action"

# Allowed characters for the action name.
# The dot is forbidden, it is used by Lizmap Web Client as a separator in the action unique ID.
ACTION_NAME_REGEX = re.compile(r"^[A-Za-z0-9_-]+$")

# Allowed characters for an option key.
# The key is written as it is inside the SQL query built by Lizmap Web Client.
OPTION_KEY_REGEX = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Parameters always sent by Lizmap Web Client to the PostgreSQL function,
# they cannot be used as option keys.
RESERVED_OPTION_KEYS = (
    "lizmap_repository",
    "lizmap_project",
    "action_name",
    "action_scope",
    "layer_name",
    "layer_schema",
    "layer_table",
    "feature_id",
    "map_center",
    "map_extent",
    "wkt",
    "user_login",
)

# Prefix of an icon from the Lizmap Web Client icon set
ICON_PREFIX = "icon-"

# Same regular expression as MEDIA_REGEX in Lizmap Web Client, for an icon stored in the media folder
ICON_MEDIA_REGEX = re.compile(r"^(/)?(?:\.\./)?media/")

# Icons available in Lizmap Web Client, from the Bootstrap 2 Glyphicons set
LWC_ICONS = (
    "icon-adjust",
    "icon-align-center",
    "icon-align-justify",
    "icon-align-left",
    "icon-align-right",
    "icon-arrow-down",
    "icon-arrow-left",
    "icon-arrow-right",
    "icon-arrow-up",
    "icon-asterisk",
    "icon-backward",
    "icon-ban-circle",
    "icon-barcode",
    "icon-bell",
    "icon-bold",
    "icon-book",
    "icon-bookmark",
    "icon-briefcase",
    "icon-bullhorn",
    "icon-calendar",
    "icon-camera",
    "icon-certificate",
    "icon-check",
    "icon-chevron-down",
    "icon-chevron-left",
    "icon-chevron-right",
    "icon-chevron-up",
    "icon-circle-arrow-down",
    "icon-circle-arrow-left",
    "icon-circle-arrow-right",
    "icon-circle-arrow-up",
    "icon-cog",
    "icon-comment",
    "icon-download",
    "icon-download-alt",
    "icon-edit",
    "icon-eject",
    "icon-envelope",
    "icon-exclamation-sign",
    "icon-eye-close",
    "icon-eye-open",
    "icon-facetime-video",
    "icon-fast-backward",
    "icon-fast-forward",
    "icon-file",
    "icon-film",
    "icon-filter",
    "icon-fire",
    "icon-flag",
    "icon-folder-close",
    "icon-folder-open",
    "icon-font",
    "icon-forward",
    "icon-fullscreen",
    "icon-gift",
    "icon-glass",
    "icon-globe",
    "icon-hand-down",
    "icon-hand-left",
    "icon-hand-right",
    "icon-hand-up",
    "icon-hdd",
    "icon-headphones",
    "icon-heart",
    "icon-home",
    "icon-inbox",
    "icon-indent-left",
    "icon-indent-right",
    "icon-info-sign",
    "icon-italic",
    "icon-leaf",
    "icon-list",
    "icon-list-alt",
    "icon-lock",
    "icon-magnet",
    "icon-map-marker",
    "icon-minus",
    "icon-minus-sign",
    "icon-move",
    "icon-music",
    "icon-off",
    "icon-ok",
    "icon-ok-circle",
    "icon-ok-sign",
    "icon-pause",
    "icon-pencil",
    "icon-picture",
    "icon-plane",
    "icon-play",
    "icon-play-circle",
    "icon-plus",
    "icon-plus-sign",
    "icon-print",
    "icon-qrcode",
    "icon-question-sign",
    "icon-random",
    "icon-refresh",
    "icon-remove",
    "icon-remove-circle",
    "icon-remove-sign",
    "icon-repeat",
    "icon-resize-full",
    "icon-resize-horizontal",
    "icon-resize-small",
    "icon-resize-vertical",
    "icon-retweet",
    "icon-road",
    "icon-screenshot",
    "icon-search",
    "icon-share",
    "icon-share-alt",
    "icon-shopping-cart",
    "icon-signal",
    "icon-star",
    "icon-star-empty",
    "icon-step-backward",
    "icon-step-forward",
    "icon-stop",
    "icon-tag",
    "icon-tags",
    "icon-tasks",
    "icon-text-height",
    "icon-text-width",
    "icon-th",
    "icon-th-large",
    "icon-th-list",
    "icon-thumbs-down",
    "icon-thumbs-up",
    "icon-time",
    "icon-tint",
    "icon-trash",
    "icon-upload",
    "icon-user",
    "icon-volume-down",
    "icon-volume-off",
    "icon-volume-up",
    "icon-warning-sign",
    "icon-wrench",
    "icon-zoom-in",
    "icon-zoom-out",
)


@unique
class ActionScope(Enum):
    """Scope of an action: where the action is available in Lizmap Web Client."""

    Project = "project"
    Layer = "layer"
    Feature = "feature"

    def has_layers(self) -> bool:
        """Check if the action is linked to some layers in this scope.

        :return: True for the layer and feature scopes.
        """
        return self in (ActionScope.Layer, ActionScope.Feature)

    def allows_geometry(self) -> bool:
        """Check if the user can draw a geometry before running the action in this scope.

        :return: True for the project and layer scopes.
        """
        return self in (ActionScope.Project, ActionScope.Layer)


@unique
class ActionGeometry(Enum):
    """Geometry the user must draw before running the action, with the Lizmap digitizing tool."""

    Point = "point"
    Line = "line"
    Polygon = "polygon"
    Box = "box"
    Circle = "circle"
    Freehand = "freehand"


@unique
class CallbackMethod(Enum):
    """Method run by Lizmap Web Client after the action has returned some features."""

    Zoom = "zoom"
    Select = "select"
    Redraw = "redraw"

    def needs_layer(self) -> bool:
        """Check if the callback method needs a target layer.

        :return: True for the select and redraw methods.
        """
        return self in (CallbackMethod.Select, CallbackMethod.Redraw)


@unique
class StyleKey(Enum):
    """OpenLayers flat style keys used to draw the features returned by the action."""

    FillColor = "fill-color"
    StrokeColor = "stroke-color"
    StrokeWidth = "stroke-width"
    CircleRadius = "circle-radius"
    CircleFillColor = "circle-fill-color"
    CircleStrokeColor = "circle-stroke-color"
    CircleStrokeWidth = "circle-stroke-width"

    def is_color(self) -> bool:
        """Check if the style value is a color.

        :return: True if the value is a CSS color, False if it is a number.
        """
        return self.value.endswith("-color")
