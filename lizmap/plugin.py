"""
/***************************************************************************
 Lizmap
                                 A QGIS plugin
 Publication plugin for Lizmap web application, by 3liz.com
                                -------------------
        begin                : 2011-11-01
        copyright            : (C) 2011 by 3liz
        email                : info@3liz.com
 ***************************************************************************/

/****** BEGIN LICENSE BLOCK *****
 Version: MPL 1.1/GPL 2.0/LGPL 2.1

 The contents of this file are subject to the Mozilla Public License Version
 1.1 (the "License"); you may not use this file except in compliance with
 the License. You may obtain a copy of the License at
 http://www.mozilla.org/MPL/

 Software distributed under the License is distributed on an "AS IS" basis,
 WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
 for the specific language governing rights and limitations under the
 License.

 The Original Code is 3liz code,

 The Initial Developer of the Original Code are René-Luc D'Hont rldhont@3liz.com
 and Michael Douchin mdouchin@3liz.com
 Portions created by the Initial Developer are Copyright (C) 2011
 the Initial Developer. All Rights Reserved.

 Alternatively, the contents of this file may be used under the terms of
 either of the GNU General Public License Version 2 or later (the "GPL"),
 or the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 in which case the provisions of the GPL or the LGPL are applicable instead
 of those above. If you wish to allow use of your version of this file only
 under the terms of either the GPL or the LGPL, and not to allow others to
 use your version of this file under the terms of the MPL, indicate your
 decision by deleting the provisions above and replace them with the notice
 and other provisions required by the GPL or the LGPL. If you do not delete
 the provisions above, a recipient may use your version of this file under
 the terms of any one of the MPL, the GPL or the LGPL.

 ***** END LICENSE BLOCK ***** */
"""
import json
import logging
import os
import re
import sys

from collections import OrderedDict
from functools import partial
from pathlib import Path
from shutil import copyfile
from typing import Optional, Tuple

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsEditFormConfig,
    QgsExpression,
    QgsLayerTree,
    QgsLayerTreeGroup,
    QgsLayerTreeLayer,
    QgsMapLayer,
    QgsMapLayerModel,
    QgsMapLayerProxyModel,
    QgsProject,
    QgsSettings,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.PyQt.QtWidgets import QLineEdit

if Qgis.QGIS_VERSION_INT >= 31400:
    from qgis.core import QgsProjectServerValidator

from qgis.PyQt import sip
from qgis.PyQt.QtCore import QCoreApplication, QRegExp, Qt, QTranslator, QUrl
from qgis.PyQt.QtGui import (
    QBrush,
    QColor,
    QDesktopServices,
    QIcon,
    QPixmap,
    QStandardItem,
)
from qgis.PyQt.QtWidgets import (
    QAction,
    QDialogButtonBox,
    QMessageBox,
    QTableWidgetItem,
    QTreeWidgetItem,
)

from lizmap import DEFAULT_LWC_VERSION
from lizmap.definitions.atlas import AtlasDefinitions
from lizmap.definitions.attribute_table import AttributeTableDefinitions
from lizmap.definitions.dataviz import DatavizDefinitions, Theme
from lizmap.definitions.definitions import (
    DOC_URL,
    ONLINE_HELP_LANGUAGES,
    UNSTABLE_VERSION_PREFIX,
    LayerProperties,
    LwcVersionComboData,
    LwcVersions,
    ReleaseStatus,
    ServerComboData,
)
from lizmap.definitions.edition import EditionDefinitions
from lizmap.definitions.filter_by_form import FilterByFormDefinitions
from lizmap.definitions.filter_by_login import FilterByLoginDefinitions
from lizmap.definitions.filter_by_polygon import FilterByPolygonDefinitions
from lizmap.definitions.layouts import LayoutsDefinitions
from lizmap.definitions.locate_by_layer import LocateByLayerDefinitions
from lizmap.definitions.time_manager import TimeManagerDefinitions
from lizmap.definitions.tooltip import ToolTipDefinitions
from lizmap.definitions.warnings import Warnings
from lizmap.dialogs.html_editor import HtmlEditorDialog
from lizmap.dialogs.lizmap_popup import LizmapPopupDialog
from lizmap.dialogs.main import LizmapDialog
from lizmap.forms.atlas_edition import AtlasEditionDialog
from lizmap.forms.attribute_table_edition import AttributeTableEditionDialog
from lizmap.forms.dataviz_edition import DatavizEditionDialog
from lizmap.forms.edition_edition import EditionLayerDialog
from lizmap.forms.filter_by_form_edition import FilterByFormEditionDialog
from lizmap.forms.filter_by_login import FilterByLoginEditionDialog
from lizmap.forms.filter_by_polygon import FilterByPolygonEditionDialog
from lizmap.forms.layout_edition import LayoutEditionDialog
from lizmap.forms.locate_layer_edition import LocateLayerEditionDialog
from lizmap.forms.time_manager_edition import TimeManagerEditionDialog
from lizmap.forms.tooltip_edition import ToolTipEditionDialog
from lizmap.lizmap_api.config import LizmapConfig
from lizmap.saas import is_lizmap_dot_com_hosting, valid_saas_lizmap_dot_com
from lizmap.table_manager.base import TableManager
from lizmap.table_manager.dataviz import TableManagerDataviz
from lizmap.table_manager.layouts import TableManagerLayouts

try:
    from lizmap.plugin_manager import PluginManager
    QGIS_PLUGIN_MANAGER = True
except ModuleNotFoundError:
    # In a standalone application
    QGIS_PLUGIN_MANAGER = False

from lizmap.dialogs.wizard_group import WizardGroupDialog
from lizmap.qgis_plugin_tools.tools.custom_logging import setup_logger
from lizmap.qgis_plugin_tools.tools.ghost_layers import remove_all_ghost_layers
from lizmap.qgis_plugin_tools.tools.i18n import setup_translation, tr
from lizmap.qgis_plugin_tools.tools.resources import (
    plugin_name,
    plugin_path,
    resources_path,
)
from lizmap.qgis_plugin_tools.tools.version import version
from lizmap.qt_style_sheets import (
    NEW_FEATURE_COLOR,
    NEW_FEATURE_CSS,
    STYLESHEET,
)
from lizmap.server_ftp import FtpServer
from lizmap.server_lwc import ServerManager
from lizmap.tools import (
    convert_lizmap_popup,
    current_git_hash,
    format_qgis_version,
    format_version_integer,
    get_layer_wms_parameters,
    has_git,
    layer_property,
    lizmap_user_folder,
    next_git_tag,
    to_bool,
    unaccent,
)
from lizmap.tooltip import Tooltip
from lizmap.version_checker import VersionChecker

LOGGER = logging.getLogger(plugin_name())
VERSION_URL = 'https://raw.githubusercontent.com/3liz/lizmap-web-client/versions/versions.json'
# To try a local file
# VERSION_URL = 'file:///home/etienne/.local/share/QGIS/QGIS3/profiles/default/Lizmap/released_versions.json'


