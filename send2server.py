# -*- coding: utf-8 -*-
"""
/***************************************************************************
 send2server
                 A QGIS plugin
 Sends a local qgis project and related files to a qgismapserver server installation using FTP
                -------------------
    begin        : 2011-04-01
    copyright      : (C) 2011 by 3liz
    email        : mdouchin@3liz.org
 ***************************************************************************/

/***************************************************************************
 *                                     *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or   *
 *   (at your option) any later version.                   *
 *                                     *
 ***************************************************************************/
"""
# Import the PyQt and QGIS libraries
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from send2serverdialog import send2serverDialog
# import other needed tool
import sys, os, glob
# configuration parser
import ConfigParser
# json handling
import simplejson
# Importing SimpleFTPMirror class
from SimpleFTPMirror import *

class send2server:

  def __init__(self, iface):
    # Save reference to the QGIS interface
    self.iface = iface

  def initGui(self):
    # Create action that will start plugin configuration
    self.action = QAction(QIcon(":/plugins/send2server/icon.png"), \
      "send2server", self.iface.mainWindow())
    # connect the action to the run method
    QObject.connect(self.action, SIGNAL("triggered()"), self.run)

    # Add toolbar button and menu item
    self.iface.addToolBarIcon(self.action)
    self.iface.addPluginToMenu("&send2server", self.action)

  def unload(self):
    # Remove the plugin menu item and icon
    self.iface.removePluginMenu("&send2server",self.action)
    self.iface.removeToolBarIcon(self.action)
     
        
#  # Choose some directory from UI
#  def chooseLocalDirectory(self):
#    localDir = QFileDialog.getExistingDirectory( None,QString("Choose the local data folder"),"" )
#    if os.path.exists(unicode(localDir)):
#      self.dlg.ui.inLocaldir.setText(localDir)
    

  # Populate the Ftp configuration input from config file
  def getConfig(self):
    # Get the config file data
    cfg = ConfigParser.ConfigParser()
    configPath = os.path.expanduser("~/.qgis/python/plugins/send2server/send2server.cfg")
    cfg.read(configPath)
    self.dlg.ui.inHost.setText(cfg.get('Ftp', 'host'))
    self.dlg.ui.inUsername.setText(cfg.get('Ftp', 'username'))
    self.dlg.ui.inRemotedir.setText(cfg.get('Ftp', 'remotedir'))
    self.dlg.ui.inPort.setText(cfg.get('Ftp', 'port'))
    self.imageFormatDic = {'png' : 0, 'jpg' : 1}
    self.dlg.ui.liImageFormat.setCurrentIndex(self.imageFormatDic[cfg.get('Map', 'imageFormat')])
    self.dlg.ui.cbSingleTile.setChecked(cfg.get('Map', 'singleTile').lower() in ("yes", "true", "t", "1"))
    self.dlg.ui.inMinScale.setText(cfg.get('Map', 'minScale'))  
    self.dlg.ui.inMaxScale.setText(cfg.get('Map', 'maxScale')) 
    self.dlg.ui.inZoomLevelNumber.setText(cfg.get('Map', 'zoomLevelNumber'))
    self.dlg.ui.inMapScales.setText(cfg.get('Map', 'mapScales'))
    
    
    return True
    
  # Get a layer by its Id
  def getQgisLayerById(self, myId):
    for layer in self.iface.legendInterface().layers():
      if myId == layer.id():
        return layer
    return None

  # Populate the layer tree of the plugin from the legend
  def populateLayerTree(self):
    myTree = self.dlg.ui.treeLayer
    myTree.headerItem().setText(0, 'Liste des couches')
    myDic = {}
    myGroups = self.iface.legendInterface().groups()

    # Check if a *.qgs.cfg exists
    p = QgsProject.instance()
    jsonFile = "%s.cfg" % p.fileName()
    jsonLayers = {}
    if os.path.exists(unicode(jsonFile)):
      f = open(jsonFile, 'r')
      json = f.read()
      sjson = simplejson.loads(json)
      jsonLayers = sjson['layers']
