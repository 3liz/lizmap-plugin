# -*- coding: utf-8 -*-
"""
/***************************************************************************
 send2server
                                 A QGIS plugin
 Sends a local qgis project and related files to a qgismapserver server installation using FTP
                              -------------------
        begin                : 2011-04-01
        copyright            : (C) 2011 by 3liz
        email                : mdouchin@3liz.org
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
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
       
                
#    # Choose some directory from UI
#    def chooseLocalDirectory(self):
#        localDir = QFileDialog.getExistingDirectory( None,QString("Choose the local data folder"),"" )
#        if os.path.exists(unicode(localDir)):
#            self.dlg.ui.inLocaldir.setText(localDir)
      

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
        
        return True
            

    # Save Qgis project and modify the xml
    def prepareSync(self):
        
        isok = True;
        
        # Get the project data
        p = QgsProject.instance()
        if not p.fileName():
            QMessageBox.critical(self.iface.mainWindow(), "Send2Server Error", ("You need to open a qgis project first."), QMessageBox.Ok)
            isok = False
            
        if isok:
            # Get the project folder
            projectDir, projectName = os.path.split(os.path.abspath(str(p.fileName())))
            self.dlg.ui.inLocaldir.setText(projectDir)
            
        # Check relative/absolute path      
        if isok and p.readEntry('Paths', 'Absolute')[0] == 'true':
            QMessageBox.critical(self.iface.mainWindow(), "Send2Server Error", ("The layers paths must be relative to the project file. Please change this options in the project settings."), QMessageBox.Ok)
            isok = False
            
        # check active layers path layer by layer
        layerSourcesOk = []
        layerSourcesBad = []
        mc = self.iface.mapCanvas()
        for i in range(mc.layerCount()):
            layerSource =  str(mc.layer( i ).source())
            if layerSource.startswith(projectDir):
                layerSourcesOk.append(layerSource)
            else:
                layerSourcesBad.append(layerSource)
                isok = False
        if len(layerSourcesBad) > 0:
            QMessageBox.critical(self.iface.mainWindow(), "Send2Server Error", ("The layers paths must be relative to the project file. Please copy the layers inside \n%s.\n (see the log for detailed layers)" % projectDir), QMessageBox.Ok)
            log("The layers paths must be relative to the project file. Please copy the layers \n%s \ninside \n%s." % (str(layerSourcesBad), projectDir), abort=True, textarea=self.dlg.ui.outLog)

            
        if isok:
          
            # Save the current project
            if p.isDirty():
                saveIt = QMessageBox.question(self.dlg, 'Send2server - Save current project ?', "Please save the current project before proceeding synchronisation. Save the project ?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if saveIt == QMessageBox.Yes:
                    p.write()
            
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
            in_username = self.dlg.ui.inUsername.text()
            in_password = self.dlg.ui.inPassword.text()
            in_account = ''
            in_host = self.dlg.ui.inHost.text()
            in_port = self.dlg.ui.inPort.text()
            in_localdir = self.dlg.ui.inLocaldir.text()
            in_remotedir = self.dlg.ui.inRemotedir.text()
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
    #            log('account = %' % accout, abort=False, textarea=self.dlg.ui.outLog)
            else:
                account = ''
            
            
            if globals['isok']:
            
              # write data in config file
              cfg = ConfigParser.ConfigParser()
              configPath = os.path.expanduser("~/.qgis/python/plugins/send2server/send2server.cfg")
              cfg.read(configPath)
              cfg.set('Ftp', 'host', host)
              cfg.set('Ftp', 'username', username)
              cfg.set('Ftp', 'port', port)
              cfg.set('Ftp', 'remotedir', in_remotedir)
              cfg.write(open(configPath,"w"))
              cfg.read(configPath)
            
              log('All the parameters are correctly set', abort=False, textarea=self.dlg.ui.outLog)
              
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
                  
                  self.dlg.ui.outLog.append('')
                  self.dlg.ui.outLog.append('=' * 20)
                  self.dlg.ui.outLog.append('Information : server side commands to run with root permissions after the first time')
                  self.dlg.ui.outLog.append('=' * 20)
                  self.dlg.ui.outLog.append('cp /usr/lib/cgi-bin/wms_metadata.xml /home/mdouchin%s/' % remotedir)
                  self.dlg.ui.outLog.append('ln -s /home/mdouchin%s /usr/lib/cgi-bin/' % remotedir)
                  self.dlg.ui.outLog.append('ln -s /usr/lib/cgi-bin/qgis_mapserv.fcgi /usr/lib/cgi-bin/qgis_mapserv.cgi')
                  self.dlg.ui.outLog.append('ln -s /usr/lib/cgi-bin/qgis_mapserv.fcgi /usr/lib/cgi-bin%s/' % remotedir)
                  self.dlg.ui.outLog.append('ln -s /usr/lib/cgi-bin/qgis_mapserv.cgi /usr/lib/cgi-bin%s/' % remotedir)
                  self.dlg.ui.outLog.append('/etc/init.d/apache2 reload')
                  self.dlg.ui.outLog.append('')
                  
                  self.dlg.ui.outLog.append('=' * 20)
                  self.dlg.ui.outLog.append('WMS URL')
                  self.dlg.ui.outLog.append('=' * 20)
                  self.dlg.ui.outLog.append('Fast CGI (needs Apache reload) = http://%s/cgi-bin%s/qgis_mapserv.fcgi?' % (host, remotedir))
                  self.dlg.ui.outLog.append('simple CGI (no reload needed) = http://%s/cgi-bin%s/qgis_mapserv.cgi?' % (host, remotedir))

                  self.dlg.ui.outLog.append('')
              
              globals['isok'] = 1

            else:
                QMessageBox.critical(self.iface.mainWindow(), "Error", ("Wrong parameters : please read the log and correct the printed errors"), QMessageBox.Ok)
                globals['isok'] = 1
            

    # run method
    def run(self):

        # create and show the dialog
        self.dlg = send2serverDialog()
        # show the dialog
        self.dlg.show()
        
        # Get config file data and set the Ftp Configuration input fields
        self.getConfig()
        
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
          QMessageBox.warning(self.iface.mainWindow(), "Debug", ("Voulez allez quitter le plugin !"), QMessageBox.Ok)
