__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from enum import Enum

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
from lizmap.definitions.qgis_settings import Settings
from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.tools import qgis_version


class Header:

    """ Header in tables. """
    def __init__(self, data: str, label: str, tooltip: str):
        self.data = data
        self.label = label
        self.tooltip = tooltip


class Headers(Header, Enum):
    """ List of headers in the table. """
    Severity = 'severity', tr('Severity'), tr("Severity of the error")
    Level = 'level', tr('Level'), tr("Level of the error")
    Object = 'source', tr('Source'), tr("Source of the error")
    Error = 'error', tr('Error'), tr('Description of the error')


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


class Severities(Severity, Enum):
    """ List of severities. """
    Blocking = 0, tr('Blocking'), tr('This is blocking the Lizmap configuration file'), 'red', 3
    Important = 1, tr('Important'), tr('This is important to fix, to improve performance'), 'orange', 2.5
    # Normal = 2, tr('Normal'), tr('This would be nice to have look'), 'blue', 2
    Low = 3, tr('Low'), tr('Nice to do'), 'yellow', 2
    # Some severities can only done on runtime, QGIS version and/or Lizmap Cloud
    Unknown = 99, 'Unknown', 'Severity will be determined on runtime', 'green', 1


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
            severity=severity.label if self.severity == Severities.Unknown else self.severity.label,
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


# Check QGIS_VERSION_INT
qgis_32200 = tr(
    'With QGIS ≥ 3.22, you can use the auto-fix button in the "Settings" panel of the plugin to fix currently loaded '
    'layers'
)
other_auth = tr('Either switch to another authentication mechanism')
safeguard = tr('Or disable this safeguard in your Lizmap plugin settings')
global_connection = tr(
    'To fix layers loaded <b>later</b>, edit your global PostgreSQL connection to enable this option, then change the '
    'datasource by right clicking on each layer above, then click "Change datasource" in the menu. Finally reselect '
    'your layer in the new dialog with the updated connection. When opening a QGIS project in your computer, with a '
    'fresh launched QGIS software, you mustn\'t have any prompt for a user or password. '
    'The edited connection will take effect only on newly added layer into a project that\'s why the right-click step '
    'is required.'
)
either_move_file = tr('Either move the file used for the layer')
move_file = tr('Move the file used for the layer')