#      self.dlg.ui.outLog.append(str(jsonLayers))
#      for k,v in sjson.items():
#        if k == 'layers':
#          for key,val in v.items():
#            self.dlg.ui.outLog.append(key)
      f.close()    
    
    for a in self.iface.legendInterface().groupLayerRelationship():
      # initialize values
      parentItem = None
      myId = a[0]
      
      # select an existing item, select the header item or create the item
      if myId in myDic:
        # if the item already exists in myDic, select it
        parentItem = myDic[myId]['item']
      elif myId == '':
        # if the id is empty string, this is a root layer, select the headerItem
        parentItem = myTree.headerItem()
      else:
        # else create the item and add it to the header item
        # add the item to the dictionary
        myDic[myId] = {'id' : myId}
        if myId in myGroups:
          # it's a group
          myDic[myId]['type'] = 'group'
          myDic[myId]['name'] = myId
          myDic[myId]['minScale'] = 1
          myDic[myId]['maxScale'] = 1000000000000
#          myDic[myId]['toggled'] = self.iface.legendInterface().isGroupVisible(myGroups.indexOf(myId))
          myDic[myId]['toggled'] = True # Method isGroupVisible not reliable, so set all to true
          if(jsonLayers.has_key('%s' % myId)):
            if jsonLayers['%s' % myId]['toggled'].lower() in ("yes", "true", "t", "1"):
              myDic[myId]['toggled'] = True
            else:
              myDic[myId]['toggled'] = False
              
          myDic[myId]['baseLayer'] = False
          if(jsonLayers.has_key('%s' % myId)):
            if jsonLayers['%s' % myId]['baseLayer'].lower() in ("yes", "true", "t", "1"):
              myDic[myId]['baseLayer'] = True
              
          myDic[myId]['groupAsLayer'] = False
          if(jsonLayers.has_key('%s' % myId)):
            if jsonLayers['%s' % myId]['type'] == 'layer':
              myDic[myId]['groupAsLayer'] = True
        else:
          # it's a layer
          myDic[myId]['type'] = 'layer'
          layer = self.getQgisLayerById(myId)
          myDic[myId]['name'] = layer.name()
          myDic[myId]['minScale'] = layer.minimumScale()
          myDic[myId]['maxScale'] = layer.maximumScale()
          
          myDic[myId]['toggled'] = self.iface.legendInterface().isLayerVisible(layer)
          if(jsonLayers.has_key('%s' % myId)):
            if jsonLayers['%s' % myId]['toggled'].lower() in ("yes", "true", "t", "1"):
              myDic[myId]['toggled'] = True
              
          myDic[myId]['baseLayer'] = False
          if(jsonLayers.has_key('%s' % myId)):
            if jsonLayers['%s' % myId]['baseLayer'].lower() in ("yes", "true", "t", "1"):
              myDic[myId]['baseLayer'] = True
              
          myDic[myId]['groupAsLayer'] = True
          
        myDic[myId]['title'] = myDic[myId]['name']
        myDic[myId]['abstract'] = ''
        if(jsonLayers.has_key('%s' % myId)):
          if jsonLayers['%s' % myId]['title'] != '':
            myDic[myId]['title'] = jsonLayers['%s' % myId]['title']
          if jsonLayers['%s' % myId]['abstract'] != '':
            myDic[myId]['abstract'] = jsonLayers['%s' % myId]['abstract']
          
        parentItem = QTreeWidgetItem(['%s' % unicode(myDic[myId]['name']), '%s' % unicode(myDic[myId]['id']), '%s' % myDic[myId]['type']])
        myTree.addTopLevelItem(parentItem)
        myDic[myId]['item'] = parentItem
      
      # loop through the children and add children to the parent item
      for b in a[1]:
        myDic[b] = {'id' : b}
        if b in myGroups:
          # it's a group
          myDic[b]['type'] = 'group'
          myDic[b]['name'] = b
          myDic[b]['minScale'] = 1
          myDic[b]['maxScale'] = 1000000000000
          
