__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import logging

from qgis.core import (
    QgsApplication,
    QgsExpression,
    QgsExpressionContext,
    QgsExpressionContextUtils,
    QgsMapLayerProxyModel,
    QgsProject,
)
from qgis.gui import QgsFeaturePickerWidget, QgsMapLayerComboBox
from qgis.PyQt.QtCore import QDateTime, QLocale, QUrl
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from qgis.utils import iface

from lizmap.toolbelt.i18n import tr
from lizmap.toolbelt.resources import resources_path
from lizmap.toolbelt.version import qgis_version

try:
    from qgis.PyQt.QtWebKitWidgets import QWebView
    WEBKIT_AVAILABLE = True
except ModuleNotFoundError:
    WEBKIT_AVAILABLE = False

LOGGER = logging.getLogger('Lizmap')


class HtmlPreview(QDockWidget):

    # noinspection PyArgumentList
    def __init__(self, parent, *__args):
        """ Constructor. """
        super().__init__(parent, *__args)
        self.setWindowTitle("Lizmap HTML Maptip Preview")

        self._server_url = None

        self.dock = QWidget(parent)
        self.layout = QVBoxLayout(self.dock)

        if not WEBKIT_AVAILABLE:
            self.label = QLabel(tr('You must install Qt Webkit to enable this feature.'))
        else:
            self.label = QLabel(tr("This only a preview of the HTML maptip. Lizmap will add more CSS classes."))

        self.label.setWordWrap(True)
        self.layout.addWidget(self.label)

        if not WEBKIT_AVAILABLE:
            return

        horizontal = QHBoxLayout(self.dock)

        self.layer = QgsMapLayerComboBox(self.dock)
        horizontal.addWidget(self.layer)

        self.feature = QgsFeaturePickerWidget(self.dock)
        horizontal.addWidget(self.feature)

        self.layout.addLayout(horizontal)

        horizontal = QHBoxLayout(self.dock)

        self.refresh = QPushButton(self.dock)
        self.refresh.setIcon(QIcon(QgsApplication.iconPath('mActionRefresh.svg')))
        # noinspection PyUnresolvedReferences
        self.refresh.clicked.connect(self.update_html)
        horizontal.addWidget(self.refresh)

        self.label = QLabel()
        horizontal.addWidget(self.label)

        self.layout.addLayout(horizontal)

        self.web_view = QWebView(self.dock)
        size_policy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
        size_policy.setHorizontalStretch(0)
        size_policy.setVerticalStretch(0)
        size_policy.setHeightForWidth(self.web_view.sizePolicy().hasHeightForWidth())
        self.web_view.setSizePolicy(size_policy)
        self.layout.addWidget(self.web_view)

        self.setWidget(self.dock)

        self.layer.setFilters(QgsMapLayerProxyModel.VectorLayer)
        # noinspection PyUnresolvedReferences
        self.layer.layerChanged.connect(self.current_layer_changed)
        self.current_layer_changed()
        # noinspection PyUnresolvedReferences
        self.feature.featureChanged.connect(self.update_html)
        self.feature.setShowBrowserButtons(True)

        if qgis_version() >= 32000:
            # We don't have a better signal to listen to
            QgsProject.instance().dirtySet.connect(self.update_html)

        self.update_html()

    def set_server_url(self, url: str):
        """ Set the server URL according to the main dialog. """
        if not url:
            return

        if not url.endswith('/'):
            url += '/'
        self._server_url = url

    def css(self) -> str:
        """ Links to CSS style sheet according to the server. """
        # Order is important
        assets = (
            'assets/css/bootstrap.min.css',
            'themes/default/css/main.css',
            'themes/default/css/map.css',
        )
        html = [f'<link type="text/css" href="{self._server_url + asset}" rel="stylesheet" />' for asset in assets]
        return '\n'.join(html)

    def current_layer_changed(self):
        """ When the layer has changed. """
        self.feature.setLayer(self.layer.currentLayer())
        # Need to disconnect all layers before ?
        # self.layer.currentLayer().repaintRequested.connect(self.update_html())

    # noinspection PyArgumentList
    def update_html(self):
        """ Update the HTML preview. """
        # This function is called when the project is "setDirty",
        # because it means maybe the vector layer properties has been "applied"

        if not self.isVisible():
            # If the dock is not visible, we don't care
            return

        layer = self.layer.currentLayer()
        if not layer:
            return

        if iface.activeLayer() != layer:
            # This function is called when the project is "setDirty",
            # because it means maybe the vector layer properties has been "applied"
            return

        feature = self.feature.feature()
        if not feature:
            return

        now = QDateTime.currentDateTime()
        now_str = now.toString(QLocale.c().timeFormat(QLocale.ShortFormat))
        self.label.setText(tr("Last update") + " " + now_str)

        exp_context = QgsExpressionContext()
        exp_context.appendScope(QgsExpressionContextUtils.globalScope())
        exp_context.appendScope(QgsExpressionContextUtils.projectScope(QgsProject.instance()))
        exp_context.appendScope(QgsExpressionContextUtils.layerScope(layer))
        exp_context.setFeature(feature)
        html_string = QgsExpression.replaceExpressionText(layer.mapTipTemplate(), exp_context)
        base_url = QUrl.fromLocalFile(resources_path('images', 'non_existing_file.png'))

        with open(resources_path('html', 'maptip_preview.html'), encoding='utf8') as f:
            html_template = f.read()

        html_content = html_template.format(
            css=self.css(),
            maptip=html_string,
        )

        self.web_view.setHtml(html_content, base_url)
