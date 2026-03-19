import json
import traceback

from functools import partial
from typing import (
    TYPE_CHECKING,
    Dict,
    List,
)

from lizmap.definitions.definitions import (
    IgnLayer,
    IgnLayers,
    LwcVersions,
)

from ..dialogs.main import LizmapDialog

if TYPE_CHECKING:
    from ..dialogs.main import LizmapDialog

from .. import logger
from ..toolbelt.i18n import tr
from ..toolbelt.resources import load_icon
from .layer_tree import LayerTreeManager

#
# Base layers
#


def configure_base_layers(dlg: "LizmapDialog", layer_mngr: LayerTreeManager):
    osm_icon = load_icon('osm-32-32.png')
    dlg.button_osm_mapnik.clicked.connect(partial(add_osm_mapnik, layer_mngr))
    dlg.button_osm_mapnik.setIcon(osm_icon)
    dlg.button_osm_opentopomap.clicked.connect(partial(add_osm_opentopomap, layer_mngr))
    dlg.button_osm_opentopomap.setIcon(osm_icon)
    dlg.button_ign_orthophoto.clicked.connect(
        partial(add_french_ign_layer, IgnLayers.IgnOrthophoto, layer_mngr))
    dlg.button_ign_plan.clicked.connect(
        partial(add_french_ign_layer, IgnLayers.IgnPlan, layer_mngr))
    dlg.button_ign_cadastre.clicked.connect(
        partial(add_french_ign_layer, IgnLayers.IgnCadastre, layer_mngr))


def add_osm_mapnik(layer_mngr: LayerTreeManager):
    """ Add the OSM mapnik base layer. """
    source = 'type=xyz&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png'
    layer_mngr._add_base_layer(
        source,
        'OpenStreetMap',
        'https://openstreetmap.org',
        '© ' + tr('OpenStreetMap contributors'))


def add_osm_opentopomap(layer_mngr: LayerTreeManager):
    """ Add the OSM OpenTopoMap base layer. """
    source = 'type=xyz&url=https://tile.opentopomap.org/{z}/{x}/{y}.png'
    layer_mngr._add_base_layer(
        source,
        'OpenTopoMap',
        'https://openstreetmap.org',
        '© ' + tr('OpenStreetMap contributors') + ', SRTM, © OpenTopoMap (CC-BY-SA)')


def add_french_ign_layer(layer: IgnLayer, layer_mngr: LayerTreeManager):
    """ Add some French IGN layers. """
    params = {
        'crs': 'EPSG:3857',
        'dpiMode': 7,
        'format': layer.format,
        'layers': layer.name,
        'styles': 'normal',
        'tileMatrixSet': 'PM',
        'url': 'https://data.geopf.fr/wmts?SERVICE%3DWMTS%26VERSION%3D1.0.0%26REQUEST%3DGetCapabilities',
    }
    # Do not use urlencode
    source = '&'.join(['{}={}'.format(k, v) for k, v in params.items()])
    layer_mngr._add_base_layer(source, layer.title, 'https://www.ign.fr/', 'IGN France')


#
# Helpers
#

def on_baselayer_checkbox_change(
    dlg: "LizmapDialog",
    layerList: Dict,
    base_layer_widget_list: Dict,
) -> List:
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
        if not v['baseLayer']:
            continue
        combo.addItem(v['name'], v['name'])
        blist.append(v['name'])
        if data == k:
            idx = i
        i += 1

    # 2/ External base-layers
    for k, v in base_layer_widget_list.items():
        if k != 'layer':
            if v.isChecked():
                combo.addItem(k, k)
                blist.append(k)
                if data == k:
                    idx = i
                i += 1

    # Set last chosen item
    combo.setCurrentIndex(idx)
    return blist


def set_startup_baselayer_from_config(dlg: "LizmapDialog"):
    """
    Read lizmap current cfg configuration
    and set the startup base-layer if found
    """
    if not dlg.check_cfg_file_exists():
        return

    with open(dlg.cfg_file(), encoding='utf8') as f:
        json_file_reader = f.read()

    try:
        json_content = json.loads(json_file_reader)
        json_options = json_content['options']

        base_layer = json_options.get('startupBaselayer')
        if not base_layer:
            return

        i = dlg.cbStartupBaselayer.findData(base_layer)
        if i < 0:
            return

        dlg.cbStartupBaselayer.setCurrentIndex(i)
    except Exception:
        logger.error(traceback.format_exc())


def check_visibility_crs_3857(
    dlg: "LizmapDialog",
    crs_3857_base_layers_list: Dict,
    current_version: LwcVersions,
):
    """ Check if we display the warning about scales.

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

        if dlg.cbStartupBaselayer.count() == 1:
            # When only one item in the combobox but it's the 'empty' base layer
            if dlg.cbStartupBaselayer.itemText(0) == 'empty':
                dlg.cbStartupBaselayer.setEnabled(False)

    else:
        # We do nothing ...
        dlg.warning_base_layer_deprecated.setVisible(False)
        dlg.gb_externalLayers.setEnabled(True)
        dlg.cbAddEmptyBaselayer.setEnabled(True)
        dlg.cbStartupBaselayer.setEnabled(True)
        dlg.scales_warning.setVisible(visible)