#          myDic[b]['toggled'] = self.iface.legendInterface().isGroupVisible(myGroups.indexOf(b))
          myDic[b]['toggled'] = True # Method isGroupVisible not reliable, so set all to true
          if(jsonLayers.has_key('%s' % b)):
            if jsonLayers['%s' % b]['toggled'].lower() in ("yes", "true", "t", "1"):
              myDic[b]['toggled'] = True
            else:
              myDic[b]['toggled'] = False
              
          myDic[b]['baseLayer'] = False
          if(jsonLayers.has_key('%s' % b)):
            if jsonLayers['%s' % b]['baseLayer'].lower() in ("yes", "true", "t", "1"):
              myDic[b]['baseLayer'] = True
              
          myDic[b]['groupAsLayer'] = False
          if(jsonLayers.has_key('%s' % b)):
            if jsonLayers['%s' % b]['type'] == 'layer':
              myDic[b]['groupAsLayer'] = True
        else:
          # it's a layer
          myDic[b]['type'] = 'layer'
          layer = self.getQgisLayerById(b)
          myDic[b]['name'] = layer.name()
          myDic[b]['minScale'] = layer.minimumScale()
          myDic[b]['maxScale'] = layer.maximumScale()
          
          myDic[b]['toggled'] = self.iface.legendInterface().isLayerVisible(layer)
          if(jsonLayers.has_key('%s' % b)):
            if jsonLayers['%s' % b]['toggled'].lower() in ("yes", "true", "t", "1"):
              myDic[b]['toggled'] = True
              
          myDic[b]['baseLayer'] = False
          if(jsonLayers.has_key('%s' % b)):
            if jsonLayers['%s' % b]['baseLayer'].lower() in ("yes", "true", "t", "1"):
              myDic[b]['baseLayer'] = True
              
          myDic[b]['groupAsLayer'] = True
          
        myDic[b]['title'] = myDic[b]['name']
        myDic[b]['abstract'] = ''
        if(jsonLayers.has_key('%s' % b)):
          if jsonLayers['%s' % b]['title'] != '':
            myDic[b]['title'] = jsonLayers['%s' % b]['title']
          if jsonLayers['%s' % b]['abstract'] != '':
            myDic[b]['abstract'] = jsonLayers['%s' % b]['abstract']
                    
        childItem = QTreeWidgetItem(['%s' % unicode(myDic[b]['name']), '%s' % unicode(myDic[b]['id']), '%s' % myDic[b]['type']])
        if myId == '':
          myTree.addTopLevelItem(childItem)
        else:
          parentItem.addChild(childItem)
        myDic[b]['item'] = childItem

    # Add the myDic to the global layerList dictionary
    self.layerList = myDic

    # Action on click
    QObject.connect(self.dlg.ui.treeLayer, SIGNAL("itemSelectionChanged()"), self.itemMetadata)
    QObject.connect(self.dlg.ui.inLayerTitle, SIGNAL("editingFinished()"), self.setLayerTitle)
    QObject.connect(self.dlg.ui.teLayerAbstract, SIGNAL("textChanged()"), self.setLayerAbstract)
    QObject.connect(self.dlg.ui.cbLayerIsBaseLayer, SIGNAL("stateChanged(int)"), self.setLayerIsBaseLayer)
    QObject.connect(self.dlg.ui.cbGroupAsLayer, SIGNAL("stateChanged(int)"), self.setGroupAsLayer)
    QObject.connect(self.dlg.ui.cbToggled, SIGNAL("stateChanged(int)"), self.setToggled)
    

  # Display metadata on click of a tree item in the layer tree
  def itemMetadata(self):
    # get the selected item
    item = self.dlg.ui.treeLayer.currentItem()
    # get information about the layer or the group
    selectedItem = self.layerList[item.text(1)]
    # set the title
    self.dlg.ui.inLayerTitle.setText(selectedItem['title'])
    # set the abstract
    self.dlg.ui.teLayerAbstract.setText(selectedItem['abstract'])
    # set the baseLayer
    self.dlg.ui.cbLayerIsBaseLayer.setChecked(selectedItem['baseLayer'])
    # set the groupAsLayer
    self.dlg.ui.cbGroupAsLayer.setChecked(selectedItem['groupAsLayer'])
    # set the toggled
    self.dlg.ui.cbToggled.setChecked(selectedItem['toggled'])     
      
  # Set a layer title when a item title is edited
  def setLayerTitle(self):
    # get the selected item
    item = self.dlg.ui.treeLayer.currentItem()
    # modify the title for the selected item
    self.layerList[item.text(1)]['title'] = self.dlg.ui.inLayerTitle.text()
    
  # Set a layer abstract when a item abstract is edited
  def setLayerAbstract(self):
    # get the selected item
    item = self.dlg.ui.treeLayer.currentItem()
    # modify the abstract for the selected item
    self.layerList[item.text(1)]['abstract'] = self.dlg.ui.teLayerAbstract.toPlainText()
    
  # Set a layer "IsBaseLayer" property when an item "Is Base layer" checkbox state has changed
  def setLayerIsBaseLayer(self):
    # get the selected item
    item = self.dlg.ui.treeLayer.currentItem()
    # modify the baseLayer property for the selected item
    self.layerList[item.text(1)]['baseLayer'] = self.dlg.ui.cbLayerIsBaseLayer.isChecked()
    
  # Set the "group as a layer" property when an item "Group As Layer" checkbox state has changed
  def setGroupAsLayer(self):
    # get the selected item
    item = self.dlg.ui.treeLayer.currentItem()
    self.layerList[item.text(1)]['groupAsLayer'] = self.dlg.ui.cbGroupAsLayer.isChecked()
    # modify the type property for the selected item
    if self.dlg.ui.cbGroupAsLayer.isChecked():
      self.layerList[item.text(1)]['type'] = 'layer'
      
  # Set a layer or group "toggled" property when an item "toggled" checkbox state has changed
  def setToggled(self):
    # get the selected item
    item = self.dlg.ui.treeLayer.currentItem()
    # modify the toggled property for the selected item
    self.layerList[item.text(1)]['toggled'] = self.dlg.ui.cbToggled.isChecked()