class Checks(Check, Enum):

    """ List of checks defined. """

    OgcValid = (
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
        ),
        Levels.Project,
        Severities.Low,
        QIcon(':/images/themes/default/mIconWms.svg'),
    )
    PkInt8 = (
        'primary_key_bigint',
        tr('Invalid bigint (integer8) field for QGIS Server as primary key'),
        tr(
            "Primary key should be an integer. If not fixed, expect layer to have some issues with some tools in "
            "Lizmap Web Client: zoom to feature, filtering…"
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
        Severities.Important,
        QIcon(':/images/themes/default/mIconFieldInteger.svg'),
    )
    MissingPk = (
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
        Severities.Important,
        QIcon(':/images/themes/default/mSourceFields.svg'),
    )
    SSLConnection = (
        'ssl_connection',
        tr('SSL connections to a PostgreSQL database'),
        tr("Connections to a PostgreSQL database hosted on {} must use a SSL secured connection.").format(CLOUD_NAME),
        (
            '<ul>'
            '<li>{auto_fix}</li>'
            '<li>{help}</li>'
            '</ul>'
        ).format(
            auto_fix=qgis_32200,
            help=global_connection,
        ),
        Levels.Layer,
        Severities.Blocking if qgis_version() >= 32200 else Severities.Important,
        QIcon(':/images/themes/default/mIconPostgis.svg'),
    )
    EstimatedMetadata = (
        'estimated_metadata',
        tr('Estimated metadata'),
        tr("PostgreSQL layer can have the use estimated metadata option enabled"),
        (
            '<ul>'
            '<li>{auto_fix}</li>'
            '<li>{help}</li>'
            '</ul>'
        ).format(
            auto_fix=qgis_32200,
            help=global_connection,
        ),
        Levels.Layer,
        Severities.Blocking if qgis_version() >= 32200 else Severities.Important,
        QIcon(':/images/themes/default/mIconPostgis.svg'),
    )
    SimplifyGeometry = (
        'simplify_geometry',
        tr('Simplify geometry on the provider side'),
        tr("PostgreSQL layer can have the geometry simplification on the server side enabled"),
        (
            '<ul>'
            '<li>{auto_fix}</li>'
            '<li>{help}</li>'
            '</ul>'
        ).format(
            auto_fix=qgis_32200,
            help=tr(
                'Visit the layer properties, then in the "Rendering" tab to enable it simplification on the provider '
                'side on the given layer.'
            ),
        ),
        Levels.Layer,
        Severities.Blocking if qgis_version() >= 32200 else Severities.Important,
        QIcon(':/images/themes/default/mIconGeometryCollectionLayer.svg'),
    )
    DuplicatedLayerNameOrGroup = (
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
        Severities.Important,
        QIcon(':/images/themes/default/propertyicons/editmetadata.svg'),
    )
    WmsUseLayerIds = (
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
        Severities.Blocking,
        QIcon(':/images/themes/default/mIconWms.svg'),
    )
    TrustProject = (
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
                auto_fix=tr('With QGIS ≥ 3.22, you can use the auto-fix button in the "Settings" panel of the plugin'),
            )
        ),
        Levels.Project,
        Severities.Blocking if qgis_version() >= 32200 else Severities.Important,
        QIcon(':/images/themes/default/mIconQgsProjectFile.svg'),
    )
    PreventEcw = (
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
        Severities.Unknown,
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
    AuthenticationDb = (
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
        Severities.Unknown,
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
    PgService = (
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
            '<li>{global_connection}</li>'
            '</ul>'.format(
                help=other_auth,
                other=safeguard,
                global_connection=global_connection,
            )
        ),
        Levels.Layer,
        Severities.Unknown,
        QIcon(':/images/themes/default/mIconPostgis.svg'),
    )
    PgForceUserPass = (
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
        Severities.Unknown,
        QIcon(':/images/themes/default/mIconPostgis.svg'),
    )
    PreventDrive = (
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
        Severities.Unknown,
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
    PreventParentFolder = (
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
        Severities.Unknown,
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

    @classmethod
    def html(cls, severity: Severity, lizmap_cloud: bool) -> str:
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
        copy_sort = list(cls.__members__.values())
        copy_sort.sort(key=lambda x: severity.data if x.severity == Severities.Unknown else x.severity.data)
        for i, check in enumerate(copy_sort):
            html_str += check.html_help(i, severity, lizmap_cloud)
        html_str += '</table>'
        return html_str


class SourceLayer:

    """ For identifying a layer in a project. """
    def __init__(self, layer_name, layer_id):
        self.layer_id = layer_id
        self.layer_name = layer_name


class SourceType:

    """ List of sources in the project. """

    Layer = SourceLayer


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
    DATA = Qt.UserRole
    JSON = DATA + 1

    def setup(self):
        """ Setting up parameters. """
        # Do not use the constructor __init__, it's not working. Maybe because of UI files ?

        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setAlternatingRowColors(True)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setVisible(True)
        # Bug, same as self.sort()
        # self.setSortingEnabled(True)

        self.setColumnCount(len(Headers))
        for i, header in enumerate(Headers):
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

        for row in range(self.rowCount()):
            data = dict()
            for i, header in enumerate(Headers):
                data[header.data] = self.item(row, i).data(self.JSON)
            result.append(data)

        return result

    def to_json_summarized(self) -> dict:
        """ Export a sum up of warnings to JSON. """
        result = {}
        for row in range(self.rowCount()):
            error_id = self.item(row, 3).data(self.JSON)
            if error_id not in result.keys():
                result[error_id] = 1
            else:
                result[error_id] += 1
        return result

    def to_markdown_summarized(self) -> str:
        """ Export a sum up of warnings to JSON. """
        result = {}
        for row in range(self.rowCount()):
            error_name = self.item(row, 3).data(Qt.DisplayRole)
            if error_name not in result.keys():
                result[error_name] = 1
            else:
                result[error_name] += 1

        text = 'Validator summarized :\n\n'
        for error_name, count in result.items():
            text += '* {} → {}\n'.format(error_name, count)
        text += '\n'
        return text

    def add_error(self, error: Error, lizmap_cloud: bool = False, severity=None):
        """ Add an error in the table. """
        # By default, let's take the one in the error
        used_severity = error.check.severity
        if used_severity == Severities.Unknown:
            if severity:
                # The given severity is overriden the one in the error
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
        item.setToolTip(error.check.level.tooltip)
        item.setIcon(error.check.level.icon)
        self.setItem(row, column, item)
        column += 1

        # Source
        item = QTableWidgetItem(error.source)
        item.setData(self.DATA, error.source)
        if isinstance(error.source_type, SourceType.Layer):
            item.setToolTip(error.source_type.layer_id)
            layer = QgsProject.instance().mapLayer(error.source_type.layer_id)
            item.setIcon(QgsMapLayerModel.iconForLayer(layer))
            item.setData(self.JSON, error.source_type.layer_id)
        else:
            # Project only for now
            # TODO fix else
            item.setData(self.JSON, error.source)
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
