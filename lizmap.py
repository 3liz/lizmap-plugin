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
import urllib.parse
from functools import partial
from shutil import copyfile

from qgis.PyQt.QtCore import (
    QCoreApplication,
    QTranslator,
    QSettings,
    QUrl,
    QFileInfo,
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
    QMenu,
)
from qgis.core import (
    Qgis,
    QgsProject,
    QgsMapLayerProxyModel,
    QgsMapLayerModel,
    QgsLayerTreeGroup,
    QgsLayerTreeLayer,
    QgsWkbTypes,
    QgsAttributeEditorField,
    QgsAttributeEditorContainer,
    QgsApplication,
)

from .definitions.atlas import AtlasDefinitions
from .definitions.filter_by_login import FilterByLoginDefinitions
from .definitions.locate_by_layer import LocateByLayerDefinitions
from .forms.atlas_edition import AtlasEditionDialog
from .forms.filter_by_login import FilterByLoginEditionDialog
from .forms.locate_layer_edition import LocateLayerEditionDialog
from .forms.table_manager import TableManager
from .html_and_expressions import STYLESHEET, CSS_TOOLTIP_FORM
from .lizmap_api.config import LizmapConfig
from .lizmap_dialog import LizmapDialog
from .lizmap_popup_dialog import LizmapPopupDialog
from .qgis_plugin_tools.tools.custom_logging import setup_logger
from .qgis_plugin_tools.tools.i18n import setup_translation, tr
from .qgis_plugin_tools.tools.resources import resources_path, plugin_path, plugin_name
from .qgis_plugin_tools.tools.ghost_layers import remove_all_ghost_layers
from .qgis_plugin_tools.tools.version import is_dev_version, version
from .qgis_plugin_tools.widgets.selectable_combobox import CheckableFieldComboBox

from .tools import excluded_providers

LOGGER = logging.getLogger(plugin_name())