#    self.dlg.ui.outLog.append('%s : %s' % (item.text(1), str(self.dlg.ui.cbToggled.isChecked())))
    
  def layerListToJson(self):
    myJson = '{'
    
    # get information from Qgis api
    r = QgsMapRenderer()
    # add all the layers to the renderer
    r.setLayerSet([a.id() for a in self.iface.legendInterface().layers()])
    # Get the project data
    p = QgsProject.instance()
    # project projection
    mc = self.iface.mapCanvas()
    pSrs = mc.mapRenderer().destinationSrs()
    pAuthid = pSrs.authid()
    pProj4 = pSrs.toProj4()
    # wms extent
    pWmsExtent = p.readListEntry('WMSExtent','')[0]
    # options
    myJson+= '"options" : {'
    myJson+= '"projection" : {"proj4":"%s", "ref":"%s"},' % (pProj4, pAuthid)
#    myJson+= '"bbox":[%s,%s,%s,%s]' % (r.fullExtent().xMinimum(), r.fullExtent().yMinimum(), r.fullExtent().xMaximum(), r.fullExtent().yMaximum())
    if len(pWmsExtent) > 1:
      myJson+= '"bbox":[%s,%s,%s,%s],' % (pWmsExtent[0], pWmsExtent[1], pWmsExtent[2], pWmsExtent[3])
    else:
      myJson+= '"bbox":[],'
