from __future__ import annotations

import json
import traceback

from functools import partial
from typing import (
    TYPE_CHECKING,
    Protocol,
)

from qgis.core import (
    Qgis,
    QgsLayerTreeGroup,
    QgsProject,
    QgsRasterLayer,
)

from ..definitions.definitions import (
    GroupNames,
    IgnLayer,
    IgnLayers,
    LayerProperties,
    LwcVersions,
)
from ..definitions.online_help import Panels

if TYPE_CHECKING:
    from ..config import GlobalOptionsDefinitions
    from ..dialogs.main import LizmapDialog

from .. import logger
from ..toolbelt.i18n import tr
from ..toolbelt.layer import set_layer_property
from ..toolbelt.resources import load_icon
from .layer_tree import LayerTreeManager


class LizmapProtocol(Protocol):
    dlg: LizmapDialog
    global_options: GlobalOptionsDefinitions

    @property
    def lwc_version(self) -> LwcVersions: ...

    @property
    def layerList(self) -> dict: ...

    def _add_base_layer(
        self,
        source: str,
        name: str,
        attribution_url: str | None = None,
        attribution_name: str | None = None,
    ):
        raise NotImplementedError("_add_base_layer")


class BaseLayersManager(LizmapProtocol):
    def initialize_base_layers(self):
        self.crs_3857_base_layers_list = {
            "osm-mapnik": self.dlg.cbOsmMapnik,
            "opentopomap": self.dlg.cb_open_topo_map,
            "google-street": self.dlg.cbGoogleStreets,
            "google-satellite": self.dlg.cbGoogleSatellite,
            "google-hybrid": self.dlg.cbGoogleHybrid,
            "google-terrain": self.dlg.cbGoogleTerrain,
            "bing-road": self.dlg.cbBingStreets,
            "bing-aerial": self.dlg.cbBingSatellite,
            "bing-hybrid": self.dlg.cbBingHybrid,
            "ign-plan": self.dlg.cbIgnStreets,
            "ign-photo": self.dlg.cbIgnSatellite,
            "ign-scan": self.dlg.cbIgnTerrain,
            "ign-cadastral": self.dlg.cbIgnCadastral,
        }

        for item in self.crs_3857_base_layers_list.values():
            slot = self.check_visibility_crs_3857
            item.stateChanged.connect(slot)

        self.check_visibility_crs_3857()

        # Connect base-layer checkboxes
        self.base_layer_widget_list = {
            "layer": self.dlg.cbLayerIsBaseLayer,
            "empty": self.dlg.cbAddEmptyBaselayer,
        }
        self.base_layer_widget_list.update(self.crs_3857_base_layers_list)

    def check_visibility_crs_3857(self):
        version = self.current_lwc_version()
        if version is None:
            raise AssertionError("Current Lizmap Web Client is unknown")

        check_visibility_crs_3857(
            self.dlg,
            self.crs_3857_base_layers_list,
            self.lwc_version,
        )

    def on_baselayer_checkbox_change(self):
        blist = on_baselayer_checkbox_change(self.dlg, self.layerList, self.base_layer_widget_list)
        # Fill self.globalOptions
        self.global_options["startupBaselayer"]["list"] = blist

    def set_startup_baselayer_from_config(self):
        set_startup_baselayer_from_config(self.dlg)

    def configure_base_layers(self):

        # Group helper
        self.dlg.add_group_hidden.setToolTip(
            tr(
                "Add a group which will be hidden by default on Lizmap Web "
                "Client. Some tables might be needed in the "
                "QGIS projet but not needed for display on the map and in the legend."
            )
        )
        self.dlg.add_group_baselayers.setToolTip(
            tr(
                'Add a group called "baselayers", you can organize your layers inside, '
                "it will be displayed in a dropdown menu."
            )
        )
        self.dlg.add_group_empty.setToolTip(
            tr(
                "Add a group which must stay empty. It will add an option in the base "
                "layer dropdown menu and allow the default background color defined "
                "in the project properties to be displayed."
            )
        )
        self.dlg.add_group_overview.setToolTip(
            tr("Add some layers in this group to make an overview map at a lower scale.")
        )
        self.dlg.add_group_hidden.clicked.connect(self.add_group_hidden)
        self.dlg.add_group_baselayers.clicked.connect(self.add_group_baselayers)
        self.dlg.add_group_empty.clicked.connect(self.add_group_empty)
        self.dlg.add_group_overview.clicked.connect(self.add_group_overview)

        osm_icon = load_icon("osm-32-32.png")
        self.dlg.button_osm_mapnik.clicked.connect(partial(add_osm_mapnik, self))
        self.dlg.button_osm_mapnik.setIcon(osm_icon)
        self.dlg.button_osm_opentopomap.clicked.connect(partial(add_osm_opentopomap, self))
        self.dlg.button_osm_opentopomap.setIcon(osm_icon)
        self.dlg.button_ign_orthophoto.clicked.connect(
            partial(add_french_ign_layer, IgnLayers.IgnOrthophoto, self)
        )
        self.dlg.button_ign_plan.clicked.connect(partial(add_french_ign_layer, IgnLayers.IgnPlan, self))
        self.dlg.button_ign_cadastre.clicked.connect(
            partial(add_french_ign_layer, IgnLayers.IgnCadastre, self)
        )

    def disable_legacy_empty_base_layer(self):
        """Legacy checkbox until it's removed."""
        # We suppose we are in LWC >= 3.7 otherwise the button is blue
        if self.lwc_version >= LwcVersions.Lizmap_3_7:
            self.dlg.cbAddEmptyBaselayer.setChecked(False)

    def add_group_hidden(self):
        """Add the hidden group."""
        self._add_group_legend(GroupNames.Hidden)

    def add_group_baselayers(self):
        """Add the baselayers group."""
        self._add_group_legend(GroupNames.BaseLayers)
        self.disable_legacy_empty_base_layer()

    def add_group_empty(self):
        """Add the default background color."""
        baselayers = self._add_group_legend(GroupNames.BaseLayers)
        self._add_group_legend(GroupNames.BackgroundColor, parent=baselayers)
        self.disable_legacy_empty_base_layer()

    def add_group_overview(self):
        """Add the overview group."""
        label = "overview"
        if self.lwc_version < LwcVersions.Lizmap_3_7:
            label = "Overview"
        self._add_group_legend(label, exclusive=False)

    def _add_group_legend(
        self,
        label: str,
        exclusive: bool = False,
        parent: QgsLayerTreeGroup = None,
        project: QgsProject = None,
    ) -> QgsLayerTreeGroup:
        """Add a group in the legend."""
        if project is None:
            project = self.project

        if parent:
            root_group = parent
        else:
            root_group = project.layerTreeRoot()

        qgis_group = LayerTreeManager.existing_group(root_group, label)
        if qgis_group:
            return qgis_group

        new_group = root_group.addGroup(label)
        if exclusive:
            new_group.setIsMutuallyExclusive(True, -1)
        return new_group

    def _add_base_layer(
        self,
        source: str,
        name: str,
        attribution_url: str | None = None,
        attribution_name: str | None = None,
    ):
        """Add a base layer to the "baselayers" group."""
        logger.info("start _add_base_layer")
        self.add_group_baselayers()
        logger.info("add_group_bselayers done")
        raster = QgsRasterLayer(source, name, "wms")
        self.project.addMapLayer(raster, False)  # False to not add it in the legend, only in the project

        if attribution_url:
            set_layer_property(raster, LayerProperties.AttributionUrl, attribution_url)
            set_layer_property(raster, LayerProperties.DataUrl, attribution_url)
        if attribution_name:
            set_layer_property(raster, LayerProperties.Attribution, attribution_name)
        root_group = self.project.layerTreeRoot()

        groups = root_group.findGroups()
        for qgis_group in groups:
            qgis_group: QgsLayerTreeGroup
            if qgis_group.name() == "baselayers":
                node = qgis_group.addLayer(raster)
                node.setExpanded(False)
                break

        self.dlg.display_message_bar(
            tr("New layer"),
            tr('Please close and reopen the dialog to display your layer in the tab "{tab_name}".').format(
                tab_name=self.dlg.mOptionsListWidget.item(Panels.Layers).text()
            ),
            Qgis.MessageLevel.Warning,
        )



