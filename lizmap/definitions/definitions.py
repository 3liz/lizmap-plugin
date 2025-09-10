"""Definitions used in Lizmap"""

__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from collections import namedtuple
from enum import Enum, unique
from functools import total_ordering
from typing import List

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

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.version_as_list(self.value) < self.version_as_list(other.value)
        return NotImplemented

    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.version_as_list(self.value) >= self.version_as_list(other.value)
        return NotImplemented

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.version_as_list(self.value) > self.version_as_list(other.value)
        return NotImplemented

    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.version_as_list(self.value) <= self.version_as_list(other.value)
        return NotImplemented

    @staticmethod
    def as_list():
        return list(map(lambda c: c, LwcVersions))

    @staticmethod
    def latest():
        """ Latest version definition in the Python files, like LWC 3.X """
        # Latest is used in test by default
        # As the plugin is not fetching the online JSON file, we still need to choose one LWC version
        return LwcVersions.as_list()[-1]

    @staticmethod
    def oldest():
        """ Oldest version definition in the Python file, like LWC 3.1 """
        return LwcVersions.as_list()[0]

    @classmethod
    def find(cls, version_string: str, raise_exception: bool = False):
        """Return the LWC version for the given string."""
        branch = cls.branch_from_version(version_string)
        for lwc_version in cls.__members__.values():
            if branch == lwc_version.value:
                return lwc_version

        if raise_exception:
            raise Exception(
                f'The version string "{version_string}" was not found in Python files. Developers, please add it. No '
                f'stress, nothing in production ;-)'
            )
        else:
            # For non developers, we return the oldest if the string was not found ...
            # Not the best of course ! They will have a lot of blue.
            # It should be fixed ASAP.
            return LwcVersions.oldest()

    @classmethod
    def branch_from_version(cls, version_string: str) -> str:
        """ Return the branch as a string from a version string. """
        split_version = version_string.split('.')
        return f"{split_version[0]}.{split_version[1]}"

    @classmethod
    def version_as_list(cls, version: str) -> List:
        """ List from a version string. """
        return [int(v) for v in version.split(".")]

    @classmethod
    def find_from_metadata(cls, metadata: dict):
        """ Return the release status from metadata. """
        version = metadata.get("info").get("version")
        return LwcVersions.find(version)


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
@total_ordering
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
    def find(cls, status_string: str):
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


class GroupNames:
    BaseLayers = 'baselayers'
    BackgroundColor = 'project-background-color'
    Hidden = 'hidden'


IgnLayer = namedtuple('IgnLayer', ['name', 'title', 'format'])


class IgnLayers(IgnLayer, Enum):
    """ IGN layers available. """
    IgnPlan = IgnLayer('GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2', 'Plan IGN', 'image/png')
    IgnOrthophoto = IgnLayer('ORTHOIMAGERY.ORTHOPHOTOS', 'Orthophoto IGN', 'image/jpeg')
    IgnCadastre = IgnLayer('CADASTRALPARCELS.PARCELLAIRE_EXPRESS', 'Parcellaire IGN', 'image/png')
