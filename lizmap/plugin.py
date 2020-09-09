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
from shutil import copyfile
from typing import Optional

from qgis.PyQt.QtCore import (
    QCoreApplication,
    QTranslator,
    QUrl,
    Qt,
)
from qgis.PyQt.QtGui import (
    QDesktopServices,
    QIcon
)
from qgis.PyQt.QtWidgets import (
    QTableWidgetItem,
    QTreeWidgetItem,
    QAction,
    QDialogButtonBox,
    QMessageBox,
)
from qgis.core import (
    Qgis,
    QgsEditFormConfig,
    QgsProject,
    QgsMapLayerModel,
    QgsLayerTreeGroup,
    QgsLayerTreeLayer,
    QgsApplication,
    QgsMapLayer,
    QgsSettings,
    QgsVectorLayer,
    QgsWkbTypes,
)

from lizmap import DEFAULT_LWC_VERSION
from lizmap.definitions.atlas import AtlasDefinitions
from lizmap.definitions.attribute_table import AttributeTableDefinitions
from lizmap.definitions.dataviz import DatavizDefinitions, Theme
from lizmap.definitions.definitions import LwcVersions, LayerProperties
from lizmap.definitions.edition import EditionDefinitions
from lizmap.definitions.filter_by_form import FilterByFormDefinitions
from lizmap.definitions.filter_by_login import FilterByLoginDefinitions
from lizmap.definitions.locate_by_layer import LocateByLayerDefinitions
from lizmap.definitions.time_manager import TimeManagerDefinitions
from lizmap.definitions.tooltip import ToolTipDefinitions
from lizmap.forms.atlas_edition import AtlasEditionDialog
from lizmap.forms.attribute_table_edition import AttributeTableEditionDialog
from lizmap.forms.dataviz_edition import DatavizEditionDialog
from lizmap.forms.edition_edition import EditionLayerDialog
from lizmap.forms.filter_by_form_edition import FilterByFormEditionDialog
from lizmap.forms.filter_by_login import FilterByLoginEditionDialog
from lizmap.forms.locate_layer_edition import LocateLayerEditionDialog
from lizmap.forms.table_manager import TableManager
from lizmap.forms.time_manager_edition import TimeManagerEditionDialog
from lizmap.forms.tooltip_edition import ToolTipEditionDialog
from lizmap.qt_style_sheets import STYLESHEET, NEW_FEATURE
from lizmap.lizmap_api.config import LizmapConfig
from lizmap.lizmap_dialog import LizmapDialog
from lizmap.lizmap_popup_dialog import LizmapPopupDialog
from lizmap.qgis_plugin_tools.tools.custom_logging import setup_logger
from lizmap.qgis_plugin_tools.tools.i18n import setup_translation, tr
from lizmap.qgis_plugin_tools.tools.resources import resources_path, plugin_path, plugin_name
from lizmap.qgis_plugin_tools.tools.ghost_layers import remove_all_ghost_layers
from lizmap.qgis_plugin_tools.tools.version import version, format_version_integer
from lizmap.tooltip import Tooltip
from lizmap.tools import get_layer_wms_parameters, layer_property