class Lizmap:

    def __init__(self, iface):
        """Constructor of the Lizmap plugin."""
        self.iface = iface
        # noinspection PyArgumentList
        self.project = QgsProject.instance()

        setup_logger(plugin_name())

        locale, file_path = setup_translation(
            'lizmap_qgis_plugin_{}.qm', plugin_path('i18n'))
        self.locale = locale[0:2]  # For the online help

        if file_path:
            self.translator = QTranslator()
            self.translator.load(file_path)
            QCoreApplication.installTranslator(self.translator)

        lizmap_config = LizmapConfig(project=self.project)

        self.dlg = LizmapDialog()
        self.version = version()
        self.is_dev_version = any(item in self.version for item in UNSTABLE_VERSION_PREFIX)
        self.dlg.label_dev_version.setVisible(False)
        if self.is_dev_version:
            self.dlg.setWindowTitle('Lizmap branch {}, commit {}, next {}'.format(
                self.version, current_git_hash(), next_git_tag()))

            if not has_git():
                text = self.dlg.label_dev_version.text().format(self.version)
                self.dlg.label_dev_version.setText(text)
                self.dlg.label_dev_version.setVisible(True)

        self.layers_table = dict()

        # List of ui widget for data driven actions and checking
        self.global_options = lizmap_config.globalOptionDefinitions
        self.global_options['externalSearch']['widget'] = self.dlg.liExternalSearch

        # List of ui widget for data driven actions and checking
        self.layer_options_list = lizmap_config.layerOptionDefinitions
        self.layer_options_list['legend_image_option']['widget'] = self.dlg.combo_legend_option
        self.layer_options_list['popupSource']['widget'] = self.dlg.liPopupSource
        self.layer_options_list['imageFormat']['widget'] = self.dlg.liImageFormat

        # Fill the combobox from the Lizmap API
        for combo_item in ('legend_image_option', 'popupSource', 'imageFormat', 'externalSearch'):

            item_info = self.layer_options_list.get(combo_item)
            if not item_info:
                item_info = self.global_options.get(combo_item)

            if not item_info:
                # This should not happen
                raise Exception('Unknown type for item_info')

            for option in item_info['list']:
                data, label, tooltip, icon = option
                item_info['widget'].addItem(label, data)
                index = item_info['widget'].findData(data)

                if tooltip:
                    # noinspection PyUnresolvedReferences
                    item_info['widget'].setItemData(index, tooltip, Qt.ToolTipRole)

                if icon:
                    if isinstance(icon, str):
                        # From QGIS resources file
                        pass
                    else:
                        # It's a list, from the plugin
                        icon = resources_path(*icon)
                    item_info['widget'].setItemIcon(index, QIcon(icon))

        # Manage LWC versions combo
        self.dlg.label_lwc_version.setStyleSheet(NEW_FEATURE_CSS)
        self.lwc_versions = OrderedDict()
        self.lwc_versions[LwcVersions.Lizmap_3_1] = []
        self.lwc_versions[LwcVersions.Lizmap_3_2] = [
            self.dlg.label_max_feature_popup,
            self.dlg.label_dataviz,
            self.dlg.label_atlas,
        ]
        self.lwc_versions[LwcVersions.Lizmap_3_3] = [
            self.dlg.label_form_filter,
            self.dlg.btQgisPopupFromForm,
        ]
        self.lwc_versions[LwcVersions.Lizmap_3_4] = [
            self.dlg.label_atlas_34,
            self.dlg.list_group_visibility,
            self.dlg.activate_first_map_theme,
            self.dlg.activate_drawing_tools,
        ]
        self.lwc_versions[LwcVersions.Lizmap_3_5] = [
            self.dlg.liPopupSource.model().item(
                self.dlg.liPopupSource.findData('form')
            ),
            self.dlg.label_filter_polygon,
            self.dlg.filter_polygon_by_user,
            self.dlg.checkbox_scale_overview_map,
        ]
        self.lwc_versions[LwcVersions.Lizmap_3_6] = [
            self.dlg.checkbox_popup_allow_download,
            self.dlg.cb_open_topo_map,
            self.dlg.combo_legend_option.model().item(
                self.dlg.combo_legend_option.findData('expand_at_startup')
            ),
            self.dlg.button_wizard_group_visibility_project,
            self.dlg.button_wizard_group_visibility_layer,
            self.dlg.label_helper_dataviz,
            self.dlg.enable_dataviz_preview,
        ]
        self.lwc_versions[LwcVersions.Lizmap_3_7] = [
            self.dlg.label_layout_panel,
            self.dlg.edit_layout_form_button,
            self.dlg.up_layout_form_button,
            self.dlg.down_layout_form_button,
        ]

        self.populate_lwc_combo()

        # Keep for a few months, 04/01/2022
        QgsSettings().remove('lizmap/instance_target_url_authid')

        self.dlg.label_lizmap_logo.setText('')
        pixmap = QPixmap(resources_path('icons', 'logo.png'))
        # noinspection PyUnresolvedReferences
        pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio)
        self.dlg.label_lizmap_logo.setPixmap(pixmap)

        i = 0

        # Information
        icon = QIcon()
        icon.addFile(resources_path('icons', '03-metadata-white'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', '03-metadata-dark'), mode=QIcon.Selected)
        self.dlg.mOptionsListWidget.item(i).setIcon(icon)
        i += 1

        # Map options
        icon = QIcon()
        icon.addFile(resources_path('icons', '15-baselayer-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', '15-baselayer-dark.png'), mode=QIcon.Selected)
        self.dlg.mOptionsListWidget.item(i).setIcon(icon)
        i += 1

        # Layers
        icon = QIcon()
        icon.addFile(resources_path('icons', '02-switcher-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', '02-switcher-dark.png'), mode=QIcon.Selected)
        self.dlg.mOptionsListWidget.item(i).setIcon(icon)
        i += 1

        # Base layer
        icon = QIcon()
        icon.addFile(resources_path('icons', '02-switcher-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', '02-switcher-dark.png'), mode=QIcon.Selected)
        self.dlg.mOptionsListWidget.item(i).setIcon(icon)
        i += 1

        # Layouts
        icon = QIcon()
        icon.addFile(resources_path('icons', '08-print-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', '08-print-dark.png'), mode=QIcon.Selected)
        self.dlg.mOptionsListWidget.item(i).setIcon(icon)
        i += 1

        # Locate by layer
        icon = QIcon()
        icon.addFile(resources_path('icons', '04-locate-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', '04-locate-dark.png'), mode=QIcon.Selected)
        self.dlg.mOptionsListWidget.item(i).setIcon(icon)
        i += 1

        # Attribute table
        icon = QIcon()
        icon.addFile(resources_path('icons', '11-attribute-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', '11-attribute-dark.png'), mode=QIcon.Selected)
        self.dlg.mOptionsListWidget.item(i).setIcon(icon)
        i += 1

        # Layer editing
        icon = QIcon()
        icon.addFile(resources_path('icons', '10-edition-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', '10-edition-dark.png'), mode=QIcon.Selected)
        self.dlg.mOptionsListWidget.item(i).setIcon(icon)
        i += 1

        # Tooltip layer
        icon = QIcon()
        icon.addFile(resources_path('icons', '16-tooltip-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', '16-tooltip-dark.png'), mode=QIcon.Selected)
        self.dlg.mOptionsListWidget.item(i).setIcon(icon)
        i += 1

        # Filter data with form
        icon = QIcon()
        icon.addFile(resources_path('icons', 'filter-icon-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', 'filter-icon-dark.png'), mode=QIcon.Selected)
        self.dlg.mOptionsListWidget.item(i).setIcon(icon)
        i += 1

        # Filter layer by user
        icon = QIcon()
        icon.addFile(resources_path('icons', '12-user-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', '12-user-dark.png'), mode=QIcon.Selected)
        self.dlg.mOptionsListWidget.item(i).setIcon(icon)
        i += 1

        # Dataviz
        icon = QIcon()
        icon.addFile(resources_path('icons', 'dataviz-icon-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', 'dataviz-icon-dark.png'), mode=QIcon.Selected)
        self.dlg.mOptionsListWidget.item(i).setIcon(icon)
        i += 1

        # Time manager
        icon = QIcon()
        icon.addFile(resources_path('icons', '13-timemanager-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', '13-timemanager-dark.png'), mode=QIcon.Selected)
        self.dlg.mOptionsListWidget.item(i).setIcon(icon)
        i += 1

        # Atlas
        icon = QIcon()
        icon.addFile(resources_path('icons', 'atlas-icon-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', 'atlas-icon-dark.png'), mode=QIcon.Selected)
        self.dlg.mOptionsListWidget.item(i).setIcon(icon)
        i += 1

        # Log
        # noinspection PyCallByClass,PyArgumentList
        icon = QIcon(QgsApplication.iconPath('mMessageLog.svg'))
        self.dlg.mOptionsListWidget.item(i).setIcon(icon)
        i += 1

        # Set stylesheet for QGroupBox
        if sys.platform.startswith('win'):
            style = ['0', '0', '0', '5%']
            margin = '4.0'
        else:
            style = ['225', '225', '225', '90%']
            margin = '2.5'
        style = STYLESHEET.format(*style, margin)
        self.style_sheet = style
        self.dlg.gb_tree.setStyleSheet(self.style_sheet)
        self.dlg.gb_layerSettings.setStyleSheet(self.style_sheet)
        self.dlg.gb_visibleTools.setStyleSheet(self.style_sheet)
        self.dlg.gb_Scales.setStyleSheet(self.style_sheet)
        self.dlg.gb_extent.setStyleSheet(self.style_sheet)
        self.dlg.gb_externalLayers.setStyleSheet(self.style_sheet)
        self.dlg.gb_lizmapExternalBaselayers.setStyleSheet(self.style_sheet)
        self.dlg.gb_generalOptions.setStyleSheet(self.style_sheet)
        self.dlg.gb_interface.setStyleSheet(self.style_sheet)
        self.dlg.gb_baselayersOptions.setStyleSheet(self.style_sheet)

        # Add widgets (not done in lizmap_var to avoid dependencies on ui)
        self.global_options['fixed_scale_overview_map']['widget'] = self.dlg.checkbox_scale_overview_map
        self.global_options['mapScales']['widget'] = self.dlg.inMapScales
        self.global_options['minScale']['widget'] = self.dlg.inMinScale
        self.global_options['maxScale']['widget'] = self.dlg.inMaxScale
        self.global_options['acl']['widget'] = self.dlg.inAcl
        self.global_options['initialExtent']['widget'] = self.dlg.inInitialExtent
        self.global_options['googleKey']['widget'] = self.dlg.inGoogleKey
        self.global_options['googleHybrid']['widget'] = self.dlg.cbGoogleHybrid
        self.global_options['googleSatellite']['widget'] = self.dlg.cbGoogleSatellite
        self.global_options['googleTerrain']['widget'] = self.dlg.cbGoogleTerrain
        self.global_options['googleStreets']['widget'] = self.dlg.cbGoogleStreets
        self.global_options['osmMapnik']['widget'] = self.dlg.cbOsmMapnik
        self.global_options['osmStamenToner']['widget'] = self.dlg.cbOsmStamenToner
        self.global_options['openTopoMap']['widget'] = self.dlg.cb_open_topo_map
        self.global_options['bingKey']['widget'] = self.dlg.inBingKey
        self.global_options['bingStreets']['widget'] = self.dlg.cbBingStreets
        self.global_options['bingSatellite']['widget'] = self.dlg.cbBingSatellite
        self.global_options['bingHybrid']['widget'] = self.dlg.cbBingHybrid
        self.global_options['ignKey']['widget'] = self.dlg.inIgnKey
        self.global_options['ignStreets']['widget'] = self.dlg.cbIgnStreets
        self.global_options['ignSatellite']['widget'] = self.dlg.cbIgnSatellite
        self.global_options['ignTerrain']['widget'] = self.dlg.cbIgnTerrain
        self.global_options['ignCadastral']['widget'] = self.dlg.cbIgnCadastral
        self.global_options['hideGroupCheckbox']['widget'] = self.dlg.cbHideGroupCheckbox
        self.global_options['activateFirstMapTheme']['widget'] = self.dlg.activate_first_map_theme
        self.global_options['popupLocation']['widget'] = self.dlg.liPopupContainer
        self.global_options['draw']['widget'] = self.dlg.activate_drawing_tools
        # Deprecated since LWC 3.7.0
        self.global_options['print']['widget'] = self.dlg.cbActivatePrint
        self.global_options['measure']['widget'] = self.dlg.cbActivateMeasure
        self.global_options['zoomHistory']['widget'] = self.dlg.cbActivateZoomHistory
        self.global_options['geolocation']['widget'] = self.dlg.cbActivateGeolocation
        self.global_options['pointTolerance']['widget'] = self.dlg.inPointTolerance
        self.global_options['lineTolerance']['widget'] = self.dlg.inLineTolerance
        self.global_options['polygonTolerance']['widget'] = self.dlg.inPolygonTolerance
        self.global_options['hideHeader']['widget'] = self.dlg.cbHideHeader
        self.global_options['hideMenu']['widget'] = self.dlg.cbHideMenu
        self.global_options['hideLegend']['widget'] = self.dlg.cbHideLegend
        self.global_options['hideOverview']['widget'] = self.dlg.cbHideOverview
        self.global_options['hideNavbar']['widget'] = self.dlg.cbHideNavbar
        self.global_options['hideProject']['widget'] = self.dlg.cbHideProject
        self.global_options['tmTimeFrameSize']['widget'] = self.dlg.inTimeFrameSize
        self.global_options['tmTimeFrameType']['widget'] = self.dlg.liTimeFrameType
        self.global_options['tmAnimationFrameLength']['widget'] = self.dlg.inAnimationFrameLength
        self.global_options['emptyBaselayer']['widget'] = self.dlg.cbAddEmptyBaselayer
        self.global_options['startupBaselayer']['widget'] = self.dlg.cbStartupBaselayer
        self.global_options['limitDataToBbox']['widget'] = self.dlg.cbLimitDataToBbox
        self.global_options['datavizLocation']['widget'] = self.dlg.liDatavizContainer
        self.global_options['datavizTemplate']['widget'] = self.dlg.inDatavizTemplate
        self.global_options['theme']['widget'] = self.dlg.combo_theme
        self.global_options['atlasShowAtStartup']['widget'] = self.dlg.atlasShowAtStartup
        self.global_options['atlasAutoPlay']['widget'] = self.dlg.atlasAutoPlay

        self.layer_options_list = lizmap_config.layerOptionDefinitions
        # Add widget information
        self.layer_options_list['title']['widget'] = self.dlg.inLayerTitle
        self.layer_options_list['abstract']['widget'] = self.dlg.teLayerAbstract
        self.layer_options_list['link']['widget'] = self.dlg.inLayerLink
        self.layer_options_list['minScale']['widget'] = None
        self.layer_options_list['maxScale']['widget'] = None
        self.layer_options_list['toggled']['widget'] = self.dlg.cbToggled
        self.layer_options_list['group_visibility']['widget'] = self.dlg.list_group_visibility
        self.layer_options_list['popup']['widget'] = self.dlg.checkbox_popup
        self.layer_options_list['popupFrame']['widget'] = self.dlg.popup_frame
        self.layer_options_list['popupTemplate']['widget'] = None
        self.layer_options_list['popupMaxFeatures']['widget'] = self.dlg.sbPopupMaxFeatures
        self.layer_options_list['popupDisplayChildren']['widget'] = self.dlg.cbPopupDisplayChildren
        self.layer_options_list['popup_allow_download']['widget'] = self.dlg.checkbox_popup_allow_download
        self.layer_options_list['groupAsLayer']['widget'] = self.dlg.cbGroupAsLayer
        self.layer_options_list['baseLayer']['widget'] = self.dlg.cbLayerIsBaseLayer
        self.layer_options_list['displayInLegend']['widget'] = self.dlg.cbDisplayInLegend
        self.layer_options_list['singleTile']['widget'] = self.dlg.cbSingleTile
        self.layer_options_list['cached']['widget'] = self.dlg.checkbox_server_cache
        self.layer_options_list['serverFrame']['widget'] = self.dlg.server_cache_frame
        self.layer_options_list['cacheExpiration']['widget'] = self.dlg.inCacheExpiration
        self.layer_options_list['metatileSize']['widget'] = self.dlg.inMetatileSize
        self.layer_options_list['clientCacheExpiration']['widget'] = self.dlg.inClientCacheExpiration
        self.layer_options_list['externalWmsToggle']['widget'] = self.dlg.cbExternalWms
        self.layer_options_list['sourceRepository']['widget'] = self.dlg.inSourceRepository
        self.layer_options_list['sourceProject']['widget'] = self.dlg.inSourceProject

        # Disabled because done earlier
        # self.layer_options_list['legend_image_option']['widget'] = self.dlg.combo_legend_option
        # self.layer_options_list['popupSource']['widget'] = self.dlg.liPopupSource
        # self.layer_options_list['imageFormat']['widget'] = self.dlg.liImageFormat
        # self.global_options['externalSearch']['widget'] = self.dlg.liExternalSearch

        # map QGIS geometry type
        # TODO lizmap 4, to remove
        self.mapQgisGeometryType = {
            0: 'point',
            1: 'line',
            2: 'polygon',
            3: 'unknown',
            4: 'none'
        }

        # Disable checkboxes on the layer tab
        self.enable_check_box(False)

        # Disable deprecated lizmap functions #121
        self.dlg.gb_lizmapExternalBaselayers.setVisible(False)

        # Catch user interaction on layer tree and inputs
        self.dlg.layer_tree.itemSelectionChanged.connect(self.setItemOptions)

        # Catch user interaction on Map Scales input
        self.dlg.inMapScales.editingFinished.connect(self.get_min_max_scales)

        # External search
        # Commented because when loading the CFG, the combobox is updated before we can read the API key from the CFG
        # file. The check is done only when saving.
        # self.dlg.liExternalSearch.currentIndexChanged.connect(self.check_api_key_address)

        warning_icon = QPixmap(":images/themes/default/mIconWarning.svg")

        # Scales
        self.dlg.min_scale_pic.setPixmap(QPixmap(":images/themes/default/mActionZoomOut.svg"))
        self.dlg.min_scale_pic.setText('')
        self.dlg.max_scale_pic.setPixmap(QPixmap(":images/themes/default/mActionZoomIn.svg"))
        self.dlg.max_scale_pic.setText('')
        self.dlg.label_warning_crs.setPixmap(warning_icon)
        ui_items = (
            self.dlg.label_min_scale, self.dlg.label_max_scale,
            self.dlg.min_scale_pic, self.dlg.max_scale_pic,
            self.dlg.inMinScale, self.dlg.inMaxScale,
        )
        for item in ui_items:
            item.setToolTip(tr("The minimum and maximum scales are defined by your minimum and maximum values above."))

        self.dlg.image_warning_project.setText("")
        self.dlg.image_warning_project.setPixmap(warning_icon)

        # Popup configuration
        self.dlg.image_warning_lizmap_popup.setPixmap(warning_icon)
        self.dlg.image_warning_lizmap_popup.setText('')

        widget_source_popup = self.layer_options_list['popupSource']['widget']
        widget_source_popup.currentIndexChanged.connect(self.enable_popup_source_button)

        index = widget_source_popup.findData('form')
        form_popup = widget_source_popup.model().item(index)

        font = form_popup.font()
        font.setUnderline(True)
        form_popup.setFont(font)

        # Connect widget signals to setLayerProperty method depending on widget type
        for key, item in self.layer_options_list.items():
            if item.get('widget'):
                control = item['widget']
                slot = partial(self.set_layer_property, key)
                if item['wType'] in ('text', 'spinbox'):
                    control.editingFinished.connect(slot)
                elif item['wType'] in ('textarea', 'html'):
                    control.textChanged.connect(slot)
                elif item['wType'] == 'checkbox':
                    control.stateChanged.connect(slot)
                elif item['wType'] == 'list':
                    control.currentIndexChanged.connect(slot)
                elif item['wType'] == 'layers':
                    control.layerChanged.connect(slot)
                elif item['wType'] == 'fields':
                    control.fieldChanged.connect(slot)

        self.crs_3857_base_layers_list = {
            'osm-mapnik': self.dlg.cbOsmMapnik,
            'osm-stamen-toner': self.dlg.cbOsmStamenToner,
            'opentopomap': self.dlg.cb_open_topo_map,
            'google-street': self.dlg.cbGoogleStreets,
            'google-satellite': self.dlg.cbGoogleSatellite,
            'google-hybrid': self.dlg.cbGoogleHybrid,
            'google-terrain': self.dlg.cbGoogleTerrain,
            'bing-road': self.dlg.cbBingStreets,
            'bing-aerial': self.dlg.cbBingSatellite,
            'bing-hybrid': self.dlg.cbBingHybrid,
            'ign-plan': self.dlg.cbIgnStreets,
            'ign-photo': self.dlg.cbIgnSatellite,
            'ign-scan': self.dlg.cbIgnTerrain,
            'ign-cadastral': self.dlg.cbIgnCadastral,
        }
        for item in self.crs_3857_base_layers_list.values():
            slot = self.check_visibility_crs_3857
            item.stateChanged.connect(slot)
        self.check_visibility_crs_3857()

        # Connect base-layer checkboxes
        self.base_layer_widget_list = {
            'layer': self.dlg.cbLayerIsBaseLayer,
            'empty': self.dlg.cbAddEmptyBaselayer
        }
        self.base_layer_widget_list.update(self.crs_3857_base_layers_list)
        for item in self.base_layer_widget_list.values():
            slot = self.onBaselayerCheckboxChange
            item.stateChanged.connect(slot)

        self.server_ftp = FtpServer(self.dlg)

        self.server_manager = ServerManager(
            self.dlg,
            self.dlg.table_server,
            self.dlg.add_server_button,
            self.dlg.remove_server_button,
            self.dlg.edit_server_button,
            self.dlg.refresh_versions_button,
            self.dlg.move_up_server_button,
            self.dlg.move_down_server_button,
            self.dlg.server_combo,
            self.refresh_combo_repositories,
            self.check_dialog_validity,
        )

        current = format_qgis_version(Qgis.QGIS_VERSION_INT)
        current = '{}.{}'.format(current[0], current[1])
        self.dlg.label_current_qgis.setText('<b>{}</b>'.format(current))
        text = self.dlg.qgis_and_lwc_versions_issue.text()
        self.dlg.qgis_and_lwc_versions_issue.setText(text.format(version=current))
        self.dlg.qgis_and_lwc_versions_issue.setVisible(False)

        # tables of layers
        # Todo Lizmap 3.4, remove dict init here
        self.layers_table = {
            'atlas': {
                'tableWidget': self.dlg.table_atlas,
                'removeButton': self.dlg.button_atlas_remove,
                'addButton': self.dlg.button_atlas_add,
                'editButton': self.dlg.button_atlas_edit,
                'upButton': self.dlg.button_atlas_up,
                'downButton': self.dlg.button_atlas_down,
                'manager': None,
            },
            'locateByLayer': {
                'tableWidget': self.dlg.table_locate_by_layer,
                'removeButton': self.dlg.remove_locate_layer_button,
                'addButton': self.dlg.add_locate_layer_button,
                'editButton': self.dlg.edit_locate_layer_button,
                'upButton': self.dlg.up_locate_layer_button,
                'downButton': self.dlg.down_locate_layer_button,
                'manager': None,
            },
            'attributeLayers': {
                'tableWidget': self.dlg.table_attribute_table,
                'removeButton': self.dlg.remove_attribute_table_button,
                'addButton': self.dlg.add_attribute_table_button,
                'editButton': self.dlg.edit_attribute_table_button,
                'upButton': self.dlg.up_attribute_table_button,
                'downButton': self.dlg.down_attribute_table_button,
                'manager': None,
            },
            'tooltipLayers': {
                'tableWidget': self.dlg.table_tooltip,
                'removeButton': self.dlg.remove_tooltip_button,
                'addButton': self.dlg.add_tooltip_button,
                'editButton': self.dlg.edit_tooltip_button,
                'upButton': self.dlg.up_tooltip_button,
                'downButton': self.dlg.down_tooltip_button,
                'manager': None,
            },
            'editionLayers': {
                'tableWidget': self.dlg.edition_table,
                'removeButton': self.dlg.remove_edition_layer,
                'addButton': self.dlg.add_edition_layer,
                'editButton': self.dlg.edit_edition_layer,
                'upButton': self.dlg.up_edition_layer,
                'downButton': self.dlg.down_edition_layer,
                'manager': None,
            },
            'layouts': {
                'tableWidget': self.dlg.table_layout,
                'editButton': self.dlg.edit_layout_form_button,
                'upButton': self.dlg.up_layout_form_button,
                'downButton': self.dlg.down_layout_form_button,
                'manager': None,
            },
            'loginFilteredLayers': {
                'tableWidget': self.dlg.table_login_filter,
                'removeButton': self.dlg.remove_filter_login_layer_button,
                'addButton': self.dlg.add_filter_login_layer_button,
                'editButton': self.dlg.edit_filter_login_layer_button,
                'manager': None,
            },
            'lizmapExternalBaselayers': {
                'tableWidget': self.dlg.twLizmapBaselayers,
                'removeButton': self.dlg.btLizmapBaselayerDel,
                'addButton': self.dlg.btLizmapBaselayerAdd,
                'cols': ['repository', 'project', 'layerName', 'layerTitle', 'layerImageFormat', 'order'],
                'jsonConfig': {}
            },
            'timemanagerLayers': {
                'tableWidget': self.dlg.time_manager_table,
                'removeButton': self.dlg.remove_time_manager_layer,
                'addButton': self.dlg.add_time_manager_layer,
                'editButton': self.dlg.edit_time_manager_layer,
                'upButton': self.dlg.up_time_manager_layer,
                'downButton': self.dlg.down_time_manager_layer,
                'manager': None,
            },
            'datavizLayers': {
                'tableWidget': self.dlg.table_dataviz,
                'removeButton': self.dlg.remove_dataviz_layer,
                'addButton': self.dlg.add_dataviz_layer,
                'editButton': self.dlg.edit_dataviz_layer,
                'upButton': self.dlg.up_dataviz_layer,
                'downButton': self.dlg.down_dataviz_layer,
                'manager': None,
            },
            'filter_by_polygon': {
                'tableWidget': self.dlg.table_filter_polygon,
                'removeButton': self.dlg.remove_filter_polygon_button,
                'addButton': self.dlg.add_filter_polygon_button,
                'editButton': self.dlg.edit_filter_polygon_button,
                'manager': None,
            },
            'formFilterLayers': {
                'tableWidget': self.dlg.table_form_filter,
                'removeButton': self.dlg.remove_filter_form_button,
                'addButton': self.dlg.add_filter_form_button,
                'editButton': self.dlg.edit_filter_form_button,
                'upButton': self.dlg.up_filter_form_button,
                'downButton': self.dlg.down_filter_form_button,
                'manager': None,
            }
        }

        # Set some tooltips
        tooltip = tr(
            'By default the layer is visible for all groups in Lizmap.\n'
            'If a comma separated list of groups IDs is defined,\n'
            'the layer will be visible only for these groups.\n'
            'Use Lizmap Web Client group IDs and not labels.')
        self.dlg.label_group_visibility.setToolTip(tooltip)
        self.dlg.list_group_visibility.setToolTip(tooltip)

        self.dlg.button_generate_html_table.setToolTip(tr(
            "A default HTML table will be generated in the layer maptip. The layout will be very similar to the auto "
            "popup, except that the display of a media must still be managed manually using HTML &lt;a&gt; or "
            "&lt;img&gt; for instance."
        ))

        # Filter by polygon
        self.dlg.layer_filter_polygon.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.dlg.layer_filter_polygon.layerChanged.connect(self.dlg.field_filter_polygon.setLayer)
        self.dlg.field_filter_polygon.setLayer(self.dlg.layer_filter_polygon.currentLayer())

        # Server combo
        server = QgsSettings().value('lizmap/instance_target_url', '')
        if server:
            index = self.dlg.server_combo.findData(server, ServerComboData.ServerUrl.value)
            if index:
                self.dlg.server_combo.setCurrentIndex(index)
        self.dlg.server_combo.currentIndexChanged.connect(self.target_server_changed)
        self.dlg.combo_lwc_version.currentIndexChanged.connect(self.lwc_version_changed)
        self.dlg.repository_combo.currentIndexChanged.connect(self.target_repository_changed)
        self.target_server_changed()
        self.refresh_combo_repositories()

        self.layerList = None
        self.action = None
        self.embeddedGroups = None
        self.myDic = None
        self.help_action = None

    def populate_lwc_combo(self):
        """ Fill the LWC selector about all versions. """
        self.dlg.combo_lwc_version.blockSignals(True)
        self.dlg.combo_lwc_version.clear()
        for lwc_version in LwcVersions:
            self.dlg.combo_lwc_version.addItem(lwc_version.value, lwc_version)

        # Find latest LWC version saved on the computer
        lwc_version = QgsSettings().value('lizmap/lizmap_web_client_version', DEFAULT_LWC_VERSION.value, str)
        try:
            lwc_version = LwcVersions(lwc_version)
        except ValueError:
            # The QgsSettings does not contain a valid LWC version item
            # Fallback on the default one from the plugin
            lwc_version = DEFAULT_LWC_VERSION
            LOGGER.info("Set value to default LWC version {}".format(lwc_version.value))

        index = self.dlg.combo_lwc_version.findData(lwc_version, LwcVersionComboData.LwcVersion.value)
        self.dlg.combo_lwc_version.setCurrentIndex(index)

        self.dlg.combo_lwc_version.blockSignals(False)
        self.lwc_version_changed()

    def target_server_changed(self):
        """ When the server destination has changed in the selector. """
        current_authid = self.dlg.server_combo.currentData(ServerComboData.AuthId.value)
        current_url = self.dlg.server_combo.currentData(ServerComboData.ServerUrl.value)
        QgsSettings().setValue('lizmap/instance_target_url', current_url)
        QgsSettings().setValue('lizmap/instance_target_url_authid', current_authid)
        self.check_dialog_validity()
        self.refresh_combo_repositories()

    def target_repository_changed(self):
        """ When the repository destination has changed in the selector. """
        current = self.dlg.repository_combo.currentData()
        QgsSettings().setValue('lizmap/instance_target_repository', current)
        if self.dlg.page_dataviz.isVisible():
            self.layers_table['datavizLayers'].get('manager').preview_dataviz_dialog()

    def refresh_combo_repositories(self):
        """ Refresh the combobox about repositories. """
        # Set the default error message that could happen for the dataviz
        error = tr(
            "Your current version of the selected server doesn't support the plot preview. "
            "You must upgrade at least to Lizmap Web Client "
            "<a href=\"https://github.com/3liz/lizmap-web-client/releases/tag/3.6.1\">3.6.1</a>."
        )
        self.dlg.dataviz_error_message.setText(error)

        self.dlg.repository_combo.clear()

        current = self.dlg.server_combo.currentData(ServerComboData.ServerUrl.value)
        if not current:
            return

        if not current.endswith('/'):
            current += '/'

        metadata = self.dlg.server_combo.currentData(ServerComboData.JsonMetadata.value)
        if not metadata:
            self.dlg.repository_combo.setVisible(False)
            self.dlg.stacked_dataviz_preview.setCurrentIndex(1)
            return

        repositories = metadata.get("repositories")
        if not repositories:
            self.dlg.repository_combo.setVisible(False)
            self.dlg.stacked_dataviz_preview.setCurrentIndex(1)
            return

        # At this stage, a more precise error message for the dataviz
        error = tr("You should select a plot to have the preview.")
        self.dlg.dataviz_error_message.setText(error)

        self.dlg.repository_combo.setVisible(True)
        self.dlg.stacked_dataviz_preview.setCurrentIndex(1)

        for repository_id, repository_data in repositories.items():
            self.dlg.repository_combo.addItem(repository_data['label'], repository_id)
            index = self.dlg.repository_combo.findData(repository_id)
            self.dlg.repository_combo.setItemData(index, repository_id, Qt.ToolTipRole)

        # Restore the previous value if possible
        previous = QgsSettings().value('lizmap/instance_target_repository')
        if not previous:
            return

        index = self.dlg.repository_combo.findData(previous)
        if not index:
            return

        self.dlg.repository_combo.setCurrentIndex(index)

    def current_repository(self) -> str:
        """ Fetch the current directory on the server if available. """
        if not self.dlg.repository_combo.isVisible():
            return ''

        return self.dlg.repository_combo.currentData()

    def lwc_version_changed(self):
        """When the version has changed in the selector."""
        current_version = self.dlg.combo_lwc_version.currentData(LwcVersionComboData.LwcVersion.value)

        if current_version is None:
            # We come from a higher version of Lizmap (from dev to master)
            current_version = DEFAULT_LWC_VERSION

        LOGGER.debug("Saving new value about the LWC target version : {}".format(current_version.value))
        QgsSettings().setValue('lizmap/lizmap_web_client_version', str(current_version.value))

        # New print panel
        # The checkbox is deprecated since LWC 3.7.0
        self.dlg.cbActivatePrint.setVisible(current_version <= LwcVersions.Lizmap_3_6)
        self.dlg.cbActivatePrint.setEnabled(current_version <= LwcVersions.Lizmap_3_6)

        found = False
        for lwc_version, items in self.lwc_versions.items():
            if found:
                for item in items:
                    if hasattr(item, 'setStyleSheet'):
                        # QLabel
                        item.setStyleSheet(NEW_FEATURE_CSS)
                    elif isinstance(item, QStandardItem):
                        # QComboBox
                        brush = QBrush()
                        # noinspection PyUnresolvedReferences
                        brush.setStyle(Qt.SolidPattern)
                        brush.setColor(QColor(NEW_FEATURE_COLOR))
                        item.setBackground(brush)
            else:
                for item in items:
                    if hasattr(item, 'setStyleSheet'):
                        # QLabel
                        item.setStyleSheet('')
                    elif isinstance(item, QStandardItem):
                        # QComboBox
                        item.setBackground(QBrush())

            if lwc_version == current_version:
                found = True

        # Change in all table manager too
        for key in self.layers_table.keys():
            manager = self.layers_table[key].get('manager')
            if manager:
                manager.set_lwc_version(current_version)

        # Compare the LWC version with the current QGIS Desktop version and the release JSON file
        version_file = os.path.join(lizmap_user_folder(), 'released_versions.json')
        if not os.path.exists(version_file):
            return

        with open(version_file) as json_file:
            json_content = json.loads(json_file.read())

        for lzm_version in json_content:
            if lzm_version['branch'] != current_version.value:
                continue

            qgis_min = lzm_version.get('qgis_min_version_recommended')
            qgis_max = lzm_version.get('qgis_max_version_recommended')
            if not (qgis_min or qgis_max):
                break

            if qgis_min <= Qgis.QGIS_VERSION_INT < qgis_max:
                self.dlg.qgis_and_lwc_versions_issue.setVisible(False)
            else:
                self.dlg.qgis_and_lwc_versions_issue.setVisible(True)

    # noinspection PyPep8Naming
    def initGui(self):
        """Create action that will start plugin configuration"""
        icon = QIcon(resources_path('icons', 'icon.png'))
        self.action = QAction(icon, 'Lizmap', self.iface.mainWindow())

        # connect the action to the run method
        # noinspection PyUnresolvedReferences
        self.action.triggered.connect(self.run)

        # Open the online help
        self.help_action = QAction(icon, 'Lizmap', self.iface.mainWindow())
        self.iface.pluginHelpMenu().addAction(self.help_action)
        # noinspection PyUnresolvedReferences
        self.help_action.triggered.connect(self.show_help)

        # connect Lizmap signals and functions
        self.dlg.buttonBox.button(QDialogButtonBox.Cancel).clicked.connect(self.dlg.close)
        self.dlg.buttonBox.button(QDialogButtonBox.Apply).clicked.connect(self.save_cfg_file)
        self.dlg.buttonBox.button(QDialogButtonBox.Ok).clicked.connect(self.ok_button_clicked)
        self.dlg.buttonBox.button(QDialogButtonBox.Help).clicked.connect(self.show_help)

        # Connect the left menu to the right panel
        self.dlg.mOptionsListWidget.currentRowChanged.connect(self.dlg.mOptionsStackedWidget.setCurrentIndex)

        # clear log button clicked
        self.dlg.button_clear_log.clicked.connect(self.clear_log)

        # Group wizard
        icon = QIcon(resources_path('icons', 'user_group.svg'))
        self.dlg.button_wizard_group_visibility_project.setText('')
        self.dlg.button_wizard_group_visibility_layer.setText('')
        self.dlg.button_wizard_group_visibility_project.setIcon(icon)
        self.dlg.button_wizard_group_visibility_layer.setIcon(icon)
        self.dlg.button_wizard_group_visibility_project.clicked.connect(self.open_wizard_group_project)
        self.dlg.button_wizard_group_visibility_layer.clicked.connect(self.open_wizard_group_layer)
        tooltip = tr("Open the group wizard")
        self.dlg.button_wizard_group_visibility_project.setToolTip(tooltip)
        self.dlg.button_wizard_group_visibility_layer.setToolTip(tooltip)

        # configure popup button
        self.dlg.btConfigurePopup.setText('')
        self.dlg.btConfigurePopup.setIcon(QIcon(":images/themes/default/console/iconSettingsConsole.svg"))
        self.dlg.btConfigurePopup.clicked.connect(self.configure_html_popup)
        self.dlg.convert_html_maptip.clicked.connect(self.convert_html_maptip)
        self.dlg.btQgisPopupFromForm.clicked.connect(self.maptip_from_form)
        self.dlg.button_generate_html_table.clicked.connect(self.html_table_from_layer)
        self.dlg.widget_deprecated_lizmap_popup.setVisible(False)

        # Link button
        self.dlg.button_refresh_link.setIcon(QIcon(QgsApplication.iconPath('mActionRefresh.svg')))
        self.dlg.button_refresh_link.setText('')
        self.dlg.button_refresh_link.setToolTip('Set the link from the dataUrl property in the layer properties.')
        self.dlg.button_refresh_link.clicked.connect(self.link_from_properties)

        # detect project closed
        self.iface.projectRead.connect(self.onProjectRead)
        self.iface.newProjectCreated.connect(self.onProjectRead)

        # initial extent
        self.dlg.btSetExtentFromProject.clicked.connect(self.set_initial_extent_from_project)
        self.dlg.btSetExtentFromCanvas.clicked.connect(self.set_initial_extent_from_canvas)

        self.dlg.btSetExtentFromProject.setIcon(QIcon(":images/themes/default/propertyicons/overlay.svg"))
        self.dlg.btSetExtentFromCanvas.setIcon(QIcon(":images/themes/default/mLayoutItemMap.svg"))

        # Dataviz options
        for item in Theme:
            self.global_options['theme']['widget'].addItem(item.value["label"], item.value["data"])
        index = self.global_options['theme']['widget'].findData(Theme.Light.value["data"])
        self.global_options['theme']['widget'].setCurrentIndex(index)

        # Manage "delete line" button
        for key, item in self.layers_table.items():
            control = item.get('removeButton')
            if control:
                slot = partial(self.remove_selected_layer_from_table, key)
                control.clicked.connect(slot)
                # noinspection PyCallByClass,PyArgumentList
                control.setIcon(QIcon(QgsApplication.iconPath('symbologyRemove.svg')))
                control.setText('')
                control.setToolTip(tr('Remove the selected layer from the list'))

            control = item.get('addButton')
            if control:
                control.setText('')
                # noinspection PyCallByClass,PyArgumentList
                control.setIcon(QIcon(QgsApplication.iconPath('symbologyAdd.svg')))
                control.setToolTip(tr('Add a new layer in the list'))

            control = item.get('editButton')
            if control:
                # If there is an edit button, it's the new generation of form
                slot = partial(self.edit_layer, key)
                control.clicked.connect(slot)
                control.setText('')
                # noinspection PyCallByClass,PyArgumentList
                control.setIcon(QIcon(QgsApplication.iconPath('symbologyEdit.svg')))
                control.setToolTip(tr('Edit the current layer configuration'))

                slot = partial(self.add_new_layer, key)
                add_button = item.get('addButton')
                if add_button:
                    add_button.clicked.connect(slot)
                if key == 'atlas':
                    definition = AtlasDefinitions()
                    dialog = AtlasEditionDialog
                elif key == 'attributeLayers':
                    definition = AttributeTableDefinitions()
                    dialog = AttributeTableEditionDialog
                elif key == 'editionLayers':
                    definition = EditionDefinitions()
                    dialog = EditionLayerDialog
                elif key == 'datavizLayers':
                    definition = DatavizDefinitions()
                    dialog = DatavizEditionDialog
                elif key == 'layouts':
                    definition = LayoutsDefinitions()
                    dialog = LayoutEditionDialog
                elif key == 'locateByLayer':
                    definition = LocateByLayerDefinitions()
                    dialog = LocateLayerEditionDialog
                elif key == 'loginFilteredLayers':
                    definition = FilterByLoginDefinitions()
                    dialog = FilterByLoginEditionDialog
                elif key == 'timemanagerLayers':
                    definition = TimeManagerDefinitions()
                    dialog = TimeManagerEditionDialog
                elif key == 'tooltipLayers':
                    definition = ToolTipDefinitions()
                    dialog = ToolTipEditionDialog
                elif key == 'formFilterLayers':
                    definition = FilterByFormDefinitions()
                    dialog = FilterByFormEditionDialog
                elif key == 'filter_by_polygon':
                    definition = FilterByPolygonDefinitions()
                    dialog = FilterByPolygonEditionDialog
                else:
                    raise Exception('Unknown panel.')

                item['tableWidget'].horizontalHeader().setStretchLastSection(True)

                if key == 'datavizLayers':
                    item['manager'] = TableManagerDataviz(
                        self.dlg,
                        definition,
                        dialog,
                        item['tableWidget'],
                        item['editButton'],
                        item.get('upButton'),
                        item.get('downButton'),
                    )
                elif key == 'layouts':
                    item['manager'] = TableManagerLayouts(
                        self.dlg,
                        definition,
                        dialog,
                        item['tableWidget'],
                        item['editButton'],
                        item.get('upButton'),
                        item.get('downButton'),
                    )
                else:
                    item['manager'] = TableManager(
                        self.dlg,
                        definition,
                        dialog,
                        item['tableWidget'],
                        item['removeButton'],
                        item['editButton'],
                        item.get('upButton'),
                        item.get('downButton'),
                    )

                control = item.get('upButton')
                if control:
                    slot = partial(self.move_layer_up, key)
                    control.clicked.connect(slot)
                    control.setText('')
                    # noinspection PyCallByClass,PyArgumentList
                    control.setIcon(QIcon(QgsApplication.iconPath('mActionArrowUp.svg')))
                    control.setToolTip(tr('Move the layer up in the table'))

                control = item.get('downButton')
                if control:
                    slot = partial(self.move_layer_down, key)
                    control.clicked.connect(slot)
                    control.setText('')
                    # noinspection PyCallByClass,PyArgumentList
                    control.setIcon(QIcon(QgsApplication.iconPath('mActionArrowDown.svg')))
                    control.setToolTip(tr('Move the layer down in the table'))

        # Delete layers from table when deleted from registry
        # noinspection PyUnresolvedReferences
        self.project.layersRemoved.connect(self.remove_layer_from_table_by_layer_ids)

        # Layouts
        # Not connecting the "layoutAdded" signal, it's done when opening the Lizmap plugin
        self.project.layoutManager().layoutRenamed.connect(self.layout_renamed)
        self.project.layoutManager().layoutRemoved.connect(self.layout_removed)

        # Lizmap external layers as baselayers
        # add a layer to the lizmap external baselayers
        self.dlg.btLizmapBaselayerAdd.clicked.connect(self.addLayerToLizmapBaselayers)

        # Atlas
        self.dlg.label_atlas_34.setVisible(self.is_dev_version)

        self.iface.addPluginToWebMenu(None, self.action)
        self.iface.addWebToolBarIcon(self.action)

        # IGN and google
        self.global_options['ignKey']['widget'].textChanged.connect(self.check_ign_french_free_key)
        self.global_options['ignKey']['widget'].textChanged.connect(self.check_api_key_address)
        self.global_options['googleKey']['widget'].textChanged.connect(self.check_api_key_address)

        server_side = tr(
            "This value will be replaced on the server side when evaluating the expression thanks to "
            "the QGIS server Lizmap plugin.")
        # Register variable helps
        if Qgis.QGIS_VERSION_INT >= 32200:
            QgsExpression.addVariableHelpText(
                "lizmap_user",
                "{}<br/>{}<br/>{}".format(
                    tr("The current Lizmap login as a string."),
                    tr("It might be an empty string if the user is not connected."),
                    server_side,
                )
            )
            QgsExpression.addVariableHelpText(
                "lizmap_user_groups",
                "{}<br/>{}<br/>{}".format(
                    tr("The current groups of the logged user as an array."),
                    tr("It might be an empty array if the user is not connected."),
                    server_side,
                )
            )

        # Let's fix the dialog to the first panel
        self.dlg.mOptionsListWidget.setCurrentRow(0)

    def check_dialog_validity(self) -> bool:
        """ Check the global dialog validity if we have :
         * at least one server
         * all servers with a login associated
         * a QGS project

        Only the first tab is always allowed.
        All other tabs must have these conditions.

        Returns True if all tabs are available.
        """
        self.dlg.project_valid.setVisible(False)
        allow_navigation = True

        valid, msg = self.check_global_project_options()
        if not valid:
            allow_navigation = False
            self.dlg.project_valid.setVisible(True)
            self.dlg.label_warning_project.setText(msg)

        # Project is valid, now check the server table validity
        try:
            self.server_manager
            if valid and not self.server_manager.check_validity_servers():
                allow_navigation = False
                msg = tr(
                    'You must have all Lizmap servers with a valid URL and a login provided before using the plugin.'
                )
                self.dlg.project_valid.setVisible(True)
                self.dlg.label_warning_project.setText(msg)
        except AttributeError:
            # Somehow in tests, we don't have the variable
            pass

        # Check the current selected server
        # Not relevant for now
        # server_url = self.dlg.server_combo.currentData(ServerComboData.ServerUrl.value)

        for i in range(1, self.dlg.mOptionsListWidget.count()):
            item = self.dlg.mOptionsListWidget.item(i)
            if allow_navigation:
                item.setFlags(item.flags() | Qt.ItemIsEnabled)
            else:
                item.setFlags(item.flags() & ~ Qt.ItemIsEnabled)

        return allow_navigation

    def add_new_layer(self, key):
        self.layers_table[key]['manager'].add_new_row()

    def move_layer_up(self, key):
        self.layers_table[key]['manager'].move_layer_up()

    def move_layer_down(self, key):
        self.layers_table[key]['manager'].move_layer_down()

    def edit_layer(self, key):
        self.layers_table[key]['manager'].edit_existing_row()

    def unload(self):
        """Remove the plugin menu item and icon."""
        self.iface.webMenu().removeAction(self.action)
        self.iface.removeWebToolBarIcon(self.action)

        if self.help_action:
            self.iface.pluginHelpMenu().removeAction(self.help_action)
            del self.help_action

    def check_api_key_address(self):
        """ Check the API key is provided for the address search bar. """
        provider = self.dlg.liExternalSearch.currentData()
        if provider in ('google', 'ign'):
            if provider == 'google':
                key = self.dlg.inGoogleKey.text()
            else:
                key = self.dlg.inIgnKey.text()

            if not key:
                QMessageBox.critical(
                    self.dlg,
                    tr('Address provider'),
                    tr('You have selected "{}" for the address search bar.').format(provider)
                    + "\n\n"
                    + tr(
                        'However, you have not provided any API key for this provider. Please add one in the '
                        '"Basemaps" panel to use this provider.'
                    ),
                    QMessageBox.Ok
                )

    def check_ign_french_free_key(self):
        """ French IGN free API keys choisirgeoportail/pratique do not include all layers. """
        key = self.global_options['ignKey']['widget'].text()
        if not key:
            self.global_options['ignTerrain']['widget'].setEnabled(False)
            self.global_options['ignTerrain']['widget'].setChecked(False)
        else:
            self.global_options['ignTerrain']['widget'].setEnabled(True)

    def enable_popup_source_button(self):
        """Enable or not the "Configure" button according to the popup source."""
        data = self.layer_options_list['popupSource']['widget'].currentData()
        self.dlg.btConfigurePopup.setVisible(data in ('lizmap', 'qgis'))
        self.dlg.widget_qgis_maptip.setVisible(data == 'qgis')

        if data == 'lizmap':
            layer = self._current_selected_layer()
            self.dlg.widget_deprecated_lizmap_popup.setVisible(isinstance(layer, QgsVectorLayer))
        else:
            self.dlg.widget_deprecated_lizmap_popup.setVisible(False)

    def open_wizard_group_layer(self):
        """ Open the group wizard for the layer visibility. """
        line_edit = self.dlg.list_group_visibility
        layer = self._current_selected_layer()
        if not layer:
            return
        helper = tr("Setting groups for the layer visibility '{}'".format(layer.name()))
        self._open_wizard_group(line_edit, helper)

    def open_wizard_group_project(self):
        """ Open the group wizard for the project visibility. """
        line_edit = self.dlg.inAcl
        helper = tr("Setting groups for the project visibility.")
        self._open_wizard_group(line_edit, helper)

    def _open_wizard_group(self, line_edit: QLineEdit, helper: str) -> Optional[str]:
        """ Open the group wizard and set the output in the line edit. """
        # Duplicated in base_edition_dialog.py, open_wizard_dialog()
        url = self.dlg.server_combo.currentData(ServerComboData.ServerUrl.value)
        if not url:
            QMessageBox.critical(
                self.dlg,
                tr('Server URL Error'),
                tr("You must have selected a server before opening the wizard, on the left panel."),
                QMessageBox.Ok
            )
            return None

        json_metadata = self.dlg.server_combo.currentData(ServerComboData.JsonMetadata.value)
        if not json_metadata:
            QMessageBox.critical(
                self.dlg,
                tr('Server URL Error'),
                tr("Check your server information table about the current selected server.")
                + "<br><br>" + url,
                QMessageBox.Ok
            )
            return None

        acl = json_metadata.get('acl')
        if not acl:
            QMessageBox.critical(
                self.dlg,
                tr('Upgrade your Lizmap instance'),
                tr(
                    "Your current Lizmap instance, running version {}, is not providing the needed information. "
                    "You should upgrade your Lizmap instance to at least 3.6.1 to use this wizard."
                ).format(json_metadata["info"]["version"]),
                QMessageBox.Ok
            )
            return None
        # End of duplicated

        current_acl = line_edit.text()
        wizard_dialog = WizardGroupDialog(helper, current_acl, acl['groups'])
        if not wizard_dialog.exec_():
            return None

        text = wizard_dialog.preview.text()
        if not text:
            return

        line_edit.setText(text)

    def show_help(self):
        """Opens the html help file content with default browser."""
        if self.locale in ONLINE_HELP_LANGUAGES:
            locale = self.locale
        else:
            locale = 'en'

        url = '{url}/{lang}/'.format(url=DOC_URL, lang=locale)
        QDesktopServices.openUrl(QUrl(url))

    @staticmethod
    def log(msg, abort=None, textarea=None):
        """Log the actions and errors and optionally show them in given text area."""
        if abort:
            sys.stdout = sys.stderr
        if textarea:
            textarea.append(msg)

    def clear_log(self):
        """Clear the content of the text area log."""
        self.dlg.outLog.clear()

    def enable_check_box(self, value):
        """Enable/Disable checkboxes and fields of the Layer tab."""
        for key, item in self.layer_options_list.items():
            if item.get('widget') and key != 'sourceProject':
                item['widget'].setEnabled(value)
        self.dlg.btConfigurePopup.setEnabled(value)
        self.dlg.btQgisPopupFromForm.setEnabled(value)
        self.dlg.button_generate_html_table.setEnabled(value)

    def get_min_max_scales(self):
        """Get Min Max Scales from scales input field."""
        LOGGER.info('Getting min/max scales')
        min_scale = 1
        max_scale = 1000000000
        in_map_scales = self.dlg.inMapScales.text()
        map_scales = [int(a.strip(' \t')) for a in in_map_scales.split(',') if str(a.strip(' \t')).isdigit()]
        map_scales.sort()
        if len(map_scales) < 2:
            QMessageBox.critical(
                self.dlg,
                tr('Lizmap Error'),
                tr(
                    'Map scales: Write down integer scales separated by comma. '
                    'You must enter at least 2 min and max values.'),
                QMessageBox.Ok)
        else:
            min_scale = min(map_scales)
            max_scale = max(map_scales)
        self.dlg.inMinScale.setText(str(min_scale))
        self.dlg.inMaxScale.setText(str(max_scale))
        self.dlg.inMapScales.setText(', '.join(map(str, map_scales)))

    def get_config(self):
        """Get the saved configuration from the projet.qgs.cfg config file.

        Populate the gui fields accordingly
        """
        # Get the project config file (projectname.qgs.cfg)
        json_file = '{}.cfg'.format(self.project.fileName())
        json_options = {}
        if os.path.exists(json_file):
            target_version = self.dlg.combo_lwc_version.currentData()
            LOGGER.info('Reading the CFG file with a LWC target version {}'.format(target_version.value))
            cfg_file = open(json_file)
            json_file_reader = cfg_file.read()
            # noinspection PyBroadException
            try:
                sjson = json.loads(json_file_reader)

                # Metadata section
                meta = sjson.get('metadata')
                if meta:
                    qgis_version = meta.get('qgis_desktop_version')
                    self.set_previous_qgis_version(qgis_version)

                json_options = sjson['options']
                for key in self.layers_table.keys():
                    if key in sjson:
                        self.layers_table[key]['jsonConfig'] = sjson[key]
                    else:
                        self.layers_table[key]['jsonConfig'] = {}

                    manager = self.layers_table[key].get('manager')
                    if manager:

                        manager.truncate()

                        if key == 'layouts':
                            manager.load_qgis_layouts(sjson.get(key, {}))
                            continue

                        if key in sjson:
                            manager.from_json(sjson[key])
                        else:
                            # get a subset of the data to give to the table form
                            data = {k: json_options[k] for k in json_options if k.startswith(manager.definitions.key())}
                            if data:
                                manager.from_json(data)

            except Exception as e:
                if self.is_dev_version:
                    raise
                LOGGER.critical(e)
                copyfile(json_file, '{}.back'.format(json_file))
                message = tr(
                    'Errors encountered while reading the last layer tree state. '
                    'Please re-configure the options in the Layers tab completely. '
                    'The previous .cfg has been saved as .cfg.back')
                QMessageBox.critical(
                    self.dlg, tr('Lizmap Error'), message, QMessageBox.Ok)
                self.log(message, abort=True, textarea=self.dlg.outLog)
                LOGGER.critical('Error while reading the CFG file')
            finally:
                cfg_file.close()

        else:
            LOGGER.info('Lizmap CFG does not exist for this project.')
            for key in self.layers_table.keys():
                manager = self.layers_table[key].get('manager')
                if manager:
                    manager.truncate()

        # Set the global options (map, tools, etc.)
        for key, item in self.global_options.items():
            if item.get('widget'):
                if item.get('tooltip'):
                    item['widget'].setToolTip(item.get('tooltip'))

                if item['wType'] == 'checkbox':
                    item['widget'].setChecked(item['default'])
                    if key in json_options:
                        if isinstance(json_options[key], str):
                            if json_options[key].lower() in ('yes', 'true', 't', '1'):
                                item['widget'].setChecked(True)
                        elif isinstance(json_options[key], bool):
                            item['widget'].setChecked(json_options[key])

                if item['wType'] in ('text', 'textarea', 'html'):
                    if isinstance(item['default'], (list, tuple)):
                        item['widget'].setText(", ".join(map(str, item['default'])))
                    else:
                        item['widget'].setText(str(item['default']))
                    if key in json_options:
                        if isinstance(json_options[key], (list, tuple)):
                            item['widget'].setText(", ".join(map(str, json_options[key])))
                        else:
                            item['widget'].setText(str(json_options[key]))

                # if item['wType'] in ('html'):
                # if isinstance(item['default'], (list, tuple)):
                # item['widget'].setHtml(", ".join(map(str, item['default'])))
                # else:
                # item['widget'].setHtml(str(item['default']))
                # if jsonOptions.has_key(key):
                # if isinstance(jsonOptions[key], (list, tuple)):
                # item['widget'].setHtml(", ".join(map(str, jsonOptions[key])))
                # else:
                # item['widget'].setHtml(str(jsonOptions[key]))

                if item['wType'] == 'spinbox':
                    item['widget'].setValue(int(item['default']))
                    if key in json_options:
                        item['widget'].setValue(int(json_options[key]))

                if item['wType'] == 'list':
                    if isinstance(item['list'][0], (list, tuple)):
                        # New way with icon, tooltip, translated label
                        pass
                    else:
                        # Legacy way
                        for i, item_config in enumerate(item['list']):
                            item['widget'].setItemData(i, item_config)

                        if item['default'] in item['list']:
                            index = item['widget'].findData(item['default'])
                            item['widget'].setCurrentIndex(index)

                    if key in json_options:
                        index = item['widget'].findData(json_options[key])
                        if index:
                            item['widget'].setCurrentIndex(index)

        # Set layer combobox
        for key, item in self.global_options.items():
            if item.get('widget'):
                if item['wType'] == 'layers':
                    if key in json_options:
                        for lyr in self.project.mapLayers().values():
                            if lyr.id() == json_options[key]:
                                item['widget'].setLayer(lyr)
                                break

        # Then set field combobox
        for key, item in self.global_options.items():
            if item.get('widget'):
                if item['wType'] == 'fields':
                    if key in json_options:
                        item['widget'].setField(str(json_options[key]))

        # Fill the table widgets
        for key, item in self.layers_table.items():
            self.load_config_into_table_widget(key)

        self.check_ign_french_free_key()
        # self.check_api_key_address() Done when the CFG is loaded
        LOGGER.info('CFG file has been loaded')

    def set_previous_qgis_version(self, qgis_version):
        """ Manage the label about the QGIS Desktop version and previous version used. """
        if not qgis_version:
            self.dlg.label_qgis_different_version.setVisible(False)
            return

        project = format_qgis_version(qgis_version)
        current = format_qgis_version(Qgis.QGIS_VERSION_INT)

        if project[0] * 100 + project[1] == current[0] * 100 + current[1]:
            self.dlg.label_qgis_different_version.setVisible(False)
            return

        self.dlg.label_qgis_different_version.setVisible(True)
        text = self.dlg.label_qgis_different_version.text()
        previous = '{}.{}'.format(project[0], project[1])
        current = '{}.{}'.format(current[0], current[1])
        text = text.format(previous_version=previous, current_version=current)
        self.dlg.label_qgis_different_version.setText(text)
        LOGGER.warning(
            'New QGIS version detected from the Lizmap CFG file. You should check QGIS Server version as '
            'well.')

    def load_config_into_table_widget(self, key):
        """Load data from lizmap config file into the widget.

        :param key: The key section to load according to the table.
        :type key: basestring
        """
        # Get parameters for the widget
        lt = self.layers_table[key]

        if lt.get('manager'):
            # Note, new generation form/manager do not use this function
            return

        widget = lt['tableWidget']
        attributes = lt['cols']
        json_config = lt['jsonConfig']

        # Get index of layerId column
        store_layer_id = 'layerId' in lt['cols']

        # For edition layers, fill capabilities
        # Fill editionlayers capabilities
        if key == 'editionLayers' and json_config:
            for k, v in json_config.items():
                if 'capabilities' in v:
                    for x, y in v['capabilities'].items():
                        json_config[k][x] = y

        # empty previous content
        for row in range(widget.rowCount()):
            widget.removeRow(row)
        widget.setRowCount(0)

        # fill from the json if exists
        col_count = len(attributes)

        # +1 for layer name column (1st column)
        if store_layer_id:
            col_count += 1

        if json_config:
            # reorder data if needed
            if 'order' in list(json_config.items())[0][1]:
                # FIXME shadow error with key
                data = [(k, json_config[k]) for k in sorted(json_config, key=lambda key: json_config[key]['order'])]
            else:
                data = list(json_config.items())

            # load content from json file
            project_layers_ids = list(self.project.mapLayers().keys())
            for k, v in data:
                # check if the layer still exists in the QGIS project
                if 'layerId' in list(v.keys()):
                    if v['layerId'] not in project_layers_ids:
                        continue
                tw_row_count = widget.rowCount()
                # add a new line
                widget.setRowCount(tw_row_count + 1)
                widget.setColumnCount(col_count)
                i = 0
                if store_layer_id:
                    # add layer name column - get name from layer if possible (if the user has renamed the layer)
                    icon = None
                    if 'layerId' in list(v.keys()):
                        layer = self.project.mapLayer(v['layerId'])
                        if layer:
                            k = layer.name()
                            # noinspection PyArgumentList
                            icon = QgsMapLayerModel.iconForLayer(layer)

                    new_item = QTableWidgetItem(k)
                    if icon:
                        new_item.setIcon(icon)
                    widget.setItem(tw_row_count, 0, new_item)
                    i += 1
                # other information
                for key in attributes:
                    if key in v:
                        value = v[key]
                    else:
                        value = ''
                    new_item = QTableWidgetItem(str(value))
                    widget.setItem(tw_row_count, i, new_item)
                    i += 1

        if key == 'lizmapExternalBaselayers':
            # We enable this widget only if there is at least one existing entry in the CFG. #121
            rows = widget.rowCount()
            if rows >= 1:
                self.dlg.gb_lizmapExternalBaselayers.setVisible(True)
                LOGGER.warning('Table "lizmapExternalBaselayers" has been loaded, which is deprecated')
        else:
            LOGGER.info('Table "{}" has been loaded'.format(key))

    def get_qgis_layer_by_id(self, my_id):
        """Get a QgsLayer by its Id"""
        for layer in self.project.mapLayers().values():
            if my_id == layer.id():
                return layer
        return None

    def set_initial_extent_from_project(self):
        """
        Get the project WMS advertised extent
        and set the initial xmin, ymin, xmax, ymax
        in the map options tab
        """
        p_wms_extent = self.project.readListEntry('WMSExtent', '')[0]
        if len(p_wms_extent) > 1:
            extent = '{}, {}, {}, {}'.format(
                p_wms_extent[0],
                p_wms_extent[1],
                p_wms_extent[2],
                p_wms_extent[3]
            )
            self.dlg.inInitialExtent.setText(extent)

        LOGGER.info('Setting extent from the project')

    def set_initial_extent_from_canvas(self):
        """
        Get the map canvas extent
        and set the initial xmin, ymin, xmax, ymax
        in the map options tab
        """
        # Get map canvas extent
        extent = self.iface.mapCanvas().extent()
        initial_extent = '{}, {}, {}, {}'.format(
            extent.xMinimum(),
            extent.yMinimum(),
            extent.xMaximum(),
            extent.yMaximum()
        )
        self.dlg.inInitialExtent.setText(initial_extent)
        LOGGER.info('Setting extent from the canvas')

    def remove_selected_layer_from_table(self, key):
        """
        Remove a layer from the list of layers
        for which to have the "locate by layer" tool
        """
        tw = self.layers_table[key]['tableWidget']
        tw.removeRow(tw.currentRow())
        LOGGER.info('Removing one row in table "{}"'.format(key))

    def check_cfg_file_exists(self) -> bool:
        """ Return boolean if a CFG file exists for the given project. """
        return Path(self.project.fileName() + '.cfg').exists()

    def remove_layer_from_table_by_layer_ids(self, layer_ids):
        """
        Remove layers from tables when deleted from layer registry
        """
        if not self.check_cfg_file_exists():
            return

        for key, item in self.layers_table.items():

            manager = self.layers_table[key].get('manager')
            if manager:
                manager.layers_has_been_deleted(layer_ids)
                continue

            tw = self.layers_table[key]['tableWidget']

            # Count lines
            tw_row_count = tw.rowCount()
            if not tw_row_count:
                continue

            # Get index of layerId column
            if 'layerId' not in self.layers_table[key]['cols']:
                continue
            idx = self.layers_table[key]['cols'].index('layerId') + 1

            # Remove layer if layerId match
            for row in range(tw_row_count):
                if tw.item(row, idx):
                    item_layer_id = str(tw.item(row, idx).text())
                    if item_layer_id in layer_ids:
                        tw.removeRow(row)

        LOGGER.info('Layer ID "{}" has been removed from the project'.format(layer_ids))

    def layout_renamed(self, layout, new_name: str):
        """ When a layout has been renamed in the project. """
        if not self.check_cfg_file_exists():
            return

        self.layers_table['layouts']['manager'].layout_renamed(layout, new_name)

    def layout_removed(self, name: str):
        """ When a layout has been removed from the project. """
        if not self.check_cfg_file_exists():
            return

        self.layers_table['layouts']['manager'].layout_removed(name)

    def check_wfs_is_checked(self, layer):
        wfs_layers_list = self.project.readListEntry('WFSLayers', '')[0]
        has_wfs_option = False
        for wfs_layer in wfs_layers_list:
            if layer.id() == wfs_layer:
                has_wfs_option = True
        if not has_wfs_option:
            self.display_error(tr(
                'The layers you have chosen for this tool must be checked in the "WFS Capabilities" option of the '
                'QGIS Server tab in the "Project Properties" dialog.'))
            return False
        return True

    def display_error(self, message):
        QMessageBox.critical(
            self.dlg,
            tr('Lizmap Error'),
            message,
            QMessageBox.Ok)

    # noinspection PyPep8Naming
    def addLayerToLizmapBaselayers(self):
        """Add a layer in the list of Lizmap external baselayers.

        This is a deprecated feature in lizmap.
        Users should use embedded layer instead.

        THIS WILL BE REMOVED IN LIZMAP 4.
        """
        layerRepository = str(self.dlg.inLizmapBaselayerRepository.text()).strip(' \t')
        layerProject = str(self.dlg.inLizmapBaselayerProject.text()).strip(' \t')
        layerName = str(self.dlg.inLizmapBaselayerLayer.text()).strip(' \t')
        layerTitle = str(self.dlg.inLizmapBaselayerTitle.text()).strip(' \t')
        layerImageFormat = str(self.dlg.inLizmapBaselayerImageFormat.text()).strip(' \t')
        content = [layerRepository, layerProject, layerName, layerTitle, layerImageFormat]
        # Check that every option is set
        for val in content:
            if not val:
                QMessageBox.critical(
                    self.dlg,
                    tr("Lizmap Error"),
                    tr(
                        "Please check that all input fields have been filled: repository, project, "
                        "layer name and title"),
                    QMessageBox.Ok
                )
                return

        lblTableWidget = self.dlg.twLizmapBaselayers
        twRowCount = lblTableWidget.rowCount()
        content.append(twRowCount)  # store order
        colCount = len(content)
        if twRowCount < 6:
            # set new rowCount
            lblTableWidget.setRowCount(twRowCount + 1)
            lblTableWidget.setColumnCount(colCount)
            # Add content in the widget line
            i = 0
            for val in content:
                item = QTableWidgetItem(val)
                lblTableWidget.setItem(twRowCount, i, item)
                i += 1

            LOGGER.info('Layer has been added to the base layer list')

    def setTreeItemData(self, itemType, itemKey, jsonLayers):
        """Define default data or data from previous configuration for one item (layer or group)
        Used in the method populateLayerTree
        """
        # Type : group or layer
        self.myDic[itemKey]['type'] = itemType

        # DEFAULT VALUES : generic default values for layers and group
        self.myDic[itemKey]['name'] = itemKey
        for key, item in self.layer_options_list.items():
            self.myDic[itemKey][key] = item['default']
        self.myDic[itemKey]['title'] = self.myDic[itemKey]['name']

        if itemType == 'group':
            # embedded group ?
            if self.embeddedGroups and itemKey in self.embeddedGroups:
                pName = self.embeddedGroups[itemKey]['project']
                pName = os.path.splitext(os.path.basename(pName))[0]
                self.myDic[itemKey]['sourceProject'] = pName

        # DEFAULT VALUES : layers have got more precise data
        keepMetadata = False
        if itemType == 'layer':

            # layer name
            layer = self.get_qgis_layer_by_id(itemKey)
            self.myDic[itemKey]['name'] = layer.name()
            # title and abstract
            self.myDic[itemKey]['title'] = layer.name()
            if layer.title():
                self.myDic[itemKey]['title'] = layer.title()
                keepMetadata = True
            if layer.abstract():
                self.myDic[itemKey]['abstract'] = layer.abstract()
                keepMetadata = True

            if not self.myDic[itemKey]['link']:
                self.myDic[itemKey]['link'] = layer_property(layer, LayerProperties.DataUrl)

            # hide non geo layers (csv, etc.)
            # if layer.type() == 0:
            #    if layer.geometryType() == 4:
            #        self.ldisplay = False

            # layer scale visibility
            if layer.hasScaleBasedVisibility():
                self.myDic[itemKey]['minScale'] = layer.maximumScale()
                self.myDic[itemKey]['maxScale'] = layer.minimumScale()
            # toggled : check if layer is toggled in qgis legend
            # self.myDic[itemKey]['toggled'] = layer.self.iface.legendInterface().isLayerVisible(layer)
            self.myDic[itemKey]['toggled'] = False
            # group as layer : always False obviously because it is already a layer
            self.myDic[itemKey]['groupAsLayer'] = False
            # embedded layer ?
            fromProject = self.project.layerIsEmbedded(itemKey)
            if os.path.exists(fromProject):
                pName = os.path.splitext(os.path.basename(fromProject))[0]
                self.myDic[itemKey]['sourceProject'] = pName

        # OVERRIDE DEFAULT FROM CONFIGURATION FILE
        if self.myDic[itemKey]['name'] in jsonLayers:
            json_key = self.myDic[itemKey]['name']
            LOGGER.info('Reading configuration from dictionary for layer {}'.format(json_key))
            # loop through layer options to override
            for key, item in self.layer_options_list.items():
                # override only for ui widgets
                if item.get('widget'):
                    if key in jsonLayers[json_key]:

                        if key == 'legend_image_option' and 'noLegendImage' in jsonLayers[json_key]:
                            if self.myDic[itemKey].get('legend_image_option'):
                                # The key is already set before with noLegendImage
                                LOGGER.info(
                                    "Skip key legend_image_option because it has been set previously with noLegendImage"
                                )
                                continue

                        # checkboxes
                        if item['wType'] == 'checkbox':
                            value = jsonLayers[json_key][key]
                            if isinstance(value, bool):
                                self.myDic[itemKey][key] = value
                            elif value.lower() in ('yes', 'true', 't', '1'):
                                self.myDic[itemKey][key] = True
                            else:
                                self.myDic[itemKey][key] = False
                        # spin box
                        elif item['wType'] == 'spinbox':
                            if jsonLayers[json_key][key] != '':
                                self.myDic[itemKey][key] = jsonLayers[json_key][key]
                        # text inputs
                        elif item['wType'] in ('text', 'textarea'):
                            if jsonLayers[json_key][key] != '':
                                if item.get('isMetadata'):  # title and abstract
                                    if not keepMetadata:
                                        self.myDic[itemKey][key] = jsonLayers[json_key][key]
                                else:
                                    self.myDic[itemKey][key] = jsonLayers[json_key][key]
                        # lists
                        elif item['wType'] == 'list':
                            # New way with data, label, tooltip and icon
                            datas = [j[0] for j in item['list']]
                            if jsonLayers[json_key][key] in datas:
                                self.myDic[itemKey][key] = jsonLayers[json_key][key]

                else:
                    if key == 'noLegendImage' and 'noLegendImage' in jsonLayers.get(json_key):
                        tmp = 'hide_at_startup'  # Default value
                        if jsonLayers[json_key].get('noLegendImage') == 'True':
                            tmp = 'disabled'
                        elif jsonLayers[json_key].get('noLegendImage') != 'False':
                            LOGGER.info(
                                "Unknown value for key noLegendImage = {}".format(
                                    jsonLayers[json_key].get('noLegendImage')))
                        self.myDic[itemKey]['legend_image_option'] = tmp

                    LOGGER.info('Skip key {} because no UI widget'.format(key))

                # popupContent
                if key == 'popupTemplate':
                    if key in jsonLayers[json_key]:
                        self.myDic[itemKey][key] = jsonLayers[json_key][key]

    def process_node(self, node, parent_node, json_layers):
        """
        Process a single node of the QGIS layer tree and adds it to Lizmap layer tree.
        """
        for child in node.children():
            if QgsLayerTree.isGroup(child):
                if not isinstance(child, QgsLayerTreeGroup):
                    # Sip cast issue , Lizmap plugin #299
                    child = sip.cast(child, QgsLayerTreeGroup)
                child_id = child.name()
                child_type = 'group'
                # noinspection PyCallByClass,PyArgumentList
                child_icon = QIcon(QgsApplication.iconPath('mActionFolder.svg'))
            elif QgsLayerTree.isLayer(child):
                if not isinstance(child, QgsLayerTreeLayer):
                    # Sip cast issue , Lizmap plugin #299
                    child = sip.cast(child, QgsLayerTreeLayer)
                child_id = child.layerId()
                child_type = 'layer'
                # noinspection PyArgumentList
                child_icon = QgsMapLayerModel.iconForLayer(child.layer())
            else:
                raise Exception('Unknown child type')

            # Select an existing item, select the header item or create the item
            if child_id in self.myDic:
                # If the item already exists in self.myDic, select it
                item = self.myDic[child_id]['item']
            elif child_id == '':
                # If the id is empty string, this is a root layer, select the headerItem
                item = self.dlg.layer_tree.headerItem()
            else:
                # else create the item and add it to the header item
                # add the item to the dictionary
                self.myDic[child_id] = {'id': child_id}
                if child_type == 'group':
                    # it is a group
                    self.setTreeItemData('group', child_id, json_layers)
                else:
                    # it is a layer
                    self.setTreeItemData('layer', child_id, json_layers)

                item = QTreeWidgetItem(
                    [
                        str(self.myDic[child_id]['name']),
                        str(self.myDic[child_id]['id']),
                        self.myDic[child_id]['type']
                    ]
                )
                item.setToolTip(0, self.myDic[child_id]['name'])
                item.setIcon(0, child_icon)
                self.myDic[child_id]['item'] = item

                # Move group or layer to its parent node
                if not parent_node:
                    self.dlg.layer_tree.addTopLevelItem(item)
                else:
                    parent_node.addChild(item)

            if child_type == 'group':
                self.process_node(child, item, json_layers)

    def read_lizmap_config_file(self) -> dict:
        """ Read the CFG file and returns the JSON content. """
        # Check if a json configuration file exists (myproject.qgs.cfg)
        json_file = '{}.cfg'.format(self.project.fileName())
        json_layers = {}
        if os.path.exists(str(json_file)):
            f = open(json_file)
            json_file_reader = f.read()
            # noinspection PyBroadException
            try:
                sjson = json.loads(json_file_reader)
                json_layers = sjson['layers']
            except Exception:
                if self.is_dev_version:
                    raise
                message = tr(
                    'Errors encountered while reading the last layer tree state. '
                    'Please re-configure the options in the Layers tab completely'
                )
                QMessageBox.critical(self.dlg, tr('Lizmap Error'), '', QMessageBox.Ok)
                self.log(message, abort=True, textarea=self.dlg.outLog)
            finally:
                f.close()
        return json_layers

    def populate_layer_tree(self):
        """Populate the layer tree of the Layers tab from QGIS legend interface.

        Needs to be refactored.
        """
        self.dlg.layer_tree.clear()
        self.dlg.layer_tree.headerItem().setText(0, tr('List of layers'))
        self.myDic = {}

        json_layers = self.read_lizmap_config_file()
        root = self.project.layerTreeRoot()

        # Recursively process layer tree nodes
        self.process_node(root, None, json_layers)
        self.dlg.layer_tree.expandAll()

        # Add the self.myDic to the global layerList dictionary
        self.layerList = self.myDic

        self.enable_check_box(False)

    def setItemOptions(self):
        """Restore layer/group input values when selecting a layer tree item"""
        # get the selected item
        item = self.dlg.layer_tree.currentItem()
        if item:
            self.enable_check_box(True)
        else:
            self.enable_check_box(False)

        iKey = item.text(1)
        if iKey in self.layerList:
            # get information about the layer or the group from the layerList dictionary
            selectedItem = self.layerList[iKey]

            # set options
            for key, val in self.layer_options_list.items():
                if val.get('widget'):

                    if val.get('tooltip'):
                        val['widget'].setToolTip(val.get('tooltip'))

                    if val['wType'] in ('text', 'textarea'):
                        if val['type'] == 'list':
                            data = selectedItem[key]
                            if isinstance(data, str):
                                # It should be a list, but it has been temporary a string during the dev process
                                data = [data]
                            text = ','.join(data)
                        else:
                            text = selectedItem[key]
                        if val['wType'] == 'text':
                            val['widget'].setText(text)
                        else:
                            # Abstract is the only textarea
                            val['widget'].setPlainText(text)
                    elif val['wType'] == 'spinbox':
                        val['widget'].setValue(int(selectedItem[key]))
                    elif val['wType'] == 'checkbox':
                        val['widget'].setChecked(selectedItem[key])
                        children = val.get('children')
                        if children:
                            exclusive = val.get('exclusive', False)
                            if exclusive:
                                is_enabled = not selectedItem[key]
                            else:
                                is_enabled = selectedItem[key]
                            self.layer_options_list[children]['widget'].setEnabled(is_enabled)
                            if self.layer_options_list[children]['wType'] == 'checkbox' and not is_enabled:
                                if self.layer_options_list[children]['widget'].isChecked():
                                    self.layer_options_list[children]['widget'].setChecked(False)

                    elif val['wType'] == 'list':
                        # New way with data, label, tooltip and icon
                        index = val['widget'].findData(selectedItem[key])

                        if index < 0 and val.get('default'):
                            # Get back to default
                            index = val['widget'].findData(val['default'])

                        val['widget'].setCurrentIndex(index)

                    # deactivate wms checkbox if not needed
                    if key == 'externalWmsToggle':
                        wms_enabled = self.get_item_wms_capability(selectedItem)
                        if wms_enabled is not None:
                            self.dlg.cbExternalWms.setEnabled(wms_enabled)
                            if wms_enabled:
                                self.dlg.cbExternalWms.toggled.connect(self.external_wms_toggled)
                                self.external_wms_toggled()
                            else:
                                self.dlg.cbExternalWms.setChecked(False)
                                try:
                                    self.dlg.cbExternalWms.toggled.disconnect(self.external_wms_toggled)
                                except TypeError:
                                    # The object was not connected
                                    pass

            layer = self._current_selected_layer()  # It can be a layer or a group

            # Disable popup configuration for groups and raster
            # Disable QGIS popup for layer without geom
            is_vector = isinstance(layer, QgsVectorLayer)
            has_geom = is_vector and layer.wkbType() != QgsWkbTypes.NoGeometry
            self.dlg.btConfigurePopup.setEnabled(has_geom)
            self.dlg.btQgisPopupFromForm.setEnabled(is_vector)
            self.dlg.button_generate_html_table.setEnabled(is_vector)
            self.layer_options_list['popupSource']['widget'].setEnabled(is_vector)

            # For a group, there isn't the toggle option, #298, TEMPORARY DISABLED
            tooltip = tr("If the layer is displayed by default")
            self.layer_options_list['toggled']['widget'].setToolTip(tooltip)
            # try:
            #     # We always disconnect everything
            #     self.layer_options_list['groupAsLayer']['widget'].disconnect()
            # except TypeError:
            #     pass
            #
            # if isinstance(layer, QgsMapLayer):
            #     # Always enabled
            #     self.layer_options_list['toggled']['widget'].setEnabled(True)
            #     tooltip = tr("If the layer is displayed by default")
            #     self.layer_options_list['toggled']['widget'].setToolTip(tooltip)
            # else:
            #     # It depends on the "Group as layer" checked or not, so it has a signal
            #     self.layer_options_list['groupAsLayer']['widget'].stateChanged.connect(
            #         self.enable_or_not_toggle_checkbox)
            #     self.enable_or_not_toggle_checkbox()

            # Checkbox display children features
            self.dlg.relation_stacked_widget.setCurrentIndex(0)
            if is_vector:
                if len(self.project.relationManager().referencedRelations(layer)) >= 1:
                    # We display options
                    self.dlg.relation_stacked_widget.setCurrentIndex(1)

        else:
            # set default values for this layer/group
            for key, val in self.layer_options_list.items():
                if val.get('widget'):
                    if val['wType'] in ('text', 'textarea'):
                        if isinstance(val['default'], (list, tuple)):
                            text = ','.join(val['default'])
                        else:
                            text = val['default']
                        if val['wType'] == 'text':
                            val['widget'].setText(text)
                        else:
                            # Abstract is the only textarea for now
                            # We shouldn't have any default value, but let's support it
                            val['widget'].setPlainText(text)
                    elif val['wType'] == 'spinbox':
                        val['widget'].setValue(val['default'])
                    elif val['wType'] == 'checkbox':
                        val['widget'].setChecked(val['default'])
                    elif val['wType'] == 'list':

                        # New way with data, label, tooltip and icon
                        index = val['widget'].findData(val['default'])
                        val['widget'].setCurrentIndex(index)

        self.enable_popup_source_button()

    # def enable_or_not_toggle_checkbox(self):
    #     """ Only for groups, to determine the state of the "toggled" option. """
    #     if self.layer_options_list['groupAsLayer']['widget'].isChecked():
    #         self.layer_options_list['toggled']['widget'].setEnabled(True)
    #         tooltip = tr(
    #             "All layers in this group are considered as a unique layer. This new layer can be displayed "
    #             "or not.")
    #     else:
    #         self.layer_options_list['toggled']['widget'].setEnabled(False)
    #         self.layer_options_list['toggled']['widget'].setChecked(False)
    #         tooltip = tr("For a group, it depends of layers inside the group")
    #     self.layer_options_list['toggled']['widget'].setToolTip(tooltip)

    def external_wms_toggled(self):
        """ Disable the format combobox is the checkbox third party WMS is checked. """
        self.dlg.liImageFormat.setEnabled(not self.dlg.cbExternalWms.isChecked())

    def get_item_wms_capability(self, selectedItem) -> Optional[bool]:
        """
        Check if an item in the tree is a layer
        and if it is a WMS layer
        """
        wms_enabled = False
        is_layer = selectedItem['type'] == 'layer'
        if is_layer:
            layer = self.get_qgis_layer_by_id(selectedItem['id'])
            if not layer:
                return
            if layer.providerType() in ['wms']:
                if get_layer_wms_parameters(layer):
                    wms_enabled = True
        return wms_enabled

    @staticmethod
    def string_to_list(text):
        """ Format a string to a list. """
        data = text.split(',') if len(text) > 0 else []
        data = [item.strip() for item in data]
        return data

    def set_layer_property(self, key):
        """Set a layer property in global self.layerList
        when the corresponding ui widget has sent changed signal.
        """
        key = str(key)
        # get the selected item in the layer tree
        item = self.dlg.layer_tree.currentItem()
        # get the definition for this property
        layer_option = self.layer_options_list[key]
        # modify the property for the selected item
        if item and item.text(1) in self.layerList:
            if layer_option['wType'] == 'text':
                text = layer_option['widget'].text()
                if layer_option['type'] == 'list':
                    text = self.string_to_list(text)
                self.layerList[item.text(1)][key] = text
                self.set_layer_metadata(item, key)
            elif layer_option['wType'] == 'textarea':
                self.layerList[item.text(1)][key] = layer_option['widget'].toPlainText()
                self.set_layer_metadata(item, key)
            elif layer_option['wType'] == 'spinbox':
                self.layerList[item.text(1)][key] = layer_option['widget'].value()
            elif layer_option['wType'] == 'checkbox':
                checked = layer_option['widget'].isChecked()
                self.layerList[item.text(1)][key] = checked
                children = layer_option.get('children')
                if children:
                    exclusive = layer_option.get('exclusive', False)
                    if exclusive:
                        is_enabled = not checked
                    else:
                        is_enabled = checked
                    self.layer_options_list[children]['widget'].setEnabled(is_enabled)
                    if self.layer_options_list[children]['wType'] == 'checkbox' and not is_enabled:
                        if self.layer_options_list[children]['widget'].isChecked():
                            self.layer_options_list[children]['widget'].setChecked(False)
            elif layer_option['wType'] == 'list':
                # New way with data, label, tooltip and icon
                datas = [j[0] for j in layer_option['list']]
                self.layerList[item.text(1)][key] = datas[layer_option['widget'].currentIndex()]

            # Deactivate the "exclude" widget if necessary
            if ('exclude' in layer_option
                    and layer_option['wType'] == 'checkbox'
                    and layer_option['widget'].isChecked()
                    and layer_option['exclude']['widget'].isChecked()
            ):
                layer_option['exclude']['widget'].setChecked(False)
                self.layerList[item.text(1)][layer_option['exclude']['key']] = False

    def set_layer_metadata(self, item, key):
        """Set a the title/abstract/link Qgis metadata when corresponding item is changed
        Used in setLayerProperty"""
        if 'isMetadata' in self.layer_options_list[key]:
            # modify the layer.title|abstract|link() if possible
            if self.layerList[item.text(1)]['type'] == 'layer':
                layer = self.get_qgis_layer_by_id(item.text(1))
                if layer:
                    if hasattr(layer, key):
                        if key == 'title':
                            layer.setTitle(self.layerList[item.text(1)][key])
                        if key == 'abstract':
                            layer.setAbstract(self.layerList[item.text(1)][key])

    def convert_html_maptip(self):
        """ Trying to convert a Lizmap popup to HTML popup. """
        item = self.dlg.layer_tree.currentItem()
        if item and item.text(1) in self.layerList:
            if 'popupTemplate' in self.layerList[item.text(1)]:
                self.layerList[item.text(1)]['popup'] = True
                text = self.layerList[item.text(1)]['popupTemplate']

                layer = self._current_selected_layer()
                html, errors = convert_lizmap_popup(text, layer)
                if errors:
                    QMessageBox.warning(
                        self.dlg,
                        tr('Lizmap - Warning'),
                        tr(
                            'Some fields or alias could not be found in the layer. You must check the result manually '
                            'about these values below :'
                        ) + '<br><br>' + ','.join(errors),
                        QMessageBox.Ok)

                flag = self._set_maptip(layer, html)
                if flag:
                    index = self.layer_options_list['popupSource']['widget'].findData('qgis')
                    self.layer_options_list['popupSource']['widget'].setCurrentIndex(index)

    def configure_html_popup(self):
        """Open the dialog with a text field to store the popup template for one layer/group"""
        # get the selected item in the layer tree
        item = self.dlg.layer_tree.currentItem()
        if not item:
            return

        if not item.text(1) in self.layerList:
            return

        # do nothing if no popup configured for this layer/group
        if self.layerList[item.text(1)]['popup'] == 'False':
            return

        # Set the content of the QTextEdit if needed
        if 'popupTemplate' in self.layerList[item.text(1)]:
            self.layerList[item.text(1)]['popup'] = True
            text = self.layerList[item.text(1)]['popupTemplate']
        else:
            text = ''

        LOGGER.info('Opening the popup configuration')

        layer = self._current_selected_layer()
        data = self.layer_options_list['popupSource']['widget'].currentData()
        if data == 'lizmap':
            # Legacy
            # Lizmap HTML popup
            if isinstance(layer, QgsVectorLayer):
                LOGGER.warning("The 'lizmap' popup is deprecated for vector layer. This will be removed soon.")

            popup_dialog = LizmapPopupDialog(self.style_sheet, text)
            if not popup_dialog.exec_():
                return

            content = popup_dialog.txtPopup.text()

            # Get the selected item in the layer tree
            item = self.dlg.layer_tree.currentItem()
            if item and item.text(1) in self.layerList:
                # Write the content into the global object
                self.layerList[item.text(1)]['popupTemplate'] = content
                if isinstance(layer, QgsVectorLayer):
                    LOGGER.warning("The 'lizmap' popup is deprecated for vector layer. This will be removed soon.")

        else:
            # QGIS HTML maptip
            layer: QgsVectorLayer
            html_editor = HtmlEditorDialog(layer)
            html_editor.editor.set_html_content(layer.mapTipTemplate())
            if not html_editor.exec_():
                return

            self._set_maptip(layer, html_editor.editor.html_content(), False)

    def _current_selected_layer(self) -> QgsMapLayer:
        """ Current selected map layer in the tree. """
        item = self.dlg.layer_tree.currentItem()
        if item and item.text(1) in self.layerList:
            lid = item.text(1)
            layers = [a for a in self.project.mapLayers().values() if a.id() == lid]
            if not layers:
                LOGGER.warning('Layers not found.')
                return
        else:
            LOGGER.warning('No item.')
            return
        layer = layers[0]
        return layer

    def link_from_properties(self):
        """ Button set link from layer in the Lizmap configuration. """
        layer = self._current_selected_layer()
        value = layer_property(layer, LayerProperties.DataUrl)
        self.layer_options_list['link']['widget'].setText(value)

    def _set_maptip(self, layer: QgsVectorLayer, html_content: str, check: bool = True) -> bool:
        """ Internal function to set the maptip on a layer. """
        if check and layer.mapTipTemplate() != '':
            box = QMessageBox(self.dlg)
            box.setIcon(QMessageBox.Question)
            box.setWindowIcon(QIcon(resources_path('icons', 'icon.png')),)
            box.setWindowTitle(tr('Existing maptip for layer {}').format(layer.title()))
            box.setText(tr(
                'A maptip already exists for this layer. This is going to override it. '
                'Are you sure you want to continue ?'))
            box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            box.setDefaultButton(QMessageBox.No)
            result = box.exec_()
            if result == QMessageBox.No:
                return False

        layer.setMapTipTemplate(html_content)
        QMessageBox.information(
            self.dlg,
            tr('Maptip'),
            tr('The maptip has been set in the layer "{}".').format(layer.name()),
            QMessageBox.Ok
        )
        return True

    def html_table_from_layer(self):
        """ Button set popup maptip from layer in the Lizmap configuration. """
        layer = self._current_selected_layer()
        if not isinstance(layer, QgsVectorLayer):
            return

        table_template = """<table class="table table-condensed table-striped table-bordered lizmapPopupTable">
  <thead>
    <tr>
      <th>{field}</th>
      <th>{value}</th>
    </tr>
  </thead>
  <tbody>
{fields_template}
  </tbody>
</table>"""
        field_template = """    <tr>
      <th>{name}</th>
      <td>[% "{value}" %]</td>
    </tr>
"""
        fields = ""
        for field in layer.fields():
            fields += field_template.format(name=field.displayName(), value=field.name())
        result = table_template.format(field=tr("Field"), value=tr("Value"), fields_template=fields)
        self._set_maptip(layer, result)

    def maptip_from_form(self):
        """ Button set popup maptip from DND form in the Lizmap configuration. """
        layer = self._current_selected_layer()
        if not isinstance(layer, QgsVectorLayer):
            return

        config = layer.editFormConfig()
        if config.layout() != QgsEditFormConfig.TabLayout:
            LOGGER.warning('Maptip : the layer is not using a drag and drop form.')
            QMessageBox.warning(
                self.dlg,
                tr('Lizmap - Warning'),
                tr('The form for this layer is not a drag and drop layout.'),
                QMessageBox.Ok)
            return

        root = config.invisibleRootContainer()
        relation_manager = self.project.relationManager()
        html_content = Tooltip.create_popup_node_item_from_form(layer, root, 0, [], '', relation_manager)
        html_content = Tooltip.create_popup(html_content)
        html_content += Tooltip.css()
        self._set_maptip(layer, html_content)

    def write_project_config_file(self):
        """Get general project options and user edited layers options from plugin gui.
        Save them into the project.qgs.cfg config file in the project.qgs folder (json format)."""

        valid, _ = self.check_project_validity()

        lwc_version = self.dlg.combo_lwc_version.currentData(LwcVersionComboData.LwcVersion.value)
        LOGGER.info("Writing CFG file for LWC version {}".format(lwc_version.value))
        current_version = self.global_options['metadata']['lizmap_plugin_version']['default']
        if self.is_dev_version:
            next_version = next_git_tag()
            if next_version != 'next':
                current_version = next_version

        warnings = []

        # Layer ID as short name
        if lwc_version >= LwcVersions.Lizmap_3_6:
            use_layer_id, _ = self.project.readEntry('WMSUseLayerIDs', '/')
            if to_bool(use_layer_id):
                QMessageBox.warning(
                    self.dlg,
                    tr('Use layer IDs as name'),
                    '{}\n\n{}'.format(
                        tr(
                            "Since Lizmap Web Client 3.6, it's not possible anymore to use the option 'Use layer IDs "
                            "as name' in the project properties dialog, QGIS server tab, then WMS capabilities."
                        ),
                        tr("Please uncheck this checkbox and re-save the Lizmap configuration file.")
                    ),
                    QMessageBox.Ok
                )
                warnings.append(Warnings.UseLayerIdAsName.value)

        target_status = self.dlg.combo_lwc_version.currentData(LwcVersionComboData.LwcBranchStatus.value)
        if not target_status:
            target_status = ReleaseStatus.Unknown

        server_metadata = self.dlg.server_combo.currentData(ServerComboData.JsonMetadata.value)

        if is_lizmap_dot_com_hosting(server_metadata):
            error, results = valid_saas_lizmap_dot_com(self.project)
            if error:
                warnings.append(Warnings.SaasLizmapDotCom.value)

                message = tr('Some configuration are not valid when used with a Lizmap.com hosting :')
                message += "<br><ul>"
                for error in results.values():
                    message += "<li>{}</li>".format(error)
                message += "</ul><br>"
                message += tr("The process is continuing but expect some layers to not be visible.")
                QMessageBox.warning(self.dlg, tr('Lizmap.com hosting'), message, QMessageBox.Ok)

        metadata = {
            'qgis_desktop_version': Qgis.QGIS_VERSION_INT,
            'lizmap_plugin_version_str': current_version,
            'lizmap_plugin_version': int(format_version_integer(current_version)),
            'lizmap_web_client_target_version': int(format_version_integer('{}.0'.format(lwc_version.value))),
            'lizmap_web_client_target_status': target_status.value,
            'instance_target_url': self.dlg.server_combo.currentData(ServerComboData.ServerUrl.value)
        }
        repository = self.current_repository()
        if repository:
            metadata['instance_target_repository'] = repository

        if valid is not None:
            metadata['project_valid'] = valid
            if not valid:
                warnings.append(Warnings.OgcNotValid.value)

        liz2json = dict()
        liz2json['metadata'] = metadata
        liz2json['warnings'] = warnings
        liz2json["options"] = dict()
        liz2json["layers"] = dict()

        # projection
        projection = self.iface.mapCanvas().mapSettings().destinationCrs()
        liz2json['options']['projection'] = dict()
        liz2json['options']['projection']['proj4'] = projection.toProj()
        liz2json['options']['projection']['ref'] = projection.authid()

        # wms extent
        liz2json['options']['bbox'] = self.project.readListEntry('WMSExtent', '')[0]

        # set initialExtent values if not defined
        if not self.dlg.inInitialExtent.text():
            self.set_initial_extent_from_project()

        # gui user defined options
        for key, item in self.global_options.items():
            if item.get('widget'):
                inputValue = None
                # Get field value depending on widget type
                if item['wType'] in ['text', 'html']:
                    inputValue = item['widget'].text().strip(' \t')

                if item['wType'] == 'textarea':
                    inputValue = item['widget'].toPlainText().strip(' \t')

                if item['wType'] == 'spinbox':
                    inputValue = item['widget'].value()

                if item['wType'] == 'checkbox':
                    inputValue = str(item['widget'].isChecked())

                if item['wType'] == 'list':
                    inputValue = item['widget'].currentData()

                if item['wType'] == 'layers':
                    lay = item['widget'].layer(item['widget'].currentIndex())
                    inputValue = lay.id()

                if item['wType'] == 'fields':
                    inputValue = item['widget'].currentField()

                # Cast value depending of data type
                if item['type'] == 'string':
                    if item['wType'] in ('text', 'textarea'):
                        inputValue = str(inputValue)
                    else:
                        inputValue = str(inputValue)

                elif item['type'] in ('intlist', 'floatlist', 'list'):
                    if item['type'] == 'intlist':
                        inputValue = [int(a) for a in inputValue.split(', ') if a.isdigit()]
                    elif item['type'] == 'floatlist':
                        inputValue = [float(a) for a in inputValue.split(', ')]
                    else:
                        inputValue = [a.strip() for a in inputValue.split(',') if a.strip()]

                elif item['type'] == 'integer':
                    try:
                        inputValue = int(inputValue)
                    except Exception:
                        inputValue = int(item['default'])

                elif item['type'] == 'boolean':
                    inputValue = item['widget'].isChecked()
                    if not item.get('use_proper_boolean'):
                        inputValue = str(inputValue)

                # Add value to the option
                if (inputValue and inputValue != "False") or item.get('always_export'):
                    liz2json["options"][key] = inputValue

        for key in self.layers_table.keys():
            manager = self.layers_table[key].get('manager')
            if manager:
                data = manager.to_json()

                if key == 'layouts':
                    # The print combobox is removed
                    # Let's remove from the CFG file
                    if lwc_version >= LwcVersions.Lizmap_3_7:
                        try:
                            del liz2json['options']['print']
                        except KeyError:
                            pass
                    else:
                        # We do not want to save this table if it's less than LWC 3.7
                        LOGGER.info("Skipping the 'layout' table because version if less than LWC 3.7")
                        continue

                if manager.use_single_row() and manager.table.rowCount() == 1:
                    liz2json['options'].update(data)
                else:
                    liz2json[key] = data

        # list of Lizmap external baselayers
        eblTableWidget = self.dlg.twLizmapBaselayers
        twRowCount = eblTableWidget.rowCount()
        if twRowCount > 0:
            liz2json["lizmapExternalBaselayers"] = dict()
            for row in range(twRowCount):
                # check that the layer is checked in the WFS capabilities
                lRepository = eblTableWidget.item(row, 0).text()
                lProject = eblTableWidget.item(row, 1).text()
                lName = eblTableWidget.item(row, 2).text()
                lTitle = eblTableWidget.item(row, 3).text()
                lImageFormat = eblTableWidget.item(row, 4).text()
                if lImageFormat not in ('png', 'png; mode=16bit', 'png; mode=8bit', 'jpg', 'jpeg'):
                    lImageFormat = 'png'
                liz2json["lizmapExternalBaselayers"][lName] = dict()
                liz2json["lizmapExternalBaselayers"][lName]["repository"] = lRepository
                liz2json["lizmapExternalBaselayers"][lName]["project"] = lProject
                liz2json["lizmapExternalBaselayers"][lName]["layerName"] = lName
                liz2json["lizmapExternalBaselayers"][lName]["layerTitle"] = lTitle
                liz2json["lizmapExternalBaselayers"][lName]["layerImageFormat"] = lImageFormat
                liz2json["lizmapExternalBaselayers"][lName]["order"] = row

        # gui user defined layers options
        for k, v in self.layerList.items():
            ltype = v['type']
            gal = v['groupAsLayer']
            layer = False
            if gal:
                ltype = 'layer'
            else:
                ltype = 'group'

            if self.get_qgis_layer_by_id(k):
                ltype = 'layer'
                gal = True

            # ~ # add layerOption only for geo layers
            # ~ if geometryType != 4:
            layerOptions = dict()
            layerOptions["id"] = str(k)
            layerOptions["name"] = str(v['name'])
            layerOptions["type"] = ltype

            geometryType = -1
            if ltype == 'layer':
                layer = self.get_qgis_layer_by_id(k)
                if layer:
                    if layer.type() == QgsMapLayer.VectorLayer:  # if it is a vector layer
                        geometryType = layer.geometryType()

            # geometry type
            if geometryType != -1:
                layerOptions["geometryType"] = self.mapQgisGeometryType[layer.geometryType()]

            # extent
            if layer:
                extent = layer.extent()
                layerOptions['extent'] = [
                    extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum()]
                layerOptions['crs'] = layer.crs().authid()

            # styles
            if layer and hasattr(layer, 'styleManager'):
                lsm = layer.styleManager()
                ls = lsm.styles()
                if len(ls) > 1:
                    layerOptions['styles'] = ls

            # Loop through the layer options and set properties from the dictionary
            for key, val in self.layer_options_list.items():
                propVal = v[key]
                if val['type'] == 'string':
                    if val['wType'] in ('text', 'textarea'):
                        propVal = str(propVal)
                    elif val['wType'] == 'list' and isinstance(propVal, tuple):
                        # Process later, do not cast for now
                        pass
                    else:
                        propVal = str(propVal)
                elif val['type'] == 'integer':
                    try:
                        propVal = int(propVal)
                    except Exception:
                        propVal = 1
                elif val['type'] == 'boolean':
                    if not val.get('use_proper_boolean'):
                        propVal = str(propVal)

                if key in ('legend_image_option', 'noLegendImage'):
                    if layerOptions.get('legend_image_option') and key == 'noLegendImage':
                        # Let's skip, the key is already saved
                        continue

                    if layerOptions.get('noLegendImage') and key == 'legend_image_option':
                        # Let's skip, the key is already saved
                        continue

                    target_version = self.dlg.combo_lwc_version.currentData()
                    max_version = val.get('max_version')
                    if max_version and target_version > max_version:
                        LOGGER.info("Skipping key '{}' because of max_version.".format(key))
                        continue

                    min_version = val.get('min_version')
                    if min_version and target_version < min_version:
                        LOGGER.info("Skipping key '{}' because of min_version.".format(key))
                        continue

                    if key == 'noLegendImage':
                        # We take the value of legend_image_option
                        propVal = 'False'
                        if v['legend_image_option'] == 'disabled':
                            propVal = 'True'
                        if v['legend_image_option'] == 'expand_at_startup':
                            # We keep False
                            QMessageBox.warning(
                                self.dlg,
                                tr('Legend image'),
                                tr(
                                    'Be careful, the option "Expand at startup" for the layer "{layer_name}" is not '
                                    'available for your Lizmap Web Client target version. Falling back to '
                                    '"Hide at startup" in the configuration file.'.format(layer_name=k)
                                ),
                            )

                    if isinstance(propVal, tuple):
                        propVal = propVal[0]

                    # LOGGER.info("Saving {} = {} for layer {}".format(key, propVal, k))

                layerOptions[key] = propVal

            # Cache Metatile: unset metatileSize if empty
            # this is to avoid, but lizmap web client must change accordingly to avoid using empty metatileSize
            # (2.2.0 does not handle it)
            # unset metatileSize
            if not re.match(r'\d,\d', layerOptions['metatileSize']):
                del layerOptions['metatileSize']
            # unset cacheExpiration if False
            if layerOptions['cached'].lower() == 'false':
                del layerOptions['cacheExpiration']
            # unset clientCacheExpiration if not needed
            if layerOptions['clientCacheExpiration'] < 0:
                del layerOptions['clientCacheExpiration']
            # unset externalWms if False
            if layerOptions['externalWmsToggle'].lower() == 'false':
                del layerOptions['externalWmsToggle']
            # unset source project and repository if needed
            if not layerOptions['sourceRepository'] or not layerOptions['sourceProject']:
                del layerOptions['sourceRepository']
                del layerOptions['sourceProject']
            # set popupSource to auto if set to lizmap and no lizmap conf found
            if layerOptions['popup'].lower() == 'true' and layerOptions['popupSource'] == 'lizmap' and layerOptions[
                'popupTemplate'] == '':
                layerOptions['popupSource'] = 'auto'

            if layerOptions.get("geometryType") in ('point', 'line', 'polygon'):
                if layerOptions.get('popupSource') == 'lizmap' and layerOptions.get('popup', '').lower() == 'true':
                    QMessageBox.warning(
                        self.dlg,
                        tr('Deprecated feature'),
                        tr(
                            'The layer "{}" is vector layer and the popup is a "Lizmap HTML". This kind of popup is '
                            'deprecated for vector layer, you should switch to another kind of popup, for instance to '
                            'a "QGIS HTML maptip". This will be removed in a future version of Lizmap.'
                        ).format(layerOptions["name"]),
                        QMessageBox.Ok
                    )

            # Add external WMS options if needed
            if layer and hasattr(layer, 'providerType') \
                    and 'externalWmsToggle' in layerOptions \
                    and layerOptions['externalWmsToggle'].lower() == 'true':
                layerProviderKey = layer.providerType()
                # Only for layers stored in disk
                if layerProviderKey in ['wms']:
                    wmsParams = get_layer_wms_parameters(layer)
                    if wmsParams:
                        layerOptions['externalAccess'] = wmsParams
                    else:
                        layerOptions['externalWmsToggle'] = "False"
                else:
                    layerOptions['externalWmsToggle'] = "False"

            # Add layer options to the json object
            liz2json["layers"]["{}".format(v['name'])] = layerOptions

        # Write json to the cfg file
        json_file_content = json.dumps(
            liz2json,
            sort_keys=False,
            indent=4
        )
        json_file_content += '\n'

        # Get the project data
        json_file = '{}.cfg'.format(self.project.fileName())
        with open(json_file, 'w') as cfg_file:
            cfg_file.write(json_file_content)

        LOGGER.info('The CFG file has been written to "{}"'.format(json_file))
        self.clean_project()

    def clean_project(self):
        """Clean a little the QGIS project.

        Mainly ghost layers for now.
        """
        layers = remove_all_ghost_layers()
        if layers:
            message = tr(
                'Lizmap has found these layers which are ghost layers: {}. '
                'They have been removed. You must save your project.').format(', '.join(layers))
            self.iface.messageBar().pushMessage(
                'Lizmap', message, level=Qgis.Warning, duration=30
            )

    def check_project_validity(self):
        """Project checker about issues that the user might hae when running in LWC."""
        if Qgis.QGIS_VERSION_INT < 31400:
            return None, None

        validator = QgsProjectServerValidator()
        valid, results = validator.validate(QgsProject.instance())

        if not valid:
            message = tr(
                'The QGIS project is not valid according to OGC standards. You should check '
                'messages in the Project properties -> QGIS Server tab then Test configuration. '
                '{} error(s) have been found').format(len(results))
            self.iface.messageBar().pushMessage(
                'Lizmap', message, level=Qgis.Warning, duration=15
            )

        self.check_api_key_address()

        return valid, results

    def check_global_project_options(self) -> Tuple[bool, str]:
        """Checks that the needed options are correctly set : relative path, project saved, etc.

        :return: Flag if the project is valid and an error message.
        :rtype: bool, basestring
        """
        base_message = "<br>" + tr("This is needed before using other tabs in the plugin.")
        message = tr('You need to open a QGIS project, using the QGS extension.')
        if not self.project.fileName():
            return False, message + base_message

        if not self.project.fileName().lower().endswith('qgs'):
            message += "\n\n" + tr(
                "Your extension is QGZ. Please save again the project using the other extension.")
            return False, message + base_message

        if QRegExp(r'\s').indexIn(self.project.baseName()) >= 0:
            message = tr(
                "Your file name has a space in its name. The project file name mustn't have a space in its name.")
            return False, message + base_message

        if self.project.baseName() != unaccent(self.project.baseName()):
            message = tr(
                "Your file name has some accents in its name. The project file name mustn't have accents in its name.")
            return False, message + base_message

        # Check if Qgis/capitaliseLayerName is set
        settings = QgsSettings()
        if settings.value('Qgis/capitaliseLayerName') and settings.value('Qgis/capitaliseLayerName', type=bool):
            message = tr(
                'Please deactivate the option "Capitalize layer names" in the tab "Canvas and legend" '
                'in the QGIS option dialog, as it could cause issues with Lizmap.')
            return False, message + base_message

        # Check relative/absolute path
        if self.project.readEntry('Paths', 'Absolute')[0] == 'true':
            message = tr(
                'The project layer paths must be set to relative. '
                'Please change this options in the project settings.')
            return False, message + base_message

        # check if a title has been given in the project QGIS Server tab configuration
        # first set the WMSServiceCapabilities to true
        if not self.project.readEntry('WMSServiceCapabilities', '/')[1]:
            self.project.writeEntry('WMSServiceCapabilities', '/', 'True')
        if self.project.readEntry('WMSServiceTitle', '')[0] == '':
            self.project.writeEntry('WMSServiceTitle', '', self.project.baseName())

        # check if a bbox has been given in the project QGIS Server tab configuration
        project_wms_extent, _ = self.project.readListEntry('WMSExtent', '')
        full_extent = self.iface.mapCanvas().extent()
        if not project_wms_extent:
            project_wms_extent.append(str(full_extent.xMinimum()))
            project_wms_extent.append(str(full_extent.yMinimum()))
            project_wms_extent.append(str(full_extent.xMaximum()))
            project_wms_extent.append(str(full_extent.yMaximum()))
            self.project.writeEntry('WMSExtent', '', project_wms_extent)
        else:
            if not project_wms_extent[0] or not project_wms_extent[1] or not \
                    project_wms_extent[2] or not project_wms_extent[3]:
                project_wms_extent[0] = str(full_extent.xMinimum())
                project_wms_extent[1] = str(full_extent.yMinimum())
                project_wms_extent[2] = str(full_extent.xMaximum())
                project_wms_extent[3] = str(full_extent.yMaximum())
                self.project.writeEntry('WMSExtent', '', project_wms_extent)

        # Add default variables in the project
        variables = self.project.customVariables()
        if not variables.get('lizmap_user'):
            variables['lizmap_user'] = ''

        if not variables.get('lizmap_user_groups'):
            variables['lizmap_user_groups'] = list()

        self.project.setCustomVariables(variables)

        return True, ''

    def ok_button_clicked(self):
        """When the OK button is press, we 'apply' and close the dialog."""
        if not self.save_cfg_file():
            return

        # Only close the dialog if no error
        self.dlg.close()

    def save_cfg_file(self) -> bool:
        """Save the CFG file.

        Check the user defined data from GUI and save them to both global and project config files.
        """
        if not self.check_dialog_validity():
            LOGGER.debug("Leaving the dialog without valid project and/or server.")
            return False

        self.isok = 1

        stop_process = tr("The process is stopping.")

        if self.dlg.table_server.rowCount() < 1 and not self.is_dev_version:
            # But by making this condition, we force people to at least have one server in the list,
            # so they can be more aware about versioning later
            QMessageBox.critical(
                self.dlg,
                tr('Lizmap Server URL'),
                '{}\n\n{}\n\n{}\n\n{}'.format(
                    tr("You haven't provided any Lizmap URL in the first Information panel."),
                    tr(
                        "Publishing a project on Lizmap requires to have a server running with the Lizmap "
                        "application."),
                    tr(
                        "By providing a URL, you will be able to check its version number for instance."
                    ),
                    stop_process
                ), QMessageBox.Ok)
            return False

        if not self.server_manager.check_admin_login_provided() and not self.is_dev_version:
            QMessageBox.critical(
                self.dlg,
                tr('Missing login on a server'),
                '{}\n\n{}\n\n{}'.format(
                    tr(
                        "You have set up a server in the first panel of the plugin, but you have not provided a "
                        "login/password."
                    ),
                    tr("Please go back to the server panel and edit the server to add a login."),
                    stop_process
                ), QMessageBox.Ok)
            return False

        if not self.is_dev_version:
            lwc_version = self.dlg.combo_lwc_version.currentData(LwcVersionComboData.LwcVersion.value)
            if not self.server_manager.check_lwc_version(lwc_version.value):
                QMessageBox.critical(
                    self.dlg,
                    tr('Lizmap Target Version'),
                    '{}\n\n{}\n\n{}'.format(
                        tr(
                            "Your Lizmap Web Client target version {version} has not been found in the server "
                            "table.".format(version=lwc_version.value)),
                        tr(
                            "Either check your Lizmap Web Client target version in the first panel of the plugin or "
                            "check you have provided the correct server URL."
                        ),
                        stop_process
                    ), QMessageBox.Ok)
                return False

        # global project option checking
        is_valid, message = self.check_global_project_options()
        if not is_valid:
            QMessageBox.critical(
                self.dlg, tr('Lizmap Error'), '{}\n\n{}'.format(message, stop_process), QMessageBox.Ok)
            return False

        # Get configuration from input fields

        # Need to get these values to check for Pseudo Mercator projection
        mercator_layers = [
            self.dlg.cbOsmMapnik.isChecked(),
            self.dlg.cbOsmStamenToner.isChecked(),
            self.dlg.cb_open_topo_map.isChecked(),
            self.dlg.cbGoogleStreets.isChecked(),
            self.dlg.cbGoogleSatellite.isChecked(),
            self.dlg.cbGoogleHybrid.isChecked(),
            self.dlg.cbGoogleTerrain.isChecked(),
            self.dlg.cbBingStreets.isChecked(),
            self.dlg.cbBingSatellite.isChecked(),
            self.dlg.cbBingHybrid.isChecked(),
            self.dlg.cbIgnStreets.isChecked(),
            self.dlg.cbIgnSatellite.isChecked(),
            self.dlg.cbIgnTerrain.isChecked(),
            self.dlg.cbIgnCadastral.isChecked(),
        ]

        self.dlg.outLog.append('=' * 20)
        self.dlg.outLog.append('<b>' + tr('Map - options') + '</b>')
        self.dlg.outLog.append('=' * 20)

        # Checking configuration data
        # Get the project data from api to check the "coordinate system restriction" of the WMS Server settings

        # public base-layers: check that the 3857 projection is set in the
        # "Coordinate System Restriction" section of the project WMS Server tab properties
        if True in mercator_layers:
            crs_list = self.project.readListEntry('WMSCrsList', '')
            mercator_found = False
            for i in crs_list[0]:
                if i == 'EPSG:3857':
                    mercator_found = True
            if not mercator_found:
                crs_list[0].append('EPSG:3857')
                self.project.writeEntry('WMSCrsList', '', crs_list[0])

        # write data in the lizmap json config file
        self.write_project_config_file()

        self.log(
            tr('All the map parameters are correctly set'),
            abort=False,
            textarea=self.dlg.outLog)
        self.log(
            '<b>' + tr('Lizmap configuration file has been updated') + '</b>',
            abort=False,
            textarea=self.dlg.outLog)

        self.get_min_max_scales()
        msg = tr('Lizmap configuration file has been updated')

        # Ask to save the project
        auto_save = self.dlg.checkbox_save_project.isChecked()
        QgsSettings().setValue('lizmap/auto_save_project', auto_save)
        if self.project.isDirty():
            if auto_save:
                # Do not use QgsProject.write() as it will trigger file
                # modified warning in QGIS Desktop later
                self.iface.actionSaveProject().trigger()
            else:
                self.iface.messageBar().pushMessage(
                    'Lizmap',
                    tr('Please do not forget to save the QGIS project before publishing your map'),
                    level=Qgis.Warning,
                    duration=30
                )

        if auto_save and self.dlg.checkbox_ftp_transfer.isChecked():
            valid, message = self.server_ftp.connect(send_files=True)
            if not valid:
                self.iface.messageBar().pushMessage(
                    'Lizmap',
                    message,
                    level=Qgis.Critical,
                )
                return False

            msg = tr(
                'Lizmap configuration file has been updated and sent to the FTP {}.'.format(
                    self.server_ftp.host)
            )

        self.iface.messageBar().pushMessage(
            'Lizmap',
            msg,
            level=Qgis.Success,
            duration=3
        )
        return True

    def check_visibility_crs_3857(self):
        """ Check if we display the warning about scales. """
        visible = False
        for item in self.crs_3857_base_layers_list.values():
            if item.isChecked():
                visible = True

        self.dlg.scales_warning_layout.setVisible(visible)

    def onBaselayerCheckboxChange(self):
        """
        Add or remove a base-layer in cbStartupBaselayer combobox
        when user change state of any base-layer related checkbox
        """
        if not self.layerList:
            return

        # Combo to fill up with base-layer
        combo = self.dlg.cbStartupBaselayer

        # First get selected item
        idx = combo.currentIndex()
        data = combo.itemData(idx)

        # Clear the combo
        combo.clear()
        i = 0
        blist = []

        # Fill with checked base-layers
        # 1/ QGIS layers
        for k, v in self.layerList.items():
            if not v['baseLayer']:
                continue
            combo.addItem(v['name'], v['name'])
            blist.append(v['name'])
            if data == k:
                idx = i
            i += 1

        # 2/ External base-layers
        for k, v in self.base_layer_widget_list.items():
            if k != 'layer':
                if v.isChecked():
                    combo.addItem(k, k)
                    blist.append(k)
                    if data == k:
                        idx = i
                    i += 1

        # Set last chosen item
        combo.setCurrentIndex(idx)

        # Fill self.globalOptions
        self.global_options['startupBaselayer']['list'] = blist

    def setStartupBaselayerFromConfig(self):
        """
        Read lizmap current cfg configuration
        and set the startup base-layer if found
        """
        # Get the project config file (projectname.qgs.cfg)
        json_file = '{}.cfg'.format(self.project.fileName())
        if os.path.exists(json_file):
            f = open(json_file)
            json_file_reader = f.read()
            # noinspection PyBroadException
            try:
                sjson = json.loads(json_file_reader)
                jsonOptions = sjson['options']
                if 'startupBaselayer' in jsonOptions:
                    sb = jsonOptions['startupBaselayer']
                    cb = self.dlg.cbStartupBaselayer
                    i = cb.findData(sb)
                    if i >= 0:
                        cb.setCurrentIndex(i)
            except Exception:
                pass
            finally:
                f.close()

    def reinitDefaultProperties(self):
        for key in self.layers_table.keys():
            self.layers_table[key]['jsonConfig'] = dict()

    def onProjectRead(self):
        """
        Close Lizmap plugin when project is opened
        """
        self.reinitDefaultProperties()
        self.dlg.close()

    def run(self) -> bool:
        """Plugin run method : launch the GUI."""
        if self.dlg.isVisible():
            # show dialog in front of QGIS
            self.dlg.raise_()
            self.dlg.activateWindow()
            return False

        self.populate_lwc_combo()

        all_tabs = self.check_dialog_validity()

        # QGIS Plugin manager
        qgis_plugin_manager = None
        if QGIS_PLUGIN_MANAGER:
            # noinspection PyBroadException
            try:
                plugin_manager = PluginManager()
                self.dlg.label_lizmap_plugin.setText(plugin_manager.lizmap_version())
                self.dlg.label_wfsoutputextension_plugin.setText(plugin_manager.wfs_output_extension_version())
                self.dlg.label_atlasprint_plugin.setText(plugin_manager.atlas_print_version())
                qgis_plugin_manager = True
            except Exception as e:
                # Core QGIS plugin manager API might not be well stable ?
                LOGGER.warning("Exception when reading the QGIS plugin manager : {}".format(str(e)))
        if not qgis_plugin_manager:
            self.dlg.label_lizmap_plugin.setText("Lizmap - Unknown")
            self.dlg.label_wfsoutputextension_plugin.setText("WfsOutputExtension - Unknown")
            self.dlg.label_atlasprint_plugin.setText("AtlasPrint - Unknown")

        version_checker = VersionChecker(self.dlg, VERSION_URL)
        version_checker.fetch()
        self.set_previous_qgis_version(None)

        if not all_tabs:
            # Go back to the first panel because no project loaded.
            # Otherwise, the plugin opens the latest valid panel before the previous project has been closed.
            self.dlg.mOptionsListWidget.setCurrentRow(0)

        self.dlg.show()

        # Get config file data
        self.get_config()

        self.layerList = dict()

        # Get embedded groups
        self.embeddedGroups = None

        # Fill the layer tree
        self.populate_layer_tree()

        # Fill base-layer startup
        self.onBaselayerCheckboxChange()
        self.setStartupBaselayerFromConfig()

        auto_save = QgsSettings().value('lizmap/auto_save_project', False, bool)
        self.dlg.checkbox_save_project.setChecked(auto_save)

        self.dlg.exec_()
        return True
