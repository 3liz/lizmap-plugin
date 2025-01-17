__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


from qgis.core import (
    QgsMapLayerModel,
    QgsMarkerSymbol,
    QgsProject,
    QgsSymbolLayerUtils,
)
from qgis.PyQt.QtCore import QSize, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QTableWidget,
    QTableWidgetItem,
)

from lizmap.definitions.lizmap_cloud import CLOUD_MAX_PARENT_FOLDER, CLOUD_NAME
from lizmap.definitions.online_help import pg_service_help
from lizmap.definitions.qgis_settings import Settings
from lizmap.toolbelt.i18n import tr

# 10 000 * 10 000
RASTER_COUNT_CELL = 100000000


class Header:

    """ Header in tables. """
    def __init__(self, data: str, label: str, tooltip: str):
        self.data = data
        self.label = label
        self.tooltip = tooltip


class Headers:
    """ List of headers in the table. """

    def __init__(self):
        self.members = []
        self.severity = Header('severity', tr('Severity'), tr("Severity of the error"))
        self.level = Header('level', tr('Level'), tr("Level of the error"))
        self.source = Header('source', tr('Source'), tr("Source of the error"))
        self.error = Header('error', tr('Error'), tr('Description of the error'))
        self.members.append(self.severity)
        self.members.append(self.level)
        self.members.append(self.source)
        self.members.append(self.error)


class Severity:

    """ A level of severity, if it's blocking or not. """
    def __init__(self, data: int, label: str, tooltip: str, color, size: int):
        self.data = data
        self.label = label
        self.color = color
        self.size = size
        self.tooltip = tooltip

    def marker(self) -> QIcon:
        """ Marker used in the table. """
        pixmap = QgsSymbolLayerUtils.symbolPreviewPixmap(
            QgsMarkerSymbol.createSimple(
                {
                    "name": "circle",
                    "color": self.color,
                    "size": "{}".format(self.size),
                }
            ),
            QSize(16, 16)
        )
        return QIcon(pixmap)

    def __str__(self):
        return f'<Severity {self.data} : {self.label}>'

    def __eq__(self, other):
        """ Overrides the default implementation. """
        if not isinstance(other, Severity):
            return False

        return self.data == other.data


class Severities:
    """ List of severities. """
    def __init__(self):
        self.members = []
        self.blocking = Severity(
            0, tr('Blocking'), tr('This is blocking the Lizmap configuration file'), 'red', 3)
        self.important = Severity(
            1, tr('Important'), tr('This is important to fix, to improve performance'), 'orange', 2.5)
        self.normal = Severity(
            2, tr('Normal'), tr('This would be nice to have look'), 'blue', 2)
        self.low = Severity(
            3, tr('Low'), tr('Nice to do'), 'yellow', 2)
        # Some severities can only done on runtime, QGIS version and/or Lizmap Cloud
        self.unknown = Severity(
            99, 'Unknown', 'Severity will be determined on runtime', 'green', 1)
        self.members.append(self.blocking)
        self.members.append(self.important)
        self.members.append(self.normal)
        self.members.append(self.low)
        self.members.append(self.unknown)


class Level:

    """ Level which is raising the issue. Important to set the icon if possible. """
    def __init__(self, data: str, label: str, tooltip: str, icon: QIcon):
        self.data = data
        self.label = label
        self.icon = icon
        self.tooltip = tooltip

    def __str__(self):
        return f'<{self.data} : {self.label}>'


class Levels:

    """ List of levels used. """

    GlobalConfig = Level(
        'global',
        tr('Global'),
        tr('Issue in the global configuration, in QGIS or Lizmap settings'),
        QIcon(':/images/themes/default/console/iconSettingsConsole.svg'),
    )
    Project = Level(
        'project',
        tr('Project'),
        tr('Issue at the project level'),
        QIcon(':/images/themes/default/mIconQgsProjectFile.svg'),
    )
    Layer = Level(
        'layer',
        tr('Layer'),
        tr('Issue at the layer level'),
        QIcon(':/images/themes/default/algorithms/mAlgorithmMergeLayers.svg'),
    )
    Field = Level(
        'field',
        tr('Field'),
        tr('Issue at the field level'),
        QIcon(':/images/themes/default/mSourceFields.svg'),
    )


