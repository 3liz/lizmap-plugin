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
from qgis.core import (QgsProject,
                       QgsMapLayer)

# import other needed tool
import os
import json
import collections



class LizmapConfigError(Exception):
    pass


class LizmapConfig:

    # Static data

    mapQgisGeometryType = {
        0 : 'point',
        1 : 'line',
        2 : 'polygon',
        3 : 'unknown',
        4 : 'none'
    }

    globalOptionDefinitions = {
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

    layerOptionDefinitions = {
        'title': {
            'wType': 'text', 'type': 'string', 'default':'', 'isMetadata':True
        },
        'abstract': {
            'wType': 'textarea', 'type': 'string', 'default': '', 'isMetadata':True
        },
        'link': {
            'wType': 'text', 'type': 'string', 'default': '', 'isMetadata':True
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
                'wType': 'text', 'type': 'string', 'default': '', '_api': False
        },
        'sourceProject': {
                'wType': 'text', 'type': 'string', 'default': '', '_api': False
        }
    }

    datavizOptionDefinitions = {
        'plotType' : {
            'wType': 'list', 'type': 'string', 'default': 'scatter',
            'list':['scatter', 'box', 'bar', 'histogram', 'pie', 'histogram2d', 'polar']
        }
    }

    def __init__(self, project, fix_json=False):
        """ Configuration setup

            :param fix_json: fix the json parsing,
                see https://github.com/3liz/lizmap-web-client/issues/925
        """
        if not isinstance(project, QgsProject):
            self.project = self._load_project(project)
        else:
            self.project = project

        self._WFSLayers = self.project.readListEntry('WFSLayers','')[0]
        self._layer_attributes = {}
        self._global_options   = {}
        self._layer_options    = {}
        self._fix_json         = fix_json

    def _load_project(self, path):
        """ Read a qgis project from path
        """
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        project = QgsProject()
        if not project.read(path):
            raise  LizmapConfigError("Error reading qgis project")
        return project

    def get_layer_by_name(self, name):
        """ Return a unique layer by its name
        """
        matches = self.project.mapLayersByName(name)
        if len(matches) > 0:
            return matches[0]

    def to_json(self, p_global_options=None, p_layer_options=None, p_attributes_options=None,
                      sort_keys=False,indent=4, **kwargs):
        """ Returns the lizmap JSON configuration
        """
        # Set the options from the default only if overriden or not defined
        if p_global_options is not None or len(self._global_options) == 0:
            self.set_global_options(p_global_options)

        if p_layer_options is not None or len(self._layer_options) == 0:
            self.set_layer_options(p_layer_options)

        if p_attributes_options:
            self.set_layer_attributes(p_attributes_options)

        config = {
            'options': self._global_options,
            'layers' : self._layer_options,
        }

        if len(self._layer_attributes):
            config['attributeLayers'] = self._layer_attributes

        if self._fix_json:
            # Fix https://github.com/3liz/lizmap-web-client/issues/925
            # copy config
            def map_dict( ob ):
                if isinstance(ob, collections.Mapping):
                    return {k: map_dict(v) for k, v in ob.items()}
                elif isinstance(ob,bool):
                    return str(ob)
                else:
                    return ob

            config = map_dict(config)

        # Write json to the cfg file
        jsonFileContent = json.dumps(config,sort_keys=sort_keys, indent=indent, **kwargs)
        return jsonFileContent

    def set_global_options(self, options):
        """ Set the global lizmap configuration options
        """
        # set defaults
        self._global_options = {}
        self._global_options.update((k,v['default']) for k,v in self.globalOptionDefinitions.items() if v.get('_api',True))

        # Set custom options
        if options is not None:
            self._global_options.update((k,v) for k,v in options.items() if k in self.globalOptionDefinitions)

        # projection
        # project projection
        pCrs = self.project.crs()
        self._global_options["projection"] = { "proj4": str(pCrs.toProj4()), "ref"  : str(pCrs.authid()) }
        # wms extent
        pWmsExtent = self.project.readListEntry('WMSExtent','')[0]
        if len(pWmsExtent) > 1:
            bbox = [pWmsExtent[0],pWmsExtent[1],pWmsExtent[2],pWmsExtent[3]]
        else:
            bbox = []
        self._global_options["bbox"] = bbox

        if self._global_options["initialExtent"] == []:
            self._global_options["initialExtent"] = bbox

    def add_layer( self, layer, **options ):
        """ Add a layer to the configuration

            Pass options as keyword arguments
        """
        lo = {}
        # lizmap default options for layer
        lo.update( (k,v['default']) for k,v in self.layerOptionDefinitions.items() if v.get('_api',True) )

        lo['title'] = layer.title() or layer.name()
        lo['abstract'] = layer.abstract()
        lo['type'] = 'layer'
        geometryType = '-1'
        if layer.type() == 0: # if it is a vector layer
            geometryType = self.mapQgisGeometryType[layer.geometryType()]
        if geometryType != -1:
            lo["geometryType"] = geometryType

        lExtent = layer.extent()
        lo["extent"] = [lExtent.xMinimum(),
                        lExtent.yMinimum(),
                        lExtent.xMaximum(),
                        lExtent.yMaximum()]

        lo['crs'] = layer.crs().authid()

        # styles
        if layer and hasattr(layer, 'styleManager'):
            ls = layer.styleManager().styles()
            if len( ls ) > 1:
                lo['styles'] = ls

        # Override with passed p_layer_options parameter
        lo.update( (k,v) for k,v in options if k in self.layerOptionDefinitions )

        # The folowing should not be overrided
        lo['id']   = layer.id()
        lo['name'] = layer.name()

        # Add metadata
        if layer.hasScaleBasedVisibility():
            lo['minScale'] = layer.minimumScale()
            lo['maxScale'] = layer.maximumScale()

        # set config
        lid = str(layer.name())
        self._layer_options[lid] = lo
        return lo

    def set_layer_options(self, p_layer_options=None ):
        """ Set the configuration options for the the project layers

            :param p_layer_options: dict of options for each layers
                    if p_layer options is None, add all layers otherwise add layer for
                    all layer names specified in p_layer_options
        """
        self._layer_options = {}

        if p_layer_options is None:
            for layer in self.project.mapLayers().values():
                self.add_layer( layer )
        else:
            for lname, options in p_layer_options.items():
                layer = self.get_layer_by_name(lname)
                if layer:
                    self.add_layer( layer, **options)

        return self._layer_options

    def hasWFSCapabilities( self, layer ):
        """ Test if layer has WFS capabilities
        """
        return layer.id() in self._WFSLayers

    def publish_layer_attribute_table(self, layer, primaryKey, hiddenFields=[], pivot=False, hideAsChild=False,
                                                   hideLayer=False, **kwargs ):
        """ publish attribute table
        """
        # Check that the layer has WFS enabled
        if not self.hasWFSCapabilities(layer):
            raise LizmapConfigError("WFS Required for layer %s" % layer.name())

        lyr_name  = layer.name()
        lyr_attrs = self._layer_attributes.get(lyr_name)
        if lyr_attrs is None:
            lyr_attrs = { 'order': len(self._layer_attributes) }

        lyr_attrs.update( primaryKey=primaryKey, hiddenFields=','.join(hiddenFields), pivot=pivot,
                          hideAsChild=hideAsChild, hideLayer=hideLayer,
                          layerId=layer.id())

        self._layer_attributes[lyr_name] = lyr_attrs
        return lyr_attrs

    def set_layer_attributes( self, p_attributes_options):
        """ Set the attribute options
        """
        self._layer_attributes = {}
        for lname, options in p_attributes_options.items():
            layer = self.get_layer_by_name(lname)
            if layer:
                self.publish_layer_attribute_table(layer, **options)

    def set_title( self, title ):
        """ Set WMS title
        """
        self.project.writeEntry( "WMSServiceTitle", "/", title)

    def set_description( self, description ):
        """ Set WMS description
        """
        self.project.writeEntry( "WMSServiceDescription", "/", description )
        self.project.setDirty()

    def set_wmsextent( self, xmin, ymin, xmax, ymax):
        """ Set WMS extent
        """
        self.project.writeEntry( "WMSExtent", "/", [str(xmin), str(ymin), str(xmax), str(ymax)])

    def configure_server_options(self, WMSTitle=None, WMSDescription=None, WFSLayersPrecision=6, WMSExtent=None):
        """ Configure server options for layers in the qgis project

            The method will set WMS/WMS publication options for the layers in the project
        """
        if WMSTitle is not None:
            self.set_title(WMSTitle)
        if WMSDescription is not None:
            self.set_description(WMSDescription)
        if WMSExtent is not None:
            self.set_wmsextent(*WMSExtent)

        prj = self.project

        prj.writeEntry( "WFSLayers", "/", [lid for lid,lyr in prj.mapLayers().items() if lyr.type() == QgsMapLayer.VectorLayer] )
        for lid,lyr in prj.mapLayers().items():
            if lyr.type() == QgsMapLayer.VectorLayer:
                prj.writeEntry( "WFSLayersPrecision", "/"+lid, WFSLayersPrecision )
        prj.writeEntry( "WCSLayers", "/", [lid for lid,lyr in prj.mapLayers().items() if lyr.type() == QgsMapLayer.RasterLayer] )
        prj.setDirty()

        # Update WFS layer list
        self._WFSLayers = prj.readListEntry('WFSLayers','')[0]

    def from_template(self, template, context = {}, **kwargs ):
        """ Read a configuration from a jinja2 template
        """
        # set context
        ctx = dict(context)
        layers = self.project.mapLayers().values()
        ctx['project'] = self.project
        ctx['layers']  = layers
        ctx['vectorlayers']  = [l for l in layers if l.type() == QgsMapLayer.VectorLayer]
        ctx['rasterlayers' ] = [l for l in layers if l.type() == QgsMapLayer.RasterLayer]
        rendered = template.render(ctx)
        with open("/srv/projects/test_lizmap_api/api_output.json","w") as fp:
            fp.write(rendered)
        options = json.loads(template.render(ctx))

        return self.to_json( options.get('options'), options.get('layers'), options.get('attributeLayers'),
                             **kwargs)