def add_osm_mapnik(proto: LizmapProtocol):
    """Add the OSM mapnik base layer."""
    source = "type=xyz&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    proto._add_base_layer(
        source, "OpenStreetMap", "https://openstreetmap.org", "© " + tr("OpenStreetMap contributors")
    )


def add_osm_opentopomap(proto: LizmapProtocol):
    """Add the OSM OpenTopoMap base layer."""
    logger.info("Start: Add the OSM OpenTopoMap base layer.")
    source = "type=xyz&url=https://tile.opentopomap.org/{z}/{x}/{y}.png"
    proto._add_base_layer(
        source,
        "OpenTopoMap",
        "https://openstreetmap.org",
        "© " + tr("OpenStreetMap contributors") + ", SRTM, © OpenTopoMap (CC-BY-SA)",
    )


def add_french_ign_layer(layer: IgnLayer, proto: LizmapProtocol):
    """Add some French IGN layers."""
    params = {
        "crs": "EPSG:3857",
        "dpiMode": 7,
        "format": layer.format,
        "layers": layer.name,
        "styles": "normal",
        "tileMatrixSet": "PM",
        "url": "https://data.geopf.fr/wmts?SERVICE%3DWMTS%26VERSION%3D1.0.0%26REQUEST%3DGetCapabilities",
    }
    # Do not use urlencode
    source = "&".join([f"{k}={v}" for k, v in params.items()])
    proto._add_base_layer(source, layer.title, "https://www.ign.fr/", "IGN France")


