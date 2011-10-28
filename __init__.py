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
    return "lizmap"
def description():
    return "Publication plugin for Lizmap web application, by 3liz.com"
def version():
    return "Version 0.1"
def icon():
    return "icon.png"
def qgisMinimumVersion():
    return "1.6"
def classFactory(iface):
    # load lizmap class from file lizmap
    from lizmap import lizmap
    return lizmap(iface)
