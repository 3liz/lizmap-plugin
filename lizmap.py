# -*- coding: utf-8 -*-

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
# Import the PyQt and QGIS libraries
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import QgsMessageBar
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from lizmapdialog import lizmapDialog
# import other needed tool
import sys, os, glob
# configuration parser
import ConfigParser
# date and time
import time, datetime
# regex
import re
# url decoding
import urllib
# json handling
import json
# supprocess module, to load external command line tools
import subprocess
# element tree to get some project properties not exposed to python api
try:
    from xml.etree import ElementTree as ET # Python >= 2.5
except ImportError:
    import elementtree.ElementTree as ET # module Python originel

class lizmap:
    if sys.platform.startswith('win'):
        style = ['0', '0', '0', '5%']
        margin = '4.0'
    else:
        style = ['225', '225', '225', '90%']
        margin = '2.5'
    STYLESHEET = "QGroupBox::title {background-color: transparent; \
                                    subcontrol-origin: margin; \
                                    margin-left: 6px; \
                                    subcontrol-position: top left; \
                                    }"
    STYLESHEET += "QGroupBox {background-color: rgba(%s, %s, %s, %s" % tuple(style)
    STYLESHEET += ");"
    STYLESHEET += "border:1px solid rgba(0,0,0,20%);  \
                   border-radius: 5px; \
                   font-weight: bold;"
    STYLESHEET += "margin-top: %s" % margin
    STYLESHEET += "ex; }"

    def __init__(self, iface):
        '''Save reference to the QGIS interface'''
        self.iface = iface

        # Qgis version
        try:
            self.QgisVersion = unicode(QGis.QGIS_VERSION_INT)
        except:
            self.QgisVersion = unicode(QGis.qgisVersion)[ 0 ]

        # initialize plugin directory
        self.plugin_dir = QFileInfo(QgsApplication.qgisUserDbFilePath()).path() + "/python/plugins/lizmap"
        # initialize locale
        localePath = ""
        self.locale = QSettings().value("locale/userLocale")[0:2]

        if QFileInfo(self.plugin_dir).exists():
            localePath = self.plugin_dir + "/i18n/lizmap_" + self.locale + ".qm"

        self.translator = QTranslator()
        if QFileInfo(localePath).exists():
            self.translator.load(localePath)
        else:
            self.translator.load(self.plugin_dir + "/i18n/lizmap_en.qm")

        if qVersion() > '4.3.3':
            QCoreApplication.installTranslator(self.translator)

        # Create the dialog and keep reference
        self.dlg = lizmapDialog()

        # Set stylesheet for QGroupBox
        self.dlg.ui.gb_tree.setStyleSheet(self.STYLESHEET)
        self.dlg.ui.gb_layerSettings.setStyleSheet(self.STYLESHEET)
        self.dlg.ui.gb_visibleTools.setStyleSheet(self.STYLESHEET)
        self.dlg.ui.gb_Scales.setStyleSheet(self.STYLESHEET)
        self.dlg.ui.gb_extent.setStyleSheet(self.STYLESHEET)
        self.dlg.ui.gb_externalLayers.setStyleSheet(self.STYLESHEET)
        self.dlg.ui.gb_locateByLayer.setStyleSheet(self.STYLESHEET)
        self.dlg.ui.gb_attributeLayers.setStyleSheet(self.STYLESHEET)
        self.dlg.ui.gb_tooltipLayers.setStyleSheet(self.STYLESHEET)
        self.dlg.ui.gb_editionLayers.setStyleSheet(self.STYLESHEET)
        self.dlg.ui.gb_loginFilteredLayers.setStyleSheet(self.STYLESHEET)
        self.dlg.ui.gb_lizmapExternalBaselayers.setStyleSheet(self.STYLESHEET)
        self.dlg.ui.gb_generalOptions.setStyleSheet(self.STYLESHEET)
        self.dlg.ui.gb_timemanager.setStyleSheet(self.STYLESHEET)
        self.dlg.ui.gb_interface.setStyleSheet(self.STYLESHEET)

        # List of ui widget for data driven actions and checking
        self.globalOptions = {
            'mapScales': {
                'widget': self.dlg.ui.inMapScales,
                'wType': 'text', 'type': 'intlist', 'default': [10000, 25000, 50000, 100000, 250000, 500000]
            },
            'minScale': {
                'widget': self.dlg.ui.inMinScale,
                'wType': 'text', 'type': 'integer', 'default': 1
            },
            'maxScale': {
                'widget': self.dlg.ui.inMaxScale,
                'wType': 'text', 'type': 'integer', 'default': 1000000000
            },
            'initialExtent': {
                'widget': self.dlg.ui.inInitialExtent,
                'wType': 'text', 'type': 'floatlist', 'default': []
            },
            'googleKey': {
                'widget': self.dlg.ui.inGoogleKey,
                'wType': 'text', 'type': 'string', 'default': ''
            },
            'googleHybrid' : {
                'widget': self.dlg.ui.cbGoogleHybrid,
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'googleSatellite' : {
                'widget': self.dlg.ui.cbGoogleSatellite,
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'googleTerrain' : {
                'widget': self.dlg.ui.cbGoogleTerrain,
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'googleStreets' : {
                'widget': self.dlg.ui.cbGoogleStreets,
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'osmMapnik' : {
                'widget': self.dlg.ui.cbOsmMapnik,
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'osmMapquest' : {
                'widget': self.dlg.ui.cbOsmMapquest,
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'osmCyclemap' : {
                'widget': self.dlg.ui.cbOsmCyclemap,
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'bingKey': {
                'widget': self.dlg.ui.inBingKey,
                'wType': 'text', 'type': 'string', 'default': ''
            },
            'bingStreets' : {
                'widget': self.dlg.ui.cbBingStreets,
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'bingSatellite' : {
                'widget': self.dlg.ui.cbBingSatellite,
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'bingHybrid' : {
                'widget': self.dlg.ui.cbBingHybrid,
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'ignKey': {
                'widget': self.dlg.ui.inIgnKey,
                'wType': 'text', 'type': 'string', 'default': ''
            },
            'ignStreets' : {
                'widget': self.dlg.ui.cbIgnStreets,
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'ignSatellite' : {
                'widget': self.dlg.ui.cbIgnSatellite,
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'ignTerrain' : {
                'widget': self.dlg.ui.cbIgnTerrain,
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'ignCadastral' : {
                'widget': self.dlg.ui.cbIgnCadastral,
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },

            'hideGroupCheckbox' : {
                'widget': self.dlg.ui.cbHideGroupCheckbox,
                'wType': 'checkbox', 'type': 'boolean', 'default': True
            },
            'popupLocation' : {
                'widget': self.dlg.ui.liPopupContainer,
                'wType': 'list', 'type': 'string', 'default': 'dock', 'list':['dock', 'minidock', 'map']
            },

            'rootGroupsAsBlock' : {
                'widget': self.dlg.ui.cbRootGroupsAsBlock,
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },

            'print' : {
                'widget': self.dlg.ui.cbActivatePrint,
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'measure' : {
                'widget': self.dlg.ui.cbActivateMeasure,
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'externalSearch' : {
                'widget': self.dlg.ui.liExternalSearch,
                'wType': 'list', 'type': 'string', 'default': '', 'list':['', 'nominatim', 'google', 'ign']
            },
            'zoomHistory' : {
                'widget': self.dlg.ui.cbActivateZoomHistory,
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'geolocation' : {
                'widget': self.dlg.ui.cbActivateGeolocation,
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'hideHeader' : {
                'widget': self.dlg.ui.cbHideHeader,
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'hideMenu' : {
                'widget': self.dlg.ui.cbHideMenu,
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'hideLegend' : {
                'widget': self.dlg.ui.cbHideLegend,
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'hideOverview' : {
                'widget': self.dlg.ui.cbHideOverview,
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'hideNavbar' : {
                'widget': self.dlg.ui.cbHideNavbar,
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'hideProject': {
                'widget': self.dlg.ui.cbHideProject,
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'tmTimeFrameSize': {
                'widget': self.dlg.ui.inTimeFrameSize,
                'wType': 'spinbox', 'type': 'integer', 'default': 10
            },
            'tmTimeFrameType' : {
                'widget': self.dlg.ui.liTimeFrameType,
                'wType': 'list', 'type': 'string', 'default': 'seconds',
                'list':['seconds', 'minutes', 'hours', 'days', 'weeks', 'months', 'years']
            },
            'tmAnimationFrameLength': {
                'widget': self.dlg.ui.inAnimationFrameLength,
                'wType': 'spinbox', 'type': 'integer', 'default': 1000
            },
            'emptyBaselayer': {
                'widget': self.dlg.ui.cbAddEmptyBaselayer,
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            }
        }

        self.layerOptionsList = {
            'title': {
                'widget': self.dlg.ui.inLayerTitle,
                'wType': 'text', 'type': 'string', 'default':'', 'isMetadata':True
            },
            'abstract': {
                'widget': self.dlg.ui.teLayerAbstract,
                'wType': 'textarea', 'type': 'string', 'default': '', 'isMetadata':True
            },
            'link': {
                'widget': self.dlg.ui.inLayerLink,
                'wType': 'text', 'type': 'string', 'default': ''
            },
            'minScale': {
                'widget': None,
                'wType': 'text', 'type': 'integer', 'default': 1
            },
            'maxScale': {
                'widget': None,
                'wType': 'text', 'type': 'integer', 'default': 1000000000000
            },
            'toggled': {
                'widget': self.dlg.ui.cbToggled,
                'wType': 'checkbox', 'type': 'boolean', 'default': True
            },
            'popup': {
                'widget': self.dlg.ui.cbPopup,
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'popupTemplate': {
                'widget': None,
                'wType': 'text', 'type': 'string', 'default': ''
            },
            'noLegendImage': {
                'widget': self.dlg.ui.cbNoLegendImage,
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'groupAsLayer': {
                'widget': self.dlg.ui.cbGroupAsLayer,
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'baseLayer': {
                'widget': self.dlg.ui.cbLayerIsBaseLayer,
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'displayInLegend': {
                'widget': self.dlg.ui.cbDisplayInLegend,
                'wType': 'checkbox', 'type': 'boolean', 'default': True
            },
            'singleTile': {
                'widget': self.dlg.ui.cbSingleTile,
                'wType': 'checkbox', 'type': 'boolean', 'default': True,
                'exclude': {'widget': self.dlg.ui.cbCached, 'key': 'cached'}
            },
            'imageFormat': {
                'widget': self.dlg.ui.liImageFormat,
                'wType': 'list', 'type': 'string', 'default': 'image/png',
                'list':["image/png", "image/png; mode=16bit", "image/png; mode=8bit", "image/jpeg"]
            },
            'cached': {
                'widget': self.dlg.ui.cbCached,
                'wType': 'checkbox', 'type': 'boolean', 'default': False,
                'exclude': {'widget': self.dlg.ui.cbSingleTile, 'key': 'singleTile'}
            },
            'cacheExpiration': {
                'widget': self.dlg.ui.inCacheExpiration,
                'wType': 'spinbox', 'type': 'integer', 'default': 0
            },
            'metatileSize': {
                'widget': self.dlg.ui.inMetatileSize,
                'wType': 'text', 'type': 'string', 'default': ''
            },
            'clientCacheExpiration': {
                'widget': self.dlg.ui.inClientCacheExpiration,
                'wType': 'spinbox', 'type': 'integer', 'default': 300
            },
            'externalWmsToggle': {
                'widget': self.dlg.ui.cbExternalWms,
                'wType': 'checkbox', 'type': 'boolean', 'default': False
            },
            'sourceRepository': {
                'widget': self.dlg.ui.inSourceRepository,
                'wType': 'text', 'type': 'string', 'default': ''
            },
            'sourceProject': {
                'widget': self.dlg.ui.inSourceProject,
                'wType': 'text', 'type': 'string', 'default': ''
            }
        }

        # map qgis geometry type
        self.mapQgisGeometryType = {
            0 : 'point',
            1 : 'line',
            2 : 'polygon',
            3 : 'unknown',
            4 : 'none'
        }

        # Disable checkboxes on the layer tab
        self.enableCheckBox(False)

        # Catch user interaction on layer tree and inputs
        self.dlg.ui.treeLayer.itemSelectionChanged.connect(self.setItemOptions)

        # Catch user interaction on Map Scales input
        self.dlg.ui.inMapScales.editingFinished.connect(self.getMinMaxScales)

        # Connect widget signals to setLayerProperty method depending on widget type
        from functools import partial
        for key, item in self.layerOptionsList.items():
            if item['widget']:
                control = item['widget']
                slot = partial(self.setLayerProperty, key)
                if item['wType'] in ('text', 'spinbox'):
                    control.editingFinished.connect(slot)
                elif item['wType'] == 'textarea':
                    control.textChanged.connect(slot)
                elif item['wType'] == 'checkbox':
                    control.stateChanged.connect(slot)
                elif item['wType'] == 'list':
                    control.currentIndexChanged.connect(slot)

        # tables of layers
        self.layersTable =  {
            'locateByLayer': {
                'tableWidget': self.dlg.ui.twLocateByLayerList,
                'removeButton' : self.dlg.ui.btLocateByLayerDel,
                'cols': ['fieldName', 'filterFieldName', 'displayGeom', 'minLength', 'filterOnLocate', 'layerId', 'order'],
                'jsonConfig' : {}
            },
            'attributeLayers': {
                'tableWidget': self.dlg.ui.twAttributeLayerList,
                'removeButton' : self.dlg.ui.btAttributeLayerDel,
                'cols': ['primaryKey', 'hiddenFields', 'pivot', 'hideAsChild', 'layerId', 'order'],
                'jsonConfig' : {}
            },
            'tooltipLayers': {
                'tableWidget': self.dlg.ui.twTooltipLayerList,
                'removeButton' : self.dlg.ui.btTooltipLayerDel,
                'cols': ['fields', 'displayGeom', 'colorGeom', 'layerId', 'order'],
                'jsonConfig' : {}
            },
            'editionLayers': {
                'tableWidget': self.dlg.ui.twEditionLayerList,
                'removeButton' : self.dlg.ui.btEditionLayerDel,
                'cols': ['createFeature', 'modifyAttribute', 'modifyGeometry', 'deleteFeature', 'layerId', 'order'],
                'jsonConfig' : {}
            },
            'loginFilteredLayers': {
                'tableWidget': self.dlg.ui.twLoginFilteredLayersList,
                'removeButton' : self.dlg.ui.btLoginFilteredLayerDel,
                'cols': ['filterAttribute', 'filterPrivate', 'layerId', 'order'],
                'jsonConfig' : {}
            },
            'lizmapExternalBaselayers': {
                'tableWidget': self.dlg.ui.twLizmapBaselayers,
                'removeButton' : self.dlg.ui.btLizmapBaselayerDel,
                'cols': ['repository', 'project', 'layerName', 'layerTitle', 'layerImageFormat', 'order'],
                'jsonConfig' : {}
            },
            'timemanagerLayers': {
                'tableWidget': self.dlg.ui.twTimemanager,
                'removeButton' : self.dlg.ui.btTimemanagerLayerDel,
                'cols': ['startAttribute', 'label', 'group', 'groupTitle', 'layerId', 'order'],
                'jsonConfig' : {}
            }
        }


    def initGui(self):
        '''Create action that will start plugin configuration'''
        self.action = QAction(QIcon(":/plugins/lizmap/icon.png"),
                                    "lizmap", self.iface.mainWindow())

        # connect the action to the run method
        self.action.triggered.connect(self.run)

        # Create action for help dialog
        self.action_help = QAction(QIcon(":/plugins/lizmap/help.png"),
                                    "&Help...", self.iface.mainWindow())
        # connect help action to help dialog
        self.action_help.triggered.connect(self.showHelp)

        # Create action for about dialog
        self.action_about = QAction(QIcon(":/plugins/lizmap/help.png"),
                                    "&About...", self.iface.mainWindow())
        # connect about action to about dialog
        self.action_about.triggered.connect(self.showAbout)

        # connect Lizmap signals and functions

        # save button clicked
        self.dlg.ui.btSave.clicked.connect(self.getMapOptions)

        # clear log button clicked
        self.dlg.ui.btClearlog.clicked.connect(self.clearLog)

        # refresh layer tree button click
#        QObject.connect(self.dlg.ui.btRefreshTree, SIGNAL("clicked()"), self.refreshLayerTree )

        # refresh layer tree button click
        self.dlg.ui.btHelp.clicked.connect(self.showHelp)

        # configure popup button
        self.dlg.ui.btConfigurePopup.clicked.connect(self.configurePopup)

        # detect close event
        self.dlg.ui.buttonClose.rejected.connect(self.warnOnClose)
        self.dlg.rejected.connect(self.warnOnClose)

        # detect project closed
        self.iface.projectRead.connect(self.onProjectRead)
        self.iface.newProjectCreated.connect(self.onNewProjectCreated)

        # initial extent
        self.dlg.ui.btSetExtentFromProject.clicked.connect(self.setInitialExtentFromProject)
        self.dlg.ui.btSetExtentFromCanvas.clicked.connect(self.setInitialExtentFromCanvas)

        # Handle tables (locate by layer, edition layers, etc.)
        #########

        # Manage "delete line" button
        from functools import partial
        for key, item in self.layersTable.items():
            control = item['removeButton']
            slot = partial( self.removeSelectedLayerFromTable, key )
            control.clicked.connect( slot )

        # Delete layers from table when deleted from registry
        lr = QgsMapLayerRegistry.instance()
        lr.layersRemoved.connect( self.removeLayerFromTableByLayerIds )

        # Locate by layers
        # detect layer locate list has changed to refresh layer field list
        self.dlg.ui.liLocateByLayerLayers.currentIndexChanged[str].connect(self.updateLocateFieldListFromLayer)
        # add a layer to the locateByLayerList
        self.dlg.ui.btLocateByLayerAdd.clicked.connect(self.addLayerToLocateByLayer)


        # Attribute layers
        # detect layer locate list has changed to refresh layer field list
        self.dlg.ui.liAttributeLayer.currentIndexChanged[str].connect(self.updateAttributeFieldListFromLayer)
        # add a layer to the list of attribute layers
        self.dlg.ui.btAttributeLayerAdd.clicked.connect(self.addLayerToAttributeLayer)

        # Tooltip layers
        # add a layer to the tooltipLayerList
        self.dlg.ui.btTooltipLayerAdd.clicked.connect(self.addLayerToTooltipLayer)

        # Edition layers
        # add a layer to the editionLayerList
        self.dlg.ui.btEditionLayerAdd.clicked.connect(self.addLayerToEditionLayer)

        # Login filtered layers
        # detect layer locate list has changed to refresh layer field list
        self.dlg.ui.liLoginFilteredLayerLayers.currentIndexChanged[str].connect(self.updateLoginFilteredFieldListFromLayer)
        # add a layer to the list
        self.dlg.ui.btLoginFilteredLayerAdd.clicked.connect(self.addLayerToLoginFilteredLayer)

        # Lizmap external layers as baselayers
        # add a layer to the lizmap external baselayers
        self.dlg.ui.btLizmapBaselayerAdd.clicked.connect(self.addLayerToLizmapBaselayers)

        # Timemanager layers
        # add a layer to the lizmap timemanager layers
        self.dlg.ui.btTimemanagerLayerAdd.clicked.connect(self.addLayerToTimemanager)
        # detect layer list has changed to refresh start attribute field list
        self.dlg.ui.liTimemanagerLayers.currentIndexChanged[str].connect(self.updateTimemanagerFieldListFromLayer)

        # first check if Web menu availbale in this QGIS version
        if hasattr(self.iface, "addPluginToWebMenu"):
            #add plugin to the web plugin menu
            self.iface.addPluginToWebMenu(u"&LizMap", self.action)
            #add plugin help to the plugin menu
            self.iface.addPluginToWebMenu(u"&LizMap", self.action_help)
            #add plugin about to the plugin menu
            self.iface.addPluginToWebMenu(u"&LizMap", self.action_about)
            # and add button to the Web panel
            self.iface.addWebToolBarIcon(self.action)
        else:
            #add icon to the toolbar
            self.iface.addToolBarIcon(self.action)
            #add plugin to the plugin menu
            self.iface.addPluginToMenu(u"&LizMap", self.action)
            #add plugin help to the plugin menu
            self.iface.addPluginToMenu(u"&LizMap", self.action_help)
            #add plugin about to the plugin menu
            self.iface.addPluginToMenu(u"&LizMap", self.action_about)


    def unload(self):
        '''Remove the plugin menu item and icon'''
        # first check if Web menu availbale in this QGIS version
        if hasattr(self.iface, "addPluginToWebMenu"):
            # new menu used, remove submenus from main Web menu
            self.iface.removePluginWebMenu(u"&LizMap", self.action)
            # also remove button from Web toolbar
            self.iface.removeWebToolBarIcon(self.action)
            # Remove help menu entry
            self.iface.removePluginWebMenu(u"&LizMap", self.action_help)
            # Remove about menu entry
            self.iface.removePluginWebMenu(u"&LizMap", self.action_about)
        else:
            #remove plugin
            self.iface.removePluginMenu(u"&LizMap", self.action)
            #remove icon
            self.iface.removeToolBarIcon(self.action)
            # Remove help menu entry
            self.iface.removePluginMenu(u"&LizMap", self.action_help)
            # Remove about menu entry
            self.iface.removePluginMenu(u"&LizMap", self.action_about)


    def showHelp(self):
        '''Opens the html help file content with default browser'''
        if self.locale in ('fr'):
            localHelpUrl = "http://docs.3liz.com/%s/" % self.locale
        else:
            localHelpUrl = 'http://translate.google.fr/translate?sl=fr&tl=%s&js=n&prev=_t&hl=fr&ie=UTF-8&eotf=1&u=http://docs.3liz.com' % self.locale
        QDesktopServices.openUrl( QUrl(localHelpUrl) )

    def showAbout(self):
        '''Opens the about html content with default browser'''
        localAbout = "http://hub.qgis.org/projects/lizmapplugin"
        self.log(localAbout, abort=True, textarea=self.dlg.ui.outLog)
        QDesktopServices.openUrl( QUrl(localAbout) )

    def log(self,msg, level=1, abort=False, textarea=False):
        '''Log the actions and errors and optionnaly show them in given textarea'''
        if abort:
            sys.stdout = sys.stderr
        if textarea:
            textarea.append(msg)
        if abort:
            self.isok = 0

    def logSpentTime(self, msg):
        '''
        Log spent time
        '''
        now = time.clock()
        t = now - self.clock
        self.clock = now
        timeString = "%d:%02d:%02d.%03d" % \
            reduce(lambda ll,b : divmod(ll[0],b) + ll[1:],
                [(t*1000,),1000,60,60])
        self.log( '%s - %s' % (timeString, msg), False, textarea=self.dlg.ui.outLog)

    def clearLog(self):
        '''Clear the content of the textarea log'''
        self.dlg.ui.outLog.clear()
        self.dlg.ui.outState.setText('<font color="green"></font>')

    def enableCheckBox(self, value):
        '''Enable/Disable checkboxes and fields of the Layer tab'''
        for key,item in self.layerOptionsList.items():
            if item['widget'] and key not in ('sourceProject'):
                item['widget'].setEnabled(value)
        self.dlg.ui.btConfigurePopup.setEnabled(value)

    def getMinMaxScales(self):
        ''' Get Min Max Scales from scales input field'''
        minScale = 1
        maxScale = 1000000000
        inMapScales = str(self.dlg.ui.inMapScales.text())
        mapScales = [int(a.strip(' \t') ) for a in inMapScales.split(',') if str(a.strip(' \t')).isdigit()]
        mapScales.sort()
        if len(mapScales) < 2:
            myReturn = False
            QMessageBox.critical(
                self.dlg,
                QApplication.translate("lizmap", "ui.msg.error.title"),
                QApplication.translate("lizmap", "log.map.mapScales.warning"),
                QMessageBox.Ok)
        else:
            minScale = min(mapScales)
            maxScale = max(mapScales)
            myReturn = True
        self.dlg.ui.inMinScale.setText(str(minScale))
        self.dlg.ui.inMaxScale.setText(str(maxScale))
        self.dlg.ui.inMapScales.setText(', '.join(map(str, mapScales)))

        return myReturn


    def getConfig(self):
        ''' Get the saved configuration from the projet.qgs.cfg config file.
        Populate the gui fields accordingly'''

        # Get the project config file (projectname.qgs.cfg)
        p = QgsProject.instance()
        jsonFile = "%s.cfg" % p.fileName()
        jsonOptions = {}
        if os.path.exists(unicode(jsonFile)):
            f = open(jsonFile, 'r')
            jsonFileReader = f.read()
            try:
                sjson = json.loads(jsonFileReader)
                jsonOptions = sjson['options']
                for key in self.layersTable.keys():
                    if sjson.has_key(key):
                        self.layersTable[key]['jsonConfig'] = sjson[key]
                    else:
                        self.layersTable[key]['jsonConfig'] = {}
            except:
                isok=0
                QMessageBox.critical(
                    self.dlg,
                    QApplication.translate("lizmap", "ui.msg.error.title"),
                    QApplication.translate("lizmap", "ui.msg.error.tree.read.content"),
                    QMessageBox.Ok)
                self.log(
                    QApplication.translate("lizmap", "ui.msg.error.tree.read.content"),
                    abort=True,
                    textarea=self.dlg.ui.outLog)
            finally:
                f.close()


        # Set the global options (map, tools, etc.)
        for key, item in self.globalOptions.items():
            if item['widget']:
                if item['wType'] == 'checkbox':
                    item['widget'].setChecked(item['default'])
                    if jsonOptions.has_key(key):
                        if jsonOptions[key].lower() in ('yes', 'true', 't', '1'):
                            item['widget'].setChecked(True)

                if item['wType'] in ('text', 'textarea'):
                    if isinstance(item['default'], (list, tuple)):
                        item['widget'].setText(", ".join(map(str, item['default'])))
                    else:
                        item['widget'].setText(str(item['default']))
                    if jsonOptions.has_key(key):
                        if isinstance(jsonOptions[key], (list, tuple)):
                            item['widget'].setText(", ".join(map(str, jsonOptions[key])))
                        else:
                            item['widget'].setText(str(jsonOptions[key]))


                if item['wType'] == 'spinbox':
                    item['widget'].setValue(int(item['default']))
                    if jsonOptions.has_key(key):
                        item['widget'].setValue(int(jsonOptions[key]))

                if item['wType'] == 'list':
                    listDic = {item['list'][i]:i for i in range(0, len(item['list']))}
                    item['widget'].setCurrentIndex(listDic[item['default']])
                    if jsonOptions.has_key(key):
                        if listDic.has_key(jsonOptions[key]):
                            item['widget'].setCurrentIndex(listDic[jsonOptions[key]])

        # Fill the table widgets
        for key, item in self.layersTable.items():
            self.loadConfigIntoTableWidget(key)

        return True


    def loadConfigIntoTableWidget(self, key):
        '''
        Load the data taken from lizmap config file
        and fill the table widget
        '''
        # Get parameters for the widget
        lt = self.layersTable[key]
        widget = lt['tableWidget']
        attributes = lt['cols']
        json = lt['jsonConfig']

        # Get index of layerId column
        storeLayerId =  'layerId' in lt['cols']

        # For edition layers, fill capabilities
        # Fill editionlayers capabilities
        if key == 'editionLayers' and json:
            for k,v in json.items():
                if v.has_key('capabilities'):
                    for x,y in v['capabilities'].items():
                        json[k][x] = y

        # empty previous content
        for row in range(widget.rowCount()):
            widget.removeRow(row)
        widget.setRowCount(0)

        # fill from the json if exists
        colCount = len(attributes)

        # +1 for layer name column (1st column)
        if storeLayerId:
            colCount+=1

        if json:
            # reorder data if needed
            if json.items()[0][1].has_key('order'):
                data = [(k, json[k]) for k in  sorted(json, key=lambda key: json[key]['order']) ]
            else:
                data = json.items()

            # load content from json file
            lr = QgsMapLayerRegistry.instance()
            projectLayersIds = lr.mapLayers().keys()
            for k,v in data:
                # check if the layer still exists in the QGIS project
                if 'layerId' in v.keys():
                    if v['layerId'] not in projectLayersIds:
                        continue
                twRowCount = widget.rowCount()
                # add a new line
                widget.setRowCount(twRowCount + 1)
                widget.setColumnCount(colCount)
                i=0
                if storeLayerId:
                    # add layer name column - get name from layer if possible (if user has renamed the layer)
                    if 'layerId' in v.keys():
                        layer = lr.mapLayer(v['layerId'])
                        if layer:
                            k = layer.name()
                    newItem = QTableWidgetItem(k)
                    newItem.setFlags(Qt.ItemIsEnabled)
                    widget.setItem(twRowCount, 0, newItem)
                    i+=1
                # other information
                for key in attributes:
                    if v.has_key(key):
                        value = v[key]
                    else:
                        value = ''
                    newItem = QTableWidgetItem(str(value))
                    newItem.setFlags(Qt.ItemIsEnabled)
                    widget.setItem(twRowCount, i, newItem)
                    i+=1

        # hide las columns
        # order (always at the end)
        widget.setColumnHidden(colCount - 1, True)
        # hide layer_id column (if present, always
        if storeLayerId:
            widget.setColumnHidden(colCount - 2, True)




    def getQgisLayerById(self, myId):
        '''Get a QgsLayer by its Id'''
        for layer in self.iface.legendInterface().layers():
            if myId == layer.id():
                return layer
        return None

    def getQgisLayerByNameFromCombobox(self, layerComboBox):
        '''Get a layer by its name'''
        returnLayer = None
        uniqueId = unicode(layerComboBox.itemData(layerComboBox.currentIndex()))
        try:
            myInstance = QgsMapLayerRegistry.instance()
            layer = myInstance.mapLayer(uniqueId)
            if layer:
                if layer.isValid():
                    returnLayer = layer
        except:
            returnLayer = None
        return returnLayer


    def populateLayerCombobox(self, combobox, ltype='all', providerTypeList=['all']):
        '''
            Get the list of layers and add them to a combo box
            * ltype can be : all, vector, raster
            * providerTypeList is a list and can be : ['all'] or a list of provider keys
            as ['spatialite', 'postgres'] or ['ogr', 'postgres'], etc.
        '''
        # empty combobox
        combobox.clear()
        # add empty item
        combobox.addItem ( '---', -1)
        # loop though the layers
        layers = self.iface.legendInterface().layers()
        for layer in layers:
            layerId = layer.id()
            # vector
            if layer.type() == QgsMapLayer.VectorLayer and ltype in ('all', 'vector'):
                if not hasattr(layer, 'providerType'):
                    continue
                if 'all' in providerTypeList or layer.providerType() in providerTypeList:
                    combobox.addItem ( layer.name(), unicode(layerId))
            # raster
            if layer.type() == QgsMapLayer.RasterLayer and ltype in ('all', 'raster'):
                combobox.addItem ( layer.name(),unicode(layerId))


    def setInitialExtentFromProject(self):
        '''
        Get the project WMS advertised extent
        and set the initial xmin, ymin, xmax, ymax
        in the map options tab
        '''
        # Get project instance
        p = QgsProject.instance()

        # Get WMS extent
        pWmsExtent = p.readListEntry('WMSExtent','')[0]
        if len(pWmsExtent) > 1:
            initialExtent = '%s, %s, %s, %s' % (
                pWmsExtent[0],
                pWmsExtent[1],
                pWmsExtent[2],
                pWmsExtent[3]
            )
            self.dlg.ui.inInitialExtent.setText(initialExtent)

    def setInitialExtentFromCanvas(self):
        '''
        Get the map canvas extent
        and set the initial xmin, ymin, xmax, ymax
        in the map options tab
        '''
        # Get map canvas extent
        mcExtent = self.iface.mapCanvas().extent()
        initialExtent = '%s, %s, %s, %s' % (
            mcExtent.xMinimum(),
            mcExtent.yMinimum(),
            mcExtent.xMaximum(),
            mcExtent.yMaximum()
        )
        self.dlg.ui.inInitialExtent.setText(initialExtent)


    def updateAttributeFieldListFromLayer(self):
        '''
            Fill the combobox with the list of fields
            for the layer chosen with the atribute layers combobox
        '''
        # get the layer selected in the combo box
        layer = self.getQgisLayerByNameFromCombobox(self.dlg.ui.liAttributeLayer)

        # remove previous items
        self.dlg.ui.liAttributeLayerFields.clear()
        # populate the columns combo box
        if layer:
            if layer.type() == QgsMapLayer.VectorLayer:
                provider = layer.dataProvider()
                fields = layer.pendingFields()
                for field in fields:
                    self.dlg.ui.liAttributeLayerFields.addItem(
                        unicode(field.name()),
                        unicode(field.name())
                    )
        else:
            return None

    def updateLocateFieldListFromLayer(self):
        '''
            Fill the combobox with the list of fields
            for the layer chosen with the liLayerLocateLayer combobox
        '''
        # get the layer selected in the combo box
        layer = self.getQgisLayerByNameFromCombobox(self.dlg.ui.liLocateByLayerLayers)

        # remove previous items
        self.dlg.ui.liLocateByLayerFields.clear()
        # populate the fields combo boxes
        cbs = [
            [False, self.dlg.ui.liLocateByLayerFields],
            [True, self.dlg.ui.liLocateByLayerFilterFields]
        ]
        if layer:
            if layer.type() == QgsMapLayer.VectorLayer:
                for cb in cbs:
                    fields = layer.pendingFields()
                    # Add empty item if allowed
                    if cb[0]:
                        cb[1].addItem(u'--', u'')
                    # Add fields to the combo
                    for field in fields:
                        cb[1].addItem(
                            unicode(field.name()),
                            unicode(field.name())
                        )
        else:
            return None

    def updateLoginFilteredFieldListFromLayer(self):
        '''
            Fill the combobox with the list of fields
            for the layer chosen with the liLayerLocateLayer combobox
        '''
        # get the layer selected in the combo box
        layer = self.getQgisLayerByNameFromCombobox(self.dlg.ui.liLoginFilteredLayerLayers)

        # remove previous items
        self.dlg.ui.liLoginFilteredLayerFields.clear()
        # populate the columns combo box
        if layer:
            if layer.type() == QgsMapLayer.VectorLayer:
                fields = layer.pendingFields()
                for field in fields:
                    self.dlg.ui.liLoginFilteredLayerFields.addItem(
                        unicode(field.name()),
                        unicode(field.name())
                    )
        else:
            return None


    def updateTimemanagerFieldListFromLayer(self):
        '''
            Fill the combobox with the list of fields
            for the layer chosen with the timemanager combobox
            !!! NEEDS REFACTORING !!!
        '''
        # get the layer selected in the combo box
        layer = self.getQgisLayerByNameFromCombobox(self.dlg.ui.liTimemanagerLayers)

        # populate the fields combo boxes
        cbs = [
            [False, self.dlg.ui.liTimemanagerStartAttribute],
            [True, self.dlg.ui.liTimemanagerLabelAttribute]
        ]
        # remove previous items
        for cb in cbs:
            cb[1].clear()

        if layer:
            if layer.type() == QgsMapLayer.VectorLayer:
                fields = layer.pendingFields()
                for cb in cbs:
                    # Add empty item if allowed
                    if cb[0]:
                        cb[1].addItem(u'--', u'')
                    # Add fields to the combo
                    for field in fields:
                        cb[1].addItem(
                            unicode(field.name()),
                            unicode(field.name())
                        )
        else:
            return None




    def removeSelectedLayerFromTable(self, key):
        '''
        Remove a layer from the list of layers
        for which to have the "locate by layer" tool
        '''
        tw = self.layersTable[key]['tableWidget']
        tw.removeRow( tw.currentRow() )

    def removeLayerFromTableByLayerIds(self, layerIds):
        '''
        Remove layers from tables when deleted from layer registry
        '''
        for key, item in self.layersTable.items():
            tw = self.layersTable[key]['tableWidget']

            # Count lines
            twRowCount = tw.rowCount()
            if not twRowCount:
                continue

            # Get index of layerId column
            if 'layerId' not in self.layersTable[key]['cols']:
                continue
            idx = self.layersTable[key]['cols'].index('layerId') + 1

            # Remove layer if layerId match
            for row in range(twRowCount):
                if tw.item(row, idx):
                    itemLayerId = str(tw.item(row, idx).text().encode('utf-8'))
                    if itemLayerId in layerIds:
                        tw.removeRow( row )



    def addLayerToLocateByLayer(self):
        '''Add a layer in the list of layers
        for which to have the "locate by layer" tool'''

        # Get the layer selected in the combo box
        layer = self.getQgisLayerByNameFromCombobox(self.dlg.ui.liLocateByLayerLayers)
        if not layer:
            return False

        # Check that the chosen layer is checked in the WFS Capabilities (OWS tab)
        p = QgsProject.instance()
        wfsLayersList = p.readListEntry('WFSLayers','')[0]
        hasWfsOption = False
        for l in wfsLayersList:
            if layer.id() == l:
                hasWfsOption = True
        if not hasWfsOption:
            QMessageBox.critical(
                self.dlg,
                QApplication.translate("lizmap", "ui.msg.error.title"),
                QApplication.translate("lizmap", "ui.msg.warning.toolLayer.notInWfs"),
                QMessageBox.Ok)
            return False

        # Retrieve layer information
        layerName = layer.name()
        layerId = layer.id()
        fieldCombobox = self.dlg.ui.liLocateByLayerFields
        filterFieldCombobox = self.dlg.ui.liLocateByLayerFilterFields
        fieldName = fieldCombobox.currentText()
        filterFieldName = filterFieldCombobox.currentText()
        displayGeom = str(self.dlg.ui.cbLocateByLayerDisplayGeom.isChecked())
        minLength = self.dlg.ui.inLocateByLayerMinLength.value()
        filterOnLocate = str(self.dlg.ui.cbFilterOnLocate.isChecked())

        lblTableWidget = self.dlg.ui.twLocateByLayerList
        twRowCount = lblTableWidget.rowCount()
        if twRowCount < 5:
            # set new rowCount
            lblTableWidget.setRowCount(twRowCount + 1)
            lblTableWidget.setColumnCount(8)

            # add layer name to the line
            newItem = QTableWidgetItem(layerName)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 0, newItem)
            # add field name to the line
            newItem = QTableWidgetItem(fieldName)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 1, newItem)
            # add filter field name to the line
            newItem = QTableWidgetItem(filterFieldName)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 2, newItem)
            # add displayGeom option to the line
            newItem = QTableWidgetItem(displayGeom)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 3, newItem)
            # add minLength to the line
            newItem = QTableWidgetItem(str(minLength))
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 4, newItem)
            # add filterOnLocate to the line
            newItem = QTableWidgetItem(filterOnLocate)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 5, newItem)
            # add layer id to the line
            newItem = QTableWidgetItem(layerId)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 6, newItem)
            # add order
            newItem = QTableWidgetItem(lblTableWidget.rowCount())
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 7, newItem)

        lblTableWidget.setColumnHidden(6, True)
        lblTableWidget.setColumnHidden(7, True)


    def addLayerToAttributeLayer(self):
        '''Add a layer in the list of layers
        for which Lizmap will display attribute tables'''

        # Get the layer selected in the combo box
        layer = self.getQgisLayerByNameFromCombobox(self.dlg.ui.liAttributeLayer)
        if not layer:
            return False

        # Check that the chosen layer is checked in the WFS Capabilities (OWS tab)
        p = QgsProject.instance()
        wfsLayersList = p.readListEntry('WFSLayers','')[0]
        hasWfsOption = False
        for l in wfsLayersList:
            if layer.id() == l:
                hasWfsOption = True
        if not hasWfsOption:
            QMessageBox.critical(
                self.dlg,
                QApplication.translate("lizmap", "ui.msg.error.title"),
                QApplication.translate("lizmap", "ui.msg.warning.toolLayer.notInWfs"),
                QMessageBox.Ok)
            return False

        # Retrieve layer information
        layerName = layer.name()
        layerId = layer.id()
        fieldCombobox = self.dlg.ui.liAttributeLayerFields
        primaryKey = fieldCombobox.currentText()
        hiddenFields = str(self.dlg.ui.inAttributeLayerHiddenFields.text().encode('utf-8')).strip(' \t')
        pivot = str(self.dlg.ui.cbAttributeLayerIsPivot.isChecked())
        hideAsChild= str(self.dlg.ui.cbAttributeLayerHideAsChild.isChecked())

        lblTableWidget = self.dlg.ui.twAttributeLayerList
        twRowCount = lblTableWidget.rowCount()
        if twRowCount < 15:
            # set new rowCount
            lblTableWidget.setRowCount(twRowCount + 1)
            lblTableWidget.setColumnCount(7)
            # add layer name to the line
            newItem = QTableWidgetItem(layerName)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 0, newItem)
            # add primary key attribute to the line
            newItem = QTableWidgetItem(primaryKey)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 1, newItem)
            # add "hiddenFields"
            newItem = QTableWidgetItem(hiddenFields)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 2, newItem)
            # add "pivot"
            newItem = QTableWidgetItem(pivot)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 3, newItem)
            # add "hideAsChild"
            newItem = QTableWidgetItem(hideAsChild)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 4, newItem)
            # add layer id to the line
            newItem = QTableWidgetItem(layerId)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 5, newItem)
            # add order
            newItem = QTableWidgetItem(lblTableWidget.rowCount())
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 6, newItem)

        lblTableWidget.setColumnHidden(5, True)
        lblTableWidget.setColumnHidden(6, True)


    def addLayerToTooltipLayer(self):
        '''Add a layer in the list of layers
        for which Lizmap will propose a tooltip'''

        # Get the layer selected in the combo box
        layer = self.getQgisLayerByNameFromCombobox(self.dlg.ui.liTooltipLayer)
        if not layer:
            return False

        # Check that the chosen layer is checked in the WFS Capabilities (OWS tab)
        p = QgsProject.instance()
        wfsLayersList = p.readListEntry('WFSLayers','')[0]
        hasWfsOption = False
        for l in wfsLayersList:
            if layer.id() == l:
                hasWfsOption = True
        if not hasWfsOption:
            QMessageBox.critical(
                self.dlg,
                QApplication.translate("lizmap", "ui.msg.error.title"),
                QApplication.translate("lizmap", "ui.msg.warning.toolLayer.notInWfs"),
                QMessageBox.Ok)
            return False

        # Retrieve layer information
        layerName = layer.name()
        layerId = layer.id()
        fields = str(self.dlg.ui.inTooltipLayerFields.text().encode('utf-8')).strip(' \t')
        displayGeom = str(self.dlg.ui.cbTooltipLayerDisplayGeom.isChecked())
        colorGeom = str(self.dlg.ui.inTooltipLayerColorGeom.text().encode('utf-8')).strip(' \t')

        lblTableWidget = self.dlg.ui.twTooltipLayerList
        twRowCount = lblTableWidget.rowCount()
        if twRowCount < 5:
            # set new rowCount
            lblTableWidget.setRowCount(twRowCount + 1)
            lblTableWidget.setColumnCount(6)
            # add layer name to the line
            newItem = QTableWidgetItem(layerName)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 0, newItem)
            # add "fields"
            newItem = QTableWidgetItem(fields)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 1, newItem)
            # add "displayGeom"
            newItem = QTableWidgetItem(displayGeom)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 2, newItem)
            # add "colorGeom"
            newItem = QTableWidgetItem(colorGeom)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 3, newItem)
            # add layer id to the line
            newItem = QTableWidgetItem(layerId)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 4, newItem)
            # add order
            newItem = QTableWidgetItem(lblTableWidget.rowCount())
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 5, newItem)

        lblTableWidget.setColumnHidden(4, True)
        lblTableWidget.setColumnHidden(5, True)


    def addLayerToEditionLayer(self):
        '''Add a layer in the list of edition layers'''

        # Get the layer selected in the combo box
        layer = self.getQgisLayerByNameFromCombobox(self.dlg.ui.liEditionLayer)
        if not layer:
            return False

        # Retrieve layer information
        layerName = layer.name()
        layerId = layer.id()
        createFeature = str(self.dlg.ui.cbEditionLayerCreate.isChecked())
        modifyAttribute = str(self.dlg.ui.cbEditionLayerModifyAttribute.isChecked())
        modifyGeometry = str(self.dlg.ui.cbEditionLayerModifyGeometry.isChecked())
        deleteFeature = str(self.dlg.ui.cbEditionLayerDeleteFeature.isChecked())
        lblTableWidget = self.dlg.ui.twEditionLayerList

        # check at least one checkbox is active
        if not self.dlg.ui.cbEditionLayerCreate.isChecked() \
        and not self.dlg.ui.cbEditionLayerModifyAttribute.isChecked() \
        and not self.dlg.ui.cbEditionLayerModifyGeometry.isChecked() \
        and not self.dlg.ui.cbEditionLayerDeleteFeature.isChecked():
            return False

        # count table widget lines
        twRowCount = lblTableWidget.rowCount()

        # check if layer already added
        if twRowCount > 0:
            for row in range(twRowCount):
                itemLayerId = str(lblTableWidget.item(row, 5).text().encode('utf-8'))
                if layerId == itemLayerId:
                    return False

        # Add layer
        if twRowCount < 10:
            # set new rowCount
            lblTableWidget.setRowCount(twRowCount + 1)
            lblTableWidget.setColumnCount(7)

            # add layer name to the line
            newItem = QTableWidgetItem(layerName)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 0, newItem)
            # create feature
            newItem = QTableWidgetItem(createFeature)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 1, newItem)
            # modify attributes
            newItem = QTableWidgetItem(modifyAttribute)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 2, newItem)
            # modify geometry
            newItem = QTableWidgetItem(modifyGeometry)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 3, newItem)
            # delete feature
            newItem = QTableWidgetItem(deleteFeature)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 4, newItem)
            # add layer id to the line
            newItem = QTableWidgetItem(layerId)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 5, newItem)
            # add order
            newItem = QTableWidgetItem(lblTableWidget.rowCount())
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 6, newItem)

        lblTableWidget.setColumnHidden(6, True)
        lblTableWidget.setColumnHidden(5, True)


    def addLayerToLoginFilteredLayer(self):
        '''Add a layer in the list of layers
        for which to have the "login filtered layer" tool'''

        # Get the layer selected in the combo box
        layer = self.getQgisLayerByNameFromCombobox(self.dlg.ui.liLoginFilteredLayerLayers)
        if not layer:
            return False

        # Retrieve layer information
        layerName = layer.name()
        layerId = layer.id()
        fieldCombobox = self.dlg.ui.liLoginFilteredLayerFields
        filterAttribute = fieldCombobox.currentText()
        filterPrivate = str(self.dlg.ui.cbLoginFilteredLayerPrivate.isChecked())
        lblTableWidget = self.dlg.ui.twLoginFilteredLayersList
        twRowCount = lblTableWidget.rowCount()
        if twRowCount < 6:
            # set new rowCount
            lblTableWidget.setRowCount(twRowCount + 1)
            lblTableWidget.setColumnCount(5)

            # add layer name to the line
            newItem = QTableWidgetItem(layerName)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 0, newItem)
            # add filter attribute to the line
            newItem = QTableWidgetItem(filterAttribute)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 1, newItem)
            # add filterPrivate
            newItem = QTableWidgetItem(filterPrivate)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 2, newItem)
            # add layer id to the line
            newItem = QTableWidgetItem(layerId)
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 3, newItem)
            # add order
            newItem = QTableWidgetItem(lblTableWidget.rowCount())
            newItem.setFlags(Qt.ItemIsEnabled)
            lblTableWidget.setItem(twRowCount, 4, newItem)

        lblTableWidget.setColumnHidden(3, True)
        lblTableWidget.setColumnHidden(4, True)


    def addLayerToLizmapBaselayers(self):
        '''
        Add a layer in the list of
        Lizmap external baselayers

        '''

        # Retrieve user options
        layerRepository = str(self.dlg.ui.inLizmapBaselayerRepository.text().encode('utf-8')).strip(' \t')
        layerProject = str(self.dlg.ui.inLizmapBaselayerProject.text().encode('utf-8')).strip(' \t')
        layerName = str(self.dlg.ui.inLizmapBaselayerLayer.text().encode('utf-8')).strip(' \t')
        layerTitle = str(self.dlg.ui.inLizmapBaselayerTitle.text().encode('utf-8')).strip(' \t')
        layerImageFormat = str(self.dlg.ui.inLizmapBaselayerImageFormat.text().encode('utf-8')).strip(' \t')
        content = [layerRepository, layerProject, layerName, layerTitle, layerImageFormat]
        # Check that every option is set
        for val in content:
            if not val:
                QMessageBox.critical(
                    self.dlg,
                    QApplication.translate("lizmap", "ui.msg.error.title"),
                    QApplication.translate("lizmap", "ui.msg.baselayers.lack.input"),
                    QMessageBox.Ok
                )
                return False

        lblTableWidget = self.dlg.ui.twLizmapBaselayers
        twRowCount = lblTableWidget.rowCount()
        content.append(twRowCount) # store order
        colCount = len(content)
        if twRowCount < 6:
            # set new rowCount
            lblTableWidget.setRowCount(twRowCount + 1)
            lblTableWidget.setColumnCount(colCount)
            # Add content the the widget line
            i=0
            for val in content:
                newItem = QTableWidgetItem(val)
                newItem.setFlags(Qt.ItemIsEnabled)
                lblTableWidget.setItem(twRowCount, i, newItem)
                i+=1


    def addLayerToTimemanager(self):
        '''
        Add a layer in the list of
        Timemanager layer
        '''

        # Get the layer selected in the combo box
        layer = self.getQgisLayerByNameFromCombobox(self.dlg.ui.liTimemanagerLayers)
        if not layer:
            return False

        # Retrieve layer information
        layerName = layer.name()
        layerId = layer.id()
        startAttribute = self.dlg.ui.liTimemanagerStartAttribute.currentText()
        labelAttribute = self.dlg.ui.liTimemanagerLabelAttribute.currentText()
        group = str(self.dlg.ui.inTimemanagerGroup.text().encode('utf-8')).strip(' \t')
        groupTitle = str(self.dlg.ui.inTimemanagerGroupTitle.text().encode('utf-8')).strip(' \t')

        content = [layerName, startAttribute, labelAttribute, group, groupTitle, layerId]

        lblTableWidget = self.dlg.ui.twTimemanager
        twRowCount = lblTableWidget.rowCount()
        content.append(twRowCount) # store order
        colCount = len(content)

        if twRowCount < 10:
            # set new rowCount
            lblTableWidget.setRowCount(twRowCount + 1)
            lblTableWidget.setColumnCount(colCount)

            i=0
            for val in content:
                newItem = QTableWidgetItem(val)
                newItem.setFlags(Qt.ItemIsEnabled)
                lblTableWidget.setItem(twRowCount, i, newItem)
                i+=1
        lblTableWidget.setColumnHidden(colCount - 1, True)
        lblTableWidget.setColumnHidden(colCount - 2, True)


    def refreshLayerTree(self):
        '''Refresh the layer tree on user demand. Uses method populateLayerTree'''
        # Ask confirmation
        refreshIt = QMessageBox.question(
            self.dlg,
            QApplication.translate("lizmap", 'ui.msg.question.refresh.title'),
            QApplication.translate("lizmap", "ui.msg.question.refresh.content"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if refreshIt == QMessageBox.Yes:
            self.populateLayerTree()

    def setTreeItemData(self, itemType, itemKey, jsonLayers):
        '''Define default data or data from previous configuration for one item (layer or group)
        Used in the method populateLayerTree
        '''
        # Type : group or layer
        self.myDic[itemKey]['type'] = itemType

        # DEFAULT VALUES : generic default values for layers and group
        self.myDic[itemKey]['name'] = "%s" % itemKey
        for key, item in self.layerOptionsList.items():
            self.myDic[itemKey][key] = item['default']
        self.myDic[itemKey]['title'] = self.myDic[itemKey]['name']

        p = QgsProject.instance()
        embeddedGroups = self.embeddedGroups
        if itemType == 'group':
            # embedded group ?
            if embeddedGroups and embeddedGroups.has_key(itemKey):
                pName = embeddedGroups[itemKey]['project']
                pName = os.path.splitext(os.path.basename(pName))[0]
                self.myDic[itemKey]['sourceProject'] = pName

        # DEFAULT VALUES : layers have got more precise data
        keepMetadata = False
        if itemType == 'layer':

            # layer name
            layer = self.getQgisLayerById(itemKey)
            lname = '%s' % layer.name()
            self.myDic[itemKey]['name'] = layer.name()
            # title and abstract
            self.myDic[itemKey]['title'] = layer.name()
            if hasattr(layer, "title"): # only from qgis>=1.8
                if layer.title():
                    self.myDic[itemKey]['title'] = layer.title()
                    keepMetadata = True
                if layer.abstract():
                    self.myDic[itemKey]['abstract'] = layer.abstract()
                    keepMetadata = True

            # hide non geo layers (csv, etc.)
            #if layer.type() == 0:
            #    if layer.geometryType() == 4:
            #        self.ldisplay = False

            # layer scale visibility
            if layer.hasScaleBasedVisibility():
                self.myDic[itemKey]['minScale'] = layer.minimumScale()
                self.myDic[itemKey]['maxScale'] = layer.maximumScale()
            # toggled : check if layer is toggled in qgis legend
            self.myDic[itemKey]['toggled'] = self.iface.legendInterface().isLayerVisible(layer)
            # group as layer : always False obviously because it is already a layer
            self.myDic[itemKey]['groupAsLayer'] = False
            # embedded layer ?
            fromProject = p.layerIsEmbedded(itemKey)
            if os.path.exists(fromProject):
                pName = os.path.splitext(os.path.basename(fromProject))[0]
                self.myDic[itemKey]['sourceProject'] = pName


        # OVERRIDE DEFAULT FROM CONFIGURATION FILE
        if jsonLayers.has_key('%s' % self.myDic[itemKey]['name']):
            jsonKey = '%s' % self.myDic[itemKey]['name']
            # loop through layer options to override
            for key, item in self.layerOptionsList.items():
                # override only for ui widgets
                if item['widget']:
                    if jsonLayers[jsonKey].has_key(key):
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
                                if item.has_key('isMetadata'): # title and abstract
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
                    if jsonLayers[jsonKey].has_key(key):
                        self.myDic[itemKey][key] = jsonLayers[jsonKey][key]


    def populateLayerTree(self):
        '''Populate the layer tree of the Layers tab from Qgis legend interface
        Needs to be refactored.
        '''

        # initialize the tree
        myTree = self.dlg.ui.treeLayer
        myTree.clear()
        myTree.headerItem().setText(0, QApplication.translate( "lizmap", "layers.tree.title" ) )
        self.myDic = {}
        myGroups = self.iface.legendInterface().groups()

        # Check if a json configuration file exists (myproject.qgs.cfg)
        isok = 1
        p = QgsProject.instance()
        jsonFile = "%s.cfg" % p.fileName()
        jsonLayers = {}
        if os.path.exists(unicode(jsonFile)):
            f = open(jsonFile, 'r')
            jsonFileReader = f.read()
            try:
                sjson = json.loads(jsonFileReader)
                jsonLayers = sjson['layers']
            except:
                isok=0
                QMessageBox.critical(self.dlg, QApplication.translate("lizmap", "ui.msg.error.title"), (u""), QMessageBox.Ok)
                self.log(
                    QApplication.translate("lizmap", "ui.msg.error.tree.read.content"),
                    abort=True,
                    textarea=self.dlg.ui.outLog)
            finally:
                f.close()

        # Loop through groupLayerRelationship to reconstruct the tree
        for a in self.iface.legendInterface().groupLayerRelationship():
            # Initialize values
            parentItem = None
            myId = a[0]

            # Select an existing item, select the header item or create the item
            if myId in self.myDic:
                # If the item already exists in self.myDic, select it
                parentItem = self.myDic[myId]['item']
            elif myId == '':
                # If the id is empty string, this is a root layer, select the headerItem
                parentItem = myTree.headerItem()
            else:
                # else create the item and add it to the header item
                # add the item to the dictionary
                self.myDic[myId] = {'id' : myId}
                self.ldisplay = True
                if myId in myGroups:
                    # it is a group
                    self.setTreeItemData('group', myId, jsonLayers)
                else:
                    # it is a layer
                    self.setTreeItemData('layer', myId, jsonLayers)

                if self.ldisplay:

                    parentItem = QTreeWidgetItem(['%s' % unicode(self.myDic[myId]['name']), '%s' % unicode(self.myDic[myId]['id']), '%s' % self.myDic[myId]['type']])
                    myTree.addTopLevelItem(parentItem)
                    self.myDic[myId]['item'] = parentItem
                else:
                    del self.myDic[myId]

            # loop through the children and add children to the parent item
            for b in a[1]:
                self.myDic[b] = {'id' : b}
                self.ldisplay = True
                if b in myGroups:
                    # it is a group
                    self.setTreeItemData('group', b, jsonLayers)
                else:
                    # it is a layer
                    self.setTreeItemData('layer', b, jsonLayers)

                # add children item to its parent
                if self.ldisplay:
                    childItem = QTreeWidgetItem(['%s' % unicode(self.myDic[b]['name']), '%s' % unicode(self.myDic[b]['id']), '%s' % self.myDic[b]['type']])
                    if myId == '':
                        myTree.addTopLevelItem(childItem)
                    else:
                        parentItem.addChild(childItem)
                    self.myDic[b]['item'] = childItem
                else:
                    del self.myDic[b]
        myTree.expandAll()

        # Add the self.myDic to the global layerList dictionary
        self.layerList = self.myDic

        self.enableCheckBox(False)

    def setItemOptions(self):
        '''Restore layer/group input values when selecting a layer tree item'''
        # get the selected item
        item = self.dlg.ui.treeLayer.currentItem()
        if item:
            self.enableCheckBox(True)
        else:
            self.enableCheckBox(False)

        iKey = item.text(1)
        if self.layerList.has_key(iKey):
            # get information about the layer or the group from the layerList dictionary
            selectedItem = self.layerList[iKey]

            # set options
            for key,val in self.layerOptionsList.items():
                if val['widget']:
                    if val['wType'] in ('text', 'textarea'):
                        val['widget'].setText(selectedItem[key])
                    elif val['wType'] == 'spinbox':
                        val['widget'].setValue(int(selectedItem[key]))
                    elif val['wType'] == 'checkbox':
                        val['widget'].setChecked(selectedItem[key])
                    elif val['wType'] == 'list':
                        listDic = {val['list'][i]:i for i in range(0, len(val['list']))}
                        val['widget'].setCurrentIndex(listDic[selectedItem[key]])
            # deactivate popup configuration for groups
            isLayer = selectedItem['type'] == 'layer'
            self.dlg.ui.btConfigurePopup.setEnabled(isLayer)

        else:
            # set default values for this layer/group
            for key,val in self.layerOptionsList.items():
                if val['widget']:
                    if val['wType'] in ('text', 'textarea'):
                        val['widget'].setText(val['default'])
                    elif val['wType'] == 'spinbox':
                        val['widget'].setValue(val['default'])
                    elif val['wType'] == 'checkbox':
                        val['widget'].setChecked(val['default'])
                    elif val['wType'] == 'list':
                        listDic = {val['list'][i]:i for i in range(0, len(val['list']))}
                        val['widget'].setCurrentIndex(listDic[val['default']])


    def setLayerProperty(self, key, *args):
        '''
            Set a layer property in global self.layerList
            when the corresponding ui widget has sent changed signal
        '''
        key = str(key)
        # get the selected item in the layer tree
        item = self.dlg.ui.treeLayer.currentItem()
        # get the definition for this property
        layerOption = self.layerOptionsList[key]
        # modify the property for the selected item
        if item and self.layerList.has_key(item.text(1)):
            if layerOption['wType'] == 'text':
                self.layerList[item.text(1)][key] = layerOption['widget'].text()
                self.setLayerMeta(item, key)
            elif layerOption['wType'] == 'textarea':
                self.layerList[item.text(1)][key] = layerOption['widget'].toPlainText()
                self.setLayerMeta(item, key)
            elif layerOption['wType'] == 'spinbox':
                self.layerList[item.text(1)][key] = layerOption['widget'].value()
            elif layerOption['wType'] == 'checkbox':
                self.layerList[item.text(1)][key] = layerOption['widget'].isChecked()
            elif layerOption['wType'] == 'list':
                self.layerList[item.text(1)][key] = layerOption['list'][layerOption['widget'].currentIndex()]

            # Deactivate the "exclude" widget if necessary
            if (layerOption.has_key('exclude')
                and layerOption['wType'] == 'checkbox'
                and layerOption['widget'].isChecked()
                and layerOption['exclude']['widget'].isChecked()
            ):
                layerOption['exclude']['widget'].setChecked(False)
                self.layerList[item.text(1)][layerOption['exclude']['key']] = False



    def setLayerMeta(self, item, key):
        '''Set a the title/abstract Qgis metadata when corresponding item is changed
        Used in setLayerProperty'''
        if self.layerOptionsList[key].has_key('isMetadata'):
            # modify the layer.title|abstract() if possible (qgis >= 1.8)
            if self.layerList[item.text(1)]['type'] == 'layer':
                layer = self.getQgisLayerById(item.text(1))
                if layer:
                    if hasattr(layer, key):
                        if key == 'title':
                            layer.setTitle(u"%s" % self.layerList[item.text(1)][key])
                        if key == 'abstract':
                            layer.setAbstract(u"%s" % self.layerList[item.text(1)][key])


    def configurePopup(self):
        '''Open the dialog with a text field to store the popup template for one layer/group'''
        # get the selected item in the layer tree
        item = self.dlg.ui.treeLayer.currentItem()
        if item and self.layerList.has_key(item.text(1)):
            # do nothing if no popup configured for this layer/group
            if self.layerList[item.text(1)]['popup'] == 'False':
                return False

            # Import the code for the dialog
            from lizmappopupdialog import lizmapPopupDialog
            self.lizmapPopupDialog = lizmapPopupDialog()

            self.lizmapPopupDialog.ui.groupBox.setStyleSheet(self.STYLESHEET)
            self.lizmapPopupDialog.ui.groupBox_2.setStyleSheet(self.STYLESHEET)

            # Connect popup dialog signals and slots
            # When the plain text template is modified
            self.lizmapPopupDialog.ui.txtPopup.textChanged.connect(self.updatePopupHtml)
            # When the ui is closed with the x
            self.lizmapPopupDialog.rejected.connect(self.popupNotConfigured)
            # When the ui is closed with the OK button
            self.lizmapPopupDialog.ui.bbConfigurePopup.accepted.connect(self.popupConfigured)
            # When the ui is closed with the CANCEL button
            self.lizmapPopupDialog.ui.bbConfigurePopup.rejected.connect(self.popupNotConfigured)

            # Set the content of the QTextEdit if needed
            if self.layerList[item.text(1)].has_key('popupTemplate'):
                self.layerList[item.text(1)]['popup'] = True
                self.lizmapPopupDialog.ui.txtPopup.setText(self.layerList[item.text(1)]['popupTemplate'])
                self.lizmapPopupDialog.ui.htmlPopup.setHtml(self.layerList[item.text(1)]['popupTemplate'])

            # Show the popup configuration window
            self.lizmapPopupDialog.show()

    def updatePopupHtml(self):
        '''Update the html preview of the popup dialog from the plain text template text'''
        # Get the content
        popupContent = unicode(self.lizmapPopupDialog.ui.txtPopup.text())

        # Update html preview
        self.lizmapPopupDialog.ui.htmlPopup.setHtml(popupContent)

    def popupConfigured(self):
        '''Save the content of the popup template'''
        # Get the content before closing the dialog
        popupContent = unicode(self.lizmapPopupDialog.ui.txtPopup.text())

        # Close the popup dialog
        self.lizmapPopupDialog.close()

        # Get the selected item in the layer tree
        item = self.dlg.ui.treeLayer.currentItem()
        if item and self.layerList.has_key(item.text(1)):
            # Write the content into the global object
            self.layerList[item.text(1)]['popupTemplate'] = popupContent


    def popupNotConfigured(self):
        '''Popup configuration dialog has been close with cancel or x : do nothing'''
        self.lizmapPopupDialog.close()



    def writeProjectConfigFile(self):
        '''Get general project options and user edited layers options from plugin gui. Save them into the project.qgs.cfg config file in the project.qgs folder (json format)'''

        # get information from Qgis api
        r = QgsMapRenderer()
        # add all the layers to the renderer
        r.setLayerSet([a.id() for a in self.iface.legendInterface().layers()])
        # Get the project data
        p = QgsProject.instance()
        # options
        liz2json = {}
        liz2json["options"] = {}
        liz2json["layers"] = {}
        # projection
        # project projection
        mc = self.iface.mapCanvas()
        pCrs = mc.mapRenderer().destinationCrs()
        pAuthid = pCrs.authid()
        pProj4 = pCrs.toProj4()
        liz2json["options"]["projection"] = {}
        liz2json["options"]["projection"]["proj4"] = '%s' % pProj4
        liz2json["options"]["projection"]["ref"] = '%s' % pAuthid
        # wms extent
        pWmsExtent = p.readListEntry('WMSExtent','')[0]
        if len(pWmsExtent) > 1:
            bbox = eval('[%s, %s, %s, %s]' % (pWmsExtent[0],pWmsExtent[1],pWmsExtent[2],pWmsExtent[3]))
        else:
            bbox = []
        liz2json["options"]["bbox"] = bbox

        # set initialExtent values if not defined
        if not self.dlg.ui.inInitialExtent.text():
            self.setInitialExtentFromProject()

        # gui user defined options
        for key, item in self.globalOptions.items():
            if item['widget']:
                inputValue = None

                # Get field value depending on widget type
                if item['wType'] == 'text':
                    inputValue = str(item['widget'].text()).strip(' \t')

                if item['wType'] == 'textarea':
                    inputValue = str(item['widget'].toPlainText()).strip(' \t')

                if item['wType'] == 'spinbox':
                    inputValue = item['widget'].value()

                if item['wType'] == 'checkbox':
                    inputValue = str(item['widget'].isChecked())

                if item['wType'] == 'list':
                    listDic = {item['list'][i]:i for i in range(0, len(item['list']))}
                    inputValue = item['list'][item['widget'].currentIndex()]

                # Cast value depending of data type
                if item['type'] == 'string':
                    if item['wType'] in ('text', 'textarea'):
                        inputValue = unicode(inputValue)
                    else:
                        inputValue = str(inputValue)

                elif item['type'] in ('intlist', 'floatlist', 'list'):
                    if item['type'] in 'intlist':
                        inputValue = [int(a) for a in inputValue.split(', ') if a.isdigit()]
                    elif item['type'] == 'floatlist':
                        inputValue = [float(a) for a in inputValue.split(', ')]
                    else:
                        inputValue = [a for a in inputValue.split(', ')]

                elif item['type'] == 'integer':
                    try:
                        inputValue = int(inputValue)
                    except:
                        inputValue = int(item['default'])

                elif item['type'] == 'boolean':
                    inputValue = str(inputValue)

                # Add value to the option
                if (inputValue and inputValue != "False"):
                    liz2json["options"][key] = inputValue
                else:
                    if item.has_key('alwaysExport'):
                        liz2json["options"][key] = item['default']


        # list of layers for which to have the tool "locate by layer"
        lblTableWidget = self.dlg.ui.twLocateByLayerList
        twRowCount = lblTableWidget.rowCount()
        p = QgsProject.instance()
        wfsLayersList = p.readListEntry('WFSLayers','')[0]
        if twRowCount > 0:
            liz2json["locateByLayer"] = {}
            for row in range(twRowCount):
                # check that the layer is checked in the WFS capabilities
                layerId = str(lblTableWidget.item(row, 6).text())
                if layerId in wfsLayersList:
                    layerName = str(lblTableWidget.item(row, 0).text().encode('utf-8'))
                    fieldName = str(lblTableWidget.item(row, 1).text().encode('utf-8'))
                    filterFieldName = str(lblTableWidget.item(row, 2).text().encode('utf-8'))
                    displayGeom = str(lblTableWidget.item(row, 3).text())
                    minLength = str(lblTableWidget.item(row, 4).text())
                    filterOnLocate = str(lblTableWidget.item(row, 5).text())
                    layerId = str(lblTableWidget.item(row, 6).text().encode('utf-8'))
                    liz2json["locateByLayer"][layerName] = {}
                    liz2json["locateByLayer"][layerName]["fieldName"] = fieldName
                    if filterFieldName and filterFieldName != '--':
                        liz2json["locateByLayer"][layerName]["filterFieldName"] = filterFieldName
                    liz2json["locateByLayer"][layerName]["displayGeom"] = displayGeom
                    liz2json["locateByLayer"][layerName]["minLength"] = minLength and int(minLength) or 0
                    liz2json["locateByLayer"][layerName]["filterOnLocate"] = filterOnLocate
                    liz2json["locateByLayer"][layerName]["layerId"] = layerId
                    liz2json["locateByLayer"][layerName]["order"] = row

        # list of layers to display attribute table
        lblTableWidget = self.dlg.ui.twAttributeLayerList
        twRowCount = lblTableWidget.rowCount()
        if twRowCount > 0:
            liz2json["attributeLayers"] = {}
            for row in range(twRowCount):
                # check that the layer is checked in the WFS capabilities
                layerName = str(lblTableWidget.item(row, 0).text().encode('utf-8'))
                primaryKey = str(lblTableWidget.item(row, 1).text().encode('utf-8'))
                hiddenFields = str(lblTableWidget.item(row, 2).text().encode('utf-8'))
                pivot = str(lblTableWidget.item(row, 3).text())
                hideAsChild = str(lblTableWidget.item(row, 4).text())
                layerId = str(lblTableWidget.item(row, 5).text().encode('utf-8'))
                liz2json["attributeLayers"][layerName] = {}
                liz2json["attributeLayers"][layerName]["primaryKey"] = primaryKey
                liz2json["attributeLayers"][layerName]["hiddenFields"] = hiddenFields
                liz2json["attributeLayers"][layerName]["pivot"] = pivot
                liz2json["attributeLayers"][layerName]["hideAsChild"] = hideAsChild
                liz2json["attributeLayers"][layerName]["layerId"] = layerId
                liz2json["attributeLayers"][layerName]["order"] = row


        # list of layers to display tooltip
        lblTableWidget = self.dlg.ui.twTooltipLayerList
        twRowCount = lblTableWidget.rowCount()
        if twRowCount > 0:
            liz2json["tooltipLayers"] = {}
            for row in range(twRowCount):
                layerName = str(lblTableWidget.item(row, 0).text().encode('utf-8'))
                fields = str(lblTableWidget.item(row, 1).text().encode('utf-8'))
                displayGeom = str(lblTableWidget.item(row, 2).text())
                colorGeom = str(lblTableWidget.item(row, 3).text().encode('utf-8'))
                layerId = str(lblTableWidget.item(row, 4).text().encode('utf-8'))
                liz2json["tooltipLayers"][layerName] = {}
                liz2json["tooltipLayers"][layerName]["fields"] = fields
                liz2json["tooltipLayers"][layerName]["displayGeom"] = displayGeom
                liz2json["tooltipLayers"][layerName]["colorGeom"] = colorGeom
                liz2json["tooltipLayers"][layerName]["layerId"] = layerId
                liz2json["tooltipLayers"][layerName]["order"] = row

        # layer(s) for the edition tool
        lblTableWidget = self.dlg.ui.twEditionLayerList
        twRowCount = lblTableWidget.rowCount()
        if twRowCount > 0:
            liz2json["editionLayers"] = {}
            for row in range(twRowCount):
                # check that the layer is checked in the WFS capabilities
                layerName = str(lblTableWidget.item(row, 0).text().encode('utf-8'))
                createFeature = str(lblTableWidget.item(row, 1).text())
                modifyAttribute = str(lblTableWidget.item(row, 2).text())
                modifyGeometry = str(lblTableWidget.item(row, 3).text())
                deleteFeature = str(lblTableWidget.item(row, 4).text())
                layerId = str(lblTableWidget.item(row, 5).text().encode('utf-8'))
                layer = self.getQgisLayerById(layerId)
                geometryType = self.mapQgisGeometryType[layer.geometryType()]
                liz2json["editionLayers"][layerName] = {}
                liz2json["editionLayers"][layerName]["layerId"] = layerId
                liz2json["editionLayers"][layerName]["geometryType"] = geometryType
                liz2json["editionLayers"][layerName]["capabilities"] = {}
                liz2json["editionLayers"][layerName]["capabilities"]["createFeature"] = createFeature
                liz2json["editionLayers"][layerName]["capabilities"]["modifyAttribute"] = modifyAttribute
                liz2json["editionLayers"][layerName]["capabilities"]["modifyGeometry"] = modifyGeometry
                liz2json["editionLayers"][layerName]["capabilities"]["deleteFeature"] = deleteFeature
                liz2json["editionLayers"][layerName]["order"] = row


        # list of layers for which to have the tool "login filtered layer"
        lblTableWidget = self.dlg.ui.twLoginFilteredLayersList
        twRowCount = lblTableWidget.rowCount()
        if twRowCount > 0:
            liz2json["loginFilteredLayers"] = {}
            for row in range(twRowCount):
                # check that the layer is checked in the WFS capabilities
                layerName = str(lblTableWidget.item(row, 0).text().encode('utf-8'))
                filterAttribute = str(lblTableWidget.item(row, 1).text().encode('utf-8'))
                filterPrivate = str(lblTableWidget.item(row, 2).text())
                layerId = str(lblTableWidget.item(row, 3).text().encode('utf-8'))
                liz2json["loginFilteredLayers"][layerName] = {}
                liz2json["loginFilteredLayers"][layerName]["filterAttribute"] = filterAttribute
                liz2json["loginFilteredLayers"][layerName]["filterPrivate"] = filterPrivate
                liz2json["loginFilteredLayers"][layerName]["layerId"] = layerId
                liz2json["loginFilteredLayers"][layerName]["order"] = row


        # list of Lizmap external baselayers
        eblTableWidget = self.dlg.ui.twLizmapBaselayers
        twRowCount = eblTableWidget.rowCount()
        if twRowCount > 0:
            liz2json["lizmapExternalBaselayers"] = {}
            for row in range(twRowCount):
                # check that the layer is checked in the WFS capabilities
                lRepository = str(eblTableWidget.item(row, 0).text().encode('utf-8'))
                lProject = str(eblTableWidget.item(row, 1).text().encode('utf-8'))
                lName = str(eblTableWidget.item(row, 2).text().encode('utf-8'))
                lTitle = str(eblTableWidget.item(row, 3).text().encode('utf-8'))
                lImageFormat = str(eblTableWidget.item(row, 4).text().encode('utf-8'))
                if lImageFormat not in ('png', 'png; mode=16bit', 'png; mode=8bit', 'jpg', 'jpeg'):
                    lImageFormat = 'png'
                liz2json["lizmapExternalBaselayers"][lName] = {}
                liz2json["lizmapExternalBaselayers"][lName]["repository"] = lRepository
                liz2json["lizmapExternalBaselayers"][lName]["project"] = lProject
                liz2json["lizmapExternalBaselayers"][lName]["layerName"] = lName
                liz2json["lizmapExternalBaselayers"][lName]["layerTitle"] = lTitle
                liz2json["lizmapExternalBaselayers"][lName]["layerImageFormat"] = lImageFormat
                liz2json["lizmapExternalBaselayers"][lName]["order"] = row

        # list of timemanager layers
        lblTableWidget = self.dlg.ui.twTimemanager
        twRowCount = lblTableWidget.rowCount()
        if twRowCount > 0:
            liz2json["timemanagerLayers"] = {}
            for row in range(twRowCount):
                # check that the layer is checked in the WFS capabilities
                layerName = str(lblTableWidget.item(row, 0).text().encode('utf-8'))
                startAttribute = str(lblTableWidget.item(row, 1).text().encode('utf-8'))
                labelAttribute = str(lblTableWidget.item(row, 2).text().encode('utf-8'))
                tmGroup = str(lblTableWidget.item(row, 3).text().encode('utf-8'))
                tmGroupTitle = str(lblTableWidget.item(row, 4).text().encode('utf-8'))
                layerId = str(lblTableWidget.item(row, 5).text().encode('utf-8'))
                liz2json["timemanagerLayers"][layerName] = {}
                liz2json["timemanagerLayers"][layerName]["startAttribute"] = startAttribute
                if labelAttribute and labelAttribute != '--':
                    liz2json["timemanagerLayers"][layerName]["label"] = labelAttribute
                liz2json["timemanagerLayers"][layerName]["group"] = tmGroup
                liz2json["timemanagerLayers"][layerName]["groupTitle"] = tmGroupTitle
                liz2json["timemanagerLayers"][layerName]["layerId"] = layerId
                liz2json["timemanagerLayers"][layerName]["order"] = row


        # gui user defined layers options
        for k,v in self.layerList.items():
            addToCfg = True
            ltype = v['type']
            gal = v['groupAsLayer']
            geometryType = -1
            layer = False
            if gal:
                ltype = 'layer'
            else:
                ltype = 'group'
            if self.getQgisLayerById(k):
                ltype = 'layer'
                gal = True
            if ltype == 'layer':
                layer = self.getQgisLayerById(k)
                if layer:
                    if layer.type() == 0: # if it is a vector layer
                        geometryType = layer.geometryType()

            #~ # add layerOption only for geo layers
            #~ if geometryType != 4:
            layerOptions = {}
            layerOptions["id"] = unicode(k)
            layerOptions["name"] = unicode(v['name'])
            layerOptions["type"] = ltype

            # geometry type
            if geometryType != -1:
                layerOptions["geometryType"] = self.mapQgisGeometryType[layer.geometryType()]

            # extent
            if layer:
                lExtent = layer.extent()
                layerOptions["extent"] = eval(
                    '[%s, %s, %s, %s]' % (
                        lExtent.xMinimum(),
                        lExtent.yMinimum(),
                        lExtent.xMaximum(),
                        lExtent.yMaximum()
                    )
                )
                layerOptions['crs'] = layer.crs().authid()

            # styles
            if layer and hasattr(layer, 'styleManager'):
                lsm = layer.styleManager()
                ls  = lsm.styles()
                if len( ls ) > 1:
                    layerOptions['styles'] = ls


            # Loop through the layer options and set properties from the dictionary
            for key, val in self.layerOptionsList.items():
                propVal = v[key]
                if val['type'] == 'string':
                    if val['wType'] in ('text', 'textarea'):
                        propVal = unicode(propVal)
                    else:
                        propVal = str(propVal)
                elif val['type'] == 'integer':
                    propVal = int(propVal)
                elif val['type'] == 'boolean':
                    propVal = str(propVal)
                layerOptions[key] = propVal

            # Cache Metatile: unset metatileSize if empty
            # this is to avoid, but lizmap web client must change accordingly to avoid using empty metatileSize (2.2.0 does not handle it)
            import re
            p = re.compile('ab*')
            # unset metatileSize
            if not re.match('\d,\d', layerOptions['metatileSize']):
                del layerOptions['metatileSize']
            # unset cacheExpiration if False
            if layerOptions['cached'].lower() == 'false':
                del layerOptions['cacheExpiration']
            # unset popupTemplate if popup False
            if layerOptions['popup'].lower() == 'false':
                del layerOptions['popupTemplate']
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

            # Add external WMS options if needed
            if layer and hasattr(layer, 'providerType') \
            and layerOptions.has_key('externalWmsToggle') \
            and layerOptions['externalWmsToggle'].lower() == 'true':
                layerProviderKey = layer.providerType()
                # Only for layers stored in disk
                if layerProviderKey in ('wms'):
                    wmsParams = self.getLayerWmsParameters(layer)
                    if wmsParams:
                        layerOptions['externalAccess'] = wmsParams
                else:
                    layerOptions['externalWmsToggle'] = "False"


            # Add layer options to the json object
            liz2json["layers"]["%s" % unicode(v['name'])] = layerOptions

        # Write json to the cfg file
        jsonFileContent = json.dumps(
            liz2json,
            sort_keys=False,
            indent=4
        )

        # Get the project data
        p = QgsProject.instance()
        jsonFile = "%s.cfg" % p.fileName()
        f = open(jsonFile, 'w')
        f.write(jsonFileContent.encode('utf-8'))
        f.close()


    def getLayerWmsParameters(self, layer):
        '''
        Get WMS parameters for a raster WMS layers
        '''
        uri = layer.dataProvider().dataSourceUri()
        # avoid WMTS layers (not supported yet in Lizmap Web Client)
        if 'wmts' in uri or 'WMTS' in uri:
            return None

        # Split WMS parameters
        wmsParams = dict([ [b for b in a.split('=') ] for a in uri.split('&')])

        # urldecode WMS url
        wmsParams['url'] = urllib.unquote(wmsParams['url']).decode('utf8').replace('&&', '&').replace('==','=')

        return wmsParams


    def checkGlobalProjectOptions(self):
        ''' Checks that the needed options are correctly set : relative path, project saved, etc.'''

        isok = True;
        errorMessage = ''
        # Get the project data from api
        p = QgsProject.instance()
        if not p.fileName():
            errorMessage+= '* '+QApplication.translate("lizmap", "ui.msg.error.init.open.project")+'\n'
            isok = False

        # Check the project state (saved or not)
        if isok and p.isDirty():
            p.write()

        if isok:
            # Get the project folder
            projectDir, projectName = os.path.split(os.path.abspath('%s' % p.fileName()))

        if isok:
            # Check if Qgis/capitaliseLayerName is set
            s = QSettings()
            if s.value('Qgis/capitaliseLayerName') and s.value('Qgis/capitaliseLayerName', type=bool):
                errorMessage+= '* ' + QApplication.translate("lizmap", "ui.msg.error.project.option.capitalizeLayerName")+'\n'
                isok = False

        if isok:
            # Check relative/absolute path
            if p.readEntry('Paths', 'Absolute')[0] == 'true':
                errorMessage+= '* '+QApplication.translate("lizmap", "ui.msg.error.project.option.path.relative")+'\n'
                isok = False

            # check active layers path layer by layer
            layerSourcesOk = []
            layerSourcesBad = []
            mc = self.iface.mapCanvas()
            layerPathError = ''

            for i in range(mc.layerCount()):
                layerSource =    unicode('%s' % mc.layer( i ).source() )
                if not hasattr(mc.layer( i ), 'providerType'):
                    continue
                layerProviderKey = mc.layer( i ).providerType()
                # Only for layers stored in disk
                if layerProviderKey in ('delimitedtext', 'gdal', 'gpx', 'grass', 'grassraster', 'ogr'):
                    try:
                        relativePath = os.path.normpath(
                            os.path.relpath(os.path.abspath(layerSource), projectDir)
                        )
                        if not relativePath.startswith('../../') and not relativePath.startswith('..\\..\\'):
                            layerSourcesOk.append(os.path.abspath(layerSource))
                        else:
                            layerSourcesBad.append(layerSource)
                            layerPathError+='--> %s \n' % relativePath
                            isok = False
                    except:
                        isok = False
                        layerSourcesBad.append(layerSource)
                        layerPathError+='--> %s \n' % mc.layer( i ).name()

            if len(layerSourcesBad) > 0:
                errorMessage+= '* '+QApplication.translate("lizmap", "ui.msg.error.project.layers.path.relative {}").format(projectDir)+'\n'
                self.log(
                    QApplication.translate("lizmap", "ui.msg.error.project.layers.path.relative {}")
                    .format(projectDir) + str(layerSourcesBad),
                    abort=True,
                    textarea=self.dlg.ui.outLog)
                errorMessage+= layerPathError

            # check if a title has been given in the project OWS tab configuration
            # first set the WMSServiceCapabilities to true
            if not p.readEntry('WMSServiceCapabilities', "/")[1]:
                p.writeEntry('WMSServiceCapabilities', "/", "True")
            if p.readEntry('WMSServiceTitle','')[0] == u'':
                p.writeEntry('WMSServiceTitle', '', u'My QGIS project title')


            # check if a bbox has been given in the project OWS tab configuration
            pWmsExtentLe = p.readListEntry('WMSExtent','')
            pWmsExtent = pWmsExtentLe[0]
            fullExtent = self.iface.mapCanvas().extent()
            if len(pWmsExtent) < 1 :
                pWmsExtent.append(u'%s' % fullExtent.xMinimum())
                pWmsExtent.append(u'%s' % fullExtent.yMinimum())
                pWmsExtent.append(u'%s' % fullExtent.xMaximum())
                pWmsExtent.append(u'%s' % fullExtent.yMaximum())
                p.writeEntry('WMSExtent', '', pWmsExtent)
            else:
                if not pWmsExtent[0] or not pWmsExtent[1] or not pWmsExtent[2] or not pWmsExtent[3]:
                    pWmsExtent[0] = u'%s' % fullExtent.xMinimum()
                    pWmsExtent[1] = u'%s' % fullExtent.yMinimum()
                    pWmsExtent[2] = u'%s' % fullExtent.xMaximum()
                    pWmsExtent[3] = u'%s' % fullExtent.yMaximum()
                    p.writeEntry('WMSExtent', '', pWmsExtent)

        # Save project
        if p.isDirty():
            p.write()

        if not isok and errorMessage:
            QMessageBox.critical(
                self.dlg,
                QApplication.translate("lizmap", "ui.msg.error.title"),
                errorMessage,
                QMessageBox.Ok)

        return isok


    def getMapOptions(self):
        '''Check the user defined data from gui and save them to both global and project config files'''
        self.isok = 1
        # global project option checking
        isok = self.checkGlobalProjectOptions()

        if isok:
            # Get configuration from input fields

            # Need to get theses values to check for Pseudo Mercator projection
            in_osmMapnik = self.dlg.ui.cbOsmMapnik.isChecked()
            in_osmMapquest = self.dlg.ui.cbOsmMapquest.isChecked()
            in_osmCyclemap = self.dlg.ui.cbOsmCyclemap.isChecked()
            in_googleStreets = self.dlg.ui.cbGoogleStreets.isChecked()
            in_googleSatellite = self.dlg.ui.cbGoogleSatellite.isChecked()
            in_googleHybrid = self.dlg.ui.cbGoogleHybrid.isChecked()
            in_googleTerrain = self.dlg.ui.cbGoogleTerrain.isChecked()
            in_bingStreets = self.dlg.ui.cbBingStreets.isChecked()
            in_bingSatellite = self.dlg.ui.cbBingSatellite.isChecked()
            in_bingHybrid = self.dlg.ui.cbBingHybrid.isChecked()
            in_ignStreets = self.dlg.ui.cbIgnStreets.isChecked()
            in_ignSatellite = self.dlg.ui.cbIgnSatellite.isChecked()
            in_ignTerrain = self.dlg.ui.cbIgnTerrain.isChecked()
            in_ignCadastral = self.dlg.ui.cbIgnCadastral.isChecked()

            isok = True

            # log
            self.dlg.ui.outLog.append('=' * 20)
            self.dlg.ui.outLog.append(QApplication.translate("lizmap", "log.map.option.title"))
            self.dlg.ui.outLog.append('=' * 20)

            # Checking configuration data
            # Get the project data from api to check the "coordinate system restriction" of the WMS Server settings
            p = QgsProject.instance()

            # public baselayers: check that the 3857 projection is set in the "Coordinate System Restriction" section of the project WMS Server tab properties
            if in_osmMapnik or in_osmMapquest or in_osmCyclemap or in_googleStreets \
            or in_googleSatellite or in_googleHybrid or in_googleTerrain \
            or in_bingSatellite or in_bingStreets or in_bingHybrid \
            or in_ignSatellite or in_ignStreets or in_ignTerrain or in_ignCadastral:
                crsList = p.readListEntry('WMSCrsList','')
                pmFound = False
                for i in crsList[0]:
                    if i == 'EPSG:3857':
                        pmFound = True
                if not pmFound:
                    crsList[0].append('EPSG:3857')
                    p.writeEntry('WMSCrsList', '', crsList[0])
                    p.write()




            # list of layers for which to have the tool "locate by layer" set
            lblTableWidget = self.dlg.ui.twLocateByLayerList
            twRowCount = lblTableWidget.rowCount()
            wfsLayersList = p.readListEntry('WFSLayers','')[0]
            if twRowCount > 0:
                good = True
                for row in range(twRowCount):
                    # check that the layer is checked in the WFS capabilities
                    layerId = str(lblTableWidget.item(row, 6).text())
                    if layerId not in wfsLayersList:
                        good = False
                if not good:
                    self.log(
                        QApplication.translate("lizmap", "ui.msg.warning.toolLayer.notInWfs"),
                        abort=True,
                        textarea=self.dlg.ui.outLog)


            if self.isok:
                # write data in the lizmap json config file
                self.writeProjectConfigFile()
                self.log(
                    QApplication.translate("lizmap", "ui.msg.map.parameters.ok"),
                    abort=False,
                    textarea=self.dlg.ui.outLog)
                self.log(
                    QApplication.translate("lizmap", "ui.msg.configuration.save.ok"),
                    abort=False,
                    textarea=self.dlg.ui.outLog)
            else:
                QMessageBox.critical(
                    self.dlg,
                    QApplication.translate("lizmap", "ui.msg.error.title"),
                    QApplication.translate("lizmap", "ui.msg.map.parameters.bad"),
                    QMessageBox.Ok)

            self.dlg.ui.outState.setText('<font color="green"></font>')
            # Go to Log tab
            self.dlg.ui.tabWidget.setCurrentIndex(5)

            # Get and check map scales
            if self.isok:
                self.getMinMaxScales()

        return self.isok


    def getProjectEmbeddedGroup(self):
        '''
        Return a dictionary containing
        properties of each embedded group
        '''
        p = QgsProject.instance()
        if not p.fileName():
            return None

        projectPath = os.path.abspath('%s' % p.fileName())
        with open(projectPath, 'r') as f:
            arbre = ET.parse(f)
            lg = list(arbre.iter('legendgroup'))
            lge = dict([(a.attrib['name'],a.attrib) for a in lg if a.attrib.has_key('embedded')])
            return lge


    def warnOnClose(self):
        '''Method triggered when the user closes the lizmap dialog by pressing Esc or clicking the x button'''
        print "close"
        #~ self.writeProjectConfigFile()


    def test(self):
        '''Debug method'''
        self.log("test", abort=False, textarea=self.dlg.ui.outLog)
        QMessageBox.critical(self.dlg, "Lizmap debug", (u"test"), QMessageBox.Ok)


    def reinitDefaultProperties(self):
        for key in self.layersTable.keys():
            self.layersTable[key]['jsonConfig'] = {}


    def onProjectRead(self):
        '''
        Close Lizmap plugin when project is opened
        '''
        self.reinitDefaultProperties()
        self.dlg.close()

    def onNewProjectCreated(self):
        '''
        When the user opens a new project
        '''
        self.reinitDefaultProperties()
        self.dlg.close()



    def run(self):
        '''Plugin run method : launch the gui and some tests'''
        self.clock = time.clock()

        if self.dlg.isVisible():
            QMessageBox.warning(
                self.dlg,
                QApplication.translate("lizmap", "ui.msg.warning.title"),
                QApplication.translate("lizmap", "ui.msg.warning.window.opened"),
                QMessageBox.Ok)

        # show the dialog only if checkGlobalProjectOptions is true
        if not self.dlg.isVisible() and self.checkGlobalProjectOptions():
            self.dlg.show()

            # Fill the layer list for the locate by layer tool
            self.populateLayerCombobox(self.dlg.ui.liLocateByLayerLayers, 'vector')
            # Fill the layer list for the attribute layer tool
            self.populateLayerCombobox(self.dlg.ui.liAttributeLayer, 'vector')
            # Fill the layer list for the tooltip layer tool
            self.populateLayerCombobox(self.dlg.ui.liTooltipLayer, 'vector')
            # Fill the layers lists for the edition tool
            self.populateLayerCombobox(self.dlg.ui.liEditionLayer, 'vector', ['spatialite', 'postgres'])
            # Fill the layer list for the login filtered layers tool
            self.populateLayerCombobox(self.dlg.ui.liLoginFilteredLayerLayers, 'vector')
            # Fill the layer list for the login filtered layers tool
            self.populateLayerCombobox(self.dlg.ui.liTimemanagerLayers, 'vector')

            # Get config file data
            self.getConfig()

            self.layerList = {}

            # Get embedded groups
            self.embeddedGroups = self.getProjectEmbeddedGroup()

            # Fill the layer tree
            self.populateLayerTree()

            self.isok = 1

            result = self.dlg.exec_()
            # See if OK was pressed
            if result == 1:
                QMessageBox.warning(self.dlg, "Debug", ("Quit !"), QMessageBox.Ok)

