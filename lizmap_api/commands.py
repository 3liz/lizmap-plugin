"""
/***************************************************************************
 commands
                                 Lizmap api
 Command line tools for creating lizmap configurations

                                -------------------
        begin                : 2018-07
        copyright            : (C) 2011,2018 by 3liz
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

 The Initial Developer of the Original Code is David Marteau dmarteau@3liz.com
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
import sys
import atexit
import pkg_resources

from .config import LizmapConfig

# We need to keep a reference instance of the qgis_application object
# And not make this object garbage collected
qgis_application = None

def init_qgis(verbose=False):
    """ Initialize qgis application
    """
    from qgis.core import Qgis, QgsApplication
    global qgis_application 

    qgisPrefixPath = os.environ.get('QGIS_PREFIX_PATH','/usr/')
    sys.path.append(os.path.join(qgisPrefixPath, "share/qgis/python/plugins/"))

    # Set offscreen mode when no display 
    # This will prevent Qt tryning to connect to display
    if os.environ.get('DISPLAY') is None:
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'

    qgis_application = QgsApplication([], False )
    qgis_application.setPrefixPath(qgisPrefixPath, True)
    qgis_application.initQgis()

    os.environ['QGIS_PREFIX_PATH'] = qgisPrefixPath

    # Auto cleanup
    @atexit.register
    def extQgis():
        global qgis_application
        if qgis_application:
            qgis_application.exitQgis()
            del qgis_application

    if verbose:
         print(qgis_application.showSettings(),file=sys.stderr)
    
    # Install logging hook
    install_message_hook( verbose )


def install_message_hook( verbose=False ):
    """ Install message log hook
    """
    from qgis.core import Qgis, QgsApplication, QgsMessageLog
    # Add a hook to qgis  message log
    def writelogmessage(message, tag, level):
        arg = '{}: {}'.format( tag, message )
        if level == Qgis.Warning:
            print("Warning: %s" % arg, file=sys.stderr)
        elif level == Qgis.Critical:
            print("Error: %s" % arg, file=sys.stderr)
        elif verbose:
            # Qgis is somehow very noisy
            # log only if verbose is set
            print(arg, file=sys.stderr)

    messageLog = QgsApplication.messageLog()
    messageLog.messageReceived.connect( writelogmessage )



# Command line

__description__="""Generate a Lizmap configuration file from Qgis project"""
__version__="1.0"



def create_config(argv=None):
    """ Create a lizmap configuration file
    """
    import argparse

    try:
        api_version = pkg_resources.get_distribution("lizmap-api").version
    except DistributionNotFound:
        api_version = "0.0.0"

    version = "version %s (api %s)" % (__version__,api_version)
    parser = argparse.ArgumentParser(description=__description__)
    parser.add_argument('project'         , metavar="PATH", help="Qgis project file")
    parser.add_argument('--version'       , action='version', version=version, help="show version and exit")
    parser.add_argument('--template'      , default=None, metavar="PATH", help="Use template")
    parser.add_argument('--server'        , action='store_true', help="Publish attributes table")
    parser.add_argument('--title'         , metavar="NAME", help="Set project title")
    parser.add_argument('--description'   , metavar="TEXT", help="Set project description")
    parser.add_argument('-o', '--output'  , default=None, metavar="PATH", help="Output file")
    parser.add_argument('--verbose'       , action='store_true', help="Verbose mode")
    parser.add_argument('--fix-json'      , action='store_true', help="Fix json syntax")

    args = parser.parse_args(argv)

    init_qgis(verbose=args.verbose)

    config = LizmapConfig(args.project, fix_json=args.fix_json)        

    output = args.project
    if args.output:
        output = args.output

    if args.title:
        config.set_title(args.title)

    if args.description:
        config.set_description(args.description)

    if args.template:
        try:
            from  jinja2 import Template
        except ImportError:
            print("Templates requires Jinja2 package", file=sys.stderr)
            sys.exit(1)

        with open(args.template,'w') as fp:
            tpl = Template(fp.read())

        json_config = config.from_template(tpl)
    else:
       json_config = config.to_json()

    if args.server:
        config.configure_server_options()

    with open(output+'.cfg','w') as fp:
        print("Writing lizmap config")
        fp.write(json_config)

    if config.project.isDirty() or args.output:
        print("Writing project to", args.output)
        config.project.write(output)


