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

import os
import subprocess
import urllib.parse

from os.path import abspath, join

from qgis.core import QgsApplication, QgsProviderRegistry, QgsVectorLayer
from qgis.PyQt.QtCore import QDir

from lizmap.definitions.definitions import LayerProperties


def excluded_providers():
    """List of excluded providers for layer edition.

    :return: List of providers.
    :rtype: list
    """
    providers = QgsProviderRegistry.instance().providerList()
    providers.remove('postgres')
    providers.remove('spatialite')
    return providers


def get_layer_wms_parameters(layer):
    """
    Get WMS parameters for a raster WMS layers
    """
    uri = layer.dataProvider().dataSourceUri()
    # avoid WMTS layers (not supported yet in Lizmap Web Client)
    if 'wmts' in uri or 'WMTS' in uri:
        return None

    # Split WMS parameters
    wms_params = dict((p.split('=') + [''])[:2] for p in uri.split('&'))

    # urldecode WMS url
    wms_params['url'] = urllib.parse.unquote(wms_params['url']).replace('&&', '&').replace('==', '=')

    return wms_params


def is_database_layer(layer) -> bool:
    """ Check if the layer is a database layer.

    It returns True for postgres, spatialite and gpkg files.
    """
    if layer.providerType() in ('postgres', 'spatialite'):
        return True

    uri = QgsProviderRegistry.instance().decodeUri('ogr', layer.source())
    extension = os.path.splitext(uri['path'])[1]
    if extension.lower() == '.gpkg':
        return True

    return False


def layer_property(layer: QgsVectorLayer, item_property: LayerProperties) -> str:
    if item_property == LayerProperties.DataUrl:
        return layer.dataUrl()
    else:
        raise NotImplementedError


def format_qgis_version(qgis_version) -> tuple:
    """ Split a QGIS int version number into major, minor, bugfix.

     If the minor version is a dev version, the next stable minor version is set.
     """
    qgis_version = str(qgis_version)
    major = int(qgis_version[0])
    minor = int(qgis_version[1:3])
    if minor % 2:
        minor += 1
    bug_fix = int(qgis_version[3:])
    return major, minor, bug_fix


def lizmap_user_folder() -> str:
    """ Get the Lizmap user folder.

    If the folder does not exist, it will create it.

    On Linux: .local/share/QGIS/QGIS3/profiles/default/Lizmap
    """
    path = abspath(join(QgsApplication.qgisSettingsDirPath(), 'Lizmap'))

    if not QDir(path).exists():
        QDir().mkdir(path)

    return path


def current_git_hash() -> str:
    """ Retrieve the current git hash number of the git repo (first 6 digit). """
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    git_show = subprocess.Popen(
        'git rev-parse --short=6 HEAD',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        cwd=repo_dir,
        universal_newlines=True,
        encoding='utf8'
    )
    hash_number = git_show.communicate()[0].partition('\n')[0]
    if hash_number == '':
        hash_number = None
    return hash_number


def next_git_tag():
    """ Using Git command, trying to guess the next tag. """
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    git_show = subprocess.Popen(
        'git describe --tags $(git rev-list --tags --max-count=1)',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        cwd=repo_dir,
        universal_newlines=True,
        encoding='utf8'
    )
    tag = git_show.communicate()[0].partition('\n')[0]
    versions = tag.split('.')
    return '{}.{}.{}-pre'.format(versions[0], versions[1], int(versions[2]) + 1)
