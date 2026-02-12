"""Definitions used in Lizmap"""

from enum import Enum, unique
from functools import cached_property, total_ordering
from types import SimpleNamespace
from typing import (
    NamedTuple,
    Optional,
    Tuple,
)

from qgis.PyQt.QtCore import Qt


@unique
@total_ordering
class LwcVersions(Enum):
    Lizmap_3_1 = '3.1'
    Lizmap_3_2 = '3.2'
    Lizmap_3_3 = '3.3'
    Lizmap_3_4 = '3.4'
    Lizmap_3_5 = '3.5'
    Lizmap_3_6 = '3.6'
    Lizmap_3_7 = '3.7'
    Lizmap_3_8 = '3.8'
    Lizmap_3_9 = '3.9'
    Lizmap_3_10 = '3.10'
    Lizmap_3_11 = '3.11'

    # When adding a new version in the list above, do also :
    # lizmap/plugin.py, add the variable self.lwc_versions[LwcVersions.Lizmap_3_X] = []
    # lizmap/forms/base_edition_dialog.py, add the variable self.lwc_versions[LwcVersions.Lizmap_3_X] = []
    # lizmap/test/test_definitions.py, change unit test about LwcVersions.latest()

    # With total_ordering only define  __lt__ definition
    def __lt__(self, other):
        if isinstance(other, LwcVersions):
            return self.version_info < other.version_info
        return NotImplemented

    @staticmethod
    def latest() -> "LwcVersions":
        """ Latest version definition in the Python files, like LWC 3.X """
        return next(reversed(LwcVersions))

    @staticmethod
    def oldest() -> "LwcVersions":
        """ Oldest version definition in the Python file, like LWC 3.1 """
        return next(iter(LwcVersions))

    @classmethod
    def find(cls, version_string: str) -> Optional["LwcVersions"]:
        """Return the LWC version for the given string."""
        major, minor = version_string.split('.', maxsplit=2)[:2]
        branch = f"{major}.{minor}"
        try:
            return LwcVersions(branch)
        except ValueError:
            return None

    @classmethod
    def find_from_metadata(cls, metadata: dict):
        """ Return the release status from metadata. """
        version = metadata.get("info").get("version")
        return LwcVersions.find(version)

    @cached_property
    def version_info(self) -> Tuple[int, int]:
        """ List from a version string. """

        return tuple(int(v) for v in self.value.split("."))


# Possible prefix before a stable release
# Note that 'pre' is not supported by the QGIS Desktop plugin manager
# https://github.com/qgis/QGIS/blob/4ace69f83af20dd597c0da69e2daca714ed49992/python/pyplugin_installer/version_compare.py#L112
# Master and dev is for internal purpose only, name of the current branch. It's not supported as well by QGIS Desktop
UNSTABLE_VERSION_PREFIX = ('master', 'dev', 'pre', 'alpha', 'beta', 'rc')
DEV_VERSION_PREFIX = ('master', 'dev')

# https://qgis.org/pyqgis/master/gui/QgsMessageBar.html#qgis.gui.QgsMessageBar.pushMessage
DURATION_MESSAGE_BAR = -1
DURATION_WARNING_BAR = 7  # A warning with -1 will stay open forever
DURATION_SUCCESS_BAR = 5  # A success with -1 will stay open forever

PLAUSIBLE_DOMAIN_PROD = "plugin.qgis.lizmap.com"
PLAUSIBLE_URL_PROD = "https://analytics.3liz.com/api/event"

PLAUSIBLE_DOMAIN_TEST = "plugin.qgis.lizmap.com"
PLAUSIBLE_URL_TEST = "https://plausible.snap.3liz.net/api/event"

# PLAUSIBLE_DOMAIN_TEST = "plugin.qgis.lizmap.com"
# PLAUSIBLE_URL_TEST = "https://analytics.3liz.com/api/event"


@unique
class ReleaseStatus(Enum):
    Unknown = 'Unknown'
    Retired = 'Retired'
    SecurityBugfixOnly = 'security_bugfix_only'
    Stable = 'Stable'
    ReleaseCandidate = 'ReleaseCandidate'
    Dev = 'Dev'

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented

    @classmethod
    def find(cls, status_string: str) -> "ReleaseStatus":
        """Return the release status from the string."""
        if status_string == 'feature_freeze':
            status_string = 'ReleaseCandidate'
        status_string = status_string.lower()
        for status in cls.__members__.values():
            if str(status.value).lower() == status_string:
                return status
        return ReleaseStatus.Unknown


@unique
class LayerProperties(Enum):
    DataUrl = 'DataUrl'


@unique
class Html(Enum):
    H1 = 'h1'
    H2 = 'h2'
    H3 = 'h3'
    H4 = 'h4'
    Strong = 'strong'
    Li = 'li'
    Td = 'td'
    P = 'p'


@unique
class ServerComboData(Enum):
    """ The server combobox. """
    AuthId = Qt.ItemDataRole.UserRole  # String with the authentication ID
    ServerUrl = Qt.ItemDataRole.UserRole + 1  # String with the server URL
    JsonMetadata = Qt.ItemDataRole.UserRole + 2  # JSON from the server, raw
    # LwcVersion = Qt.ItemDataRole.UserRole + 3  # Enum item with the LWC version
    LwcBranchStatus = Qt.ItemDataRole.UserRole + 4  # Enum item about the release status at that time.
    MarkDown = Qt.ItemDataRole.UserRole + 5  # Markdown for the server


@unique
class RepositoryComboData(Enum):
    """ The repository combobox. """
    Id = Qt.ItemDataRole.UserRole  # ID of the repository
    Path = Qt.ItemDataRole.UserRole + 1  # Path on the server


@unique
class PredefinedGroup(Enum):
    """ The list of predefined group in LWC. """
    No = Qt.ItemDataRole.UserRole                    # 256
    Hidden = Qt.ItemDataRole.UserRole + 1            # 257
    Baselayers = Qt.ItemDataRole.UserRole + 2        # 258 The group `baselayers`
    BackgroundColor = Qt.ItemDataRole.UserRole + 3   # 259
    Overview = Qt.ItemDataRole.UserRole + 4          # 260
    BaselayerItem = Qt.ItemDataRole.UserRole + 5     # 261 Layer or group in the `baselayers`, which will be an item in the combobox


GroupNames = SimpleNamespace(
    BaseLayers='baselayers',
    BackgroundColor='project-background-color',
    Hidden='hidden',
)


class IgnLayer(NamedTuple):
    name: str
    title: str
    format: str


class IgnLayers(IgnLayer, Enum):
    """ IGN layers available. """
    IgnPlan = IgnLayer('GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2', 'Plan IGN', 'image/png')
    IgnOrthophoto = IgnLayer('ORTHOIMAGERY.ORTHOPHOTOS', 'Orthophoto IGN', 'image/jpeg')
    IgnCadastre = IgnLayer('CADASTRALPARCELS.PARCELLAIRE_EXPRESS', 'Parcellaire IGN', 'image/png')