class Check:

    """ Definition of a check. """
    def __init__(
            self,
            data: str,
            title: str,
            description: str,
            helper: str,
            level: Level,
            severity: Severity,
            icon: QIcon,
            alt_description_lizmap_cloud: str = None,
            alt_help_lizmap_cloud: str = None,
            export_in_json: bool = True,
    ):
        self.data = data
        self.title = title
        self.description = description
        self.alt_description = alt_description_lizmap_cloud
        self.helper = helper
        self.alt_help = alt_help_lizmap_cloud
        self.level = level
        self.severity = severity
        self.icon = icon
        self.export_in_json = export_in_json

    def description_text(self, lizmap_cloud: bool) -> str:
        """ Return the best description of the check, depending on Lizmap Cloud. """
        if lizmap_cloud and self.alt_description:
            return self.alt_description
        else:
            return self.description

    def help_text(self, lizmap_cloud: bool) -> str:
        """ Return the best help of the check, depending on Lizmap Cloud. """
        if lizmap_cloud and self.alt_help:
            return self.alt_help
        else:
            return self.helper

    def html_help(self, index: int, severity: Severity, lizmap_cloud: False) -> str:
        """ HTML string to show in an HTML table. """
        row_class = ''
        if index % 2:
            row_class = "class=\"odd-row\""

        severities = Severities()
        html_str = (
            "<tr {row_class}>"
            "<td>{title}</td>"
            "<td>{description}</td>"
            "<td>{how_to_fix}</td>"
            "<td>{level}</td>"
            "<td>{severity}</td>"
            "</tr>"
        ).format(
            row_class=row_class,
            title=self.title,
            description=self.description_text(lizmap_cloud),
            how_to_fix=self.help_text(lizmap_cloud),
            level=self.level.label,
            severity=severity.label if self.severity == severities.unknown else self.severity.label,
        )
        return html_str

    def html_tooltip(self, lizmap_cloud: bool = False) -> str:
        """ HTML string to be used as a tooltip. """
        html_str = (
            "<strong>{description}</strong>"
            "<br>"
            "<p>{how_to_fix}</p>"
        ).format(
            description=self.description_text(lizmap_cloud),
            how_to_fix=self.help_text(lizmap_cloud),
        )
        return html_str

    def __str__(self):
        return f'<{self.title} : {self.description_text(False)} :{self.level} → {self.severity}>'

    def __eq__(self, other):
        """ Overrides the default implementation. """
        if not isinstance(other, Check):
            return False

        return self.data == other.data