#
# Helpers
#


def on_baselayer_checkbox_change(
    dlg: LizmapDialog,
    layerList: dict,
    base_layer_widget_list: dict,
) -> list:
    """
    Add or remove a base-layer in cbStartupBaselayer combobox
    when user change state of any base-layer related checkbox
    """
    if not layerList:
        return None

    # Combo to fill up with base-layer
    combo = dlg.cbStartupBaselayer

    # First get selected item
    idx = combo.currentIndex()
    data = combo.itemData(idx)

    # Clear the combo
    combo.clear()
    i = 0
    blist = []

    # Fill with checked base-layers
    # 1/ QGIS layers
    for k, v in layerList.items():
        if not v["baseLayer"]:
            continue
        combo.addItem(v["name"], v["name"])
        blist.append(v["name"])
        if data == k:
            idx = i
        i += 1

    # 2/ External base-layers
    for k, v in base_layer_widget_list.items():
        if k != "layer" and v.isChecked():
            combo.addItem(k, k)
            blist.append(k)
            if data == k:
                idx = i
            i += 1

    # Set last chosen item
    combo.setCurrentIndex(idx)
    return blist


def set_startup_baselayer_from_config(dlg: LizmapDialog):
    """
    Read lizmap current cfg configuration
    and set the startup base-layer if found
    """
    if not dlg.check_cfg_file_exists():
        return

    with open(dlg.cfg_file(), encoding="utf8") as f:
        json_file_reader = f.read()

    try:
        json_content = json.loads(json_file_reader)
        json_options = json_content["options"]

        base_layer = json_options.get("startupBaselayer")
        if not base_layer:
            return

        i = dlg.cbStartupBaselayer.findData(base_layer)
        if i < 0:
            return

        dlg.cbStartupBaselayer.setCurrentIndex(i)
    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.error(traceback.format_exc())


def check_visibility_crs_3857(
    dlg: LizmapDialog,
    crs_3857_base_layers_list: dict,
    current_version: LwcVersions,
):
    """Check if we display the warning about scales.

    These checkboxes are deprecated starting from Lizmap Web Client 3.7.
    """
    visible = False
    for item in crs_3857_base_layers_list.values():
        if item.isChecked():
            visible = True

    if current_version >= LwcVersions.Lizmap_3_7:
        # We start showing some deprecated warnings if needed
        dlg.warning_base_layer_deprecated.setVisible(True)

        if visible:
            # At least one checkbox was used, we still need to enable widgets
            dlg.gb_externalLayers.setEnabled(True)
        else:
            # It means no checkboxes were used
            dlg.gb_externalLayers.setEnabled(False)

        if not dlg.cbAddEmptyBaselayer.isChecked():
            # Only when the checkbox wasn't used before
            dlg.cbAddEmptyBaselayer.setEnabled(False)

        if dlg.cbStartupBaselayer.count() == 0:
            # When no item in the combobox
            dlg.cbStartupBaselayer.setEnabled(False)

        # When only one item in the combobox but it's the 'empty' base layer
        if dlg.cbStartupBaselayer.count() == 1 and dlg.cbStartupBaselayer.itemText(0) == "empty":
            dlg.cbStartupBaselayer.setEnabled(False)

    else:
        # We do nothing ...
        dlg.warning_base_layer_deprecated.setVisible(False)
        dlg.gb_externalLayers.setEnabled(True)
        dlg.cbAddEmptyBaselayer.setEnabled(True)
        dlg.cbStartupBaselayer.setEnabled(True)
        dlg.scales_warning.setVisible(visible)