#    myJson+= ', "center" : {"lon":%s, "lat":%s}' % (r.fullExtent().center().x(), r.fullExtent().center().y())

    in_imageFormat = self.dlg.ui.liImageFormat.currentText()
    in_singleTile = self.dlg.ui.cbSingleTile.isChecked()
    in_minScale = self.dlg.ui.inMinScale.text()
    in_maxScale = self.dlg.ui.inMaxScale.text()
    in_zoomLevelNumber = self.dlg.ui.inZoomLevelNumber.text()
    in_mapScales = self.dlg.ui.inMapScales.text()
    myJson+= ' "imageFormat" : "image/%s", "singleTile" : "%s", "minScale" : %s, "maxScale" : %s, "zoomLevelNumber" : %s, "mapScales" : [%s]' % (in_imageFormat, in_singleTile, in_minScale, in_maxScale, in_zoomLevelNumber, in_mapScales)

    myJson+= '},'
    
    # layers
    myJson+= '"layers" : {'
    myVirg = ''
    for k,v in self.layerList.items():
      myJson+= '%s "%s" : {"id":"%s", "name":"%s", "type":"%s", "title":"%s", "abstract":"%s", "minScale":%d, "maxScale":%d, "toggled":"%s", "baseLayer":"%s"}' % (myVirg, unicode(v['name']), unicode(k), unicode(v['name']), v['type'], unicode(v['title']), unicode(v['abstract']), v['minScale'], v['maxScale'] , str(v['toggled']), str(v['baseLayer']) )
      myVirg = ','
    myJson+= '}'
    myJson+= '}'
    
    # Write json to the cfg file
    # Get the project data
    p = QgsProject.instance()
    jsonFile = "%s.cfg" % p.fileName()
    f = open(jsonFile, 'w')
