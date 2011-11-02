# -*- coding: utf-8 -*-

"""
/***************************************************************************
 Lizmap
                 A QGIS plugin
 Publication plugin for Lizmap web application, by 3liz.com
                -------------------
    begin        : 2011-04-01
    copyright      : (C) 2011 by 3liz
    email        : mdouchin@3liz.com
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
from lizmapdialog import lizmapDialog
# import other needed tool
import sys, os, glob
# ftp lib
import ftplib
# configuration parser
import ConfigParser
# date and time
import time, datetime
# json handling
import simplejson
# supprocess module, to load external command line tools
import subprocess

class lizmap:

  def __init__(self, iface):
    '''Save reference to the QGIS interface'''
    self.iface = iface

  def initGui(self):
    '''Create action that will start plugin configuration'''
    self.action = QAction(QIcon(":/plugins/lizmap/icon.png"), \
      "lizmap", self.iface.mainWindow())
    # connect the action to the run method
    QObject.connect(self.action, SIGNAL("triggered()"), self.run)

    # Add toolbar button and menu item
    self.iface.addToolBarIcon(self.action)
    self.iface.addPluginToMenu("&lizmap", self.action)


  def unload(self):
    '''Remove the plugin menu item and icon'''
    self.iface.removePluginMenu("&lizmap",self.action)
    self.iface.removeToolBarIcon(self.action)


  def log(self,msg, level=1, abort=False, textarea=False):
    '''Log the actions and errors and optionnaly print them in given textarea'''
    if abort:
      sys.stdout = sys.stderr
    if textarea:
      textarea.append(msg)
    if abort:
      self.isok = 0
      
  def clearLog(self):
    '''Clear the content of the textarea log'''
    self.dlg.ui.outLog.clear()
    self.dlg.ui.progressBar.setValue(0)
    self.dlg.ui.outState.setText('<font color="green"></font>')
    self.dlg.ui.outSyncCommand.setText('')




  def getConfig(self):
    ''' Get the saved configuration from lizmap.cfg file and from the projet.qgs.cfg config file. Populate the gui fields accordingly'''
    
    # Get the global config file 
    cfg = ConfigParser.ConfigParser()
    configPath = os.path.expanduser("~/.qgis/python/plugins/lizmap/lizmap.cfg")
    cfg.read(configPath)
    
    # Set the FTP tab fields values
    self.dlg.ui.inHost.setText(cfg.get('Ftp', 'host'))
    self.dlg.ui.inUsername.setText(cfg.get('Ftp', 'username'))
#    self.dlg.ui.inPassword.setText(cfg.get('Ftp', 'password'))
    self.dlg.ui.inRemotedir.setText(cfg.get('Ftp', 'remotedir'))
    self.dlg.ui.inPort.setText(cfg.get('Ftp', 'port'))

    # Get the project config file (projectname.qgs.cfg)
    p = QgsProject.instance()
    jsonFile = "%s.cfg" % p.fileName()
    jsonOptions = {}
    if os.path.exists(unicode(jsonFile)):
      f = open(jsonFile, 'r')
      json = f.read()
      try:
        sjson = simplejson.loads(json)
        jsonOptions = sjson['options']
      except:
        isok=0
        QMessageBox.critical(self.dlg, "Lizmap error", (u"Errors encoutered while reading the last layer tree state. Please re-configure completely the options in the Layers tab "), QMessageBox.Ok)
        self.log(u"Errors encoutered while reading the last layer tree state. Please re-configure completely the options in the Layers tab", abort=True, textarea=self.dlg.ui.outLog)
    
    # Set the Map options tab fields values
    self.imageFormatDic = {'image/png' : 0, 'image/jpg' : 1}
    if jsonOptions.has_key('imageFormat'):
      self.dlg.ui.liImageFormat.setCurrentIndex(self.imageFormatDic[jsonOptions['imageFormat']])
    if jsonOptions.has_key('minScale'):
      self.dlg.ui.inMinScale.setText(str(jsonOptions['minScale']))
    if jsonOptions.has_key('maxScale'):
      self.dlg.ui.inMaxScale.setText(str(jsonOptions['maxScale'])) 
    if jsonOptions.has_key('zoomLevelNumber'):
      self.dlg.ui.inZoomLevelNumber.setText(str(jsonOptions['zoomLevelNumber']))
    if jsonOptions.has_key('mapScales'):
      self.dlg.ui.inMapScales.setText(", ".join(map(str, jsonOptions['mapScales'])))
        
    return True
    

    
  def getQgisLayerById(self, myId):
    '''Get a QgsLayer by its Id'''
    for layer in self.iface.legendInterface().layers():
      if myId == layer.id():
        return layer
    return None



  def populateLayerTree(self):
    '''Populate the layer tree of the Layers tab from Qgis legend interface'''
    myTree = self.dlg.ui.treeLayer
    myTree.clear()
    myTree.headerItem().setText(0, 'List of layers')
    myDic = {}
    myGroups = self.iface.legendInterface().groups()

    # Check if a *.qgs.cfg exists
    isok = 1
    p = QgsProject.instance()
    jsonFile = "%s.cfg" % p.fileName()
    jsonLayers = {}
    if os.path.exists(unicode(jsonFile)):
      f = open(jsonFile, 'r')
      json = f.read()
      try:
        sjson = simplejson.loads(json)
        jsonLayers = sjson['layers']
      except:
        isok=0
        QMessageBox.critical(self.dlg, "Lizmap Error", (u"Errors encoutered while reading the last layer tree state. Please re-configure completely the options in the Layers tab "), QMessageBox.Ok)
        self.log(u"Errors encoutered while reading the last layer tree state. Please re-configure completely the options in the Layers tab", abort=True, textarea=self.dlg.ui.outLog)
      f.close()    
    
    # Loop through groupLayerRelationship to reconstruct the tree
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
          lname = myId
          myDic[myId]['type'] = 'group'
          myDic[myId]['name'] = myId
          myDic[myId]['minScale'] = 1
          myDic[myId]['maxScale'] = 1000000000000
#          myDic[myId]['toggled'] = self.iface.legendInterface().isGroupVisible(myGroups.indexOf(myId))
          myDic[myId]['toggled'] = True # Method isGroupVisible not reliable, so set all to true
          myDic[myId]['baseLayer'] = False
          myDic[myId]['groupAsLayer'] = False
          myDic[myId]['singleTile'] = False
          myDic[myId]['cached'] = False
          
          # if the there are configuration for myid
          if jsonLayers.has_key('%s' % myId):
            if jsonLayers['%s' % myId].has_key('toggled'):
              if jsonLayers['%s' % myId]['toggled'].lower() in ("yes", "true", "t", "1"):
                myDic[myId]['toggled'] = True
                        
            if jsonLayers['%s' % myId].has_key('baseLayer'):
              if jsonLayers['%s' % myId]['baseLayer'].lower() in ("yes", "true", "t", "1"):
                myDic[myId]['baseLayer'] = True
              
            if jsonLayers['%s' % myId].has_key('groupAsLayer'):
              if jsonLayers['%s' % myId]['type'] == 'layer':
                myDic[myId]['groupAsLayer'] = True

            if jsonLayers['%s' % myId].has_key('singleTile'):
              if jsonLayers['%s' % myId]['singleTile'].lower() in ("yes", "true", "t", "1"):
                myDic[myId]['singleTile'] = True

            if jsonLayers['%s' % myId].has_key('cached'):
              if jsonLayers['%s' % myId]['cached'].lower() in ("yes", "true", "t", "1"):
                myDic[myId]['cached'] = True
        else:
          # it's a layer
          myDic[myId]['type'] = 'layer'
          layer = self.getQgisLayerById(myId)
          lname = '%s' % layer.name()
          myDic[myId]['name'] = layer.name()
          if layer.hasScaleBasedVisibility():
            myDic[myId]['minScale'] = layer.minimumScale()
            myDic[myId]['maxScale'] = layer.maximumScale()
          else:
            myDic[myId]['minScale'] = 1
            myDic[myId]['maxScale'] = 1000000000000           
          
          myDic[myId]['toggled'] = self.iface.legendInterface().isLayerVisible(layer)
          myDic[myId]['baseLayer'] = False
          myDic[myId]['groupAsLayer'] = True
          myDic[myId]['singleTile'] = False
          myDic[myId]['cached'] = False
          
          # if the there are configuration for lname
          if jsonLayers.has_key('%s' % lname):
            if jsonLayers['%s' % lname].has_key('toggled'):
              if jsonLayers['%s' % lname]['toggled'].lower() in ("yes", "true", "t", "1"):
                myDic[myId]['toggled'] = True
                
            if jsonLayers['%s' % lname].has_key('baseLayer'):
              if jsonLayers['%s' % lname]['baseLayer'].lower() in ("yes", "true", "t", "1"):
                myDic[myId]['baseLayer'] = True
                     
            if jsonLayers['%s' % lname].has_key('singleTile'):
              if jsonLayers['%s' % myId]['singleTile'].lower() in ("yes", "true", "t", "1"):
                myDic[myId]['singleTile'] = True

            if jsonLayers['%s' % lname].has_key('cached'):
              if jsonLayers['%s' % myId]['cached'].lower() in ("yes", "true", "t", "1"):
                myDic[myId]['cached'] = True
          
        myDic[myId]['title'] = myDic[myId]['name']
        myDic[myId]['abstract'] = ''
        myDic[myId]['link'] = ''
        if(jsonLayers.has_key('%s' % lname)):
          if jsonLayers['%s' % lname].has_key('title') and jsonLayers['%s' % myId]['title'] != '':
            myDic[myId]['title'] = jsonLayers['%s' % myId]['title']
          if jsonLayers['%s' % lname].has_key('abstract') and jsonLayers['%s' % myId]['abstract'] != '':
            myDic[myId]['abstract'] = jsonLayers['%s' % myId]['abstract']
          if jsonLayers['%s' % lname].has_key('link') and jsonLayers['%s' % myId]['link'] != '':
            myDic[myId]['link'] = jsonLayers['%s' % myId]['link']
          
        parentItem = QTreeWidgetItem(['%s' % unicode(myDic[myId]['name']), '%s' % unicode(myDic[myId]['id']), '%s' % myDic[myId]['type']])
        myTree.addTopLevelItem(parentItem)
        myDic[myId]['item'] = parentItem
      
      # loop through the children and add children to the parent item
      for b in a[1]:
        myDic[b] = {'id' : b}
        if b in myGroups:
          # it's a group
          lname = '%s' % b
          myDic[b]['type'] = 'group'
          myDic[b]['name'] = b
          myDic[b]['minScale'] = 1
          myDic[b]['maxScale'] = 1000000000000
          
#          myDic[b]['toggled'] = self.iface.legendInterface().isGroupVisible(myGroups.indexOf(b))
          myDic[b]['toggled'] = True # Method isGroupVisible seems to be not reliable, so set all to true
          myDic[b]['baseLayer'] = False
          myDic[b]['groupAsLayer'] = False
          myDic[b]['singleTile'] = False
          myDic[b]['cached'] = False
          
          # if the there are configuration for b
          if jsonLayers.has_key('%s' % b):
            if jsonLayers['%s' % b].has_key('toggled'):
              if jsonLayers['%s' % b]['toggled'].lower() in ("yes", "true", "t", "1"):
                myDic[b]['toggled'] = True
              else:
                myDic[b]['toggled'] = False
                
            if jsonLayers['%s' % b].has_key('baseLayer'):
              if jsonLayers['%s' % b]['baseLayer'].lower() in ("yes", "true", "t", "1"):
                myDic[b]['baseLayer'] = True
                
            if jsonLayers['%s' % b].has_key('groupAsLayer'):
              if jsonLayers['%s' % b]['type'] == 'layer':
                myDic[b]['groupAsLayer'] = True
                
            if jsonLayers['%s' % b].has_key('singleTile'):
              if jsonLayers['%s' % b]['singleTile'].lower() in ("yes", "true", "t", "1"):
                myDic[b]['singleTile'] = True

            if jsonLayers['%s' % b].has_key('cached'):
              if jsonLayers['%s' % b]['cached'].lower() in ("yes", "true", "t", "1"):
                myDic[b]['cached'] = True
        else:
          # it's a layer
          myDic[b]['type'] = 'layer'
          layer = self.getQgisLayerById(b)
          lname = '%s' % layer.name()
          myDic[b]['name'] = layer.name()
          if layer.hasScaleBasedVisibility():
            myDic[b]['minScale'] = layer.minimumScale()
            myDic[b]['maxScale'] = layer.maximumScale()
          else:
            myDic[b]['minScale'] = 1
            myDic[b]['maxScale'] = 1000000000000   
          
          myDic[b]['toggled'] = self.iface.legendInterface().isLayerVisible(layer)
          myDic[b]['baseLayer'] = False
          myDic[b]['groupAsLayer'] = True
          myDic[b]['singleTile'] = False
          myDic[b]['cached'] = False
          
          # if the there are configuration for lname
          if jsonLayers.has_key('%s' % lname):
            if jsonLayers['%s' % lname].has_key('toggled'):
              if jsonLayers['%s' % lname]['toggled'].lower() in ("yes", "true", "t", "1"):
                myDic[b]['toggled'] = True
                
            if jsonLayers['%s' % lname].has_key('baseLayer'):
              if jsonLayers['%s' % lname]['baseLayer'].lower() in ("yes", "true", "t", "1"):
                myDic[b]['baseLayer'] = True
                
            if jsonLayers['%s' % lname].has_key('singleTile'):
              if jsonLayers['%s' % lname]['singleTile'].lower() in ("yes", "true", "t", "1"):
                myDic[b]['singleTile'] = True

            if jsonLayers['%s' % lname].has_key('cached'):
              if jsonLayers['%s' % lname]['cached'].lower() in ("yes", "true", "t", "1"):
                myDic[b]['cached'] = True
          
        myDic[b]['title'] = myDic[b]['name']
        myDic[b]['abstract'] = ''
        myDic[b]['link'] = ''
        if(jsonLayers.has_key('%s' % lname)):
          if jsonLayers[lname].has_key('title') and jsonLayers[lname]['title'] != '':
            myDic[b]['title'] = jsonLayers[lname]['title']
          if jsonLayers[lname].has_key('abstract') and jsonLayers[lname]['abstract'] != '':
            myDic[b]['abstract'] = jsonLayers[lname]['abstract']
          if jsonLayers[lname].has_key('link') and jsonLayers[lname]['link'] != '':
            myDic[b]['link'] = jsonLayers[lname]['link']
                    
        childItem = QTreeWidgetItem(['%s' % unicode(myDic[b]['name']), '%s' % unicode(myDic[b]['id']), '%s' % myDic[b]['type']])
        

        if myId == '':
          myTree.addTopLevelItem(childItem)
        else:
          parentItem.addChild(childItem)
        myDic[b]['item'] = childItem

    myTree.expandAll()
    
    # Add the myDic to the global layerList dictionary
    self.layerList = myDic

    # Catch user interaction on layer tree and inputs
    QObject.connect(self.dlg.ui.treeLayer, SIGNAL("itemSelectionChanged()"), self.setItemOptions)
    QObject.connect(self.dlg.ui.inLayerTitle, SIGNAL("editingFinished()"), self.setLayerTitle)
    QObject.connect(self.dlg.ui.teLayerAbstract, SIGNAL("textChanged()"), self.setLayerAbstract)
    QObject.connect(self.dlg.ui.inLayerLink, SIGNAL("editingFinished()"), self.setLayerLink)
    QObject.connect(self.dlg.ui.cbLayerIsBaseLayer, SIGNAL("stateChanged(int)"), self.setLayerIsBaseLayer)
    QObject.connect(self.dlg.ui.cbGroupAsLayer, SIGNAL("stateChanged(int)"), self.setGroupAsLayer)
    QObject.connect(self.dlg.ui.cbToggled, SIGNAL("stateChanged(int)"), self.setToggled)
    QObject.connect(self.dlg.ui.cbSingleTile, SIGNAL("stateChanged(int)"), self.setSingleTile)
    QObject.connect(self.dlg.ui.cbCached, SIGNAL("stateChanged(int)"), self.setCached)
    


  def setItemOptions(self):
    '''Refresh layer/group metadata and options on click of a layer tree item'''
    # get the selected item
    item = self.dlg.ui.treeLayer.currentItem()
    # get information about the layer or the group
    selectedItem = self.layerList[item.text(1)]
    # set the title
    self.dlg.ui.inLayerTitle.setText(selectedItem['title'])
    # set the abstract
    self.dlg.ui.teLayerAbstract.setText(selectedItem['abstract'])
    # set the link
    self.dlg.ui.inLayerLink.setText(selectedItem['link'])    
    # set the baseLayer
    self.dlg.ui.cbLayerIsBaseLayer.setChecked(selectedItem['baseLayer'])
    # set the groupAsLayer
    self.dlg.ui.cbGroupAsLayer.setChecked(selectedItem['groupAsLayer'])
    # set the toggled
    self.dlg.ui.cbToggled.setChecked(selectedItem['toggled'])
    # set the singleTile
    self.dlg.ui.cbSingleTile.setChecked(selectedItem['singleTile'])  
    # set the cached
    self.dlg.ui.cbCached.setChecked(selectedItem['cached'])
      

  def setLayerTitle(self):
    '''Set a layer title when a item title is edited'''
    # get the selected item
    item = self.dlg.ui.treeLayer.currentItem()
    # modify the title for the selected item
    self.layerList[item.text(1)]['title'] = self.dlg.ui.inLayerTitle.text()
    
  def setLayerAbstract(self):
    '''Set a layer abstract when a item abstract is edited'''
    # get the selected item
    item = self.dlg.ui.treeLayer.currentItem()
    # modify the abstract for the selected item
    self.layerList[item.text(1)]['abstract'] = self.dlg.ui.teLayerAbstract.toPlainText()

  def setLayerLink(self):
    '''Set a layer link when a item link is edited'''
    # get the selected item
    item = self.dlg.ui.treeLayer.currentItem()
    # modify the link for the selected item
    self.layerList[item.text(1)]['link'] = self.dlg.ui.inLayerLink.text()
     
  def setLayerIsBaseLayer(self):
    '''Set a layer "IsBaseLayer" property when an item "Is Base layer" checkbox state has changed'''
    # get the selected item
    item = self.dlg.ui.treeLayer.currentItem()
    # modify the baseLayer property for the selected item
    self.layerList[item.text(1)]['baseLayer'] = self.dlg.ui.cbLayerIsBaseLayer.isChecked()
    
  def setGroupAsLayer(self):
    '''Set the "group as a layer" property when an item "Group As Layer" checkbox state has changed'''
    # get the selected item
    item = self.dlg.ui.treeLayer.currentItem()
    self.layerList[item.text(1)]['groupAsLayer'] = self.dlg.ui.cbGroupAsLayer.isChecked()
    # modify the type property for the selected item
    if self.dlg.ui.cbGroupAsLayer.isChecked():
      self.layerList[item.text(1)]['type'] = 'layer'
      
  def setToggled(self):
    '''Set a layer or group "toggled" property when an item "toggled" checkbox state has changed'''
    # get the selected item
    item = self.dlg.ui.treeLayer.currentItem()
    # modify the toggled property for the selected item
    self.layerList[item.text(1)]['toggled'] = self.dlg.ui.cbToggled.isChecked()

  def setSingleTile(self):
    '''Set a layer or group "singleTile" property when an item "singleTile" checkbox state has changed'''
    # get the selected item
    item = self.dlg.ui.treeLayer.currentItem()
    # modify the singleTile property for the selected item
    self.layerList[item.text(1)]['singleTile'] = self.dlg.ui.cbSingleTile.isChecked()

  def setCached(self):
    '''Set a layer or group "cached" property when an item "cached" checkbox state has changed'''
    # get the selected item
    item = self.dlg.ui.treeLayer.currentItem()
    # modify the cached property for the selected item
    self.layerList[item.text(1)]['cached'] = self.dlg.ui.cbCached.isChecked()



  def writeProjectConfigFile(self):
    '''Get general project options and user edited layers options from plugin gui. Save them into the project.qgs.cfg config file in the project.qgs folder (json format)'''
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
    if len(pWmsExtent) > 1:
      myJson+= '"bbox":[%s,%s,%s,%s],' % (pWmsExtent[0], pWmsExtent[1], pWmsExtent[2], pWmsExtent[3])
    else:
      myJson+= '"bbox":[],'
    
    # gui user defined options
    in_imageFormat = self.dlg.ui.liImageFormat.currentText()
    in_minScale = str(self.dlg.ui.inMinScale.text()).strip(' \t')
    in_maxScale = str(self.dlg.ui.inMaxScale.text()).strip(' \t')
    in_zoomLevelNumber = str(self.dlg.ui.inZoomLevelNumber.text()).strip(' \t')
    in_mapScales = str(self.dlg.ui.inMapScales.text()).strip(' \t')
    if len(in_minScale) == 0:
      in_minScale = 10000
    if len(in_maxScale) == 0:
      in_maxScale = 10000000
    if len(in_zoomLevelNumber) == 0:
      in_zoomLevelNumber = 10
    myJson+= ' "imageFormat" : "image/%s", "minScale" : %s, "maxScale" : %s, "zoomLevelNumber" : %s, "mapScales" : [%s]' % (in_imageFormat, in_minScale, in_maxScale, in_zoomLevelNumber, in_mapScales)

    myJson+= '},'
    
    # gui user defined layers options
    myJson+= '"layers" : {'
    myVirg = ''
    for k,v in self.layerList.items():
      ltype = v['type']
      gal = v['groupAsLayer']
      if gal:
        ltype = 'layer'
      else:
        ltype = 'group'
      if self.getQgisLayerById(k):
        ltype = 'layer'
        gal = True
        
      myJson+= '%s "%s" : {"id":"%s", "name":"%s", "type":"%s", "groupAsLayer":"%s", "title":"%s", "abstract":"%s", "link":"%s", "minScale":%d, "maxScale":%d, "toggled":"%s", "baseLayer":"%s", "singleTile" : "%s", "cached" : "%s"}' % (myVirg, unicode(v['name']), unicode(k), unicode(v['name']), ltype, v['groupAsLayer'], unicode(v['title']), unicode(v['abstract']), unicode(v['link']), v['minScale'], v['maxScale'] , str(v['toggled']), str(v['baseLayer']), str(v['singleTile']), str(v['cached']) )
      myVirg = ','
    myJson+= '}'
    myJson+= '}'
    
    # Write json to the cfg file
    # Get the project data
    p = QgsProject.instance()
    jsonFile = "%s.cfg" % p.fileName()
    f = open(jsonFile, 'w')
    f.write(myJson.encode('utf-8'))
    f.close()




  def checkGlobalProjectOptions(self):
    ''' Checks that the needed options are correctly set : relative path, project saved, etc.'''
    
    isok = True;
    # Get the project data from api
    p = QgsProject.instance()
    if not p.fileName():
      QMessageBox.critical(self.dlg, "Lizmap Error", ("You need to open a qgis project first."), QMessageBox.Ok)
      isok = False
      
    if isok:
      # Get the project folder
      projectDir, projectName = os.path.split(os.path.abspath('%s' % p.fileName()))
      self.dlg.ui.inLocaldir.setText(projectDir)
      
    # Check relative/absolute path    
    if isok and p.readEntry('Paths', 'Absolute')[0] == 'true':
      QMessageBox.critical(self.dlg, "Lizmap Error", ("The project layer paths must be set to relative. Please change this options in the project settings."), QMessageBox.Ok)
      isok = False
      
    # check active layers path layer by layer
    layerSourcesOk = []
    layerSourcesBad = []
    mc = self.iface.mapCanvas()
    for i in range(mc.layerCount()):
      layerSource =  unicode('%s' % mc.layer( i ).source() )
      if os.path.abspath(layerSource).startswith(projectDir):
        layerSourcesOk.append(os.path.abspath(layerSource))
      elif layerSource.startswith('dbname=') or layerSource.startswith('http'):
        layerSourcesOk.append(layerSource)
      else:
        layerSourcesBad.append(layerSource)
        isok = False
    if len(layerSourcesBad) > 0:
      QMessageBox.critical(self.dlg, "Lizmap Error", ("The layers paths must be relative to the project file. Please copy the layers inside \n%s.\n (see the log for detailed layers)" % projectDir), QMessageBox.Ok)
      self.log("The layers paths must be relative to the project file. Please copy the layers \n%s \ninside \n%s." % (str(layerSourcesBad), projectDir), abort=True, textarea=self.dlg.ui.outLog)
      
    # check if a bbox has been given in the project WMS tab configuration
    pWmsExtent = p.readListEntry('WMSExtent','')[0]
    if len(pWmsExtent) <1 :
      QMessageBox.critical(self.dlg, "Lizmap Error", ("The project WMS extent must be set. Please change this options in the project settings."), QMessageBox.Ok)
      isok = False
      
    if isok:
      # Check the project state (saved or not)
      if p.isDirty():
        saveIt = QMessageBox.question(self.dlg, 'Lizmap - Save current project ?', "Please save the current project before proceeding synchronisation. Save the project ?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if saveIt == QMessageBox.Yes:
          p.write()
        else:
          isOk = False
      
    return isok



    
  def getMapOptions(self):
    '''Check the user defined data from gui and save them to both global and project config files'''
    self.isok = 1
    # global project option checking
    isok = self.checkGlobalProjectOptions()
    
    if isok:
      # Get configuration from input fields
      # Map
      in_imageFormat = str(self.dlg.ui.liImageFormat.currentText()).strip(' \t')
      in_minScale = str(self.dlg.ui.inMinScale.text()).strip(' \t')
      in_maxScale = str(self.dlg.ui.inMaxScale.text()).strip(' \t')
      in_zoomLevelNumber = str(self.dlg.ui.inZoomLevelNumber.text()).strip(' \t')
      in_mapScales = str(self.dlg.ui.inMapScales.text()).strip(' \t')
      
      isok = True
      
      # log
      self.dlg.ui.outLog.append('=' * 20)
      self.dlg.ui.outLog.append('<b>Map options</b>')
      self.dlg.ui.outLog.append('=' * 20)
      
      # Checking configuration data
      # Map config
      # image format
      if in_imageFormat == 'png' or in_imageFormat == 'jpg':
        imageFormat = in_imageFormat
      else:
        self.log('<b>** WARNING **</b> Wrong image format !', abort=True, textarea=self.dlg.ui.outLog)
        
      # check that the triolet minScale, maxScale, zoomLevelNumber OR mapScales is et
      if len(in_mapScales) == 0 and ( len(in_minScale) == 0 or len(in_maxScale) == 0 or len(in_zoomLevelNumber) == 0):
        self.log('<b>** WARNING **</b> : You must give either minScale + maxScale + zoomLevelNumber OR mapScales in the "Map options" tab!', abort=True, textarea=self.dlg.ui.outLog)  
      
      # minScale
      minScale = 1
      if len(in_minScale) > 0:
        try:
          minScale = int(in_minScale)
        except (ValueError, IndexError):
          self.dlg.ui.inMinScale.setText(minScale)
          self.log('<b>** WARNING **</b> : minScale must be an integer !', abort=True, textarea=self.dlg.ui.outLog)
      self.log('minScale = %d' % minScale, abort=False, textarea=self.dlg.ui.outLog)
      
      # maxScale
      maxScale = 1000000
      if len(in_maxScale) > 0:
        try:
          maxScale = int(in_maxScale)
        except (ValueError, IndexError):
          self.dlg.ui.inMaxScale.setText(maxScale)
          self.log('<b>** WARNING **</b> : maxScale must be an integer !', abort=True, textarea=self.dlg.ui.outLog)   
      self.log('maxScale = %d' % maxScale, abort=False, textarea=self.dlg.ui.outLog)
      
      # zoom levels number
      zoomLevelNumber = 10
      if len(in_zoomLevelNumber) > 0:
        try:
          zoomLevelNumber = int(in_zoomLevelNumber)
        except (ValueError, IndexError):
          self.dlg.ui.inZoomLevelNumber.setText(zoomLevelNumber)
          self.log('<b>** WARNING **</b> : zoomLevelNumber must be an integer !', abort=True, textarea=self.dlg.ui.outLog)
      self.log('zoomLevelNumber = %d' % zoomLevelNumber, abort=False, textarea=self.dlg.ui.outLog)
      
      # mapScales
      if len(in_mapScales) > 0:
        good = 1
        sp = in_mapScales.split(',')
        # check that every mapScales item is an integer
        for p in sp:
          try:
            test = int(p.strip(' \t'))
          except (ValueError, IndexError):
            good = 0
            
        if good:
          self.log('mapScales = %s' % in_mapScales, abort=False, textarea=self.dlg.ui.outLog)      
        else:
          self.log('<b>** WARNING **</b> : mapScales must be series of integers separated by comma !', abort=True, textarea=self.dlg.ui.outLog)
        
      
      if self.isok:        
        # write data in the QgisWebClient json config file (to be send with the project file)
        self.writeProjectConfigFile()
        self.log('All the parameters are correctly set', abort=False, textarea=self.dlg.ui.outLog)
      else:
        QMessageBox.critical(self.dlg, "Error", ("Wrong parameters : please read the log and correct the printed errors before FTP synchronization"), QMessageBox.Ok)
        
      self.dlg.ui.progressBar.setValue(0)
      self.dlg.ui.outState.setText('<font color="green"></font>')
      self.dlg.ui.outSyncCommand.setText('')
      # Go to Log tab
      self.dlg.ui.tabWidget.setCurrentIndex(3)
        
    return self.isok
    

  def getFtpOptions(self):
    '''Get and check FTP options defined by user. Returns FTP options'''
    # Get FTP options
    in_username = str(self.dlg.ui.inUsername.text()).strip(' \t')
    in_password = str(self.dlg.ui.inPassword.text()).strip(' \t')
    in_host = str(self.dlg.ui.inHost.text()).strip(' \t')
    in_port = str(self.dlg.ui.inPort.text()).strip(' \t')
    in_localdir = str(self.dlg.ui.inLocaldir.text().toUtf8()).strip(' \t')
    in_remotedir = str(self.dlg.ui.inRemotedir.text()).strip(' \t')

    self.dlg.ui.outLog.append('')
    self.dlg.ui.outLog.append('=' * 20)
    self.dlg.ui.outLog.append('<b>FTP options</b>')
    self.dlg.ui.outLog.append('=' * 20)
    
    # Check FTP options
    # host
    if len(in_host) == 0:
      host = ''
      self.log('<b>** WARNING **</b> Missing hostname !', abort=True, textarea=self.dlg.ui.outLog)
    elif len(in_host) < 4:
      host=''
      self.log('<b>** WARNING **</b>Incorrect hostname : %s !' % in_host, abort=True, textarea=self.dlg.ui.outLog)
    else:
      host = unicode(in_host)
      self.log('host = %s' % host, abort=False, textarea=self.dlg.ui.outLog)
      
    # port
    port = 21
    if len(in_port) > 0:
      try:
        port = int(in_port)
      except (ValueError, IndexError):
        port = 21
        self.dlg.ui.inPort.setText('21')
        
    self.log('port = %d' % port, abort=False, textarea=self.dlg.ui.outLog)
    
    # remote directory
    if len(in_remotedir) > 0:
      remotedir = unicode(in_remotedir)
      if not str(remotedir).startswith('/'):
        remotedir = '/' + remotedir
      if str(remotedir).endswith('/'):
        remotedir = remotedir.rstrip('/')
      self.log('remotedir = %s' % remotedir, abort=False, textarea=self.dlg.ui.outLog)
    else:
      remotedir=''
      self.log('<b>** WARNING **</b> Remote directory must be set', abort=True, textarea=self.dlg.ui.outLog)
    
    # local directory    
    localdir = in_localdir
    if not str(localdir).endswith('/'):
      localdir = localdir + '/'
    if not os.path.isdir(localdir):
      localdir=''
      self.log('<b>** WARNING **</b> Localdir does not exist: %s' % localdir, abort=True, textarea=self.dlg.ui.outLog)
    else:
      self.log('localdir = %s' % localdir, abort=False, textarea=self.dlg.ui.outLog)
    
    # username
    if len(in_username) > 0:
      username = unicode(in_username)
      self.log('username = %s' % username, abort=False, textarea=self.dlg.ui.outLog)
    else:
      username=''
      self.log('<b>** WARNING **</b> Missing username !', abort=True, textarea=self.dlg.ui.outLog)
    
    # password  
    if len(in_password) > 0:
      password = unicode(in_password)
      self.log('password ok', abort=False, textarea=self.dlg.ui.outLog)
    else:
      password=''
      self.log('<b>** WARNING **</b> Missing password !', abort=True, textarea=self.dlg.ui.outLog)
      
    if self.isok:
      # write FTP options data in the python plugin config file
      cfg = ConfigParser.ConfigParser()
      configPath = os.path.expanduser("~/.qgis/python/plugins/lizmap/lizmap.cfg")
      cfg.read(configPath)
      cfg.set('Ftp', 'host', host)
      cfg.set('Ftp', 'username', username)
#        cfg.set('Ftp', 'password', password)
      cfg.set('Ftp', 'port', port)
      cfg.set('Ftp', 'remotedir', in_remotedir)
      cfg.write(open(configPath,"w"))
      cfg.read(configPath)
      # log the errors
      self.log('All the FTP parameters are correctly set', abort=False, textarea=self.dlg.ui.outLog)
    else:
      QMessageBox.critical(self.dlg, "Error", ("Wrong FTP parameters : please read the log and correct the printed errors before FTP synchronization"), QMessageBox.Ok)
    
    return [self.isok, host, port, username, password, localdir, remotedir]


  def ftpSync(self):
    '''Synchronize data (project file, project config file and all data contained in the project file folder) from local computer to remote host.
    Based on lftp library : only works on linux.
    '''
    # Ask for confirmation
    letsGo = QMessageBox.question(self.dlg, 'Lizmap', "You are about to send your project file and all the data contained in :\n\n%s\n\n to the server directory: \n\n%s\n\n This will remove every data in this remote directory which are not related to your current qgis project. Are you sure you want to proceed ?" % ( self.dlg.ui.inLocaldir.text(), self.dlg.ui.inRemotedir.text()), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    if letsGo == QMessageBox.Yes:
      isok = True
    else:
      isok = False
      return False
    
    self.isok = 1
    
    # Check user defined options
    getMapOptions = self.getMapOptions()    
    if not getMapOptions:
      return False
      
    # Check FTP user defined options
    getFtpOptions = self.getFtpOptions()
    if not getFtpOptions[0]:
      return False
    
    # Go to Log tab
    self.dlg.ui.tabWidget.setCurrentIndex(3)
    
    # Check the platform
    # FTP Sync only active for linux users.
    if sys.platform != 'linux2':
      QMessageBox.warning(self.dlg, "Lizmap", ('The configuration has been saved. Please synchronize your local project folder\n%s\nwith the remote FTP folder\n%s'  % (localdir, remotedir)), QMessageBox.Ok)
      return False

    # Get ftp user entered data from getMapOptions()
    host = getFtpOptions[1]
    port = getFtpOptions[2]
    username = getFtpOptions[3]
    password = getFtpOptions[4]
    localdir = getFtpOptions[5]
    remotedir = getFtpOptions[6]

    myOutput = ''
    # display the stateLabel
    self.dlg.ui.outState.setText('<font color="orange">running</font>')
    # setting progressbar refreshes the plygin ui
    self.dlg.ui.progressBar.setValue(0)  
    self.dlg.ui.outLog.append('')
    self.dlg.ui.outLog.append('=' * 20)
    self.dlg.ui.outLog.append('FTP Synchronisation')
    self.dlg.ui.outLog.append('=' * 20)
    
    if self.isok:
      self.dlg.ui.progressBar.setValue(33)
      ftp = ftplib.FTP()
      # Connection to FTP host
      try:
        ftp.connect(host, port)
        ftp.login(username, password, '')
        self.log('FTP connection OK', abort=False, textarea=self.dlg.ui.outLog)
      except:
        self.log('Impossible to connect to %s:' % host, abort=True, textarea=self.dlg.ui.outLog)
    
    # Process the sync with lftp
    if self.isok:
      self.dlg.ui.progressBar.setValue(0)
      time_started = datetime.datetime.now()
      
      # construction of lftp command line
      lftpStr1 = u'lftp ftp://%s:%s@%s -e "mirror --verbose -e -R %s %s ; quit"' % (username, password, host, localdir.decode('utf-8'), remotedir)
      lftpStr2 = u'lftp ftp://%s:%s@%s -e "chmod 775 -R %s ; quit"' % (username, password, host, remotedir)
      workingDir = os.getcwd()
      
      # run lftp
      proc = subprocess.Popen( lftpStr1, cwd=workingDir, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
      # read output
      i=33
      while True:
        # progressBar (needed to avoid the ui freezing)
        if i == 33:
          i=66
        else:
          i=33
        self.dlg.ui.progressBar.setValue(i)
        # output formating
        try:
          output = proc.stdout.readline()
          output = output.decode('utf-8')
          output = output.strip(' \t\n')
          output = output.replace(u'du fichier', 'de')
          output = output.replace(u'Â ', '')
          self.dlg.ui.outSyncCommand.setText(output)
          myOutput+=output + '\n'
          # if output empty --> break the loop - opeartion complete
          if output == "":
            self.dlg.ui.progressBar.setValue(100)
            myOutput+="Synchronisation completed !"
            self.dlg.ui.outState.setText('<font color="green">completed</font>')
            self.dlg.ui.outSyncCommand.setText("Synchronisation completed !")
            break
        except:
          anerror = True

      self.dlg.ui.outLog.append(myOutput)      
      proc = subprocess.Popen( lftpStr2, cwd=workingDir, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
      ftp.quit()
      self.dlg.ui.progressBar.setValue(0)
      self.dlg.ui.outSyncCommand.setText('')
      
    return self.isok
  

  def run(self):
    '''Plugin run method : launch the gui and some tests'''

    # create and show the dialog
    self.dlg = lizmapDialog()
    # show the dialog
    self.dlg.show()
    
    # FTP Sync only active for linux users.
    if sys.platform != 'linux2':
      self.dlg.ui.tabWidget.setTabEnabled(2, False)
      self.dlg.ui.btSync.setEnabled(False)
    
    # Get config file data and set the Ftp Configuration input fields
    self.getConfig()
    
    self.layerList = {}
    
    # Fill the layer tree
    self.populateLayerTree()
    
    self.isok = 1
    
    # pre-sync checkings
    checkGlobalProjectOptions = self.checkGlobalProjectOptions()
    
    # connect signals and functions
    # save button clicked
    QObject.connect(self.dlg.ui.btSave, SIGNAL("clicked()"), self.getMapOptions)
    # ftp sync button clicked
    QObject.connect(self.dlg.ui.btSync, SIGNAL("clicked()"), self.ftpSync)
    # clear log button clicked
    QObject.connect(self.dlg.ui.btClearlog, SIGNAL("clicked()"), self.clearLog)
    # refresh layer tree button click
    QObject.connect(self.dlg.ui.btRefreshTree, SIGNAL("clicked()"), self.populateLayerTree )
    
    result = self.dlg.exec_()
    # See if OK was pressed
    if result == 1: 
      QMessageBox.warning(self.dlg, "Debug", ("Voulez allez quitter le plugin !"), QMessageBox.Ok)
      
      