LOGGER = logging.getLogger(plugin_name())
DOC_URL = 'https://docs.lizmap.com/next/'


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

        self.dlg = LizmapDialog()
        self.version = version()
        self.is_dev_version = self.version not in ['master', 'dev'] or 'beta' in self.version
        if self.is_dev_version:
            self.dlg.setWindowTitle('Lizmap branch {}'.format(self.version))
            text = self.dlg.label_dev_version.text().format(self.version)
            self.dlg.label_dev_version.setText(text)
        else:
            self.dlg.label_dev_version.setVisible(False)
        self.popup_dialog = None
        self.layers_table = dict()

        # Manage LWC versions combo
        self.dlg.label_lwc_version.setStyleSheet(NEW_FEATURE)
        self.lwc_versions = OrderedDict()
        self.lwc_versions[LwcVersions.Lizmap_3_1] = []
        self.lwc_versions[LwcVersions.Lizmap_3_2] = [
            self.dlg.label_max_feature_popup,
            self.dlg.label_display_popup_children,
            self.dlg.label_dataviz,
            self.dlg.label_atlas,
        ]
        self.lwc_versions[LwcVersions.Lizmap_3_3] = [
            self.dlg.label_form_filter,
            self.dlg.label_drag_drop_form,
            self.dlg.btQgisPopupFromForm,
        ]
        self.lwc_versions[LwcVersions.Lizmap_3_4] = [
            self.dlg.label_atlas_34,
            self.dlg.label_group_visibility,
            self.dlg.list_group_visiblity,
            self.dlg.activate_first_maptheme,
            self.dlg.activate_drawing_tools,
        ]
        next_release = False
        for lwc_version in LwcVersions:
            if not next_release:
                self.dlg.combo_lwc_version.addItem(lwc_version.value, lwc_version)
                if lwc_version == DEFAULT_LWC_VERSION:
                    next_release = not self.is_dev_version

        lwc_version = QgsSettings().value('lizmap/lizmap_web_client_version', DEFAULT_LWC_VERSION.value, str)
        lwc_version = LwcVersions(lwc_version)
        index = self.dlg.combo_lwc_version.findData(lwc_version)
        self.dlg.combo_lwc_version.setCurrentIndex(index)
        self.dlg.combo_lwc_version.currentIndexChanged.connect(self.lwc_version_changed)
        self.lwc_version_changed()

        # Map options
        icon = QIcon()
        icon.addFile(resources_path('icons', '15-baselayer-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', '15-baselayer-dark.png'), mode=QIcon.Selected)
        self.dlg.mOptionsListWidget.item(0).setIcon(icon)

        # Layers
        icon = QIcon()
        icon.addFile(resources_path('icons', '02-switcher-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', '02-switcher-dark.png'), mode=QIcon.Selected)
        self.dlg.mOptionsListWidget.item(1).setIcon(icon)

        # Base layer
        icon = QIcon()
        icon.addFile(resources_path('icons', '02-switcher-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', '02-switcher-dark.png'), mode=QIcon.Selected)
        self.dlg.mOptionsListWidget.item(2).setIcon(icon)

        # Locate by layer
        icon = QIcon()
        icon.addFile(resources_path('icons', '04-locate-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', '04-locate-dark.png'), mode=QIcon.Selected)
        self.dlg.mOptionsListWidget.item(3).setIcon(icon)

        # Attribute table
        icon = QIcon()
        icon.addFile(resources_path('icons', '11-attribute-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', '11-attribute-dark.png'), mode=QIcon.Selected)
        self.dlg.mOptionsListWidget.item(4).setIcon(icon)

        # Layer editing
        icon = QIcon()
        icon.addFile(resources_path('icons', '10-edition-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', '10-edition-dark.png'), mode=QIcon.Selected)
        self.dlg.mOptionsListWidget.item(5).setIcon(icon)

        # Tooltip layer
        icon = QIcon()
        icon.addFile(resources_path('icons', '16-tooltip-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', '16-tooltip-dark.png'), mode=QIcon.Selected)
        self.dlg.mOptionsListWidget.item(6).setIcon(icon)

        # Filter layer by user
        icon = QIcon()
        icon.addFile(resources_path('icons', '12-user-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', '12-user-dark.png'), mode=QIcon.Selected)
        self.dlg.mOptionsListWidget.item(7).setIcon(icon)

        # Dataviz
        icon = QIcon()
        icon.addFile(resources_path('icons', 'dataviz-icon-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', 'dataviz-icon-dark.png'), mode=QIcon.Selected)
        self.dlg.mOptionsListWidget.item(8).setIcon(icon)

        # Time manager
        icon = QIcon()
        icon.addFile(resources_path('icons', '13-timemanager-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', '13-timemanager-dark.png'), mode=QIcon.Selected)
        self.dlg.mOptionsListWidget.item(9).setIcon(icon)

        # Atlas
        icon = QIcon()
        icon.addFile(resources_path('icons', 'atlas-icon-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', 'atlas-icon-dark.png'), mode=QIcon.Selected)
        self.dlg.mOptionsListWidget.item(10).setIcon(icon)

        # Filter data with form
        icon = QIcon()
        icon.addFile(resources_path('icons', 'filter-icon-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', 'filter-icon-dark.png'), mode=QIcon.Selected)
        self.dlg.mOptionsListWidget.item(11).setIcon(icon)

        # Log
        # noinspection PyCallByClass,PyArgumentList
        icon = QIcon(QgsApplication.iconPath('mMessageLog.svg'))
        self.dlg.mOptionsListWidget.item(12).setIcon(icon)

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

        # List of ui widget for data driven actions and checking
        self.global_options = LizmapConfig.globalOptionDefinitions
        # Add widgets (not done in lizmap_var to avoid dependencies on ui)
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
        self.global_options['activateFirstMapTheme']['widget'] = self.dlg.activate_first_maptheme
        self.global_options['popupLocation']['widget'] = self.dlg.liPopupContainer
        self.global_options['draw']['widget'] = self.dlg.activate_drawing_tools
        self.global_options['print']['widget'] = self.dlg.cbActivatePrint
        self.global_options['measure']['widget'] = self.dlg.cbActivateMeasure
        self.global_options['externalSearch']['widget'] = self.dlg.liExternalSearch
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

        self.layer_options_list = LizmapConfig.layerOptionDefinitions
        # Add widget information
        self.layer_options_list['title']['widget'] = self.dlg.inLayerTitle
        self.layer_options_list['abstract']['widget'] = self.dlg.teLayerAbstract
        self.layer_options_list['link']['widget'] = self.dlg.inLayerLink
        self.layer_options_list['minScale']['widget'] = None
        self.layer_options_list['maxScale']['widget'] = None
        self.layer_options_list['toggled']['widget'] = self.dlg.cbToggled
        self.layer_options_list['group_visibility']['widget'] = self.dlg.list_group_visiblity
        self.layer_options_list['popup']['widget'] = self.dlg.checkbox_popup
        self.layer_options_list['popupFrame']['widget'] = self.dlg.popup_frame
        self.layer_options_list['popupSource']['widget'] = self.dlg.liPopupSource
        self.layer_options_list['popupTemplate']['widget'] = None
        self.layer_options_list['popupMaxFeatures']['widget'] = self.dlg.sbPopupMaxFeatures
        self.layer_options_list['popupDisplayChildren']['widget'] = self.dlg.cbPopupDisplayChildren
        self.layer_options_list['noLegendImage']['widget'] = self.dlg.cbNoLegendImage
        self.layer_options_list['groupAsLayer']['widget'] = self.dlg.cbGroupAsLayer
        self.layer_options_list['baseLayer']['widget'] = self.dlg.cbLayerIsBaseLayer
        self.layer_options_list['displayInLegend']['widget'] = self.dlg.cbDisplayInLegend
        self.layer_options_list['singleTile']['widget'] = self.dlg.cbSingleTile
        self.layer_options_list['imageFormat']['widget'] = self.dlg.liImageFormat
        self.layer_options_list['cached']['widget'] = self.dlg.checkbox_server_cache
        self.layer_options_list['serverFrame']['widget'] = self.dlg.server_cache_frame
        self.layer_options_list['cacheExpiration']['widget'] = self.dlg.inCacheExpiration
        self.layer_options_list['metatileSize']['widget'] = self.dlg.inMetatileSize
        self.layer_options_list['clientCacheExpiration']['widget'] = self.dlg.inClientCacheExpiration
        self.layer_options_list['externalWmsToggle']['widget'] = self.dlg.cbExternalWms
        self.layer_options_list['sourceRepository']['widget'] = self.dlg.inSourceRepository
        self.layer_options_list['sourceProject']['widget'] = self.dlg.inSourceProject

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

        self.layer_options_list['popupSource']['widget'].currentIndexChanged.connect(self.enable_popup_source_button)

        # Connect widget signals to setLayerProperty method depending on widget type
        for key, item in self.layer_options_list.items():
            if item['widget']:
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

        # Connect baselayer checkboxes
        self.base_layer_widget_list = {
            'layer': self.dlg.cbLayerIsBaseLayer,
            'osm-mapnik': self.dlg.cbOsmMapnik,
            'osm-stamen-toner': self.dlg.cbOsmStamenToner,
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
            'empty': self.dlg.cbAddEmptyBaselayer
        }
        for key, item in self.base_layer_widget_list.items():
            slot = self.onBaselayerCheckboxChange
            item.stateChanged.connect(slot)

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
        self.dlg.list_group_visiblity.setToolTip(tooltip)

        self.layerList = None
        self.action = None
        self.isok = None
        self.embeddedGroups = None
        self.myDic = None

    def lwc_version_changed(self):
        current_version = self.dlg.combo_lwc_version.currentData()

        if current_version is None:
            # We come from a higher version of Lizmap
            current_version = DEFAULT_LWC_VERSION

        found = False
        for lwc_version, items in self.lwc_versions.items():
            if found:
                for item in items:
                    item.setStyleSheet(NEW_FEATURE)
            else:
                for item in items:
                    item.setStyleSheet('')

            if lwc_version == current_version:
                found = True

        # Change in all table manager too
        for key in self.layers_table.keys():
            manager = self.layers_table[key].get('manager')
            if manager:
                manager.set_lwc_version(current_version)

        QgsSettings().setValue('lizmap/lizmap_web_client_version', str(current_version.value))

    # noinspection PyPep8Naming
    def initGui(self):
        """Create action that will start plugin configuration"""
        self.action = QAction(
            QIcon(resources_path('icons', 'icon.png')),
            'Lizmap', self.iface.mainWindow())

        # connect the action to the run method
        # noinspection PyUnresolvedReferences
        self.action.triggered.connect(self.run)

        # connect Lizmap signals and functions
        self.dlg.buttonBox.button(QDialogButtonBox.Cancel).clicked.connect(self.dlg.close)
        self.dlg.buttonBox.button(QDialogButtonBox.Apply).clicked.connect(self.get_map_options)
        self.dlg.buttonBox.button(QDialogButtonBox.Ok).clicked.connect(self.ok_button_clicked)
        self.dlg.buttonBox.button(QDialogButtonBox.Help).clicked.connect(self.show_help)

        self.dlg.mOptionsListWidget.currentRowChanged.connect(self.dlg.mOptionsStackedWidget.setCurrentIndex)

        # clear log button clicked
        self.dlg.btClearlog.clicked.connect(self.clear_log)

        # configure popup button
        self.dlg.btConfigurePopup.clicked.connect(self.configure_popup)
        self.dlg.btQgisPopupFromForm.clicked.connect(self.maptip_from_form)

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

        # Dataviz options
        for item in Theme:
            self.global_options['theme']['widget'].addItem(item.value["label"], item.value["data"])
        index = self.global_options['theme']['widget'].findData(Theme.Light.value["data"])
        self.global_options['theme']['widget'].setCurrentIndex(index)

        # Manage "delete line" button
        for key, item in self.layers_table.items():
            control = item['removeButton']
            slot = partial(self.remove_selected_layer_from_table, key)
            control.clicked.connect(slot)
            # noinspection PyCallByClass,PyArgumentList
            control.setIcon(QIcon(QgsApplication.iconPath('symbologyRemove.svg')))
            control.setText('')
            control.setToolTip(tr('Remove the selected layer from the list'))

            control = item.get('addButton')
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
                item.get('addButton').clicked.connect(slot)
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
                else:
                    raise Exception('Unknown panel.')

                item['tableWidget'].horizontalHeader().setStretchLastSection(True)

                item['manager'] = TableManager(
                    self.dlg,
                    definition,
                    dialog,
                    item['tableWidget'],
                    item['removeButton'],
                    item['editButton'],
                    item.get('upButton'),
                    item.get('downButton')
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
        self.project.layersRemoved.connect(self.remove_layer_from_table_by_layer_ids)

        # Lizmap external layers as baselayers
        # add a layer to the lizmap external baselayers
        self.dlg.btLizmapBaselayerAdd.clicked.connect(self.addLayerToLizmapBaselayers)

        # Atlas
        self.dlg.label_atlas_34.setVisible(self.is_dev_version)

        self.iface.addPluginToWebMenu(None, self.action)
        self.iface.addWebToolBarIcon(self.action)

        # Let's fix the dialog to the first panel
        self.dlg.mOptionsListWidget.setCurrentRow(0)

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
        self.iface.databaseMenu().removeAction(self.action)
        self.iface.removeWebToolBarIcon(self.action)

    def enable_popup_source_button(self):
        """Enable or not the "Configure" button according to the popup source."""
        data = self.layer_options_list['popupSource']['widget'].currentText()
        self.dlg.btConfigurePopup.setEnabled(data not in ['auto', 'qgis'])
        self.dlg.btQgisPopupFromForm.setEnabled(data == 'qgis')

        layer = self._current_selected_layer()
        is_vector = isinstance(layer, QgsVectorLayer)
        has_geom = is_vector and layer.wkbType() != QgsWkbTypes.NoGeometry
        index = self.layer_options_list['popupSource']['widget'].findText('qgis')
        qgis_popup = self.layer_options_list['popupSource']['widget'].model().item(index)
        qgis_popup.setFlags(qgis_popup.flags() & ~ Qt.ItemIsEnabled)

        if has_geom:
            qgis_popup.setFlags(qgis_popup.flags() | Qt.ItemIsEnabled)

        if not has_geom and Qgis.QGIS_VERSION_INT >= 31000:
            qgis_popup.setFlags(qgis_popup.flags() | Qt.ItemIsEnabled)

    def show_help(self):
        """Opens the html help file content with default browser."""
        if self.locale in ('en', 'es', 'it', 'pt', 'fi', 'fr'):
            local_help_url = '{url}{lang}/'.format(url=DOC_URL, lang=self.locale)
        else:
            local_help_url = (
                'https://translate.google.fr/translate?'
                'sl=fr&tl={lang}&js=n&prev=_t&hl=fr&ie=UTF-8&eotf=1&u={url}').format(lang=self.locale, url=DOC_URL)
        QDesktopServices.openUrl(QUrl(local_help_url))

    def log(self, msg, abort=None, textarea=None):
        """Log the actions and errors and optionally show them in given text area."""
        if abort:
            sys.stdout = sys.stderr
            self.isok = 0
        if textarea:
            textarea.append(msg)

    def clear_log(self):
        """Clear the content of the text area log."""
        self.dlg.outLog.clear()

    def enable_check_box(self, value):
        """Enable/Disable checkboxes and fields of the Layer tab."""
        for key, item in self.layer_options_list.items():
            if item['widget'] and key != 'sourceProject':
                item['widget'].setEnabled(value)
        self.dlg.btConfigurePopup.setEnabled(value)
        self.dlg.btQgisPopupFromForm.setEnabled(value)

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
            LOGGER.info('Reading the CFG file')
            cfg_file = open(json_file, 'r')
            json_file_reader = cfg_file.read()
            # noinspection PyBroadException
            try:
                sjson = json.loads(json_file_reader)
                json_options = sjson['options']
                for key in self.layers_table.keys():
                    if key in sjson:
                        self.layers_table[key]['jsonConfig'] = sjson[key]
                    else:
                        self.layers_table[key]['jsonConfig'] = {}

                    manager = self.layers_table[key].get('manager')
                    if manager:
                        manager.truncate()
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
                if item['wType'] == 'checkbox':
                    item['widget'].setChecked(item['default'])
                    if key in json_options:
                        if json_options[key].lower() in ('yes', 'true', 't', '1'):
                            item['widget'].setChecked(True)

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
                    list_dic = {item['list'][i]: i for i in range(0, len(item['list']))}
                    for k, i in list_dic.items():
                        item['widget'].setItemData(i, k)
                    if item['default'] in list_dic:
                        item['widget'].setCurrentIndex(list_dic[item['default']])
                    if key in json_options:
                        if json_options[key] in list_dic:
                            item['widget'].setCurrentIndex(list_dic[json_options[key]])

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

        LOGGER.info('CFG file has been loaded')

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
                    # add layer name column - get name from layer if possible (if user has renamed the layer)
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

    def remove_layer_from_table_by_layer_ids(self, layer_ids):
        """
        Remove layers from tables when deleted from layer registry
        """
        json_file = '{}.cfg'.format(self.project.fileName())
        if not os.path.exists(json_file):
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
            # Add content the the widget line
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
            jsonKey = self.myDic[itemKey]['name']
            # loop through layer options to override
            for key, item in self.layer_options_list.items():
                # override only for ui widgets
                if item['widget']:
                    if key in jsonLayers[jsonKey]:
                        # checkboxes
                        if item['wType'] == 'checkbox':
                            if jsonLayers[jsonKey][key].lower() in ('yes', 'true', 't', '1'):
                                self.myDic[itemKey][key] = True
                            else:
                                self.myDic[itemKey][key] = False
                        # spin box
                        elif item['wType'] == 'spinbox':
                            if jsonLayers[jsonKey][key] != '':
                                self.myDic[itemKey][key] = jsonLayers[jsonKey][key]
                        # text inputs
                        elif item['wType'] in ('text', 'textarea'):
                            if jsonLayers[jsonKey][key] != '':
                                if item.get('isMetadata'):  # title and abstract
                                    if not keepMetadata:
                                        self.myDic[itemKey][key] = jsonLayers[jsonKey][key]
                                else:
                                    self.myDic[itemKey][key] = jsonLayers[jsonKey][key]
                        # lists
                        elif item['wType'] == 'list':
                            if jsonLayers[jsonKey][key] in item['list']:
                                self.myDic[itemKey][key] = jsonLayers[jsonKey][key]

                # popupContent
                if key == 'popupTemplate':
                    if key in jsonLayers[jsonKey]:
                        self.myDic[itemKey][key] = jsonLayers[jsonKey][key]

    def process_node(self, node, parent_node, json_layers):
        """
        Process a single node of the QGIS layer tree and adds it to Lizmap layer tree.
        """
        for child in node.children():
            if isinstance(child, QgsLayerTreeGroup):
                child_id = child.name()
                child_type = 'group'
                # noinspection PyCallByClass,PyArgumentList
                child_icon = QIcon(QgsApplication.iconPath('mActionFolder.svg'))
            elif isinstance(child, QgsLayerTreeLayer):
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
            f = open(json_file, 'r')
            json_file_reader = f.read()
            # noinspection PyBroadException
            try:
                sjson = json.loads(json_file_reader)
                json_layers = sjson['layers']
            except Exception:
                if self.is_dev_version:
                    raise
                QMessageBox.critical(self.dlg, tr('Lizmap Error'), '', QMessageBox.Ok)
                self.log(
                    tr(
                        'Errors encountered while reading the last layer tree state. '
                        'Please re-configure the options in the Layers tab completely'),
                    abort=True,
                    textarea=self.dlg.outLog)
            finally:
                f.close()
        return json_layers

    def populateLayerTree(self):
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
                if val['widget']:
                    if val['wType'] in ('text', 'textarea'):
                        val['widget'].setText(selectedItem[key])
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
                        listDic = {val['list'][i]: i for i in range(0, len(val['list']))}
                        val['widget'].setCurrentIndex(listDic[selectedItem[key]])

                    # deactivate wms checkbox if not needed
                    if key == 'externalWmsToggle':
                        wms_enabled = self.get_item_wms_capability(selectedItem)
                        if wms_enabled is not None:
                            self.dlg.cbExternalWms.setEnabled(wms_enabled)
                            if not wms_enabled:
                                self.dlg.cbExternalWms.setChecked(False)

            layer = self._current_selected_layer()  # It can be a layer or a group

            # Disable popup configuration for groups and raster
            # Disable QGIS popup for layer without geom
            is_vector = isinstance(layer, QgsVectorLayer)
            has_geom = is_vector and layer.wkbType() != QgsWkbTypes.NoGeometry
            self.dlg.btConfigurePopup.setEnabled(has_geom)
            self.dlg.btQgisPopupFromForm.setEnabled(is_vector)
            self.dlg.label_drag_drop_form.setEnabled(has_geom)
            self.layer_options_list['popupSource']['widget'].setEnabled(is_vector)

            # Max feature per popup
            self.dlg.label_max_feature_popup.setEnabled(is_vector)
            self.layer_options_list['popupMaxFeatures']['widget'].setEnabled(is_vector)

            # Checkbox display children
            self.layer_options_list['popupDisplayChildren']['widget'].setEnabled(is_vector)
            self.dlg.label_display_popup_children.setEnabled(is_vector)

        else:
            # set default values for this layer/group
            for key, val in self.layer_options_list.items():
                if val['widget']:
                    if val['wType'] in ('text', 'textarea'):
                        val['widget'].setText(val['default'])
                    elif val['wType'] == 'spinbox':
                        val['widget'].setValue(val['default'])
                    elif val['wType'] == 'checkbox':
                        val['widget'].setChecked(val['default'])
                    elif val['wType'] == 'list':
                        listDic = {val['list'][i]: i for i in range(0, len(val['list']))}
                        val['widget'].setCurrentIndex(listDic[val['default']])

        self.enable_popup_source_button()

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
                self.layerList[item.text(1)][key] = layer_option['widget'].text()
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
                self.layerList[item.text(1)][key] = layer_option['list'][layer_option['widget'].currentIndex()]

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

    def configure_popup(self):
        """Open the dialog with a text field to store the popup template for one layer/group"""
        # get the selected item in the layer tree
        item = self.dlg.layer_tree.currentItem()
        if item and item.text(1) in self.layerList:
            # do nothing if no popup configured for this layer/group
            if self.layerList[item.text(1)]['popup'] == 'False':
                return

            # Set the content of the QTextEdit if needed
            if 'popupTemplate' in self.layerList[item.text(1)]:
                self.layerList[item.text(1)]['popup'] = True
                text = self.layerList[item.text(1)]['popupTemplate']
            else:
                text = ''
            self.popup_dialog = LizmapPopupDialog(self.style_sheet, text)
            LOGGER.info('Opening the popup configuration')
            result = self.popup_dialog.exec_()
            if not result:
                return

            content = self.popup_dialog.txtPopup.text()

            # Get the selected item in the layer tree
            item = self.dlg.layer_tree.currentItem()
            if item and item.text(1) in self.layerList:
                # Write the content into the global object
                self.layerList[item.text(1)]['popupTemplate'] = content

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

    def maptip_from_form(self):
        """ Button set popup maptip from layer in the Lizmap configuration. """
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

        if layer.mapTipTemplate() != '':
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
                return

        layer.setMapTipTemplate(html_content)
        QMessageBox.information(
            self.dlg, tr('Maptip'), tr('The maptip has been set in the layer.'), QMessageBox.Ok)

    def writeProjectConfigFile(self):
        """Get general project options and user edited layers options from plugin gui.
        Save them into the project.qgs.cfg config file in the project.qgs folder (json format)."""
        lwc_version = QgsSettings().value('lizmap/lizmap_web_client_version', DEFAULT_LWC_VERSION.value, str)
        metadata = {
            'lizmap_plugin_version': self.global_options['metadata']['lizmap_plugin_version']['default'],
            'lizmap_web_client_target_version': format_version_integer('{}.0'.format(lwc_version)),
        }

        liz2json = dict()
        liz2json['metadata'] = metadata
        liz2json["options"] = dict()
        liz2json["layers"] = dict()

        # projection
        projection = self.iface.mapCanvas().mapSettings().destinationCrs()
        liz2json['options']['projection'] = dict()
        liz2json['options']['projection']['proj4'] = projection.toProj4()
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
                    inputValue = item['list'][item['widget'].currentIndex()]

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
                    inputValue = str(inputValue)

                # Add value to the option
                if inputValue and inputValue != "False":
                    liz2json["options"][key] = inputValue
                else:
                    if 'alwaysExport' in item:
                        liz2json["options"][key] = item['default']

        for key in self.layers_table.keys():
            manager = self.layers_table[key].get('manager')
            if manager:
                data = manager.to_json()
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
            geometryType = -1
            layer = False
            if gal:
                ltype = 'layer'
            else:
                ltype = 'group'
            if self.get_qgis_layer_by_id(k):
                ltype = 'layer'
                gal = True
            if ltype == 'layer':
                layer = self.get_qgis_layer_by_id(k)
                if layer:
                    if layer.type() == QgsMapLayer.VectorLayer:  # if it is a vector layer
                        geometryType = layer.geometryType()

            # ~ # add layerOption only for geo layers
            # ~ if geometryType != 4:
            layerOptions = dict()
            layerOptions["id"] = str(k)
            layerOptions["name"] = str(v['name'])
            layerOptions["type"] = ltype

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
                    else:
                        propVal = str(propVal)
                elif val['type'] == 'integer':
                    try:
                        propVal = int(propVal)
                    except Exception:
                        propVal = 1
                elif val['type'] == 'boolean':
                    propVal = str(propVal)
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

        # Get the project data
        json_file = '{}.cfg'.format(self.project.fileName())
        cfg_file = open(json_file, 'w')
        cfg_file.write(json_file_content)
        cfg_file.close()

        LOGGER.info('The CFG file has been written to "{}"'.format(json_file))
        self.clean_project()

    def clean_project(self):
        """Clean a little bit the QGIS project.

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

    def check_project(self):
        """Project checker about issues that the user might hae when running in LWC."""
        if Qgis.QGIS_VERSION_INT >= 31400:
            from qgis.core import QgsProjectServerValidator
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

    def check_global_project_options(self):
        """Checks that the needed options are correctly set : relative path, project saved, etc.

        :return: Flag if the project is valid and an error message.
        :rtype: bool, basestring
        """
        is_valid = True
        error_message = ''
        # Get the project data from api
        if not self.project.fileName() or not self.project.fileName().lower().endswith('qgs'):
            error_message += tr(
                'You need to open a QGIS project, using the QGS extension, before using Lizmap.')
            is_valid = False

        project_dir = None
        if is_valid:
            # Get the project folder
            project_dir, project_name = os.path.split(os.path.abspath(self.project.fileName()))

        if is_valid:
            # Check if Qgis/capitaliseLayerName is set
            settings = QgsSettings()
            if settings.value('Qgis/capitaliseLayerName') and settings.value('Qgis/capitaliseLayerName', type=bool):
                message = tr(
                    'Please deactivate the option "Capitalize layer names" in the tab "Canvas and legend" '
                    'in the QGIS option dialog, as it could cause issues with Lizmap.')
                error_message += '* {} \n'.format(message)
                is_valid = False

        if is_valid:
            # Check relative/absolute path
            if self.project.readEntry('Paths', 'Absolute')[0] == 'true':
                error_message += '* ' + tr(
                    'The project layer paths must be set to relative. '
                    'Please change this options in the project settings.') + '\n'
                is_valid = False

            # check active layers path layer by layer
            layer_sources_ok = []
            layer_sources_bad = []
            canvas = self.iface.mapCanvas()
            layer_path_error = ''

            for i in range(canvas.layerCount()):
                layer_source = '{}'.format(canvas.layer(i).source())
                if not hasattr(canvas.layer(i), 'providerType'):
                    continue
                layer_provider_key = canvas.layer(i).providerType()
                # Only for layers stored in disk
                if layer_provider_key in ('delimitedtext', 'gdal', 'gpx', 'grass', 'grassraster', 'ogr') \
                        and not layer_source.lower().startswith('mysql'):
                    # noinspection PyBroadException
                    try:
                        relative_path = os.path.normpath(
                            os.path.relpath(os.path.abspath(layer_source), project_dir)
                        )
                        if (not relative_path.startswith('../../../')
                            and not relative_path.startswith('..\\..\\..\\')) \
                                or (layer_provider_key == 'ogr' and layer_source.startswith('http')):
                            layer_sources_ok.append(os.path.abspath(layer_source))
                        else:
                            layer_sources_bad.append(layer_source)
                            layer_path_error += '--> {} \n'.format(relative_path)
                            is_valid = False
                    except Exception:
                        is_valid = False
                        layer_sources_bad.append(layer_source)
                        layer_path_error += '--> {} \n'.format(canvas.layer(i).name())

            if len(layer_sources_bad) > 0:
                message = tr(
                    'The layers paths must be relative to the project file. '
                    'Please copy the layers inside {}.').format(project_dir)
                error_message += '* {}\n'.format(message)
                self.log(
                    tr('The layers paths must be relative to the project file. '
                       'Please copy the layers inside {} or in one folder above '
                       'or aside {}.').format(project_dir, layer_sources_bad),
                    abort=True,
                    textarea=self.dlg.outLog)
                error_message += layer_path_error

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

        return is_valid, error_message

    def ok_button_clicked(self):
        """When the OK button is press, we 'apply' and close the dialog."""
        self.get_map_options()
        self.dlg.close()

    def get_map_options(self):
        """Check the user defined data from gui and save them to both global and project config files"""
        self.isok = 1
        # global project option checking
        is_valid, message = self.check_global_project_options()
        if not is_valid:
            QMessageBox.critical(
                self.dlg, tr('Lizmap Error'), message, QMessageBox.Ok)

        if is_valid:
            # Get configuration from input fields

            # Need to get theses values to check for Pseudo Mercator projection
            mercator_layers = [
                self.dlg.cbOsmMapnik.isChecked(),
                self.dlg.cbOsmStamenToner.isChecked(),
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

            # public baselayers: check that the 3857 projection is set in the
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

            if self.isok:
                # write data in the lizmap json config file
                self.writeProjectConfigFile()
                self.log(
                    tr('All the map parameters are correctly set'),
                    abort=False,
                    textarea=self.dlg.outLog)
                self.log(
                    '<b>' + tr('Lizmap configuration file has been updated') + '</b>',
                    abort=False,
                    textarea=self.dlg.outLog)
            else:
                QMessageBox.critical(
                    self.dlg,
                    tr('Lizmap Error'),
                    tr('Wrong or missing map parameters: please read the log and correct the printed errors.'),
                    QMessageBox.Ok)

            # Get and check map scales
            if self.isok:
                self.get_min_max_scales()
                self.iface.messageBar().pushMessage(
                    'Lizmap',
                    tr('Lizmap configuration file has been updated'),
                    level=Qgis.Success,
                    duration=3
                )

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

    def onBaselayerCheckboxChange(self):
        """
        Add or remove a baselayer in cbStartupBaselayer combobox
        when user change state of any baselayer related checkbox
        """
        if not self.layerList:
            return

        # Combo to fill up with baselayers
        combo = self.dlg.cbStartupBaselayer

        # First get selected item
        idx = combo.currentIndex()
        data = combo.itemData(idx)

        # Clear the combo
        combo.clear()
        i = 0
        blist = []

        # Fill with checked baselayers
        # 1/ QGIS layers
        for k, v in self.layerList.items():
            if not v['baseLayer']:
                continue
            combo.addItem(v['name'], v['name'])
            blist.append(v['name'])
            if data == k:
                idx = i
            i += 1

        # 2/ External baselayers
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
        and set the startup baselayer if found
        """
        # Get the project config file (projectname.qgs.cfg)
        json_file = '{}.cfg'.format(self.project.fileName())
        if os.path.exists(json_file):
            f = open(json_file, 'r')
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

    def run(self):
        """Plugin run method : launch the GUI."""
        if self.dlg.isVisible():
            QMessageBox.warning(
                self.dlg,
                tr("Lizmap - Warning"),
                tr("A Lizmap window is already opened"),
                QMessageBox.Ok)
            return False

        # show the dialog only if checkGlobalProjectOptions is true
        if not self.dlg.isVisible():
            project_is_valid, message = self.check_global_project_options()

            if not project_is_valid:
                QMessageBox.critical(
                    self.dlg,
                    tr('Lizmap Error'),
                    message,
                    QMessageBox.Ok)
                return False

            self.dlg.show()

            # Get config file data
            self.get_config()

            self.layerList = dict()

            # Get embedded groups
            self.embeddedGroups = None

            # Fill the layer tree
            self.populateLayerTree()

            # Fill baselayer startup
            self.onBaselayerCheckboxChange()
            self.setStartupBaselayerFromConfig()

            auto_save = QgsSettings().value('lizmap/auto_save_project', False, bool)
            self.dlg.checkbox_save_project.setChecked(auto_save)

            self.isok = 1

            result = self.dlg.exec_()
            # See if OK was pressed
            if result == 1:
                QMessageBox.warning(self.dlg, "Debug", "Quit !", QMessageBox.Ok)

            return True
