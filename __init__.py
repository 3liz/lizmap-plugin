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
 This script initializes the plugin, making it known to QGIS.
"""
def name():
    return "send2server"
def description():
    return "Sends a local qgis project and related files to a qgismapserver server installation using FTP"
def version():
    return "Version 0.1"
def icon():
    return "icon.png"
def qgisMinimumVersion():
    return "1.6"
def classFactory(iface):
    # load send2server class from file send2server
    from send2server import send2server
    return send2server(iface)
