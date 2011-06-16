"""
/***************************************************************************
 send2serverDialog
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

from PyQt4 import QtCore, QtGui
from ui_send2server import Ui_send2server
# create the dialog for zoom to point
class send2serverDialog(QtGui.QDialog):
    def __init__(self):
        QtGui.QDialog.__init__(self)
        # Set up the user interface from Designer.
        self.ui = Ui_send2server()
        self.ui.setupUi(self)
