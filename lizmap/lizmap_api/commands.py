__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import atexit
import os
import sys

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

def api_version():
    try:
        return pkg_resources.get_distribution("lizmap-api").version
    except DistributionNotFound:
        return "0.0.0"

def create_config(argv=None):
    """ Create a lizmap configuration file
    """
    import argparse

    version = "version %s (api %s)" % (__version__,api_version())
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
            from jinja2 import Template
        except ImportError:
            print("Templates requires Jinja2 package", file=sys.stderr)
            sys.exit(1)

        with open(args.template) as fp:
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