class Checks:

    """ List of checks defined. """

    def __init__(self):
        qgis_auto_fix_button = tr(
            'You can use the auto-fix button in the dedicated panel of the plugin to fix currently '
            'loaded layers'
        )
        other_auth = tr('Either switch to another authentication mechanism')
        safeguard = tr('Or disable this safeguard in your Lizmap plugin settings')
        global_connection = tr(
            'To fix layers loaded <b>later</b>, edit your global PostgreSQL/raster connection to enable this option, then '
            'change the datasource by right clicking on each layer above, then click "Change datasource" in the menu. '
            'Finally reselect your layer in the new dialog with the updated connection. When opening a QGIS project in '
            'your computer, with a fresh launched QGIS software, you mustn\'t have any prompt for a user or password. '
            'The edited connection will take effect only on newly added layer into a project that\'s why the '
            'right-click step is required.'
        )
        either_move_file = tr('Either move the file used for the layer')
        move_file = tr('Move the file used for the layer')
        sql_example = "SELECT (row_number() OVER ())::integer AS id"

        self.OgcValid = Check(
            'ogc_validity',
            tr('OGC validity (QGIS server)'),
            tr(
                "According to OGC standard, the project is not valid."
            ),
            (
                '<ul>'
                '<li>{project_properties}</li>'
                '<li>{project_shortname}</li>'
                '<li>{layer_shortname}</li>'
                '<li>{group_shortname}</li>'
                '</ul>'
            ).format(
                project_properties=tr(
                    "Open the 'Project properties', then 'QGIS Server' tab, at the bottom, you can check your project "
                    "according to OGC standard"
                ),
                layer_shortname=tr(
                    "If you need to fix a layer shortname, go to the 'Layer properties' "
                    "for the given layer, then 'QGIS Server' tab, edit the shortname."
                ),
                project_shortname=tr(
                    "If you need to fix the project shortname, go to the 'Project properties', "
                    "then 'QGIS Server' tab, first tab, and change the shortname."
                ),
                group_shortname=tr(
                    "If you need to fix a group shortname, right-click on the group in the legend and then "
                    "'Set Group WMS data…' and change the shortname."
                )
            ),
            Levels.Project,
            Severities().important,
            QIcon(':/images/themes/default/mIconWms.svg'),
        )
        self.PluginDesktopVersion = Check(
            'outdated_plugin_version',
            tr('QGIS desktop Lizmap plugin outdated'),
            tr(
                "The QGIS desktop Lizmap plugin is not up to date. A new plugin version is available. You should "
                "check from time to time your QGIS plugin manager."
            ),
            (
                '<ul>'
                '<li>{}</li>'
                '</ul>'
            ).format(
                tr("Upgrade your plugin in QGIS Desktop"),
            ),
            Levels.GlobalConfig,
            Severities().important,
            QIcon(':/images/icons/qgis_icon.svg'),
        )
        self.ServerVersion = Check(
            'old_qgis_server_version',
            tr('QGIS server version is lower than QGIS desktop version'),
            tr(
                "QGIS desktop is writing QGS project file in the future compare to QGIS server. QGIS server might not "
                "be able to read the file correctly. Versions between desktop and server must be equal, or QGIS server "
                "can have a newer version."
            ),
            (
                '<ul>'
                '<li>{upgrade}</li>'
                '<li>{downgrade}</li>'
                '</ul>'
            ).format(
                upgrade=tr("Either upgrade your QGIS Server"),
                downgrade=tr("Or downgrade your QGIS Desktop"),
            ),
            Levels.GlobalConfig,
            Severities().important,
            QIcon(':/images/icons/qgis_icon.svg'),
            (
                '<ul>'
                '<li>{upgrade}</li>'
                '<li>{downgrade}</li>'
                '</ul>'
            ).format(
                upgrade=tr(
                    "Either check if an upgrade of QGIS server is available in Lizmap Web Client, in the "
                    "administration panel. Current LTR versions should be available."
                ),
                downgrade=tr("Or downgrade your QGIS Desktop"),
            ),
            # A CFG file can be moved between server, and mainly because the LWC is already checking by itself between
            # QGIS Desktop in XML versus QGIS Server settings
            export_in_json=False,
        )
        self.PkInt8 = Check(
            'primary_key_bigint',
            tr('Invalid bigint (integer8) field for QGIS Server as primary key'),
            tr(
                "Primary key should be an integer. If not fixed, expect layer to have some issues with some tools in "
                "Lizmap Web Client: zoom to feature, filtering…"
            ),
            (
                '<ul>'
                '<li>{help}</li>'
                '<li>{sql}</li>'
                '</ul>'
            ).format(
                help=tr(
                    "We highly recommend you to set a proper integer field as a primary key, but neither a bigint nor "
                    "an integer8."
                ),
                sql=tr("For PostgreSQL, it's possible to cast a view with : ") + sql_example,
            ),
            Levels.Layer,
            Severities().important,
            QIcon(':/images/themes/default/mIconFieldInteger.svg'),
        )
        self.PkVarchar = Check(
            'primary_key_varchar',
            tr('Invalid varchar field for QGIS Server as primary key'),
            tr(
                "Primary key should be an integer. If not fixed, expect layer to have some issues with some tools in "
                "Lizmap Web Client: zoom to feature, filtering…"
            ),
            (
                '<ul>'
                '<li>{help}</li>'
                '<li>{sql}</li>'
                '</ul>'
            ).format(
                help=tr(
                    "We highly recommend you to set a proper integer field as a primary key, but neither a bigint nor "
                    "an integer8."
                ),
                sql=tr("For PostgreSQL, it's possible to cast a view with : ") + sql_example,
            ),
            Levels.Layer,
            Severities().important,
            QIcon(':/images/themes/default/mIconFieldInteger.svg'),
        )
        self.MissingPk = Check(
            'missing_primary_key',
            tr('Missing a proper primary key in the database.'),
            tr(
                "The layer must have a proper primary key defined. When it's missing, QGIS Desktop tried to set a "
                "temporary field called 'tid/ctid/…' to be a unique identifier. On QGIS Server, this will bring issues."
            ),
            (
                '<ul>'
                '<li>{help}</li>'
                '</ul>'
            ).format(
                help=tr(
                    "We highly recommend you to set a proper integer field as a primary key, but neither a bigint nor "
                    "an integer8."
                ),
            ),
            Levels.Layer,
            Severities().important,
            QIcon(':/images/themes/default/mSourceFields.svg'),
        )
        self.SSLConnection = Check(
            'ssl_connection',
            tr('SSL connections to a PostgreSQL database'),
            tr("Connections to a PostgreSQL database hosted on {} must use a SSL secured connection.").format(CLOUD_NAME),
            (
                '<ul>'
                '<li>{auto_fix}</li>'
                '<li>{help}</li>'
                '</ul>'
            ).format(
                auto_fix=qgis_auto_fix_button,
                help=global_connection,
            ),
            Levels.Layer,
            Severities().blocking,
            QIcon(':/images/themes/default/mIconPostgis.svg'),
        )
        self.EstimatedMetadata = Check(
            'estimated_metadata',
            tr('Estimated metadata'),
            tr("PostgreSQL layer can have the use estimated metadata option enabled"),
            (
                '<ul>'
                '<li>{auto_fix}</li>'
                '<li>{help}</li>'
                '</ul>'
            ).format(
                auto_fix=qgis_auto_fix_button,
                help=global_connection,
            ),
            Levels.Layer,
            Severities().blocking,
            QIcon(':/images/themes/default/mIconPostgis.svg'),
        )
        self.SimplifyGeometry = Check(
            'simplify_geometry',
            tr('Simplify geometry on the provider side'),
            tr("PostgreSQL layer can have the geometry simplification on the server side enabled"),
            (
                '<ul>'
                '<li>{auto_fix}</li>'
                '<li>{help}</li>'
                '</ul>'
            ).format(
                auto_fix=qgis_auto_fix_button,
                help=tr(
                    'Visit the layer properties, then in the "Rendering" tab to enable it simplification on the provider '
                    'side on the given layer.'
                ),
            ),
            Levels.Layer,
            Severities().blocking,
            QIcon(':/images/themes/default/mIconGeometryCollectionLayer.svg'),
        )
        self.RasterWithoutPyramid = Check(
            'raster_without_pyramid',
            tr('Raster is missing a pyramid'),
            tr(
                "The raster has more than {count} cells and is missing a pyramid. A pyramid is important for "
                "performances for this raster."
            ).format(count=RASTER_COUNT_CELL),
            (
                '<ul>'
                '<li>{help}</li>'
                '</ul>'
            ).format(
                help=tr(
                    "In the raster properties, pyramids panel, it's possible to create it."
                ),
            ),
            Levels.Layer,
            Severities().blocking,
            QIcon(':/images/themes/default/mIconNoPyramid.svg'),
        )
        self.FrenchGeoPlateformeUrl = Check(
            'french_geopf_url',
            tr('French Géoplateforme URL contains an authentification token'),
            (
                "Le raster utilise le système d'authentification de QGIS. Ce système n'est pas compatible avec QGIS "
                "Server. Quelque soit votre version de QGIS, vous devez utiliser la méthode pour une version "
                "antérieure à QGIS 3.28 sur le lien ci-dessous."
            ),
            (
                '<ul>'
                '<li>'
                'Visiter la documentation sur <a href="{french_url}">le site de l\'IGN</a> en suivant la '
                'documentation pour la version antérieur à 3.28.'
                '</li>'
                '<li>{french_url}</li>'
                '</ul>'
            ).format(
                french_url=(
                    "https://geoservices.ign.fr/documentation/services/utilisation-sig/tutoriel-qgis/"
                    "gpf-wms-wmts-donneesnonlibres"
                ),
            ),
            Levels.Layer,
            Severities().blocking,
            QIcon(':images/flags/fr.svg'),
        )
        self.CrsInvertedAxis = Check(
            'crs_has_inverted_axis',
            tr('The project CRS has inverted axis'),
            tr(
                "The current project CRS has inverted axis. Due to a bug in the stack between QGIS Server, Proj4js, "
                "OpenLayers 8 and Lizmap Web Client ≥ 3.7.0 and Lizmap Web Client < 3.7.4, using a CRS with inverted "
                "axis is discouraged. Tiles might be transparent."),
            (
                '<ul>'
                '<li>{}</li>'
                '<li>{}</li>'
                '</ul>'
            ).format(
                tr('Switch to a CRS having not inverted axis.'),
                tr('Upgrade your Lizmap Web Client to latest 3.7.'),
            ),
            Levels.Project,
            Severities().important,
            QIcon(':/images/themes/default/propertyicons/CRS.svg'),
        )
        self.DuplicatedRuleKeyLegend = Check(
            'duplicated_rule_key_legend',
            tr('The layer has some duplicated "key" in the legend'),
            tr(
                "Due to a previous bug in QGIS, the project has some duplicated rule key in the legend."
            ), (
                '<ol>'
                '<li>{}</li>'
                '<li>{}</li>'
                '<li>{}</li>'
                '<li>{}</li>'
                '<li>{}</li>'
                '<li>{}</li>'
                '</ol>'
            ).format(
                tr(
                    'Open the last tab in this panel, to have raw HTML logs, '
                    'you have a table showing all duplicated keys'),
                tr('Close your project in QGIS Desktop'),
                tr('Open a file editor for editing the QGS XML file manually'),
                tr(
                    'Look for all occurrences of \'key="{KEY SHOWN IN THE TABLE}"\' '
                    'and make sure all these keys are unique.'
                ),
                tr('After saving your file in the text editor, open it again in QGIS Desktop'),
                tr('Validation should be OK'),
            ),
            Levels.Layer,
            Severities().important,
            QIcon(':/images/themes/default/rendererRuleBasedSymbol.svg'),
        )
        self.DuplicatedRuleKeyLabelLegend = Check(
            'duplicated_labels_legend',
            tr('The layer has some duplicated "labels" within its own legend'),
            tr(
                "The layer should not have duplicated labels within its own legend. This is a limitation on "
                "QGIS Server."
            ), (
                '<ul>'
                '<li>{}</li>'
                '<li>{}</li>'
                '</ul>'
            ).format(
                tr(
                    'Open the last tab in this panel, to have raw HTML logs, '
                    'you have a table showing all duplicated labels'
                ),
                tr('Make these labels unique'),
            ),
            Levels.Layer,
            Severities().important,
            QIcon(':/images/themes/default/legend.svg'),
        )
        self.DuplicatedLayerFilterLegend = Check(
            'duplicated_layers_with_different_filters',
            tr('Many layers next to each other having different filters.'),
            tr(
                "Many layers have been detected being next to each other in the legend, but having different filters "
                "(the funnel icon). This is discouraged because checkboxes are supported within the same layer."
            ), (
                '<ol>'
                '<li>{}</li>'
                '<li>{}</li>'
                '</ol>'
            ).format(
                tr(
                    'Open the last tab in this panel, to have raw HTML logs, '
                    'you have a table showing all duplicated layers'),
                tr(
                    'Remove one of the duplicated layer and remove the filter on the other one.'
                ),
            ),
            Levels.Layer,
            Severities().important,
            QIcon(':/images/themes/default/mActionFilter2.svg'),
        )
        self.MissingWfsLayer = Check(
            'layer_not_in_wfs',
            tr('Layer not published in the WFS'),
            tr("The layer is used in one of the Lizmap tool, the layer needs to be in the WFS for Lizmap"),
            (
                '<ul>'
                '<li>{}</li>'
                '<li>{}</li>'
                '</ul>'
            ).format(
                tr('Either enable WFS on this layer (Project properties, then "QGIS server" tab)'),
                tr('Or remove this layer from a tool in Lizmap')
            ),
            Levels.Layer,
            Severities().blocking,
            QIcon(':/images/themes/default/mIconWfs.svg'),
        )
        self.MissingWfsField = Check(
            'field_not_in_wfs',
            tr('Field not published in the WFS'),
            tr(
                "The field is used in one the Lizmap tool (attribute table, dataviz, etc. This field must be published "
                "in the WFS."),
            (
                '<ul>'
                '<li>{}</li>'
                '<li>{}</li>'
                '</ul>'
            ).format(
                tr('Either enable this field in the WFS (layer properties, then in the "Field" tab'),
                tr('Or remove this field from a tool in Lizmap')
            ),
            Levels.Field,
            Severities().blocking,
            QIcon(':/images/themes/default/mIconWfs.svg'),
        )
        self.DuplicatedLayerNameOrGroup = Check(
            'duplicated_layer_name_or_group',
            tr('Duplicated layer name or group'),
            tr("It's not possible to store all the Lizmap configuration for these layer(s) or group(s)."),
            (
                '<ul>'
                '<li>{}</li>'
                '<li>{}</li>'
                '</ul>'
            ).format(
                tr('You must change them to make them unique'),
                tr('Reconfigure their settings in the "Layers" tab of the plugin')
            ),
            Levels.Project,
            Severities().important,
            QIcon(':/images/themes/default/propertyicons/editmetadata.svg'),
        )
        self.WmsUseLayerIds = Check(
            'wms_use_layer_id',
            tr('Do not use layer IDs as name'),
            tr(
                "It's not possible anymore to use the option 'Use layer IDs as name' in the project properties dialog, "
                "QGIS server tab, then WMS capabilities."
            ),
            '<ul><li>{help}</li></ul>'.format(
                help=tr("Uncheck this checkbox and re-save the Lizmap configuration file")
            ),
            Levels.Project,
            Severities().blocking,
            QIcon(':/images/themes/default/mIconWms.svg'),
        )
        self.LayerMissingApiKey = Check(
            'layer_without_api_key',
            tr('Missing API key'),
            tr(
                "The layer requires an API key to be exposed on the internet but the Lizmap configuration is missing "
                "the API key. The layer will be discarded "
                "on the server side."
            ),
            (
                '<ul>'
                '<li>{}</li>'
                '<li>{}</li>'
                '<li>{}</li>'
                '</ul>'.format(
                    tr("Either add the API key for this provider"),
                    tr('Or remove the layer.'),
                    tr(
                        'Or disable these API checks using environment variables on the server side of the Lizmap '
                        'server plugin.'
                    ),
                )
            ),
            Levels.Layer,
            Severities().low,
            QIcon(':/images/themes/default/locked.svg'),
            (
                '<ul>'
                '<li>{}</li>'
                '<li>{}</li>'
                '</ul>'.format(
                    tr("Either add the API key for this provider"),
                    tr('Or remove the layer.'),
                )
            ),
        )
        self.TrustProject = Check(
            'trust_project_metadata',
            tr('Trust project metadata'),
            tr('The project does not have the "Trust project metadata" enabled at the project level'),
            (
                '<ul>'
                '<li>{auto_fix}</li>'
                '<li>{help}</li>'
                '</ul>'.format(
                    help=tr(
                        'In the project properties → Data sources → at the bottom, there is a checkbox to trust the '
                        'project when the layer has no metadata.'
                    ),
                    auto_fix=tr('You can use the auto-fix button in the dedicated panel of the plugin'),
                )
            ),
            Levels.Project,
            Severities().blocking,
            QIcon(':/images/themes/default/mIconQgsProjectFile.svg'),
        )
        self.EmptyBaseLayersGroup = Check(
            'empty_baselayers_group',
            tr('Empty "baselayers" group'),
            tr('The group "baselayers" cannot be empty.'),
            (
                '<ul>'
                '<li>{}</li>'
                '<li>{}</li>'
                '</ul>'.format(
                    tr("Either add some layers in it"),
                    tr('Or remove it.'),
                )
            ),
            Levels.Project,
            Severities().blocking,
            QIcon(':/images/themes/default/mIconQgsProjectFile.svg'),
        )
        self.LeadingTrailingSpaceLayerGroupName = Check(
            'leading_trailing_space',
            tr('Leading/trailing space in layer/group name'),
            tr(
                'The layer/group name has some leading/trailing spaces. It must be removed and the configuration in the '
                'plugin might be needed.'
            ), (
                '<ul>'
                '<li>{edit_layer}</li>'
                '</ul>'.format(
                    edit_layer=tr('Rename your layer/group to remove leading/trailing spaces (left and right)'),
                )
            ),
            Levels.Layer,
            Severities().blocking,
            QIcon(':/images/themes/default/algorithms/mAlgorithmMergeLayers.svg'),
        )
        self.PreventEcw = Check(
            Settings.PreventEcw,
            tr('ECW raster'),
            tr(
                'The layer is using the ECW raster format. Because of the ECW\'s licence, this format is not compatible '
                'with most of QGIS server installations. You have activated a safeguard about preventing you using an '
                'ECW layer.'),
            (
                '<ul>'
                '<li>{help}</li>'
                '<li>{other}</li>'
                '</ul>'.format(
                    help=tr('Either switch to a COG format'),
                    other=safeguard,
                )
            ),
            Levels.Layer,
            Severities().unknown,
            QIcon(':/images/themes/default/mIconRasterLayer.svg'),
            tr(
                'The layer is using an ECW raster format. Because of the ECW\'s licence, this format is not compatible '
                'with QGIS server.'
            ),
            (
                '<ul>'
                '<li>{help}</li>'
                '</ul>'
            ).format(help=tr('Switch to a COG format'))
        )
        self.RasterAuthenticationDb = Check(
            f"{Settings.PreventPgAuthDb}_raster",
            tr('QGIS Authentication database'),
            tr(
                'The layer is using the QGIS authentication database. You have activated a safeguard preventing you '
                'using the QGIS authentication database.'
            ),
            (
                '<ul>'
                '<li>{help}</li>'
                '<li>{other}</li>'
                '<li>{global_connection}</li>'
                '</ul>'.format(
                    help=other_auth,
                    other=safeguard,
                    global_connection=global_connection,
                )
            ),
            Levels.Layer,
            Severities().unknown,
            QIcon(':/images/themes/default/mIconPostgis.svg'),
            tr('The layer is using the QGIS authentication database. This is not compatible with {}').format(CLOUD_NAME),
            (
                '<ul>'
                '<li>{login_pass}</li>'
                '</ul>'
            ).format(
                login_pass=tr(
                    'Store the login and password in the layer by editing the global connection and do the '
                    '"Change datasource" on each layer.'
                )
            )
        )
        self.AuthenticationDb = Check(
            Settings.PreventPgAuthDb,
            tr('QGIS Authentication database'),
            tr(
                'The layer is using the QGIS authentication database. You have activated a safeguard preventing you using '
                'the QGIS authentication database.'
            ),
            (
                '<ul>'
                '<li>{help}</li>'
                '<li>{other}</li>'
                '<li>{global_connection}</li>'
                '</ul>'.format(
                    help=other_auth,
                    other=safeguard,
                    global_connection=global_connection,
                )
            ),
            Levels.Layer,
            Severities().unknown,
            QIcon(':/images/themes/default/mIconPostgis.svg'),
            tr('The layer is using the QGIS authentication database. This is not compatible with {}').format(CLOUD_NAME),
            (
                '<ul>'
                '<li>{service}</li>'
                '<li>{login_pass}</li>'
                '</ul>'
            ).format(
                service=tr('Either use a PostgreSQL service'),
                login_pass=tr('Or store the login and password in the layer.')
            )
        )
        self.PgService = Check(
            Settings.PreventPgService,
            tr('PostgreSQL service'),
            tr(
                'Using a PostgreSQL service file is recommended in many cases, but it requires a configuration step. '
                'If you have done the configuration (on the server side mainly), you can disable this safeguard.'
            ),
            (
                '<ul>'
                '<li>{help}</li>'
                '<li>{other}</li>'
                '<li>{doc}</li>'
                '<li>{global_connection}</li>'
                '</ul>'.format(
                    help=other_auth,
                    other=safeguard,
                    doc=pg_service_help().toString(),  # Sorry, the link is not easily clickable in a QTextEdit
                    global_connection=global_connection,
                )
            ),
            Levels.Layer,
            Severities().unknown,
            QIcon(':/images/themes/default/mIconPostgis.svg'),
        )
        self.PgForceUserPass = Check(
            Settings.ForcePgUserPass,
            tr('PostgreSQL user and/or password'),
            tr(
                'The layer is missing some credentials, either user and/or password.'
            ),
            (
                '<ul>'
                '<li>{edit_layer}</li>'
                '<li>{help}</li>'
                '<li>{other}</li>'
                '<li>{global_connection}</li>'
                '</ul>'.format(
                    edit_layer=tr('Edit your layer configuration by force saving user&password'),
                    help=other_auth,
                    other=safeguard,
                    global_connection=global_connection,
                )
            ),
            Levels.Layer,
            Severities().unknown,
            QIcon(':/images/themes/default/mIconPostgis.svg'),
        )
        self.PreventDrive = Check(
            Settings.PreventDrive,
            tr('Other drive (network or local)'),
            tr('The layer is stored on another drive.'),
            (
                '<ul>'
                '<li>{help}</li>'
                '<li>{other}</li>'
                '</ul>'.format(
                    help=either_move_file,
                    other=safeguard,
                )
            ),
            Levels.Layer,
            Severities().unknown,
            QIcon(':/qt-project.org/styles/commonstyle/images/networkdrive-16.png'),
            tr('The layer is stored on another drive, which is not possible using {}.').format(CLOUD_NAME),
            (
                '<ul>'
                '<li>{help}</li>'
                '</ul>'
            ).format(
                help=move_file,
            )
        )
        self.PreventParentFolder = Check(
            Settings.AllowParentFolder,
            tr('Parent folder'),
            tr('The layer is stored in too many parent\'s folder, compare to the QGS file.'),
            (
                '<ul>'
                '<li>{help}</li>'
                '<li>{other}</li>'
                '</ul>'.format(
                    help=either_move_file,
                    other=safeguard,
                )
            ),
            Levels.Layer,
            Severities().unknown,
            QIcon(':/images/themes/default/mIconFolderOpen.svg'),
            tr('The layer is stored in too many parent\'s folder, compare to the QGS file.'),
            (
                '<ul>'
                '<li>{help}</li>'
                '<li>{other}</li>'
                '<li>{fyi}</li>'
                '</ul>'
            ).format(
                help=either_move_file,
                other=safeguard,
                fyi=tr(
                    'For your information, the maximum of parents is {count} on {hosting_name}. This will be overriden '
                    'on runtime if you use a higher value according to the server selected in the first panel.'
                ).format(
                    count=CLOUD_MAX_PARENT_FOLDER,
                    hosting_name=CLOUD_NAME
                ),
            )
        )

    def html(self, severity: Severity, lizmap_cloud: bool) -> str:
        """ Generate an HTML table, according to the instance. """
        html_str = '<table class=\"tabular-view\" width=\"100%\">'
        html_str += (
            '<tr><th>{title}</th><th>{description}</th><th>{howto}</th><th>{level}</th><th>{severity}</th></tr>'
        ).format(
            title=tr('Title'),
            description=tr('Description'),
            howto=tr('How to fix'),
            level=tr('Level'),
            severity=tr('Severity'),
        )
        copy_sort = list(self.__dict__.values())
        copy_sort = [c for c in copy_sort if isinstance(c, Check)]
        copy_sort.sort(key=lambda x: severity.data if x.severity == Severities().unknown else x.severity.data)
        for i, check in enumerate(copy_sort):
            html_str += check.html_help(i, severity, lizmap_cloud)
        html_str += '</table>'
        return html_str


