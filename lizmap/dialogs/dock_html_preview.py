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

LOGGER = logging.getLogger('Lizmap')

# Detect available Web widget
WEBKIT_AVAILABLE = False
WEB_ENGINE = False
try:
    # Prefer QWebEngine (modern)
    from qgis.PyQt.QtWebEngineWidgets import QWebEngineView
    WebView = QWebEngineView
    WEBKIT_AVAILABLE = True
    WEB_ENGINE = True
except ModuleNotFoundError:
    try:
        # Fallback to legacy QtWebKit
        from qgis.PyQt.QtWebKitWidgets import QWebView
        from qgis.PyQt.QtWebKit import QWebSettings
        WebView = QWebView
        WEBKIT_AVAILABLE = True
        WEB_ENGINE = False
    except ModuleNotFoundError:
        # Neither WebEngine nor WebKit is available
        WebView = None
        WEB_ENGINE = False
        WEBKIT_AVAILABLE = False


class HtmlPreview(QDockWidget):

    # noinspection PyArgumentList
    def __init__(self, parent, *__args):
        """ Constructor. """
        super().__init__(parent, *__args)
        self.setObjectName("html_maptip_preview")
        self.setWindowTitle("Lizmap HTML Maptip Preview")
        self._server_url = None

        # Main dock container
        self.dock = QWidget(parent)
        self.layout = QVBoxLayout(self.dock)

        # Web view or fallback label
        if WebView:
            self.web_view = WebView(self.dock)
        else:
            self.web_view = QLabel(tr('You must install Qt Webkit to enable this feature.'))
            self.web_view.setWordWrap(True)

        self.layout.addWidget(self.web_view)

        # Info label
        if not WEBKIT_AVAILABLE:
            self.label = QLabel(tr('You must install Qt Webkit to enable this feature.'))
        else:
            self.label = QLabel(tr("This only a preview of the HTML maptip. Lizmap will add more CSS classes."))
        self.label.setWordWrap(True)
        self.layout.addWidget(self.label)

        if not WEBKIT_AVAILABLE:
            self.setWidget(self.dock)
            return

        # Layer and feature selection
        horizontal = QHBoxLayout()
        self.layer = QgsMapLayerComboBox(self.dock)
        horizontal.addWidget(self.layer)

        self.feature = QgsFeaturePickerWidget(self.dock)
        horizontal.addWidget(self.feature)

        self.layout.addLayout(horizontal)

        # Refresh button and last update label
        horizontal = QHBoxLayout()
        self.refresh = QPushButton(self.dock)
        self.refresh.setIcon(QIcon(QgsApplication.iconPath('mActionRefresh.svg')))
        self.refresh.clicked.connect(self.update_html)
        horizontal.addWidget(self.refresh)

        self.last_update_label = QLabel()
        horizontal.addWidget(self.last_update_label)
        self.layout.addLayout(horizontal)

        # Size policy for web view
        size_policy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.MinimumExpanding)
        size_policy.setHorizontalStretch(0)
        size_policy.setVerticalStretch(0)
        size_policy.setHeightForWidth(self.web_view.sizePolicy().hasHeightForWidth())
        self.web_view.setSizePolicy(size_policy)

        self.setWidget(self.dock)

        # Connect signals
        self.layer.setFilters(QgsMapLayerProxyModel.Filter.VectorLayer)
        self.layer.layerChanged.connect(self.current_layer_changed)
        self.current_layer_changed()
        self.feature.featureChanged.connect(self.update_html)
        self.feature.setShowBrowserButtons(True)
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

    # noinspection PyArgumentList
    def update_html(self):
        """ Update the HTML preview. """
        if not self.isVisible():
            return

        layer = self.layer.currentLayer()
        if not layer:
            return

        if iface.activeLayer() != layer:
            return

        feature = self.feature.feature()
        if not feature:
            return

        now = QDateTime.currentDateTime()
        now_str = now.toString(QLocale.c().timeFormat(QLocale.FormatType.ShortFormat))
        self.last_update_label.setText(tr("Last update") + " " + now_str)

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

        if WebView:
            self.web_view.setHtml(html_content, base_url)
        else:
            self.web_view.setText(html_content)