#    f.write(unicode(myJson))    
    f.write(myJson.encode('utf-8'))
    f.close()


  # Save Qgis project
  def prepareSync(self):
    
    isok = True;
    
    # Get the project data
    p = QgsProject.instance()
    if not p.fileName():
      QMessageBox.critical(self.dlg, "Send2Server Error", ("You need to open a qgis project first."), QMessageBox.Ok)
      isok = False
      
    if isok:
      # Get the project folder
      projectDir, projectName = os.path.split(os.path.abspath(str(p.fileName())))
      self.dlg.ui.inLocaldir.setText(projectDir)
      
    # Check relative/absolute path    
    if isok and p.readEntry('Paths', 'Absolute')[0] == 'true':
      QMessageBox.critical(self.dlg, "Send2Server Error", ("The layers paths must be relative to the project file. Please change this options in the project settings."), QMessageBox.Ok)
      isok = False
      
    # check active layers path layer by layer
    layerSourcesOk = []
    layerSourcesBad = []
    mc = self.iface.mapCanvas()
    for i in range(mc.layerCount()):
      layerSource =  str(mc.layer( i ).source())
      if layerSource.startswith(projectDir) or layerSource.startswith('dbname='):
        layerSourcesOk.append(layerSource)
      else:
        layerSourcesBad.append(layerSource)
        isok = False
    if len(layerSourcesBad) > 0:
      QMessageBox.critical(self.dlg, "Send2Server Error", ("The layers paths must be relative to the project file. Please copy the layers inside \n%s.\n (see the log for detailed layers)" % projectDir), QMessageBox.Ok)
      log("The layers paths must be relative to the project file. Please copy the layers \n%s \ninside \n%s." % (str(layerSourcesBad), projectDir), abort=True, textarea=self.dlg.ui.outLog)
      
    # check if a bbox has been given
    pWmsExtent = p.readListEntry('WMSExtent','')[0]
    if len(pWmsExtent) <1 :
      QMessageBox.critical(self.dlg, "Send2Server Error", ("The project WMS extent must be set. Please change this options in the project settings."), QMessageBox.Ok)
      isok = False
      
    if isok:
      
      # Save the current project
      if p.isDirty():
        saveIt = QMessageBox.question(self.dlg, 'Send2server - Save current project ?', "Please save the current project before proceeding synchronisation. Save the project ?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if saveIt == QMessageBox.Yes:
          p.write()
        else:
          isOk = False
      
    return isok

    
  # Process the sync
  def processSync(self):
  
    # pre-sync checkings
    isok = self.prepareSync()
    
    if isok:
      letsGo = QMessageBox.question(self.dlg, 'Send2server - Send the current project to the server ?', "You are about to send your project file and all the data contained in :\n\n%s\n\n to the server directory  \n\nThis will remove every data in this remote directory which are not related to your current qgis project. Are you sure you want to proceed ?" % self.dlg.ui.inLocaldir.text(), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
      if letsGo == QMessageBox.Yes:
        isok = True
      else:
        isok = False
    
    if isok:
      # Get configuration from input fields
      # FTP
      in_username = self.dlg.ui.inUsername.text()
      in_password = self.dlg.ui.inPassword.text()
      in_account = ''
      in_host = self.dlg.ui.inHost.text()
      in_port = self.dlg.ui.inPort.text()
      in_localdir = self.dlg.ui.inLocaldir.text()
      in_remotedir = self.dlg.ui.inRemotedir.text()
      # Map
      in_imageFormat = self.dlg.ui.liImageFormat.currentText()
      in_singleTile = self.dlg.ui.cbSingleTile.isChecked()
      in_minScale = self.dlg.ui.inMinScale.text()
      in_maxScale = self.dlg.ui.inMaxScale.text()
      in_zoomLevelNumber = self.dlg.ui.inZoomLevelNumber.text()
      in_mapScales = self.dlg.ui.inMapScales.text()
      
      isok = True
      
      # log
      self.dlg.ui.outLog.append('=' * 20)
      self.dlg.ui.outLog.append('Checking configuration data')
      self.dlg.ui.outLog.append('=' * 20)
      
      # Checking configuration data
      # host
      if len(in_host) == 0:
        log('Missing hostname !', abort=True, textarea=self.dlg.ui.outLog)
      elif len(in_host) < 4:
        log('Incorrect hostname : %s !' % in_host, abort=True, textarea=self.dlg.ui.outLog)
      else:
        host = unicode(in_host)
        log('host = %s' % host, abort=False, textarea=self.dlg.ui.outLog)
        
      # port
      port = 21
      if len(in_port) > 0:
        try:
          port = int(in_port)
        except (ValueError, IndexError):
          port = 21
          self.dlg.ui.inPort.setText('21')
          
      log('port = %d' % port, abort=False, textarea=self.dlg.ui.outLog)
      
      # remote directory
      remotedir = os.path.normpath(unicode(in_remotedir))
      # windows bug
      remotedir.replace('\\', '/')
      if not str(remotedir).startswith('/'):
        remotedir = '/' + remotedir 
      log('remotedir = %s' % remotedir, abort=False, textarea=self.dlg.ui.outLog)
      
      # local directory    
      localdir = in_localdir
      if not os.path.isdir(localdir):
        log('Localdir does not exist: %s' % localdir, abort=True, textarea=self.dlg.ui.outLog)
      else:
        log('localdir = %s' % localdir, abort=False, textarea=self.dlg.ui.outLog)
      
      # username
      if len(in_username) > 0:
        username = unicode(in_username)
        log('username = %s' % username, abort=False, textarea=self.dlg.ui.outLog)
      else:
        log('Missing username !', abort=True, textarea=self.dlg.ui.outLog)
      
      # password  
      if len(in_password) > 0:
        password = unicode(in_password)
        log('password ok', abort=False, textarea=self.dlg.ui.outLog)
      else:
        log('Missing password !', abort=True, textarea=self.dlg.ui.outLog)
      
      # account  
      if len(in_account) > 0:
        account = in_account
  #      log('account = %' % accout, abort=False, textarea=self.dlg.ui.outLog)
      else:
        account = ''
        
      # Map config
      # image format
      if in_imageFormat == 'png' or in_imageFormat == 'jpg':
        imageFormat = in_imageFormat
#        log('password ok', abort=False, textarea=self.dlg.ui.outLog)
      else:
        log('Wrong image format !', abort=True, textarea=self.dlg.ui.outLog)
        
      # singletile
      singleTile = in_singleTile
      
      # minScale
      minScale = 1
      if len(in_minScale) > 0:
        try:
          minScale = int(in_minScale)
        except (ValueError, IndexError):
          self.dlg.ui.inMinScale.setText(minScale)   
      log('minScale = %d' % minScale, abort=False, textarea=self.dlg.ui.outLog)
      
      # maxScale
      maxScale = 1000000
      if len(in_maxScale) > 0:
        try:
          maxScale = int(in_maxScale)
        except (ValueError, IndexError):
          self.dlg.ui.inMaxScale.setText(maxScale)   
      log('maxScale = %d' % maxScale, abort=False, textarea=self.dlg.ui.outLog)
      
      # zoom levels number
      zoomLevelNumber = 10
      if len(in_zoomLevelNumber) > 0:
        try:
          zoomLevelNumber = int(in_zoomLevelNumber)
        except (ValueError, IndexError):
          self.dlg.ui.inZoomLevelNumber.setText(zoomLevelNumber)   
      log('zoomLevelNumber = %d' % zoomLevelNumber, abort=False, textarea=self.dlg.ui.outLog)
      
      if globals['isok']:
      
        # write data in the python plugin config file
        cfg = ConfigParser.ConfigParser()
        configPath = os.path.expanduser("~/.qgis/python/plugins/send2server/send2server.cfg")
        cfg.read(configPath)
        cfg.set('Ftp', 'host', host)
        cfg.set('Ftp', 'username', username)
        cfg.set('Ftp', 'port', port)
        cfg.set('Ftp', 'remotedir', in_remotedir)
        cfg.set('Map', 'imageFormat', in_imageFormat)
        cfg.set('Map', 'singleTile', in_singleTile)
        cfg.set('Map', 'minScale', in_minScale)
        cfg.set('Map', 'maxScale', in_maxScale)
        cfg.set('Map', 'zoomLevelNumber', in_zoomLevelNumber)
        cfg.set('Map', 'mapScales', in_mapScales)
        cfg.write(open(configPath,"w"))
        cfg.read(configPath)
      
        log('All the parameters are correctly set', abort=False, textarea=self.dlg.ui.outLog)
        
        # write data in the QgisWebClient json config file (to be send with the project file)
        self.layerListToJson()
        
        self.dlg.ui.outLog.append('')
        self.dlg.ui.outLog.append('=' * 20)
        self.dlg.ui.outLog.append('Synchronisation')
        self.dlg.ui.outLog.append('=' * 20)
        
        ftp = ftplib.FTP()
        # Connection to FTP host
        try:
          ftp.connect(host, port)
          ftp.login(username, password, account)
        except:
          log('Impossible to connect to %s:' % host, abort=True, textarea=self.dlg.ui.outLog)
        
        # Check that the remotedir exists  
        if globals['isok']:
          try:
            ftp.cwd(remotedir)
            log('Connected to FTP host. Remote dir access ok.', abort=False, textarea=self.dlg.ui.outLog)
          except ftplib.error_perm, err:
            if err[0].startswith('550'):
              log('Remotedir does not exist: %s' % remotedir, abort=False, textarea=self.dlg.ui.outLog)
              ftp.mkd(remotedir)
            else:
              raise
          ftp.cwd('/')
        
        # Process the sync
        if globals['isok']:
          # Get SimpleFTPMirror handlers
          local = localHandler(ftp, localdir)
          remote = remoteHandler(ftp, remotedir)
          subdir=''
          src_path = os.path.normpath('%s/%s' % (local.root, subdir))
          src_dirs, src_files = local.list(src_path)
          # Mirror the local directory to the remote
          action = 'store'
          if action == 'store':
            mirror(local, remote, subdir='', textarea=self.dlg.ui.outLog)
          elif action == 'retrieve':
            mirror(remote, local, subdir='', textarea=self.dlg.ui.outLog)
          elif action == 'remove':
            remove(remote)
          elif action == 'info':
            info(remote)
            ftp.quit()
            return
          
          ftp.quit()

        # Final log
        if globals['isok']:
          status = globals['status']
          status['time_finished'] = datetime.datetime.now()
          self.dlg.ui.outLog.append('\n')
          self.dlg.ui.outLog.append('=' * 20)
          self.dlg.ui.outLog.append('Processing Summary')
          self.dlg.ui.outLog.append('=' * 20)
          self.dlg.ui.outLog.append('%-10s%10s' % ('Directories created', status['dirs_created']))
          self.dlg.ui.outLog.append('%-10s%10s' % ('Directories removed', status['dirs_removed']))
          self.dlg.ui.outLog.append('%-10s%10s' % ('Directories total', status['dirs_total']))
          self.dlg.ui.outLog.append('%-10s%10s' % ('Files created', status['files_created']))
          self.dlg.ui.outLog.append('%-10s%10s' % ('Files updated', status['files_updated']))
          self.dlg.ui.outLog.append('%-10s%10s' % ('Files removed', status['files_removed']))
          self.dlg.ui.outLog.append('%-10s%10s' % ('Files total', status['files_total']))
          self.dlg.ui.outLog.append('%-10s%10s' % ('Bytes transfered', strfbytes(status['bytes_transfered'])))
          self.dlg.ui.outLog.append('%-10s%10s' % ('Bytes total', strfbytes(status['bytes_total'])))
          self.dlg.ui.outLog.append('%-10s%10s' % ('Time started', status['time_started']))
          self.dlg.ui.outLog.append('%-10s%10s' % ('Time finished', status['time_finished']))
          self.dlg.ui.outLog.append('%-10s%10s' % ('Duration', status['time_finished']-status['time_started']))
          
          self.dlg.ui.outLog.append('=' * 20)
          self.dlg.ui.outLog.append('WMS URL')
          self.dlg.ui.outLog.append('=' * 20)
          self.dlg.ui.outLog.append('Fast CGI (needs Apache reload) = http://%s/cgi-bin/qgis_mapserv.fcgi?map=/home/%s%s' % (host, username, remotedir))
          self.dlg.ui.outLog.append('simple CGI (no reload needed) = http://%s/cgi-bin/qgis_mapserv.cgi?map=/home/%s%s' % (host, username, remotedir))

          self.dlg.ui.outLog.append('')
        
        globals['isok'] = 1

      else:
        QMessageBox.critical(self.dlg, "Error", ("Wrong parameters : please read the log and correct the printed errors"), QMessageBox.Ok)
        globals['isok'] = 1
      

  # run method
  def run(self):

    # create and show the dialog
    self.dlg = send2serverDialog()
    # show the dialog
    self.dlg.show()
    
    # Get config file data and set the Ftp Configuration input fields
    self.getConfig()
    
    self.layerList = {}
    
    # Fill the layer tree
    self.populateLayerTree()
    
    # pre-sync checkings
    prepareSync = self.prepareSync()
    
    # connect signals and functions
    # synchronize button clicked
    QObject.connect(self.dlg.ui.btSync, SIGNAL("clicked()"), self.processSync)
    # clear log button clicked
    QObject.connect(self.dlg.ui.btClearlog, SIGNAL("clicked()"), self.dlg.ui.outLog.clear)

    
    
    
    result = self.dlg.exec_()
    # See if OK was pressed
    if result == 1: 
      QMessageBox.warning(self.dlg, "Debug", ("Voulez allez quitter le plugin !"), QMessageBox.Ok)