class Source:

    def __init__(self, name):
        self.name = name


class SourceLayer(Source):

    """ For identifying a layer in a project. """
    def __init__(self, name, layer_id):
        super().__init__(name)
        self.layer_id = layer_id


class SourceField(Source):

    """ For identifying a field in a layer in a project. """
    def __init__(self, name, layer_id: str):
        super().__init__(name)
        self.layer_id = layer_id


class SourceGroup(Source):

    """ For identifying a group in a project. """
    def __init__(self, name):
        super().__init__(name)


class SourceType:

    """ List of sources in the project. """

    Field = SourceField
    Layer = SourceLayer
    Group = SourceGroup


class Error:

    """ An error is defined by a check and a source. """
    def __init__(self, source: str, check: Check, source_type=None):
        self.source = source
        self.check = check
        self.source_type = source_type

    def __str__(self):
        return f'<{self.source} : {self.check}>'


class TableCheck(QTableWidget):

    """ Subclassing of QTableWidget in the plugin. """

    # noinspection PyUnresolvedReferences
    DATA = Qt.ItemDataRole.UserRole
    JSON = DATA + 1
    EXPORT = JSON + 1

    def setup(self):
        """ Setting up parameters. """
        # Do not use the constructor __init__, it's not working. Maybe because of UI files ?

        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setVisible(True)
        # Bug, same as self.sort()
        # self.setSortingEnabled(True)

        headers = Headers()
        self.setColumnCount(len(headers.members))
        for i, header in enumerate(headers.members):
            column = QTableWidgetItem(header.label)
            column.setToolTip(header.tooltip)
            self.setHorizontalHeaderItem(i, column)

    def truncate(self):
        """ Truncate the table. """
        self.setRowCount(0)

    def has_blocking(self) -> bool:
        """ If the table has at least one blocking issue. """
        for row in range(self.rowCount()):
            if self.item(row, 0).data(self.DATA) == 0:
                return True
        return False

    def has_importants(self) -> int:
        """ If the table has at least one important issue. """
        count = 0
        for row in range(self.rowCount()):
            if self.item(row, 0).data(self.DATA) == 1:
                count += 1
        return count

    def has_rows(self) -> int:
        """ If the table has at least one row displayed. """
        return self.rowCount()

    def sort(self):
        """ Sort the table by severity. """
        # Strange bug occurring when we launch the analysis on the second time
        # Lines are disappearing
        # self.sortByColumn(0, Qt.AscendingOrder)
        pass

    def to_json(self) -> list:
        """ Export data to JSON. """
        result = []

        headers = Headers()
        for row in range(self.rowCount()):
            data = dict()
            for i, header in enumerate(headers.members):
                data[header.data] = self.item(row, i).data(self.JSON)
            result.append(data)

        return result

    def to_json_summarized(self) -> dict:
        """ Export a sum up of warnings to JSON. """
        result = {}
        for row in range(self.rowCount()):
            if not self.item(row, 1).data(self.EXPORT):
                continue
            error_id = self.item(row, 3).data(self.JSON)
            if error_id not in result.keys():
                result[error_id] = 1
            else:
                result[error_id] += 1
        return result

    def to_markdown_summarized(self) -> str:
        """ Export a sum up of warnings to Markdown. """
        result = {}
        for row in range(self.rowCount()):
            error_name = self.item(row, 3).data(Qt.ItemDataRole.DisplayRole)
            if error_name not in result.keys():
                result[error_name] = 1
            else:
                result[error_name] += 1

        text = 'Validation summarized :\n\n'
        for error_name, count in result.items():
            text += '* {} → {}\n'.format(error_name, count)
        text += '\n'
        return text

    def add_error(self, error: Error, lizmap_cloud: bool = False, severity=None, icon=None):
        """ Add an error in the table. """
        # By default, let's take the one in the error
        used_severity = error.check.severity
        if used_severity == Severities().unknown:
            if severity:
                # The given severity is overridden the one in the error
                used_severity = severity
            else:
                raise NotImplementedError('Missing severity level')

        row = self.rowCount()
        self.setRowCount(row + 1)

        column = 0

        # Severity
        item = QTableWidgetItem(used_severity.label)
        item.setData(self.DATA, used_severity.data)
        item.setData(self.JSON, used_severity.data)
        item.setToolTip(used_severity.tooltip)
        item.setIcon(used_severity.marker())
        self.setItem(row, column, item)
        column += 1

        # Level
        item = QTableWidgetItem(error.check.level.label)
        item.setData(self.DATA, error.check.level.data)
        item.setData(self.JSON, error.check.level.data)
        item.setData(self.EXPORT, error.check.export_in_json)
        item.setToolTip(error.check.level.tooltip)
        item.setIcon(error.check.level.icon)
        self.setItem(row, column, item)
        column += 1

        # Source
        item = QTableWidgetItem(error.source)
        item.setToolTip(error.source)
        item.setData(self.DATA, error.source)
        if isinstance(error.source_type, SourceType.Layer):
            item.setToolTip(error.source_type.layer_id)
            layer = QgsProject.instance().mapLayer(error.source_type.layer_id)
            item.setIcon(QgsMapLayerModel.iconForLayer(layer))
            item.setData(self.JSON, error.source_type.layer_id)
        elif isinstance(error.source_type, SourceType.Group):
            item.setToolTip(error.source_type.name)
            item.setIcon(QIcon(":images/themes/default/mActionFolder.svg"))
            item.setData(self.JSON, error.source_type.name)
        elif isinstance(error.source_type, SourceType.Field):
            layer = QgsProject.instance().mapLayer(error.source_type.layer_id)
            item.setToolTip(tr(
                'Field "{}" in layer name "{}"'
            ).format(error.source_type.name, layer.name()))
            # Override the text
            item.setText('{} ({})'.format(error.source, layer.name()))
            index = layer.fields().indexFromName(error.source_type.name)
            item.setIcon(layer.fields().iconForField(index))
            item.setData(self.JSON, error.source_type.name)
        else:
            # TODO fix else
            item.setData(self.JSON, error.source)

            if icon:
                item.setIcon(icon)

        self.setItem(row, column, item)
        column += 1

        # Error
        item = QTableWidgetItem(error.check.title)
        item.setData(self.DATA, error.source)
        item.setData(self.JSON, error.check.data)
        item.setToolTip(error.check.html_tooltip(lizmap_cloud))
        if error.check.icon:
            item.setIcon(error.check.icon)
        self.setItem(row, column, item)
        column += 1
