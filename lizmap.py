# -*- coding: utf-8 -*-

"""
/***************************************************************************
 Lizmap
                 A QGIS plugin
 Publication plugin for Lizmap web application, by 3liz.com
                -------------------
    begin        : 2011-11-01
    copyright      : (C) 2011 by 3liz
    email        : info@3liz.com
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
    # Qgis version
    try:
      self.QgisVersion = unicode(QGis.QGIS_VERSION_INT)
    except:
      self.QgisVersion = unicode(QGis.qgisVersion)[ 0 ]
    
    # initialize plugin directory
    self.plugin_dir = QFileInfo(QgsApplication.qgisUserDbFilePath()).path() + "/python/plugins/lizmap"
    # initialize locale
    localePath = ""
    locale = QSettings().value("locale/userLocale").toString()[0:2]
     
    if QFileInfo(self.plugin_dir).exists():
      localePath = self.plugin_dir + "/i18n/lizmap_" + locale + ".qm"

    self.translator = QTranslator()
    if QFileInfo(localePath).exists():
      self.translator.load(localePath)
    else:
      self.translator.load(self.plugin_dir + "/i18n/lizmap_en.qm")

    if qVersion() > '4.3.3':
      QCoreApplication.installTranslator(self.translator)
        
    # Create the dialog and keep reference
    self.dlg = lizmapDialog()
    
    # FTP Sync only active for linux and windows users.
    if not sys.platform.startswith('linux') and sys.platform != 'win32' :
      self.dlg.ui.tabWidget.setTabEnabled(2, False)
      self.dlg.ui.btSync.setEnabled(False)
    
    # Disable winscp path field for non windows users
    if sys.platform != 'win32':
      self.dlg.ui.inWinscpPath.setEnabled(False)
      self.dlg.ui.btWinscpPath.setEnabled(False)
      self.dlg.ui.lbWinscpHelp.setEnabled(False)
      self.dlg.ui.lbWinscpIn.setEnabled(False)
    
    # connect signals and functions
    # save button clicked
    QObject.connect(self.dlg.ui.btSave, SIGNAL("clicked()"), self.getMapOptions)
    # ftp sync button clicked
    QObject.connect(self.dlg.ui.btSync, SIGNAL("clicked()"), self.ftpSync)
    # winscp get path button
    QObject.connect(self.dlg.ui.btWinscpPath, SIGNAL("clicked()"), self.chooseWinscpPath)
    # clear log button clicked
    QObject.connect(self.dlg.ui.btClearlog, SIGNAL("clicked()"), self.clearLog)
    # Cancel FTP Sync
    QObject.connect(self.dlg.ui.btCancelFtpSync, SIGNAL("clicked()"), self.ftpSyncCancel)
    # refresh layer tree button click
    QObject.connect(self.dlg.ui.btRefreshTree, SIGNAL("clicked()"), self.refreshLayerTree )
    
    # detect close event
    QObject.connect(self.dlg, SIGNAL("rejected()"), self.warnOnClose )
    

  def initGui(self):
    '''Create action that will start plugin configuration'''
    self.action = QAction(QIcon(":/plugins/lizmap/icon.png"), \
      "lizmap", self.iface.mainWindow())
    # connect the action to the run method
    QObject.connect(self.action, SIGNAL("triggered()"), self.run)

    # first check if Web menu availbale in this QGIS version
    if hasattr(self.iface, "addPluginToWebMenu"):
      #add plugin to the web plugin menu
      self.iface.addPluginToWebMenu(u"&LizMap", self.action)
      # and add button to the Web panel
      self.iface.addWebToolBarIcon(self.action)
    else:
      #add icon to the toolbar
      self.iface.addToolBarIcon(self.action)
      #add plugin to the plugin menu
      self.iface.addPluginToMenu(u"&LizMap", self.action)


  def unload(self):
    '''Remove the plugin menu item and icon'''
    # first check if Web menu availbale in this QGIS version
    if hasattr(self.iface, "addPluginToWebMenu"):
      # new menu used, remove submenus from main Web menu
      self.iface.removePluginWebMenu(u"&LizMap", self.action)
      # also remove button from Web toolbar
      self.iface.removeWebToolBarIcon(self.action)
    else:
      #remove plugin
      self.iface.removePluginMenu(u"&LizMap", self.action)
      #remove icon
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
    self.dlg.ui.outState.setText('<font color="green"></font>')



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
    self.dlg.ui.inRemotedir.setText(str(cfg.get('Ftp', 'remotedir')).decode('utf-8'))
    self.dlg.ui.inWinscpPath.setText(str(cfg.get('Ftp', 'winscppath')).decode('utf-8'))
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
        QMessageBox.critical(self.dlg, QApplication.translate("lizmap", "ui.msg.error.title"), (QApplication.translate("lizmap", "ui.msg.error.tree.read.content")), QMessageBox.Ok)
        self.log(QApplication.translate("lizmap", "ui.msg.error.tree.read.content"), abort=True, textarea=self.dlg.ui.outLog)
    
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
    # openstreetmap baselayers
    if jsonOptions.has_key('osmMapnik'):
      if jsonOptions['osmMapnik'].lower() in ("yes", "true", "t", "1"):
        self.dlg.ui.cbOsmMapnik.setChecked(True);
    if jsonOptions.has_key('osmMapquest'):
      if jsonOptions['osmMapquest'].lower() in ("yes", "true", "t", "1"):
        self.dlg.ui.cbOsmMapquest.setChecked(True);
    # google baselayers
    if jsonOptions.has_key('googleKey'):
      self.dlg.ui.inGoogleKey.setText(str(jsonOptions['googleKey']))
    if jsonOptions.has_key('googleStreets'):
      if jsonOptions['googleStreets'].lower() in ("yes", "true", "t", "1"):
        self.dlg.ui.cbGoogleStreets.setChecked(True);
    if jsonOptions.has_key('googleSatellite'):
      if jsonOptions['googleSatellite'].lower() in ("yes", "true", "t", "1"):
        self.dlg.ui.cbGoogleSatellite.setChecked(True);
    if jsonOptions.has_key('googleHybrid'):
      if jsonOptions['googleHybrid'].lower() in ("yes", "true", "t", "1"):
        self.dlg.ui.cbGoogleHybrid.setChecked(True);
    if jsonOptions.has_key('googleTerrain'):
      if jsonOptions['googleTerrain'].lower() in ("yes", "true", "t", "1"):
        self.dlg.ui.cbGoogleTerrain.setChecked(True);
        
    return True
    

    
  def getQgisLayerById(self, myId):
    '''Get a QgsLayer by its Id'''
    for layer in self.iface.legendInterface().layers():
      if myId == layer.id():
        return layer
    return None


  def refreshLayerTree(self):
    # Ask confirmation
    refreshIt = QMessageBox.question(self.dlg, QApplication.translate("lizmap", 'ui.msg.question.refresh.title'), QApplication.translate("lizmap", "ui.msg.question.refresh.content"), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    if refreshIt == QMessageBox.Yes:
      self.populateLayerTree()


  def populateLayerTree(self):
    '''Populate the layer tree of the Layers tab from Qgis legend interface
    Needs to be refactored.
    '''
    myTree = self.dlg.ui.treeLayer
    myTree.clear()
    myTree.headerItem().setText(0, QApplication.translate("lizmap", QApplication.translate("lizmap", "ui.tab.layers.tree.title")))
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
        QMessageBox.critical(self.dlg, QApplication.translate("lizmap", "ui.msg.error.title"), (u""), QMessageBox.Ok)
        self.log( QApplication.translate("lizmap", "ui.msg.error.tree.read.content"), abort=True, textarea=self.dlg.ui.outLog)
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
        ldisplay = True
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
              else:
                 myDic[myId]['toggled'] = False
                        
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
          if layer.type() == 0:
            if layer.geometryType() == 4:
              ldisplay = False
            
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
              else:
                myDic[myId]['toggled'] = False
                
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
        
        if ldisplay:
          parentItem = QTreeWidgetItem(['%s' % unicode(myDic[myId]['name']), '%s' % unicode(myDic[myId]['id']), '%s' % myDic[myId]['type']])
          myTree.addTopLevelItem(parentItem)
          myDic[myId]['item'] = parentItem
        else:
          del myDic[myId]
      
      # loop through the children and add children to the parent item
      for b in a[1]:
        myDic[b] = {'id' : b}
        ldisplay = True
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
          if layer.type() == 0:
            if layer.geometryType() == 4:
              ldisplay = False
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
              else:
                myDic[b]['toggled'] = False
                
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
        
        if ldisplay:            
          childItem = QTreeWidgetItem(['%s' % unicode(myDic[b]['name']), '%s' % unicode(myDic[b]['id']), '%s' % myDic[b]['type']])
          if myId == '':
            myTree.addTopLevelItem(childItem)
          else:
            parentItem.addChild(childItem)
          myDic[b]['item'] = childItem
        else:
          del myDic[b]  

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
    if self.layerList.has_key(item.text(1)):
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
    else:
      self.dlg.ui.inLayerTitle.setText('')
      self.dlg.ui.teLayerAbstract.setText('')
      self.dlg.ui.inLayerLink.setText('')
      self.dlg.ui.cbLayerIsBaseLayer.setChecked(False)
      self.dlg.ui.cbGroupAsLayer.setChecked(False)
      self.dlg.ui.cbToggled.setChecked(False)
      self.dlg.ui.cbSingleTile.setChecked(False)
      self.dlg.ui.cbCached.setChecked(False)      
      

  def setLayerTitle(self):
    '''Set a layer title when a item title is edited'''
    # get the selected item
    item = self.dlg.ui.treeLayer.currentItem()
    # modify the title for the selected item
    if item and self.layerList.has_key(item.text(1)):
      self.layerList[item.text(1)]['title'] = self.dlg.ui.inLayerTitle.text()
    
  def setLayerAbstract(self):
    '''Set a layer abstract when a item abstract is edited'''
    # get the selected item
    item = self.dlg.ui.treeLayer.currentItem()
    # modify the abstract for the selected item
    if self.layerList.has_key(item.text(1)):
      self.layerList[item.text(1)]['abstract'] = self.dlg.ui.teLayerAbstract.toPlainText()

  def setLayerLink(self):
    '''Set a layer link when a item link is edited'''
    # get the selected item
    item = self.dlg.ui.treeLayer.currentItem()
    # modify the link for the selected item
    if self.layerList.has_key(item.text(1)):
      self.layerList[item.text(1)]['link'] = self.dlg.ui.inLayerLink.text()
     
  def setLayerIsBaseLayer(self):
    '''Set a layer "IsBaseLayer" property when an item "Is Base layer" checkbox state has changed'''
    # get the selected item
    item = self.dlg.ui.treeLayer.currentItem()
    # modify the baseLayer property for the selected item
    if self.layerList.has_key(item.text(1)):
      self.layerList[item.text(1)]['baseLayer'] = self.dlg.ui.cbLayerIsBaseLayer.isChecked()
    
  def setGroupAsLayer(self):
    '''Set the "group as a layer" property when an item "Group As Layer" checkbox state has changed'''
    # get the selected item
    item = self.dlg.ui.treeLayer.currentItem()
    if self.layerList.has_key(item.text(1)):
      self.layerList[item.text(1)]['groupAsLayer'] = self.dlg.ui.cbGroupAsLayer.isChecked()
      # modify the type property for the selected item
      if self.dlg.ui.cbGroupAsLayer.isChecked():
          self.layerList[item.text(1)]['type'] = 'layer'
      
  def setToggled(self):
    '''Set a layer or group "toggled" property when an item "toggled" checkbox state has changed'''
    # get the selected item
    item = self.dlg.ui.treeLayer.currentItem()
    # modify the toggled property for the selected item
    if self.layerList.has_key(item.text(1)):
      self.layerList[item.text(1)]['toggled'] = self.dlg.ui.cbToggled.isChecked()

  def setSingleTile(self):
    '''Set a layer or group "singleTile" property when an item "singleTile" checkbox state has changed'''
    # get the selected item
    item = self.dlg.ui.treeLayer.currentItem()
    # modify the singleTile property for the selected item
    if self.layerList.has_key(item.text(1)):
      self.layerList[item.text(1)]['singleTile'] = self.dlg.ui.cbSingleTile.isChecked()

  def setCached(self):
    '''Set a layer or group "cached" property when an item "cached" checkbox state has changed'''
    # get the selected item
    item = self.dlg.ui.treeLayer.currentItem()
    # modify the cached property for the selected item
    if self.layerList.has_key(item.text(1)):
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
    # options
    liz2json = {}
    liz2json["options"] = {}
    liz2json["layers"] = {}
    # projection
    # project projection
    mc = self.iface.mapCanvas()
    pSrs = mc.mapRenderer().destinationSrs()
    pAuthid = pSrs.authid()
    pProj4 = pSrs.toProj4()
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
    
    # gui user defined options
    in_imageFormat = self.dlg.ui.liImageFormat.currentText()
    liz2json["options"]["imageFormat"] = 'image/%s' % in_imageFormat
    in_minScale = str(self.dlg.ui.inMinScale.text()).strip(' \t')
    if len(in_minScale) == 0:
      in_minScale = 10000    
    liz2json["options"]["minScale"] = in_minScale
    in_maxScale = str(self.dlg.ui.inMaxScale.text()).strip(' \t')
    if len(in_maxScale) == 0:
      in_maxScale = 10000000
    liz2json["options"]["maxScale"] = in_maxScale
    in_zoomLevelNumber = str(self.dlg.ui.inZoomLevelNumber.text()).strip(' \t')
    if len(in_zoomLevelNumber) == 0:
      in_zoomLevelNumber = 10
    liz2json["options"]["zoomLevelNumber"] = in_zoomLevelNumber
    in_mapScales = str(self.dlg.ui.inMapScales.text()).strip(' \t')
    liz2json["options"]["mapScales"] = eval("[%s]" % in_mapScales)
    in_osmMapnik = str(self.dlg.ui.cbOsmMapnik.isChecked())
    liz2json["options"]["osmMapnik"] = in_osmMapnik
    in_osmMapquest = str(self.dlg.ui.cbOsmMapquest.isChecked())
    liz2json["options"]["osmMapquest"] = in_osmMapquest
    in_googleKey = str(self.dlg.ui.inGoogleKey.text()).strip(' \t')
    liz2json["options"]["googleKey"] = in_googleKey
    in_googleStreets = str(self.dlg.ui.cbGoogleStreets.isChecked())
    liz2json["options"]["googleStreets"] = in_googleStreets
    in_googleSatellite = str(self.dlg.ui.cbGoogleSatellite.isChecked())
    liz2json["options"]["googleSatellite"] = in_googleSatellite
    in_googleHybrid = str(self.dlg.ui.cbGoogleHybrid.isChecked())
    liz2json["options"]["googleHybrid"] = in_googleHybrid
    in_googleTerrain = str(self.dlg.ui.cbGoogleTerrain.isChecked())
    liz2json["options"]["googleTerrain"] = in_googleTerrain
        
    # gui user defined layers options
    for k,v in self.layerList.items():
      addToCfg = True
      ltype = v['type']
      gal = v['groupAsLayer']
      geometryType = -1
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
          if layer.type() == 0:
            geometryType = layer.geometryType()
      
      if geometryType != 4:
        layerOptions = {}
        layerOptions["id"] = unicode(k)
        layerOptions["name"] = unicode(v['name'])
        layerOptions["type"] = ltype
        layerOptions["groupAsLayer"] = v['groupAsLayer']
        layerOptions["title"] = unicode(v['title'])
        layerOptions["abstract"] = unicode(v['abstract'])
        layerOptions["link"] = unicode(v['link'])
        layerOptions["minScale"] = v['minScale']
        layerOptions["maxScale"] = v['maxScale']
        layerOptions["toggled"] = str(v['toggled'])
        layerOptions["baseLayer"] = str(v['baseLayer'])
        layerOptions["singleTile"] = str(v['singleTile'])
        layerOptions["cached"] = str(v['cached'])
        liz2json["layers"]["%s" % unicode(v['name'])] = layerOptions
      
    
    jsonFileContent = simplejson.dumps(liz2json)
    # Write json to the cfg file
    # Get the project data
    p = QgsProject.instance()
    jsonFile = "%s.cfg" % p.fileName()
    f = open(jsonFile, 'w')
    f.write(jsonFileContent.encode('utf-8'))
    f.close()




  def checkGlobalProjectOptions(self):
    ''' Checks that the needed options are correctly set : relative path, project saved, etc.'''
    
    isok = True;
    # Get the project data from api
    p = QgsProject.instance()
    if not p.fileName():
      QMessageBox.critical(self.dlg, QApplication.translate("lizmap", "ui.msg.error.title"), QApplication.translate("lizmap", "ui.msg.error.init.open.project"), QMessageBox.Ok)
      isok = False
      
    # Check the project state (saved or not)
    if isok and p.isDirty():
      saveIt = QMessageBox.question(self.dlg, QApplication.translate("lizmap", "ui.msg.question.save.project.title"), QApplication.translate("lizmap", "ui.msg.question.save.project.content"), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
      if saveIt == QMessageBox.Yes:
        p.write()
      else:
        isok = False
      
    if isok:
      # Get the project folder
      projectDir, projectName = os.path.split(os.path.abspath('%s' % p.fileName()))
      self.dlg.ui.inLocaldir.setText(projectDir)
      
    # Check relative/absolute path    
    if isok and p.readEntry('Paths', 'Absolute')[0] == 'true':
      QMessageBox.critical(self.dlg, QApplication.translate("lizmap", "ui.msg.error.title"), QApplication.translate("lizmap", "ui.msg.error.project.option.path.relative %1"), QMessageBox.Ok)
      isok = False
      
    # check active layers path layer by layer
    if isok:
      layerSourcesOk = []
      layerSourcesBad = []
      mc = self.iface.mapCanvas()
      for i in range(mc.layerCount()):
        layerSource =  unicode('%s' % mc.layer( i ).source() )
        if os.path.abspath(layerSource).startswith(projectDir):
          layerSourcesOk.append(os.path.abspath(layerSource))
        elif layerSource.startswith('dbname=') or layerSource.startswith('http') or layerSource.startswith('tiled='):
          layerSourcesOk.append(layerSource)
        else:
          layerSourcesBad.append(layerSource)
          isok = False
      if len(layerSourcesBad) > 0:
        QMessageBox.critical(
          self.dlg, 
          QApplication.translate("lizmap", "ui.msg.error.title"),
          QApplication.translate("lizmap", "ui.msg.error.project.layers.path.relative")
          .arg(projectDir), 
          QMessageBox.Ok)
        self.log(
          QApplication.translate("lizmap", "ui.msg.error.project.layers.path.relative")
          .arg(str(layerSourcesBad))
          .arg(projectDir), 
          abort=True, 
          textarea=self.dlg.ui.outLog)
      
    # check if a bbox has been given in the project WMS tab configuration
    if isok:
      pWmsExtent = p.readListEntry('WMSExtent','')[0]
      if len(pWmsExtent) <1 :
        QMessageBox.critical(
          self.dlg, 
          QApplication.translate("lizmap", "ui.msg.error.title"), 
          QApplication.translate("lizmap", "ui.msg.error.project.wms.extent"), 
          QMessageBox.Ok)
        isok = False
        
    # for linux users, check if lftp has been installed
    if isok and sys.platform.startswith('linux'):
      lftpCheck = u'lftp --version'
      workingDir = os.getcwd()
      proc = subprocess.Popen( lftpCheck, cwd=workingDir, shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
      output = proc.communicate()
      proc.wait()
      if "LFTP" not in output[0]:
        QMessageBox.critical(
          self.dlg,
          QApplication.translate("lizmap", "ui.msg.warning.title"),
          QApplication.translate("lizmap", "ui.msg.warning.lftp.installation"),
          QMessageBox.Ok)
        self.dlg.ui.tabWidget.setTabEnabled(2, False)
        self.dlg.ui.btSync.setEnabled(False)
      
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
      in_osmMapnik = self.dlg.ui.cbOsmMapnik.isChecked()
      in_osmMapquest = self.dlg.ui.cbOsmMapquest.isChecked()
      in_googleKey = str(self.dlg.ui.inGoogleKey.text()).strip(' \t')
      in_googleStreets = self.dlg.ui.cbGoogleStreets.isChecked()
      in_googleSatellite = self.dlg.ui.cbGoogleSatellite.isChecked()
      in_googleHybrid = self.dlg.ui.cbGoogleHybrid.isChecked()
      in_googleTerrain = self.dlg.ui.cbGoogleTerrain.isChecked()
      
      isok = True
      
      # log
      self.dlg.ui.outLog.append('=' * 20)
      self.dlg.ui.outLog.append(QApplication.translate("lizmap", "ui.tab.log.map.option.title"))
      self.dlg.ui.outLog.append('=' * 20)
      
      # Checking configuration data
      # Map config
      # image format
      if in_imageFormat == 'png' or in_imageFormat == 'jpg':
        imageFormat = in_imageFormat
      else:
        self.log(
          QApplication.translate("lizmap", "ui.tab.log.map.image.format.warning"),
          abort=True, 
          textarea=self.dlg.ui.outLog)
        
      # check that the triolet minScale, maxScale, zoomLevelNumber OR mapScales is et
      if len(in_mapScales) == 0 and (len(in_minScale) == 0 or len(in_maxScale) == 0 or len(in_zoomLevelNumber) == 0):
        self.log(
          QApplication.translate("lizmap", "ui.tab.log.map.scale.warning"), 
          abort=True, 
          textarea=self.dlg.ui.outLog)  
      
      # minScale
      minScale = 1
      if len(in_minScale) > 0:
        try:
          minScale = int(in_minScale)
        except (ValueError, IndexError):
          self.dlg.ui.inMinScale.setText(str(minScale))
          self.log(
            QApplication.translate("lizmap", "ui.tab.log.map.minscale.warning"),
            abort=True, 
            textarea=self.dlg.ui.outLog)
      self.log('minScale = %d' % minScale, abort=False, textarea=self.dlg.ui.outLog)
      
      # maxScale
      maxScale = 1000000
      if len(in_maxScale) > 0:
        try:
          maxScale = int(in_maxScale)
        except (ValueError, IndexError):
          self.dlg.ui.inMaxScale.setText(str(maxScale))
          self.log(
            QApplication.translate("lizmap", "ui.tab.log.map.maxscale.warning"),
            abort=True, 
            textarea=self.dlg.ui.outLog)
      self.log('maxScale = %d' % maxScale, abort=False, textarea=self.dlg.ui.outLog)
      
      # zoom levels number
      zoomLevelNumber = 10
      if len(in_zoomLevelNumber) > 0:
        try:
          zoomLevelNumber = int(in_zoomLevelNumber)
        except (ValueError, IndexError):
          self.dlg.ui.inZoomLevelNumber.setText(str(zoomLevelNumber))
          self.log(
            QApplication.translate("lizmap", "ui.tab.log.map.zoomLevelNumber.warning"),
            abort=True, 
            textarea=self.dlg.ui.outLog)
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
          self.log(
            QApplication.translate("lizmap", "ui.tab.log.map.mapScales.warning"),
            abort=True, 
            textarea=self.dlg.ui.outLog)


      # Get the project data from api to check the "coordinate system restriction" of the WMS Server settings
      p = QgsProject.instance()
      
      # public baselayers: check that the 900913 projection is set in the "Coordinate System Restriction" section of the project WMS Server tab properties
      if in_osmMapnik or in_osmMapquest or in_googleStreets or in_googleSatellite or in_googleHybrid or in_googleTerrain:
        good = False
        for i in p.readListEntry('WMSCrsList','')[0]:
          if i == 'EPSG:900913':
            good = True
        if not good:
          self.log(
            QApplication.translate("lizmap", "ui.tab.log.map.externalBaseLayers.warning"),
            abort=True, 
            textarea=self.dlg.ui.outLog)
      
        
      
      if self.isok:        
        # write data in the QgisWebClient json config file (to be send with the project file)
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
      self.dlg.ui.tabWidget.setCurrentIndex(3)
        
    return self.isok
    


  def chooseWinscpPath(self):
    '''Ask the user to select a folder and write down the path to inWinscpPath field'''
    winscpPath = QFileDialog.getExistingDirectory( None,QString("Choose the folder where WinScp portable is installed"), str(self.dlg.ui.inWinscpPath.text().toUtf8()).strip(' \t') )
    if os.path.exists(unicode(winscpPath)):
      self.dlg.ui.inWinscpPath.setText(unicode(winscpPath))
      if not os.path.exists(os.path.join(os.path.abspath('%s' % winscpPath), 'WinSCP.com')):
        QMessageBox.critical(
          self.dlg,
          QApplication.translate("lizmap", "ui.msg.error.title"),
          QApplication.translate("lizmap", "ui.msg.error.winscp.not.found %1")
          .arg(os.path.abspath('%s' % winscpPath)),
          QMessageBox.Ok)


  def getFtpOptions(self):
    '''Get and check FTP options defined by user. Returns FTP options'''
    # Get FTP options
    in_username = str(self.dlg.ui.inUsername.text()).strip(' \t')
    in_password = str(self.dlg.ui.inPassword.text()).strip(' \t')
    in_host = str(self.dlg.ui.inHost.text()).strip(' \t')
    in_port = str(self.dlg.ui.inPort.text()).strip(' \t')
    in_localdir = str(self.dlg.ui.inLocaldir.text().toUtf8()).strip(' \t')
    in_remotedir = str(self.dlg.ui.inRemotedir.text().toUtf8()).strip(' \t')
    in_winscpPath = str(self.dlg.ui.inWinscpPath.text().toUtf8()).strip(' \t')

    self.dlg.ui.outLog.append(QApplication.translate("lizmap", "ui.tab.log.ftp.option.title"))
    self.dlg.ui.outLog.append('=' * 20)
    self.dlg.ui.outLog.append(QApplication.translate("lizmap", "ui.tab.log.ftp.option.title"))
    self.dlg.ui.outLog.append('=' * 20)
    
    # Check FTP options
    # host
    if len(in_host) == 0:
      host = ''
      self.log(
        QApplication.translate("lizmap", "ui.tab.log.ftp.hostname.missing.warning"), 
        abort=True,
        textarea=self.dlg.ui.outLog)
    elif len(in_host) < 4:
      host=''
      self.log(
        QApplication.translate("lizmap", "ui.tab.log.ftp.hostname.wrong.warning %1")
        .arg(in_host), 
        abort=True,
        textarea=self.dlg.ui.outLog)
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
      remotedir = in_remotedir
      if not str(remotedir).startswith('/'):
        remotedir = '/' + remotedir
      if str(remotedir).endswith('/'):
        remotedir = remotedir.rstrip('/')
      self.log('remotedir = %s' % remotedir, abort=False, textarea=self.dlg.ui.outLog)
    else:
      remotedir=''
      self.log(
        QApplication.translate("lizmap", "ui.tab.log.ftp.remotedir.missing.warning"), 
        abort=True,
        textarea=self.dlg.ui.outLog)
    
    # local directory    
    localdir = in_localdir
    if not str(localdir).endswith('/'):
      localdir = localdir + '/'
    if not os.path.isdir(localdir):
      localdir=''
      self.log(
        QApplication.translate("lizmap", "ui.tab.log.ftp.localdir.warning %1")
        .arg(localdir), 
        abort=True,
        textarea=self.dlg.ui.outLog)
    else:
      self.log('localdir = %s' % localdir, abort=False, textarea=self.dlg.ui.outLog)

    # For windows users : winscp path
    if sys.platform == 'win32':
      winscpPath = in_winscpPath
      #if not str(winscpPath).endswith('/'):
      #  winscpPath = winscpPath + '/'
      if not os.path.exists(os.path.join(os.path.abspath('%s' % winscpPath), 'WinSCP.com') ):
        self.log(
          QApplication.translate("lizmap", "ui.tab.log.ftp.winscpPath.warning %1")
          .arg(winscpPath), 
          abort=True,
          textarea=self.dlg.ui.outLog)
        winscpPath=''
      else:
        self.log('winscp path = %s' % winscpPath, abort=False, textarea=self.dlg.ui.outLog)
    else:
      winscpPath = ''
    
    # username
    if len(in_username) > 0:
      username = unicode(in_username)
      self.log('username = %s' % username, abort=False, textarea=self.dlg.ui.outLog)
    else:
      username=''
      self.log(
        QApplication.translate("lizmap", "ui.tab.log.ftp.username.missing.warning"), 
        abort=True,
        textarea=self.dlg.ui.outLog)
    
    # password  
    if len(in_password) > 0:
      password = unicode(in_password)
      self.log('password ok', abort=False, textarea=self.dlg.ui.outLog)
    else:
      password=''
      self.log(
        QApplication.translate("lizmap", "ui.tab.log.ftp.password.missing.warning"), 
        abort=True,
        textarea=self.dlg.ui.outLog)
      
    if self.isok:
      # write FTP options data in the python plugin config file
      cfg = ConfigParser.ConfigParser()
      configPath = os.path.expanduser("~/.qgis/python/plugins/lizmap/lizmap.cfg")
      cfg.read(configPath)
      cfg.set('Ftp', 'host', host)
      cfg.set('Ftp', 'username', username)
#        cfg.set('Ftp', 'password', password)
      cfg.set('Ftp', 'port', port)
      cfg.set('Ftp', 'remotedir', remotedir)
      cfg.set('Ftp', 'winscppath', winscpPath)
      cfg.write(open(configPath,"w"))
      cfg.read(configPath)
      # log the errors
      self.log(
        QApplication.translate("lizmap", "ui.msg.ftp.parameters.ok"), 
        abort=False,
        textarea=self.dlg.ui.outLog)
    else:
      self.log(
        QApplication.translate("lizmap", "ui.msg.ftp.parameters.bad"), 
        abort=True,
        textarea=self.dlg.ui.outLog)
      QMessageBox.critical(
        self.dlg, 
        QApplication.translate("lizmap", "ui.msg.error.title"),
        QApplication.translate("lizmap", "ui.msg.ftp.parameters.bad"),
        QMessageBox.Ok)
    
    return [self.isok, host, port, username, password, localdir, remotedir, winscpPath]


  def ftpSyncStdout(self):
    '''Get the ftp sync process Stdout and append it to the log textarea'''
    data = QString(self.proc.readAllStandardOutput())
    output = QString.fromUtf8(data)
    self.dlg.ui.outLog.append(output)

  def ftpSyncError(self):
    '''Get the ftp sync process Error and append it to the log textarea'''
    data = QString(self.proc.readAllStandardError())
    output = QString.fromUtf8(data)
    self.dlg.ui.outLog.append(output)

  def ftpSyncFinished(self):
    '''Loaded when the sync process has finished its job.'''
    if self.proc.exitStatus() == 0:
      self.dlg.ui.outLog.append(QApplication.translate("lizmap", "ui.tab.log.sync.completed"))
      self.dlg.ui.outState.setText(QApplication.translate("lizmap", "ui.tab.log.outState.completed"))
    else:
      self.dlg.ui.outLog.append(QApplication.translate("lizmap", "ui.tab.log.sync.canceled"))
      self.dlg.ui.outState.setText(QApplication.translate("lizmap", "ui.tab.log.outState.canceled"))
    

  def ftpSyncCancel(self):
    '''Cancel the ftp sync process by killing it'''
    # Ask for confirmation
    letsGo = QMessageBox.question(
      self.dlg, 
      QApplication.translate("lizmap", "ui.msg.warning.title"), 
      QApplication.translate("lizmap", "ui.tab.log.kill.warning"), 
      QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    if letsGo == QMessageBox.Yes:
      try:
        self.proc.kill()
      except:
        return False
      return True
    else:
      return False


  def ftpSync(self):
    '''Synchronize data (project file, project config file and all data contained in the project file folder) from local computer to remote host.
    * linux : Based on lftp library which needs to be installed
    * windows : based on winscp portable which needs to be manually downloaded and installed
    * mac : needs to be done
    '''
    # Ask for confirmation
    letsGo = QMessageBox.question(
      self.dlg, 
      QApplication.translate("lizmap", "ui.msg.warning.title"),
      QApplication.translate("lizmap", "ui.msg.warning.run.sync %1 %2").arg(self.dlg.ui.inLocaldir.text()).arg(self.dlg.ui.inRemotedir.text()), 
      QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
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
    # FTP Sync only active for linux and windows users.
    if not sys.platform.startswith('linux') and sys.platform != 'win32':
      QMessageBox.warning(
        self.dlg,
        QApplication.translate("lizmap", "ui.msg.warning.title"),
        QApplication.translate("lizmap", "ui.msg.configuration.saved %1 %2")
        .arg(localdir)
        .arg(remotedir), 
        QMessageBox.Ok)
      return False

    # Get ftp user entered data from getMapOptions()
    host = getFtpOptions[1]
    port = getFtpOptions[2]
    username = getFtpOptions[3]
    password = getFtpOptions[4]
    localdir = getFtpOptions[5]
    remotedir = getFtpOptions[6]
    winscpPath = getFtpOptions[7]

    myOutput = ''
    # display the stateLabel
    self.dlg.ui.outState.setText(QApplication.translate("lizmap", "ui.tab.log.outState.running"))
    # setting progressbar refreshes the plygin ui
    self.dlg.ui.outLog.append('')
    self.dlg.ui.outLog.append('=' * 20)
    self.dlg.ui.outLog.appendQApplication.translate("lizmap", "ui.log.ftp.sync.title")()
    self.dlg.ui.outLog.append('=' * 20)
    
    # Process the sync with lftp
    if self.isok:
      time_started = datetime.datetime.now()
      
      if sys.platform.startswith('linux'):
        # construction of ftp sync command line
        ftpStr1 = u'lftp ftp://%s:%s@%s -e "mirror --verbose -e -R %s %s ; quit"' % (username, password, host, localdir.decode('utf-8'), remotedir.decode('utf-8'))
        ftpStr2 = u'lftp ftp://%s:%s@%s -e "chmod 775 -R %s ; quit"' % (username, password, host, remotedir.decode('utf-8'))

      else:
#        winscp = '"%s"' % os.path.expanduser("~/.qgis/python/plugins/lizmap/winscp435/WinSCP.com")
        winscp = os.path.join(os.path.abspath('%s' % winscpPath.decode('utf-8')), 'WinSCP.com')
        winLocaldir = localdir.replace("/", "\\")
        winLocaldir = winLocaldir.replace("\\", "\\\\")
        # needs to create the directory if not present
        ftpStr0 = '%s /console /command "option batch off" "option confirm off" "open %s:%s@%s" "option transfer binary" "mkdir %s" "close" "exit"'  % (winscp, username, password, host, remotedir.decode('utf-8'))
        self.log(ftpStr0, abort=False, textarea=self.dlg.ui.outLog)
        self.proc = QProcess()
        #QObject.connect(self.proc, SIGNAL("readyReadStandardOutput()"), self.ftpSyncStdout)
        QObject.connect(self.proc, SIGNAL("readyReadStandardError()"), self.ftpSyncError)
        QObject.connect(self.proc, SIGNAL("finished(int, QProcess::ExitStatus)"), self.ftpSyncFinished)
        self.proc.start(ftpStr0)
        self.proc.waitForFinished()
        # sync command 
        ftpStr1 = '%s /console /command "option batch off" "option confirm off" "open %s:%s@%s" "option transfer binary" "synchronize remote %s %s -mirror -delete" "close" "exit"' % (winscp, username, password, host, winLocaldir.decode('utf-8'), remotedir.decode('utf-8'))
        self.log(ftpStr1, abort=False, textarea=self.dlg.ui.outLog)

      # run the ftp sync      
      self.proc = QProcess()
      QObject.connect(self.proc, SIGNAL("readyReadStandardOutput()"), self.ftpSyncStdout)
      QObject.connect(self.proc, SIGNAL("readyReadStandardError()"), self.ftpSyncError)
      QObject.connect(self.proc, SIGNAL("finished(int, QProcess::ExitStatus)"), self.ftpSyncFinished)
      self.proc.start(ftpStr1)
      
      if sys.platform.startswith('linux'):
        # chmod 775 (nb: must find a way to pass the right option to ftpStr1 instead)
        proc = subprocess.Popen( ftpStr2, cwd=os.getcwd(), shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        proc.wait()
           
    return self.isok


  def warnOnClose(self):
    '''Method triggerd when the user closes the lizmap dialog by pressing Esc or clicking the x button'''
    # Ask confirmation
#    saveBeforeClose = QMessageBox.question(
#      self.dlg,
#      QApplication.translate("lizmap", "ui.msg.warning.title"),
#      QApplication.translate("lizmap", "ui.msg.warning.close.window"),
#      QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
#    if saveBeforeClose == QMessageBox.Yes:
#      self.writeProjectConfigFile()
    self.writeProjectConfigFile()

    
  def test(self):
    '''Debug method'''
    self.log("test", abort=False, textarea=self.dlg.ui.outLog)
    QMessageBox.critical(self.dlg, "Lizmap debug", (u"test"), QMessageBox.Ok)
    

  def run(self):
    '''Plugin run method : launch the gui and some tests'''
    
    if self.dlg.isVisible():
      QMessageBox.warning(
        self.dlg,
        QApplication.translate("lizmap", "ui.msg.warning.title"),
        QApplication.translate("lizmap", "ui.msg.warning.window.opened"),
        QMessageBox.Ok)
    
    # show the dialog only if checkGlobalProjectOptions is true
    if not self.dlg.isVisible() and self.checkGlobalProjectOptions():
      self.dlg.show()
      
      # Get config file data and set the Ftp Configuration input fields
      self.getConfig()
      
      self.layerList = {}
      
      # Fill the layer tree
      self.populateLayerTree()
      
      self.isok = 1
    
      result = self.dlg.exec_()
      # See if OK was pressed
      if result == 1: 
        QMessageBox.warning(self.dlg, "Debug", ("Quit !"), QMessageBox.Ok)
      
      