class Lizmap:

    def __init__(self, iface):
        """Constructor of the Lizmap plugin."""
        self.iface = iface
        # noinspection PyArgumentList
        self.project = QgsProject.instance()

        setup_logger(plugin_name())

        locale, file_path = setup_translation(
            'lizmap_{}.qm', plugin_path('lizmap-locales', 'plugin', 'i18n'))
        self.locale = locale[0:2]  # For the online help

        if file_path:
            translator = QTranslator()
            translator.load(file_path)
            QCoreApplication.installTranslator(translator)

        english_path = plugin_path('lizmap-locales', 'plugin', 'i18n', 'lizmap_en.qm')
        if not file_path and not QFileInfo(english_path).exists():
            # It means the submodule is not here.
            # Either lizmap has been downloaded from Github automatic ZIP
            # Or git submodule has never been used
            text = (
                'The translation submodule has not been found. '
                'You should do "git submodule init" and "git submodule update" or if you need a new '
                'clone, do "git clone --recursive https://github.com/3liz/lizmap-plugin.git". '
                'Finally, restart QGIS.')
            self.iface.messageBar().pushMessage('Lizmap Submodule', text, Qgis.Warning)
            LOGGER.warning('Translation is not set, missing the submodule')

        self.dlg = LizmapDialog()
        if is_dev_version():
            self.dlg.setWindowTitle('DEV Lizmap {}'.format(version()))
        self.popup_dialog = None

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
        self.global_options['popupLocation']['widget'] = self.dlg.liPopupContainer
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

        self.dataviz_options = LizmapConfig.datavizOptionDefinitions
        self.dataviz_options['plotType']['widget'] = self.dlg.liDatavizPlotType

        # Add text and icons
        self.dlg.liDatavizPlotType.addItem(QIcon(resources_path('icons', 'plots', 'scatterplot.svg')), 'scatter')
        self.dlg.liDatavizPlotType.addItem(QIcon(resources_path('icons', 'plots', 'boxplot.svg')), 'box')
        self.dlg.liDatavizPlotType.addItem(QIcon(resources_path('icons', 'plots', 'barplot.svg')), 'bar')
        self.dlg.liDatavizPlotType.addItem(QIcon(resources_path('icons', 'plots', 'histogram.svg')), 'histogram')
        self.dlg.liDatavizPlotType.addItem(QIcon(resources_path('icons', 'plots', 'pie.svg')), 'pie')
        self.dlg.liDatavizPlotType.addItem(QIcon(resources_path('icons', 'plots', '2dhistogram.svg')), 'histogram2d')
        self.dlg.liDatavizPlotType.addItem(QIcon(resources_path('icons', 'plots', 'polar.svg')), 'polar')

        self.dataviz_options['plotAggregation']['widget'] = self.dlg.liDatavizAggregation

        self.form_filter_options = LizmapConfig.formFilterOptionDefinitions
        self.form_filter_options['type']['widget'] = self.dlg.liFormFilterFieldType
        self.form_filter_options['uniqueValuesFormat']['widget'] = self.dlg.liFormFilterFormat

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
                'tableWidget': self.dlg.twAttributeLayerList,
                'removeButton': self.dlg.btAttributeLayerDel,
                'addButton': self.dlg.btAttributeLayerAdd,
                'cols': ['primaryKey', 'hiddenFields', 'pivot', 'hideAsChild', 'hideLayer', 'layerId', 'order'],
                'jsonConfig': {}
            },
            'tooltipLayers': {
                'tableWidget': self.dlg.twTooltipLayerList,
                'removeButton': self.dlg.btTooltipLayerDel,
                'addButton': self.dlg.btTooltipLayerAdd,
                'cols': ['fields', 'displayGeom', 'colorGeom', 'layerId', 'order'],
                'jsonConfig': {}
            },
            'editionLayers': {
                'tableWidget': self.dlg.twEditionLayerList,
                'removeButton': self.dlg.btEditionLayerDel,
                'addButton': self.dlg.btEditionLayerAdd,
                'cols': ['createFeature', 'modifyAttribute', 'modifyGeometry', 'deleteFeature', 'acl', 'layerId',
                         'order'],
                'jsonConfig': {}
            },
            'loginFilteredLayers': {
                'tableWidget': self.dlg.table_login_filter,
                'removeButton': self.dlg.remove_filter_login_layer_button,
                'addButton': self.dlg.add_filter_login_layer_button,
                'editButton': self.dlg.edit_filter_login_layer_button,
            },
            'lizmapExternalBaselayers': {
                'tableWidget': self.dlg.twLizmapBaselayers,
                'removeButton': self.dlg.btLizmapBaselayerDel,
                'addButton': self.dlg.btLizmapBaselayerAdd,
                'cols': ['repository', 'project', 'layerName', 'layerTitle', 'layerImageFormat', 'order'],
                'jsonConfig': {}
            },
            'timemanagerLayers': {
                'tableWidget': self.dlg.twTimemanager,
                'removeButton': self.dlg.btTimemanagerLayerDel,
                'addButton': self.dlg.btTimemanagerLayerAdd,
                'cols': ['startAttribute', 'label', 'group', 'groupTitle', 'layerId', 'order'],
                'jsonConfig': {}
            },
            'datavizLayers': {
                'tableWidget': self.dlg.twDatavizLayers,
                'removeButton': self.dlg.btDatavizRemoveLayer,
                'addButton': self.dlg.btDatavizAddLayer,
                'cols': ['title', 'type', 'x_field', 'aggregation', 'y_field', 'color', 'colorfield', 'has_y2_field',
                         'y2_field', 'color2', 'colorfield2', 'popup_display_child_plot', 'only_show_child', 'layerId',
                         'order'],
                'jsonConfig': {}
            },
            'formFilterLayers': {
                'tableWidget': self.dlg.twFormFilterLayers,
                'removeButton': self.dlg.btFormFilterRemoveField,
                'addButton': self.dlg.btFormFilterAddField,
                'cols': [
                    'title', 'type', 'field', 'min_date', 'max_date', 'format', 'splitter', 'provider', 'layerId',
                    'order'],
                'jsonConfig': {}
            }
        }
        self.attribute_fields_checkable = None
        self.tooltip_fields_checkable = None
        self.layerList = None
        self.action = None
        self.web_menu = None
        self.isok = None
        self.embeddedGroups = None
        self.myDic = None

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
        self.dlg.btQgisPopupFromForm.clicked.connect(self.setTooltipContentFromForm)

        # detect project closed
        self.iface.projectRead.connect(self.onProjectRead)
        self.iface.newProjectCreated.connect(self.onNewProjectCreated)

        # initial extent
        self.dlg.btSetExtentFromProject.clicked.connect(self.set_initial_extent_from_project)
        self.dlg.btSetExtentFromCanvas.clicked.connect(self.set_initial_extent_from_canvas)

        # Handle tables (locate by layer, edition layers, etc.)
        #########

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
                elif key == 'locateByLayer':
                    definition = LocateByLayerDefinitions()
                    dialog = LocateLayerEditionDialog
                elif key == 'loginFilteredLayers':
                    definition = FilterByLoginDefinitions()
                    dialog = FilterByLoginEditionDialog
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

        # Attribute layers
        self.dlg.twAttributeLayerList.setColumnHidden(6, True)
        self.dlg.twAttributeLayerList.setColumnHidden(7, True)
        self.dlg.twAttributeLayerList.horizontalHeader().setStretchLastSection(True)
        self.dlg.liAttributeLayer.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.dlg.liAttributeLayer.layerChanged.connect(self.dlg.liAttributeLayerFields.setLayer)
        self.dlg.liAttributeLayerFields.setLayer(self.dlg.liAttributeLayer.currentLayer())
        self.dlg.btAttributeLayerAdd.clicked.connect(self.add_layer_to_attribute_layer)
        self.attribute_fields_checkable = CheckableFieldComboBox(self.dlg.inAttributeLayerHiddenFields)
        self.dlg.liAttributeLayer.layerChanged.connect(self.attribute_fields_checkable.set_layer)
        self.attribute_fields_checkable.set_layer(self.dlg.liAttributeLayer.currentLayer())

        # Tooltip layers
        self.dlg.twTooltipLayerList.setColumnHidden(4, True)
        self.dlg.twTooltipLayerList.setColumnHidden(5, True)
        self.dlg.twTooltipLayerList.horizontalHeader().setStretchLastSection(True)
        self.dlg.liTooltipLayer.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.dlg.btTooltipLayerAdd.clicked.connect(self.add_layer_to_tooltip)
        self.tooltip_fields_checkable = CheckableFieldComboBox(self.dlg.inTooltipLayerFields)
        self.dlg.liTooltipLayer.layerChanged.connect(self.tooltip_fields_checkable.set_layer)
        self.tooltip_fields_checkable.set_layer(self.dlg.liTooltipLayer.currentLayer())

        # Edition layers
        self.dlg.twEditionLayerList.setColumnHidden(6, True)
        self.dlg.twEditionLayerList.setColumnHidden(7, True)
        self.dlg.twEditionLayerList.horizontalHeader().setStretchLastSection(True)
        self.dlg.liEditionLayer.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.dlg.liEditionLayer.setExcludedProviders(excluded_providers())
        self.dlg.btEditionLayerAdd.clicked.connect(self.add_layer_to_edition)

        # Time manager layers
        self.dlg.twTimemanager.setColumnHidden(5, True)
        self.dlg.twTimemanager.setColumnHidden(6, True)
        self.dlg.twTimemanager.horizontalHeader().setStretchLastSection(True)
        self.dlg.liTimemanagerLayers.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.dlg.liTimemanagerLabelAttribute.setAllowEmptyFieldName(True)
        self.dlg.liTimemanagerLayers.layerChanged.connect(self.dlg.liTimemanagerStartAttribute.setLayer)
        self.dlg.liTimemanagerLayers.layerChanged.connect(self.dlg.liTimemanagerLabelAttribute.setLayer)
        self.dlg.liTimemanagerStartAttribute.setLayer(self.dlg.liTimemanagerLayers.currentLayer())
        self.dlg.liTimemanagerLabelAttribute.setLayer(self.dlg.liTimemanagerLayers.currentLayer())
        self.dlg.btTimemanagerLayerAdd.clicked.connect(self.add_layer_to_time_manager)

        # Dataviz layers
        self.dlg.liDatavizPlotLayer.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.dlg.liDatavizPlotLayer.layerChanged.connect(self.dlg.inDatavizPlotXfield.setLayer)
        self.dlg.liDatavizPlotLayer.layerChanged.connect(self.dlg.inDatavizPlotYfield.setLayer)
        self.dlg.liDatavizPlotLayer.layerChanged.connect(self.dlg.inDatavizPlotYfield2.setLayer)
        self.dlg.liDatavizPlotLayer.layerChanged.connect(self.dlg.inDatavizColorField.setLayer)
        self.dlg.liDatavizPlotLayer.layerChanged.connect(self.dlg.inDatavizColorField2.setLayer)
        self.dlg.cbDatavizYField2.toggled.connect(self.dlg.inDatavizPlotYfield2.setEnabled)
        self.dlg.cbDatavizYField2.toggled.connect(self.dlg.inDatavizPlotColor2.setEnabled)
        self.dlg.cbDatavizUseColorField.toggled.connect(self.dlg.inDatavizColorField.setEnabled)
        self.dlg.cbDatavizUseColorField.toggled.connect(self.dlg.inDatavizPlotColor.setDisabled)
        self.dlg.cbDatavizUseColorField2.toggled.connect(self.dlg.inDatavizColorField2.setEnabled)
        self.dlg.cbDatavizUseColorField2.toggled.connect(self.dlg.inDatavizPlotColor2.setDisabled)
        self.dlg.inDatavizPlotXfield.setLayer(self.dlg.liDatavizPlotLayer.currentLayer())
        self.dlg.inDatavizPlotYfield.setLayer(self.dlg.liDatavizPlotLayer.currentLayer())
        self.dlg.inDatavizPlotYfield2.setLayer(self.dlg.liDatavizPlotLayer.currentLayer())
        self.dlg.inDatavizColorField.setLayer(self.dlg.liDatavizPlotLayer.currentLayer())
        self.dlg.inDatavizColorField2.setLayer(self.dlg.liDatavizPlotLayer.currentLayer())

        # Lizmap external layers as baselayers
        # add a layer to the lizmap external baselayers
        self.dlg.btLizmapBaselayerAdd.clicked.connect(self.addLayerToLizmapBaselayers)

        # Add a layer to the lizmap dataviz layers
        self.dlg.btDatavizAddLayer.clicked.connect(self.add_layer_to_dataviz)
        self.dlg.liDatavizPlotType.currentText()

        # Set the dataviz options (type, etc.)
        for key, item in self.dataviz_options.items():
            if item['widget']:
                if item['wType'] == 'list':
                    list_dic = {item['list'][i]: i for i in range(0, len(item['list']))}
                    for k, i in list_dic.items():
                        item['widget'].setItemData(i, k)

        # Set the form filter options (type, etc.)
        self.dlg.btFormFilterAddField.clicked.connect(self.addLayerToFormFilter)
        for key, item in self.form_filter_options.items():
            if item['widget']:
                if item['wType'] == 'list':
                    list_dic = {item['list'][i]: i for i in range(0, len(item['list']))}
                    for k, i in list_dic.items():
                        item['widget'].setItemData(i, k)
        self.dlg.liFormFilterLayer.currentText()
        # Hide some form filter inputs depending on value
        self.update_form_filter_visible_fields()
        self.dlg.liFormFilterFieldType.currentIndexChanged[str].connect(self.update_form_filter_visible_fields)

        # Add empty item in some field comboboxes
        # only in QGIS 3.0 TODO
        # self.dlg.inDatavizColorField.setAllowEmptyFieldName(True)
        # self.dlg.inDatavizColorField2.setAllowEmptyFieldName(True)
        self.dlg.inDatavizPlotXfield.setAllowEmptyFieldName(True)

        # Atlas
        self.dlg.label_atlas_34.setVisible(is_dev_version())

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

    def show_help(self):
        """Opens the html help file content with default browser."""
        if self.locale in ('en', 'es', 'it', 'pt', 'fi', 'fr'):
            local_help_url = 'http://docs.3liz.com/{}/'.format(self.locale)
        else:
            local_help_url = (
                'http://translate.google.fr/translate?'
                'sl=fr&tl={}&js=n&prev=_t&hl=fr&ie=UTF-8&eotf=1&u=http://docs.3liz.com').format(self.locale)
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
                        if key in sjson:
                            manager.truncate()
                            manager.from_json(sjson[key])
                        else:
                            # get a subset of the data to give to the table form
                            data = {k: json_options[k] for k in json_options if k.startswith(manager.definitions.key())}
                            manager.truncate()
                            manager.from_json(data)

            except Exception as e:
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
            extent = '%s, %s, %s, %s' % (
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
        initial_extent = '%s, %s, %s, %s' % (
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
            self.display_error(
                tr('The layers you have chosen for this tool must be checked in the "WFS Capabilities" option of the '
               'QGIS Server tab in the "Project Properties" dialog.'))
            return False
        return True

    def display_error(self, message):
        QMessageBox.critical(
            self.dlg,
            tr('Lizmap Error'),
            message,
            QMessageBox.Ok)

    def add_layer_to_attribute_layer(self):
        """Add a layer in the 'attribute table' tool."""
        table = self.dlg.twAttributeLayerList
        row = table.rowCount()

        if row >= self.dlg.liAttributeLayer.count():
            self.display_error('Not possible to add again this layer.')
            return

        layer = self.dlg.liAttributeLayer.currentLayer()
        if not layer:
            self.display_error('Layer is compulsory.')
            return

        if not self.check_wfs_is_checked(layer):
            return

        primary_key = self.dlg.liAttributeLayerFields.currentField()
        if not primary_key:
            self.display_error('Primary key is compulsory.')
            return

        name = layer.name()
        layer_id = layer.id()
        hidden_fields = ','.join(self.attribute_fields_checkable.selected_items())
        pivot = self.dlg.cbAttributeLayerIsPivot.isChecked()
        hide_as_child = self.dlg.cbAttributeLayerHideAsChild.isChecked()
        hide_layer = self.dlg.cbAttributeLayerHideLayer.isChecked()
        # noinspection PyArgumentList
        icon = QgsMapLayerModel.iconForLayer(layer)

        content = [
            name, primary_key, hidden_fields, str(pivot), str(hide_as_child), str(hide_layer), layer_id, str(row)]

        table.setRowCount(row + 1)

        for i, val in enumerate(content):
            item = QTableWidgetItem(val)
            if i == 0:
                item.setIcon(icon)
            table.setItem(row, i, item)

        LOGGER.info('Layer "{}" has been added to attribute table tool'.format(layer_id))

    def add_layer_to_tooltip(self):
        """Add a layer in the 'tooltip' tool."""
        table = self.dlg.twTooltipLayerList
        row = table.rowCount()

        if row >= self.dlg.liTooltipLayer.count():
            self.display_error('Not possible to add again this layer.')
            return

        layer = self.dlg.liTooltipLayer.currentLayer()
        if not layer:
            self.display_error('Layer is compulsory.')
            return

        if not self.check_wfs_is_checked(layer):
            return

        fields = self.tooltip_fields_checkable.selected_items()
        if not fields:
            self.display_error('At least one field is compulsory.')
            return

        layer_name = layer.name()
        layer_id = layer.id()
        fields = ','.join(fields)
        display_geom = self.dlg.cbTooltipLayerDisplayGeom.isChecked()
        color_geom = self.dlg.inTooltipLayerColorGeom.text().strip(' \t')
        # noinspection PyArgumentList
        icon = QgsMapLayerModel.iconForLayer(layer)

        content = [layer_name, fields, str(display_geom), str(color_geom), layer_id, str(row)]

        table.setRowCount(row + 1)

        for i, val in enumerate(content):
            item = QTableWidgetItem(val)
            if i == 0:
                item.setIcon(icon)
            table.setItem(row, i, item)

        LOGGER.info('Layer "{}" has been added to the tooltip tool'.format(layer_id))

    def add_layer_to_edition(self):
        """Add a layer in the list of edition layers."""
        table = self.dlg.twEditionLayerList
        row = table.rowCount()

        if row >= self.dlg.liEditionLayer.count():
            self.display_error('Not possible to add again this layer.')
            return

        layer = self.dlg.liEditionLayer.currentLayer()
        if not layer:
            self.display_error('Layer is compulsory.')
            return

        if not self.check_wfs_is_checked(layer):
            return

        layer_name = layer.name()
        layer_id = layer.id()
        create_feature = self.dlg.cbEditionLayerCreate.isChecked()
        modify_attribute = self.dlg.cbEditionLayerModifyAttribute.isChecked()
        modify_geometry = self.dlg.cbEditionLayerModifyGeometry.isChecked()
        delete_feature = self.dlg.cbEditionLayerDeleteFeature.isChecked()
        acl = self.dlg.inEditionLayerAcl.text().strip(' \t')
        # noinspection PyArgumentList
        icon = QgsMapLayerModel.iconForLayer(layer)

        # check at least one checkbox is active
        if not create_feature and not modify_attribute and not modify_geometry and not delete_feature:
            self.display_error('At least one action is compulsory.')
            return

        # check if layer already added
        for existing_row in range(row):
            item_layer_id = str(table.item(existing_row, 6).text())
            if layer_id == item_layer_id:
                self.display_error('Not possible to add again this layer.')
                return

        # Check Z or M values which will be lost when editing
        geometry_type = layer.wkbType()
        # noinspection PyArgumentList
        has_m_values = QgsWkbTypes.hasM(geometry_type)
        # noinspection PyArgumentList
        has_z_values = QgsWkbTypes.hasZ(geometry_type)
        if has_z_values or has_m_values:
            QMessageBox.warning(
                self.dlg,
                tr('Editing Z/M Values'),
                tr('Be careful, editing this layer with Lizmap will set the Z and M to 0.'),
            )

        content = [
            layer_name, str(create_feature), str(modify_attribute), str(modify_geometry), str(delete_feature), acl,
            layer_id, str(row)]

        table.setRowCount(row + 1)

        for i, val in enumerate(content):
            item = QTableWidgetItem(val)
            if i == 0:
                item.setIcon(icon)
            table.setItem(row, i, item)

        LOGGER.info('Layer "{}" has been added to the edition tool'.format(layer_id))

    def add_layer_to_time_manager(self):
        """Add a layer in the list of 'time manager' tool."""
        table = self.dlg.twTimemanager
        row = table.rowCount()

        if row >= self.dlg.liTimemanagerLayers.count():
            self.display_error('Not possible to add again this layer.')
            return

        layer = self.dlg.liTimemanagerLayers.currentLayer()
        if not layer:
            self.display_error('Layer is compulsory.')
            return

        if not self.check_wfs_is_checked(layer):
            return

        start_attribute = self.dlg.liTimemanagerStartAttribute.currentField()
        if not start_attribute:
            self.display_error('Start attribute is compulsory.')
            return

        layer_name = layer.name()
        layer_id = layer.id()
        start_attribute = self.dlg.liTimemanagerStartAttribute.currentField()
        label_attribute = self.dlg.liTimemanagerLabelAttribute.currentField()
        group = self.dlg.inTimemanagerGroup.text().strip(' \t')
        group_title = self.dlg.inTimemanagerGroupTitle.text().strip(' \t')
        icon = QgsMapLayerModel.iconForLayer(layer)

        content = [layer_name, start_attribute, label_attribute, group, group_title, layer_id, row]

        table.setRowCount(row + 1)

        for i, val in enumerate(content):
            item = QTableWidgetItem(val)
            if i == 0:
                item.setIcon(icon)
            table.setItem(row, i, item)

        LOGGER.info('Layer "{}" has been added to the time manager tool'.format(layer_id))

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

    def add_layer_to_dataviz(self):
        """Add a layer in the list of Dataviz layer."""
        layer = self.dlg.liDatavizPlotLayer.currentLayer()
        if not layer:
            self.display_error('Not possible to add again this layer.')
            return

        if not self.check_wfs_is_checked(layer):
            return

        graph_y_field = self.dlg.inDatavizPlotYfield.currentField()
        if not graph_y_field:
            self.display_error('Field Y is compulsory.')
            return

        layer_name = layer.name()
        layer_id = layer.id()
        # noinspection PyArgumentList
        icon = QgsMapLayerModel.iconForLayer(layer)

        graph_title = self.dlg.inDatavizPlotTitle.text().strip(' \t')
        graph_type = self.dlg.liDatavizPlotType.itemData(self.dlg.liDatavizPlotType.currentIndex())
        graph_x_field = self.dlg.inDatavizPlotXfield.currentField()
        graph_y_field = self.dlg.inDatavizPlotYfield.currentField()
        aggregation = self.dlg.liDatavizAggregation.itemData(self.dlg.liDatavizAggregation.currentIndex())

        color = self.dlg.inDatavizPlotColor.color()
        colorfield = ''
        if self.dlg.cbDatavizUseColorField.isChecked():
            colorfield = str(self.dlg.inDatavizColorField.currentField())
        pcolor = "%s" % color.name()

        py2fields = ''
        pcolor2 = ''
        colorfield2 = ''
        hasYField2 = str(self.dlg.cbDatavizYField2.isChecked())
        if self.dlg.cbDatavizYField2.isChecked():
            py2fields = str(self.dlg.inDatavizPlotYfield2.currentField()).strip(' \t')
            color2 = self.dlg.inDatavizPlotColor2.color()
            colorfield2 = ''
            if self.dlg.cbDatavizUseColorField2.isChecked():
                colorfield2 = str(self.dlg.inDatavizColorField2.currentField())
            pcolor2 = "%s" % color2.name()

        popup_display_child_plot = str(self.dlg.cbDatavizDisplayChildPlot.isChecked())
        only_show_child = str(self.dlg.cbDatavizOnlyShowChild.isChecked())

        table = self.dlg.twDatavizLayers
        row = table.rowCount()
        content = [
            layer_name, graph_title, graph_type, graph_x_field, aggregation, graph_y_field, pcolor,
            colorfield, hasYField2, py2fields, pcolor2, colorfield2, popup_display_child_plot,
            only_show_child, layer_id, row
        ]
        colCount = len(content)

        # set new rowCount and col count
        table.setRowCount(row + 1)
        table.setColumnCount(colCount)

        for i, val in enumerate(content):
            item = QTableWidgetItem(val)
            if i == 0:
                item.setIcon(icon)
            table.setItem(row, i, item)
            i += 1
        # Hide layer Id
        table.setColumnHidden(colCount - 2, True)

        LOGGER.info('Layer "{}" has been added to the dataviz tool'.format(layer_id))

    def addLayerToFormFilter(self):
        """
        Add a layer in the list of
        Form filter layer
        """

        # Get the layer selected in the combo box
        layer = self.dlg.liFormFilterLayer.currentLayer()
        if not layer:
            self.display_error('Layer is compulsory')
            return

        # Check that the chosen layer is checked in the WFS Capabilities (QGIS Server tab)
        if not self.check_wfs_is_checked(layer):
            return

        layerName = layer.name()
        layerId = layer.id()
        fprovider = layer.providerType()
        # noinspection PyArgumentList
        icon = QgsMapLayerModel.iconForLayer(layer)

        ftitle = str(self.dlg.inFormFilterFieldTitle.text()).strip(' \t')
        ftype = self.dlg.liFormFilterFieldType.itemData(self.dlg.liFormFilterFieldType.currentIndex())
        ffield = str(self.dlg.liFormFilterField.currentField())
        fmindate = str(self.dlg.liFormFilterMinDate.currentField())
        fmaxdate = str(self.dlg.liFormFilterMaxDate.currentField())
        fformat = self.dlg.liFormFilterFormat.itemData(self.dlg.liFormFilterFormat.currentIndex())
        fsplitter = str(self.dlg.liFormFilterSplitter.text()).strip('\t')

        lblTableWidget = self.dlg.twFormFilterLayers
        twRowCount = lblTableWidget.rowCount()
        content = [
            layerName, ftitle, ftype, ffield, fmindate, fmaxdate, fformat, fsplitter, fprovider, layerId, twRowCount]
        colCount = len(content)

        # set new rowCount and col count
        lblTableWidget.setRowCount(twRowCount + 1)
        lblTableWidget.setColumnCount(colCount)

        for i, val in enumerate(content):
            item = QTableWidgetItem(val)
            if i == 0:
                item.setIcon(icon)
            lblTableWidget.setItem(twRowCount, i, item)
            i += 1

        lblTableWidget.setColumnHidden(colCount - 2, True)
        # Hide layer Id
        lblTableWidget.setColumnHidden(colCount - 2, True)

        LOGGER.info('Layer "{}" has been added to the form filter tool'.format(layerId))

    def update_form_filter_visible_fields(self):
        """Show/Hide fields depending of chosen type."""
        index = self.dlg.liFormFilterFieldType.currentIndex()
        ftype = self.dlg.liFormFilterFieldType.itemData(index)
        self.dlg.liFormFilterField.setLayer(self.dlg.liFormFilterLayer.currentLayer())
        self.dlg.liFormFilterMinDate.setLayer(self.dlg.liFormFilterLayer.currentLayer())
        self.dlg.liFormFilterMaxDate.setLayer(self.dlg.liFormFilterLayer.currentLayer())

        if ftype == 'date':
            self.dlg.liFormFilterMinDate.setVisible(True)
            self.dlg.liFormFilterMinDate.setAllowEmptyFieldName(False)
            self.dlg.liFormFilterMaxDate.setVisible(True)
            self.dlg.label_min_date_filter.setVisible(True)
            self.dlg.label_max_date_filter.setVisible(True)
        else:
            self.dlg.liFormFilterMinDate.setVisible(False)
            self.dlg.liFormFilterMinDate.setAllowEmptyFieldName(True)
            self.dlg.liFormFilterMinDate.setField('')
            self.dlg.liFormFilterMaxDate.setVisible(False)
            self.dlg.liFormFilterMaxDate.setField('')
            self.dlg.label_min_date_filter.setVisible(False)
            self.dlg.label_max_date_filter.setVisible(False)

        if ftype == 'uniquevalues':
            self.dlg.liFormFilterFormat.setVisible(True)
            self.dlg.liFormFilterSplitter.setVisible(True)
            self.dlg.label_format_filter.setVisible(True)
            self.dlg.label_splitter_filter.setVisible(True)
        else:
            self.dlg.liFormFilterSplitter.setText('')
            self.dlg.liFormFilterFormat.setVisible(False)
            self.dlg.liFormFilterSplitter.setVisible(False)
            self.dlg.label_format_filter.setVisible(False)
            self.dlg.label_splitter_filter.setVisible(False)

        if ftype in ['text', 'uniquevalues', 'numeric']:
            self.dlg.liFormFilterField.setVisible(True)
            self.dlg.label_field_filter.setVisible(True)
            self.dlg.liFormFilterField.setAllowEmptyFieldName(False)
        else:
            self.dlg.liFormFilterField.setVisible(False)
            self.dlg.label_field_filter.setVisible(False)
            self.dlg.liFormFilterField.setAllowEmptyFieldName(True)
            self.dlg.liFormFilterField.setField('')

    def refresh_layer_tree(self):
        """Refresh the layer tree on user demand. Uses method populateLayerTree."""
        # Ask confirmation
        message = tr(
            'You can refresh the layer tree by pressing "Yes". '
            'Be aware that you will lose all the changes made in this Layers tab '
            '(group or layer metadata and options) since your last "Save". '
            'If you have renamed one or more groups or layers, you will also lose '
            'the associated information.\n'
            'Refresh layer tree?')
        refresh_it = QMessageBox.question(
            self.dlg,
            tr('Lizmap - Refresh layer tree?'),
            message,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if refresh_it == QMessageBox.Yes:
            self.populateLayerTree()
            LOGGER.info('Layer tree has been refreshed')

    def setTreeItemData(self, itemType, itemKey, jsonLayers):
        """Define default data or data from previous configuration for one item (layer or group)
        Used in the method populateLayerTree
        """
        # Type : group or layer
        self.myDic[itemKey]['type'] = itemType

        # DEFAULT VALUES : generic default values for layers and group
        self.myDic[itemKey]['name'] = "%s" % itemKey
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
        if '%s' % self.myDic[itemKey]['name'] in jsonLayers:
            jsonKey = '%s' % self.myDic[itemKey]['name']
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
                                if 'isMetadata' in item:  # title and abstract and link
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
                child_icon = QIcon(QgsApplication.iconPath('mActionAddGroup.svg'))
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

    def populateLayerTree(self):
        """Populate the layer tree of the Layers tab from Qgis legend interface.

        Needs to be refactored.
        """
        self.dlg.layer_tree.clear()
        self.dlg.layer_tree.headerItem().setText(0, tr('List of layers'))
        self.myDic = {}

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
                QMessageBox.critical(self.dlg, tr('Lizmap Error'), '', QMessageBox.Ok)
                self.log(
                    tr(
                        'Errors encountered while reading the last layer tree state. '
                        'Please re-configure the options in the Layers tab completely'),
                    abort=True,
                    textarea=self.dlg.outLog)
            finally:
                f.close()

        # Get layer tree root
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

            isLayer = selectedItem['type'] == 'layer'

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
                        self.dlg.cbExternalWms.setEnabled(wms_enabled)
                        if not wms_enabled:
                            self.dlg.cbExternalWms.setChecked(False)

            # deactivate popup configuration for groups
            self.dlg.btConfigurePopup.setEnabled(isLayer)
            self.dlg.btQgisPopupFromForm.setEnabled(isLayer)

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

    def get_item_wms_capability(self, selectedItem):
        """
        Check if an item in the tree is a layer
        and if it is a WMS layer
        """
        wms_enabled = False
        is_layer = selectedItem['type'] == 'layer'
        if is_layer:
            layer = self.get_qgis_layer_by_id(selectedItem['id'])
            if layer.providerType() in ['wms']:
                if self.getLayerWmsParameters(layer):
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
                            layer.setTitle("%s" % self.layerList[item.text(1)][key])
                        if key == 'abstract':
                            layer.setAbstract("%s" % self.layerList[item.text(1)][key])
                        if key == 'link':
                            layer.setAttributionUrl("%s" % self.layerList[item.text(1)][key])

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

    def createPopupNodeItemFromForm(self, layer, node, level, headers, html):
        regex = re.compile(r"[^a-zA-Z0-9_]", re.IGNORECASE)
        a = ''
        h = ''
        if isinstance(node, QgsAttributeEditorField):
            fidx = node.idx()
            fields = layer.fields()
            field = fields[fidx]

            # display field name or alias if filled
            alias = field.alias()
            name = field.name()
            fname = alias if alias else name
            fname = fname.replace("'", "’")

            # adapt the view depending on the field type
            fset = field.editorWidgetSetup()
            ftype = fset.type()
            fconf = fset.config()
            fview = '"%s"' % name

            # If hidden field, do nothing
            if ftype == 'Hidden':
                return html

            # External ressource: file, url, photo, iframe
            if ftype == 'ExternalResource':
                dview = fconf['DocumentViewer']
                fview = '''
                    concat(
                        '<a href="',
                        "{0}",
                        '" target="_blank">{1}</a>'
                    )
                '''.format(
                    name,
                    fname
                )
                if dview == 1:
                    # image
                    fview = '''
                        concat(
                            '<a href="',
                            "{0}",
                            '" target="_blank">',
                            '
                            <img src="',
                            "{0}",
                            '" width="100%" title="{1}">',
                            '
                            </a>'
                        )
                    '''.format(
                        name,
                        fname
                    )
                if dview == 2:
                    # web view
                    fview = '''
                        concat(
                            '<a href="',
                            "{0}",
                            '" target="_blank">
                            ',
                            '
                            <iframe src="',
                            "{0}",
                            '" width="100%" height="300" title="{1}"/>',
                            '
                            </a>'
                        )
                    '''.format(
                        name,
                        fname
                    )

            # Value relation
            if ftype == 'ValueRelation':
                vlid = fconf['Layer']
                fexp = '''"{0}" = attribute(@parent, '{1}')'''.format(
                    fconf['Key'],
                    name
                )
                filter_exp = fconf['FilterExpression'].strip()
                if filter_exp:
                    fexp += ' AND %s' % filter_exp
                fview = '''
                    aggregate(
                        layer:='{0}',
                        aggregate:='concatenate',
                        expression:="{1}",
                        filter:={2}
                    )
                '''.format(
                    vlid,
                    fconf['Value'],
                    fexp
                )

            # Value relation
            if ftype == 'RelationReference':
                rem = self.project.relationManager()
                rel = rem.relation(fconf['Relation'])
                vlay = rel.referencedLayer()
                vlid = rel.referencedLayerId()
                parent_pk = rel.resolveReferencedField(name)
                fexp = '''
                    "{0}" = attribute(@parent, '{1}')
                '''.format(
                    parent_pk,
                    name
                )
                fview = '''
                    aggregate(
                        layer:='{0}',
                        aggregate:='concatenate',
                        expression:={1},
                        filter:={2}
                    )
                '''.format(
                    vlid,
                    vlay.displayExpression(),
                    fexp
                )

            # Value map
            if ftype == 'ValueMap':
                fmap = fconf['map']
                m = []
                # build hstore
                for d in fmap:
                    m.append(['%s=>%s' % (v.replace("'", "’"), k.replace("'", "’")) for k, v in d.items()][0])
                hmap = ', '.join(m)
                fview = '''
                    map_get(
                        hstore_to_map('{0}'),
                        "{1}"
                    )
                '''.format(
                    hmap,
                    name
                )

            # Date
            if ftype == 'DateTime':
                dfor = fconf['display_format']
                fview = '''
                    format_date(
                        "{0}",
                        '{1}'
                    )
                '''.format(
                    name,
                    dfor
                )

            # fview = '''
            # represent_value("{0}")
            # '''.format(
            # name
            # )

            a += '\n' + '  ' * level
            a += '''
            [% CASE
                WHEN "{0}" IS NOT NULL OR trim("{0}") != ''
                THEN concat(
                    '<p>', '<b>{1}</b>',
                    '<div class="field">', {2}, '</div>',
                    '</p>'
                )
                ELSE ''
            END %]
            '''.format(
                name,
                fname,
                fview
            )

        if isinstance(node, QgsAttributeEditorContainer):
            l = level
            # create div container
            if l == 1:
                act = ''
                if not headers:
                    act = 'active'
                a += '\n' + '  ' * l + '<div id="popup_dd_%s" class="tab-pane %s">' % (
                    regex.sub('_', node.name()),
                    act
                )
                h += '\n    ' + '<li class="%s"><a href="#popup_dd_%s" data-toggle="tab">%s</a></li>' % (
                    act,
                    regex.sub('_', node.name()),
                    node.name()
                )
                headers.append(h)
            if l > 1:
                a += '\n' + '  ' * l + '<fieldset>'
                a += '\n' + '  ' * l + '<legend>%s</legend>' % node.name()
                a += '\n' + '  ' * l + '<div>'

            # In cas of root children
            before_tabs = []
            content_tabs = []
            after_tabs = []

            level += 1
            for n in node.children():
                h = self.createPopupNodeItemFromForm(layer, n, level, headers, html)
                # If it is not root children, add html
                if l > 0:
                    a += h
                    continue
                # If it is root children, store html in the right list
                if isinstance(n, QgsAttributeEditorField):
                    if not headers:
                        before_tabs.append(h)
                    else:
                        after_tabs.append(h)
                else:
                    content_tabs.append(h)

            if l == 0:
                if before_tabs:
                    a += '\n<div class="before-tabs">' + '\n'.join(before_tabs) + '\n</div>'
                if headers:
                    a += '<ul class="nav nav-tabs">\n' + '\n'.join(headers) + '\n</ul>'
                    a += '\n<div class="tab-content">' + '\n'.join(content_tabs) + '\n</div>'
                if after_tabs:
                    a += '\n<div class="after-tabs">' + '\n'.join(after_tabs) + '\n</div>'
            elif l == 1:
                a += '\n' + '  ' * l + '</div>'
            elif l > 1:
                a += '\n' + '  ' * l + '</div>'
                a += '\n' + '  ' * l + '</fieldset>'

        html += a
        return html

    def setTooltipContentFromForm(self):
        item = self.dlg.layer_tree.currentItem()
        if item and item.text(1) in self.layerList:
            lid = item.text(1)
            layers = [a for a in self.project.mapLayers().values() if a.id() == lid]
            if not layers:
                return
        else:
            return
        layer = layers[0]

        cfg = layer.editFormConfig()
        lay = cfg.layout()
        if lay != 1:
            return

        # Get root
        root = cfg.invisibleRootContainer()

        # Build HTML content by using recursive method
        htmlcontent = self.createPopupNodeItemFromForm(layer, root, 0, [], '')

        # package css style, header and content
        html = CSS_TOOLTIP_FORM
        html += '\n<div class="container popup_lizmap_dd" style="width:100%;">'
        html += '\n' + htmlcontent
        html += '\n' + '</div>'

        layer.setMapTipTemplate(html)

    def writeProjectConfigFile(self):
        """Get general project options and user edited layers options from plugin gui.
        Save them into the project.qgs.cfg config file in the project.qgs folder (json format)."""

        metadata = {
            'lizmap_plugin_version': self.global_options['lizmap_plugin_version']['default'],
        }

        liz2json = dict()
        liz2json['metadata'] = metadata
        liz2json["options"] = dict()
        liz2json["layers"] = dict()
        # projection
        # project projection
        mc = self.iface.mapCanvas().mapSettings()
        pCrs = mc.destinationCrs()
        pAuthid = pCrs.authid()
        pProj4 = pCrs.toProj4()
        liz2json["options"]["projection"] = dict()
        liz2json["options"]["projection"]["proj4"] = '{}'.format(pProj4)
        liz2json["options"]["projection"]["ref"] = '{}'.format(pAuthid)
        # wms extent
        pWmsExtent = self.project.readListEntry('WMSExtent', '')[0]
        if len(pWmsExtent) > 1:
            bbox = [pWmsExtent[0], pWmsExtent[1], pWmsExtent[2], pWmsExtent[3]]
        else:
            bbox = []
        liz2json["options"]["bbox"] = bbox

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
                    listDic = {item['list'][i]: i for i in range(0, len(item['list']))}
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
                    except:
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

        wfsLayersList = self.project.readListEntry('WFSLayers', '')[0]

        # list of layers to display attribute table
        lblTableWidget = self.dlg.twAttributeLayerList
        twRowCount = lblTableWidget.rowCount()
        if twRowCount > 0:
            liz2json["attributeLayers"] = dict()
            for row in range(twRowCount):
                # check that the layer is checked in the WFS capabilities
                layerName = lblTableWidget.item(row, 0).text()
                primaryKey = lblTableWidget.item(row, 1).text()
                hiddenFields = lblTableWidget.item(row, 2).text()
                pivot = lblTableWidget.item(row, 3).text()
                hideAsChild = lblTableWidget.item(row, 4).text()
                hideLayer = lblTableWidget.item(row, 5).text()
                layerId = lblTableWidget.item(row, 6).text()
                if layerId in wfsLayersList:
                    liz2json["attributeLayers"][layerName] = dict()
                    liz2json["attributeLayers"][layerName]["primaryKey"] = primaryKey
                    liz2json["attributeLayers"][layerName]["hiddenFields"] = hiddenFields
                    liz2json["attributeLayers"][layerName]["pivot"] = pivot
                    liz2json["attributeLayers"][layerName]["hideAsChild"] = hideAsChild
                    liz2json["attributeLayers"][layerName]["hideLayer"] = hideLayer
                    liz2json["attributeLayers"][layerName]["layerId"] = layerId
                    liz2json["attributeLayers"][layerName]["order"] = row

        # list of layers to display tooltip
        lblTableWidget = self.dlg.twTooltipLayerList
        twRowCount = lblTableWidget.rowCount()
        if twRowCount > 0:
            liz2json["tooltipLayers"] = dict()
            for row in range(twRowCount):
                layerName = lblTableWidget.item(row, 0).text()
                fields = lblTableWidget.item(row, 1).text()
                displayGeom = lblTableWidget.item(row, 2).text()
                colorGeom = lblTableWidget.item(row, 3).text()
                layerId = lblTableWidget.item(row, 4).text()
                if layerId in wfsLayersList:
                    liz2json["tooltipLayers"][layerName] = dict()
                    liz2json["tooltipLayers"][layerName]["fields"] = fields
                    liz2json["tooltipLayers"][layerName]["displayGeom"] = displayGeom
                    liz2json["tooltipLayers"][layerName]["colorGeom"] = colorGeom
                    liz2json["tooltipLayers"][layerName]["layerId"] = layerId
                    liz2json["tooltipLayers"][layerName]["order"] = row

        # layer(s) for the edition tool
        lblTableWidget = self.dlg.twEditionLayerList
        twRowCount = lblTableWidget.rowCount()
        if twRowCount > 0:
            liz2json["editionLayers"] = dict()
            for row in range(twRowCount):
                # check that the layer is checked in the WFS capabilities
                layerName = lblTableWidget.item(row, 0).text()
                createFeature = lblTableWidget.item(row, 1).text()
                modifyAttribute = lblTableWidget.item(row, 2).text()
                modifyGeometry = lblTableWidget.item(row, 3).text()
                deleteFeature = lblTableWidget.item(row, 4).text()
                acl = lblTableWidget.item(row, 5).text()
                layerId = lblTableWidget.item(row, 6).text()
                layer = self.get_qgis_layer_by_id(layerId)
                geometryType = self.mapQgisGeometryType[layer.geometryType()]
                if layerId in wfsLayersList:
                    liz2json["editionLayers"][layerName] = dict()
                    liz2json["editionLayers"][layerName]["layerId"] = layerId
                    liz2json["editionLayers"][layerName]["geometryType"] = geometryType
                    liz2json["editionLayers"][layerName]["capabilities"] = dict()
                    liz2json["editionLayers"][layerName]["capabilities"]["createFeature"] = createFeature
                    liz2json["editionLayers"][layerName]["capabilities"]["modifyAttribute"] = modifyAttribute
                    liz2json["editionLayers"][layerName]["capabilities"]["modifyGeometry"] = modifyGeometry
                    liz2json["editionLayers"][layerName]["capabilities"]["deleteFeature"] = deleteFeature
                    liz2json["editionLayers"][layerName]["acl"] = acl
                    liz2json["editionLayers"][layerName]["order"] = row

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

        # list of timemanager layers
        lblTableWidget = self.dlg.twTimemanager
        twRowCount = lblTableWidget.rowCount()
        if twRowCount > 0:
            liz2json["timemanagerLayers"] = dict()
            for row in range(twRowCount):
                # check that the layer is checked in the WFS capabilities
                layerName = lblTableWidget.item(row, 0).text()
                startAttribute = lblTableWidget.item(row, 1).text()
                labelAttribute = lblTableWidget.item(row, 2).text()
                tmGroup = lblTableWidget.item(row, 3).text()
                tmGroupTitle = lblTableWidget.item(row, 4).text()
                layerId = lblTableWidget.item(row, 5).text()
                if layerId in wfsLayersList:
                    liz2json["timemanagerLayers"][layerName] = dict()
                    liz2json["timemanagerLayers"][layerName]["startAttribute"] = startAttribute
                    if labelAttribute and labelAttribute != '--':
                        liz2json["timemanagerLayers"][layerName]["label"] = labelAttribute
                    liz2json["timemanagerLayers"][layerName]["group"] = tmGroup
                    liz2json["timemanagerLayers"][layerName]["groupTitle"] = tmGroupTitle
                    liz2json["timemanagerLayers"][layerName]["layerId"] = layerId
                    liz2json["timemanagerLayers"][layerName]["order"] = row

        # list of dataviz layers
        lblTableWidget = self.dlg.twDatavizLayers
        twRowCount = lblTableWidget.rowCount()
        if twRowCount > 0:
            liz2json["datavizLayers"] = dict()
            for row in range(twRowCount):
                ptitle = lblTableWidget.item(row, 1).text()
                ptype = lblTableWidget.item(row, 2).text()
                pxfields = lblTableWidget.item(row, 3).text()
                paggregation = lblTableWidget.item(row, 4).text()
                pyfields = lblTableWidget.item(row, 5).text()
                pcolor = lblTableWidget.item(row, 6).text()
                colorfield = lblTableWidget.item(row, 7).text()
                hasy2fields = lblTableWidget.item(row, 8).text()
                py2fields = lblTableWidget.item(row, 9).text()
                pcolor2 = lblTableWidget.item(row, 10).text()
                colorfield2 = lblTableWidget.item(row, 11).text()
                popup_display_child_plot = lblTableWidget.item(row, 12).text()
                only_show_child = lblTableWidget.item(row, 13).text()
                layerId = lblTableWidget.item(row, 14).text()
                if layerId in wfsLayersList:
                    prow = dict()
                    prow["title"] = ptitle
                    prow["type"] = ptype
                    prow["x_field"] = pxfields
                    prow["aggregation"] = paggregation
                    prow["y_field"] = pyfields
                    prow["color"] = pcolor
                    prow["colorfield"] = colorfield
                    prow["has_y2_field"] = hasy2fields
                    prow["y2_field"] = py2fields
                    prow["color2"] = pcolor2
                    prow["colorfield2"] = colorfield2
                    prow["popup_display_child_plot"] = popup_display_child_plot
                    prow["only_show_child"] = only_show_child
                    prow["layerId"] = layerId
                    prow["order"] = row
                    liz2json["datavizLayers"][row] = prow

        # list of form filter layers
        lblTableWidget = self.dlg.twFormFilterLayers
        twRowCount = lblTableWidget.rowCount()
        if twRowCount > 0:
            liz2json["formFilterLayers"] = dict()
            for row in range(twRowCount):
                ftitle = lblTableWidget.item(row, 1).text()
                ftype = lblTableWidget.item(row, 2).text()
                ffield = lblTableWidget.item(row, 3).text()
                if not ftitle.strip():
                    ftitle = ffield
                fmindate = lblTableWidget.item(row, 4).text()
                fmaxdate = lblTableWidget.item(row, 5).text()
                if not fmaxdate.strip():
                    fmaxdate = fmindate
                fformat = lblTableWidget.item(row, 6).text()
                fsplitter = lblTableWidget.item(row, 7).text()
                fprovider = lblTableWidget.item(row, 8).text()
                layerId = lblTableWidget.item(row, 9).text()
                if layerId in wfsLayersList:
                    formFilterField = dict()
                    formFilterField["title"] = ftitle
                    formFilterField["type"] = ftype
                    formFilterField["field"] = ffield
                    formFilterField["min_date"] = fmindate
                    formFilterField["max_date"] = fmaxdate
                    formFilterField["format"] = fformat
                    formFilterField["splitter"] = fsplitter
                    formFilterField["provider"] = fprovider
                    formFilterField["layerId"] = layerId
                    formFilterField["order"] = row
                    liz2json["formFilterLayers"][row] = formFilterField

        # gui user defined layers options
        for k, v in self.layerList.items():
            addToCfg = True
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
                    if layer.type() == 0:  # if it is a vector layer
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
                    wmsParams = self.getLayerWmsParameters(layer)
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

        layers = remove_all_ghost_layers()
        if layers:
            message = tr(
                'Lizmap has found these layers which are ghost layers: {}. '
                'They have been removed. You must save your project.').format(', '.join(layers))
            self.iface.messageBar().pushMessage(
                'Lizmap', message, level=Qgis.Warning, duration=30
            )

    def getLayerWmsParameters(self, layer):
        """
        Get WMS parameters for a raster WMS layers
        """
        uri = layer.dataProvider().dataSourceUri()
        # avoid WMTS layers (not supported yet in Lizmap Web Client)
        if 'wmts' in uri or 'WMTS' in uri:
            return None

        # Split WMS parameters
        wms_params = dict((p.split('=') + [''])[:2] for p in uri.split('&'))

        # urldecode WMS url
        wms_params['url'] = urllib.parse.unquote(wms_params['url']).replace('&&', '&').replace('==', '=')

        return wms_params

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
            settings = QSettings()
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
                project_wms_extent.append('%s' % full_extent.xMinimum())
                project_wms_extent.append('%s' % full_extent.yMinimum())
                project_wms_extent.append('%s' % full_extent.xMaximum())
                project_wms_extent.append('%s' % full_extent.yMaximum())
                self.project.writeEntry('WMSExtent', '', project_wms_extent)
            else:
                if not project_wms_extent[0] or not project_wms_extent[1] or not \
                        project_wms_extent[2] or not project_wms_extent[3]:
                    project_wms_extent[0] = '%s' % full_extent.xMinimum()
                    project_wms_extent[1] = '%s' % full_extent.yMinimum()
                    project_wms_extent[2] = '%s' % full_extent.xMaximum()
                    project_wms_extent[3] = '%s' % full_extent.yMaximum()
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
                QSettings().setValue('lizmap/auto_save_project', auto_save)
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

    def onNewProjectCreated(self):
        """
        When the user opens a new project
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

            # Filter Form layers
            self.dlg.liFormFilterLayer.setFilters(QgsMapLayerProxyModel.VectorLayer)
            black_list = []
            for layer in self.project.mapLayers().values():
                if layer.providerType() not in ('ogr', 'postgres', 'spatialite'):
                    black_list.append(layer)
                if layer.providerType() == 'ogr':
                    if '|layername=' not in layer.dataProvider().dataSourceUri():
                        black_list.append(layer)
            self.dlg.liFormFilterLayer.setExceptedLayerList(black_list)
            self.dlg.liFormFilterLayer.layerChanged.connect(self.dlg.liFormFilterField.setLayer)
            self.dlg.liFormFilterLayer.layerChanged.connect(self.dlg.liFormFilterMinDate.setLayer)
            self.dlg.liFormFilterLayer.layerChanged.connect(self.dlg.liFormFilterMaxDate.setLayer)

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

            auto_save = QSettings().value('lizmap/auto_save_project', False, bool)
            self.dlg.checkbox_save_project.setChecked(auto_save)

            self.isok = 1

            result = self.dlg.exec_()
            # See if OK was pressed
            if result == 1:
                QMessageBox.warning(self.dlg, "Debug", "Quit !", QMessageBox.Ok)

            return True
