"""
/***************************************************************************
 Lizmap_api
                                 Lizmap api
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
from qgis.core import QgsProject

# import other needed tool
import os
import json

class lizmap_config:

    # Static data

    mapQgisGeometryType = {
        0 : 'point',
        1 : 'line',
        2 : 'polygon',
        3 : 'unknown',
        4 : 'none'
    }

    globalOptions = {
        'mapScales': {
            'wType': 'text', 'type': 'intlist', 'default': [10000, 25000, 50000, 100000, 250000, 500000]
        },
        'minScale': {
            'wType': 'text', 'type': 'integer', 'default': 1
        },
        'maxScale': {
            'wType': 'text', 'type': 'integer', 'default': 1000000000
        },
        'acl': {
            'wType': 'text', 'type': 'list', 'default': []
        },
        'initialExtent': {
            'wType': 'text', 'type': 'floatlist', 'default': []
        },
        'googleKey': {
            'wType': 'text', 'type': 'string', 'default': ''
        },
        'googleHybrid' : {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },
        'googleSatellite' : {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },
        'googleTerrain' : {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },
        'googleStreets' : {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },
        'osmMapnik' : {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },
        'osmStamenToner' : {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },
        'bingKey': {
            'wType': 'text', 'type': 'string', 'default': ''
        },
        'bingStreets' : {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },
        'bingSatellite' : {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },
        'bingHybrid' : {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },
        'ignKey': {
            'wType': 'text', 'type': 'string', 'default': ''
        },
        'ignStreets' : {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },
        'ignSatellite' : {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },
        'ignTerrain' : {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },
        'ignCadastral' : {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },

        'hideGroupCheckbox' : {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },
        'popupLocation' : {
            'wType': 'list', 'type': 'string', 'default': 'dock', 'list':['dock', 'minidock', 'map', 'bottomdock', 'right-dock']
        },

        'print' : {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },
        'measure' : {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },
        'externalSearch' : {
            'wType': 'list', 'type': 'string', 'default': '', 'list':['', 'nominatim', 'google', 'ign']
        },
        'zoomHistory' : {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },
        'geolocation' : {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },
        'pointTolerance': {
            'wType': 'spinbox', 'type': 'integer', 'default': 25
        },
        'lineTolerance': {
            'wType': 'spinbox', 'type': 'integer', 'default': 10
        },
        'polygonTolerance': {
            'wType': 'spinbox', 'type': 'integer', 'default': 5
        },
        'hideHeader' : {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },
        'hideMenu' : {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },
        'hideLegend' : {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },
        'hideOverview' : {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },
        'hideNavbar' : {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },
        'hideProject': {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },
        'tmTimeFrameSize': {
            'wType': 'spinbox', 'type': 'integer', 'default': 10
        },
        'tmTimeFrameType' : {
            'wType': 'list', 'type': 'string', 'default': 'seconds',
            'list':['seconds', 'minutes', 'hours', 'days', 'weeks', 'months', 'years']
        },
        'tmAnimationFrameLength': {
            'wType': 'spinbox', 'type': 'integer', 'default': 1000
        },
        'emptyBaselayer': {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },
        'startupBaselayer' : {
            'wType': 'list', 'type': 'string', 'default': '', 'list':['']
        },
        'limitDataToBbox' : {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },
        'datavizLocation' : {
            'wType': 'list', 'type': 'string', 'default': 'dock', 'list':['dock', 'bottomdock', 'right-dock']
        },
        'datavizTemplate': {
            'wType': 'html', 'type': 'string', 'default': ''
        },
        'atlasEnabled' : {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },
        'atlasLayer': {
            'wType': 'layers', 'type': 'layer', 'default': '', 'list':[]
        },
        'atlasPrimaryKey': {
            'wType': 'fields', 'type': 'field', 'default': ''
        },
        'atlasDisplayLayerDescription' : {
            'wType': 'checkbox', 'type': 'boolean', 'default': True
        },
        'atlasFeatureLabel': {
            'wType': 'fields', 'type': 'field', 'default': ''
        },
        'atlasSortField': {
            'wType': 'fields', 'type': 'field', 'default': ''
        },
        'atlasHighlightGeometry' : {
            'wType': 'checkbox', 'type': 'boolean', 'default': True
        },
        'atlasZoom' : {
            'wType': 'list', 'type': 'string', 'default': 'zoom', 'list':['', 'zoom', 'center']
        },
        'atlasDisplayPopup' : {
            'wType': 'checkbox', 'type': 'boolean', 'default': True
        },
        'atlasTriggerFilter' : {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },
        'atlasShowAtStartup' : {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },
        'atlasAutoPlay' : {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },
        'atlasMaxWidth' : {
            'wType': 'spinbox', 'type': 'integer', 'default': 25
        },
        'atlasDuration' : {
            'wType': 'spinbox', 'type': 'integer', 'default': 5
        }
    }

    layerOptionsList = {
        'title': {
            'wType': 'text', 'type': 'string', 'default':'', 'isMetadata':True
        },
        'abstract': {
            'wType': 'textarea', 'type': 'string', 'default': '', 'isMetadata':True
        },
        'link': {
            'wType': 'text', 'type': 'string', 'default': ''
        },
        'minScale': {
            'wType': 'text', 'type': 'integer', 'default': 1
        },
        'maxScale': {
            'wType': 'text', 'type': 'integer', 'default': 1000000000000
        },
        'toggled': {
            'wType': 'checkbox', 'type': 'boolean', 'default': True
        },
        'popup': {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },
        'popupSource': {
            'wType': 'list', 'type': 'string', 'default': 'auto',
            'list':["auto", "lizmap", "qgis"]
        },
        'popupTemplate': {
            'wType': 'text', 'type': 'string', 'default': ''
        },
        'popupMaxFeatures': {
            'wType': 'spinbox', 'type': 'integer', 'default': 10
        },
        'popupDisplayChildren': {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },
        'noLegendImage': {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },
        'groupAsLayer': {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },
        'baseLayer': {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },
        'displayInLegend': {
            'wType': 'checkbox', 'type': 'boolean', 'default': True
        },
        'singleTile': {
            'wType': 'checkbox', 'type': 'boolean', 'default': True,
        },
        'imageFormat': {
            'wType': 'list', 'type': 'string', 'default': 'image/png',
            'list':["image/png", "image/png; mode=16bit", "image/png; mode=8bit", "image/jpeg"]
        },
        'cached': {
            'wType': 'checkbox', 'type': 'boolean', 'default': False,
        },
        'cacheExpiration': {
            'wType': 'spinbox', 'type': 'integer', 'default': 0
        },
        'metatileSize': {
            'wType': 'text', 'type': 'string', 'default': ''
        },
        'clientCacheExpiration': {
            'wType': 'spinbox', 'type': 'integer', 'default': 300
        },
        'externalWmsToggle': {
            'wType': 'checkbox', 'type': 'boolean', 'default': False
        },
        'sourceRepository': {
            'wType': 'text', 'type': 'string', 'default': ''
        },
        'sourceProject': {
            'wType': 'text', 'type': 'string', 'default': ''
        }
    }



    def __init__(self):

        self.lizmap_json_config = {}

    def get_json_config(self, project_path, p_global_options={}, p_layer_options={}):
        '''
        Returns the lizmap JSON configuration
        '''
        # Read the project
        self.project = None
        if not os.path.exists(project_path):
            return None

        from qgis.core import QgsProject
        p = QgsProject()
        pr = p.read(project_path)
        if not pr:
            return None
        self.project = p

        # Set the options from the default
        self.set_global_options(p_global_options)
        self.set_layer_options(p_layer_options)

        # Write json to the cfg file
        import json
        jsonFileContent = json.dumps(
            self.lizmap_json_config,
            sort_keys=False,
            indent=4
        )
        return jsonFileContent


    def set_global_options(self, p_global_options={}):
        '''
        Set the global lizmap configuration options
        '''
        if not self.project:
            return None

        # options
        self.lizmap_json_config["options"] = {}
        # projection
        # project projection

        pCrs = self.project.crs()
        pAuthid = pCrs.authid()
        pProj4 = pCrs.toProj4()

        self.lizmap_json_config["options"]["projection"] = {}
        self.lizmap_json_config["options"]["projection"]["proj4"] = '%s' % pProj4
        self.lizmap_json_config["options"]["projection"]["ref"] = '%s' % pAuthid
        # wms extent
        pWmsExtent = self.project.readListEntry('WMSExtent','')[0]
        if len(pWmsExtent) > 1:
            bbox = eval('[%s, %s, %s, %s]' % (pWmsExtent[0],pWmsExtent[1],pWmsExtent[2],pWmsExtent[3]))
        else:
            bbox = []
        self.lizmap_json_config["options"]["bbox"] = bbox

        # Set default
        for key, item in list(self.globalOptions.items()):
            # Add value to the option
            if key in p_global_options and p_global_options[key]:
                self.lizmap_json_config["options"][key] = p_global_options[key]
            else:
                self.lizmap_json_config["options"][key] = item['default']

    def set_layer_options(self, p_layer_options={}):
        '''
        Set the configuration options for all the project layers
        '''
        self.lizmap_json_config["layers"] = {}

        if not self.project:
            return None

        layers = {}
        for layer in self.project.mapLayers().values():
            lo = {}
            lo['id'] = layer.id()
            lo['name'] = layer.name()
            lo['title'] = layer.title()
            lo['abstract'] = layer.abstract()
            lo['type'] = 'layer'
            geometryType = '-1'
            if layer.type() == 0: # if it is a vector layer
                geometryType = self.mapQgisGeometryType[layer.geometryType()]
            if geometryType != -1:
                lo["geometryType"] = geometryType

            lExtent = layer.extent()
            lo["extent"] = eval(
                '[%s, %s, %s, %s]' % (
                    lExtent.xMinimum(),
                    lExtent.yMinimum(),
                    lExtent.xMaximum(),
                    lExtent.yMaximum()
                )
            )
            lo['crs'] = layer.crs().authid()

            # styles
            if layer and hasattr(layer, 'styleManager'):
                lsm = layer.styleManager()
                ls  = lsm.styles()
                if len( ls ) > 1:
                    lo['styles'] = ls

            # lizmap default options for layer
            for key, item in list(self.layerOptionsList.items()):
                lo[key] = item['default']

            # Add metadata
            if layer.hasScaleBasedVisibility():
                lo['minScale'] = layer.minimumScale()
                lo['maxScale'] = layer.maximumScale()

            # override with passed p_layer_options parameter
            lid = layer.name()
            for key, item in list(self.layerOptionsList.items()):
                if lid in p_layer_options and p_layer_options[lid]:
                    plo = p_layer_options[lid]
                    if key in plo and plo[key]:
                        # do not override some options ( must be set by QGIS
                        if key not in ('id', 'name', 'minScale', 'maxScale'):
                            lo[key] = plo[key]

            # set config
            self.lizmap_json_config['layers'][layer.name()] = lo


