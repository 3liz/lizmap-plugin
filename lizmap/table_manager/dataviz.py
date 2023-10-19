""" Table manager for dataviz. """
import json
import logging

from typing import Optional

from qgis.core import (
    QgsApplication,
    QgsAuthMethodConfig,
    QgsBlockingNetworkRequest,
    QgsProject,
    QgsSettings,
)
from qgis.PyQt.QtCore import (
    QByteArray,
    QCoreApplication,
    QJsonDocument,
    QLocale,
    Qt,
    QUrl,
    QUrlQuery,
)
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtNetwork import QNetworkRequest
from qgis.PyQt.QtWidgets import QDialog, QLabel
from qgis.utils import OverrideCursor

from lizmap.definitions.base import BaseDefinitions
from lizmap.definitions.dataviz import GraphType
from lizmap.definitions.definitions import ServerComboData
from lizmap.dialogs.main import LizmapDialog
from lizmap.dialogs.server_wizard import ServerWizard
from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.qgis_plugin_tools.tools.resources import (
    plugin_name,
    resources_path,
)
from lizmap.table_manager.base import TableManager
from lizmap.tools import merge_strings, qgis_version, to_bool

LOGGER = logging.getLogger(plugin_name())


__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


class TableManagerDataviz(TableManager):

    """ Table manager for dataviz.

    Note, this subclass is coming way later than the actual implementation of TableManager.
    There are a lot of lines of code in TableManager related to only the dataviz.
    """

    def __init__(
            self, parent: LizmapDialog, definitions: BaseDefinitions, edition: Optional[QDialog], table, edit_button,
            up_button, down_button):
        TableManager.__init__(self, parent, definitions, edition, table, None, edit_button, up_button, down_button)

        label = tr(
            "This plot is a preview, using the <b>data</b> and the <b>project</b> currently stored "
            "<b>on the server</b>, but using your <b>current</b> configuration for the given plot."
        )
        self.parent.label_helper_dataviz.setText(label)

        self.table.itemSelectionChanged.connect(self.preview_dataviz_dialog)

        if qgis_version() >= 31400:
            self.parent.dataviz_feature_picker.setShowBrowserButtons(True)
            self.parent.dataviz_feature_picker.featureChanged.connect(self.preview_dataviz_dialog)

        self.parent.enable_dataviz_preview.setText('')
        self.parent.enable_dataviz_preview.setCheckable(True)
        self.parent.enable_dataviz_preview.setChecked(True)
        self.toggle_preview()
        self.parent.enable_dataviz_preview.clicked.connect(self.toggle_preview)

    def toggle_preview(self):
        """ When the toggle preview button is pressed. """
        if self.parent.enable_dataviz_preview.isChecked():
            self.parent.enable_dataviz_preview.setIcon(QIcon(":images/themes/default/mActionShowAllLayers.svg"))
            self.parent.enable_dataviz_preview.setToolTip(tr(
                "The preview of plots is currently activated. Click on a plot to have its preview."))
        else:
            self.parent.enable_dataviz_preview.setIcon(QIcon(":images/themes/default/mActionHideAllLayers.svg"))
            self.parent.enable_dataviz_preview.setToolTip(tr("The preview of plots is currently disabled."))
        self.preview_dataviz_dialog()

    def display_error(self, error_text: str):
        """ Display an error message and change the tab. """
        self.parent.dataviz_error_message.setText(error_text)
        self.parent.stacked_dataviz_preview.setCurrentWidget(self.parent.error_content)
        QCoreApplication.processEvents()

    def preview_dataviz_dialog(self):
        """ Open a new dialog with a preview of the dataviz. """
        if isinstance(self.parent.dataviz_viewer, QLabel):
            # QtWebkit not available
            self.parent.stacked_dataviz_preview.setCurrentWidget(self.parent.html_content)
            return

        # qgis_version() < 3.14
        if isinstance(self.parent.dataviz_feature_picker, QLabel):
            self.parent.stacked_dataviz_preview.setCurrentWidget(self.parent.html_content)
            return

        self.parent.dataviz_feature_picker.setVisible(False)
        # Not an error, just a message...
        self.display_error(tr('Loading preview' + '…'))

        # Try to display a GIF instead of the text
        # html_content = "<body><center><img src=\"{}\"></center><body>".format(resources_path('icons/loading.gif'))
        # base_url = QUrl.fromLocalFile(resources_path('images', 'non_existing_file.png'))
        # self.parent.dataviz_viewer.setHtml(html_content, base_url)
        # self.parent.stacked_dataviz_preview.setCurrentWidget(self.parent.html_content)
        # QCoreApplication.processEvents()

        selection = self.table.selectedIndexes()
        if len(selection) <= 0:
            return

        if not self.parent.repository_combo.isVisible():
            return

        # The check before is not enough if we just have changed the server while we are in the dataviz panel.
        metadata = self.parent.current_server_info(ServerComboData.JsonMetadata.value)
        if not metadata:
            return

        if not metadata.get("repositories"):
            return

        if not self.parent.enable_dataviz_preview.isChecked():
            self.display_error(tr('Dataviz preview is disabled.'))
            return

        data = self.to_json()
        row = str(selection[0].row())
        plot_config = data[row]

        if plot_config['type'] == GraphType.HtmlTemplate.value['data']:
            self.display_error(tr('It\'s not possible to have a preview for an HTML plot.'))
            return

        server = self.parent.current_server_info(ServerComboData.ServerUrl.value)
        auth_id = self.parent.current_server_info(ServerComboData.AuthId.value)
        if not server or not auth_id:
            return

        repository = self.parent.repository_combo.currentData()
        if not repository:
            # Shouldn't happen, but maybe we have changed the server somehow ?
            self.display_error(tr('No repository selected.'))
            return

        repository_label = self.parent.repository_combo.currentText()
        project = QgsProject.instance().baseName()

        json_data = {
            "repository": repository,
            "project": project,
            "plot_config": plot_config,
        }
        if to_bool(plot_config.get('popup_display_child_plot', False)):
            self.parent.dataviz_feature_picker.setAllowNull(not to_bool(plot_config.get('only_show_child', False)))
            expression_filter = self.dataviz_expression_filter(plot_config['layerId'])
            if expression_filter:
                json_data['exp_filter'] = expression_filter

        json_object = json.dumps(json_data, indent=4)

        url = ServerWizard.url_dataviz(server)

        conf = QgsAuthMethodConfig()
        QgsApplication.authManager().loadAuthenticationConfig(auth_id, conf, True)

        locale = QgsSettings().value("locale/userLocale", QLocale().name())[0:2]

        params = QUrlQuery()
        params.addQueryItem("lang", locale)

        url = QUrl(url)
        url.setQuery(params)
        network_request = QNetworkRequest()
        network_request.setRawHeader(b"Content-Type", b"application/json")
        network_request.setRawHeader(b"Accept", b"application/json")
        network_request.setUrl(url)

        request = QgsBlockingNetworkRequest()
        request.setAuthCfg(auth_id)

        doc = QJsonDocument.fromJson(json_object.encode('utf8'))

        with OverrideCursor(Qt.WaitCursor):
            error = request.post(network_request, QByteArray(doc.toJson()))

        if error != QgsBlockingNetworkRequest.NoError:
            if error == QgsBlockingNetworkRequest.NetworkError:
                message = tr('Network error : {}').format(server)
            elif error == QgsBlockingNetworkRequest.TimeoutError:
                message = tr('Timeout error : {}').format(server)
            elif error == QgsBlockingNetworkRequest.ServerExceptionError:
                # Customized error from the server about the request
                # We should have a JSON
                response = request.reply().content()
                json_response = json.loads(response.data().decode('utf-8'))
                errors = json_response.get('errors')
                if errors:
                    # Message from the server
                    message = '<b>{}</b><br><br>{}'.format(errors.get('title'), errors.get('detail'))
                elif json_response.get('errorMessage'):
                    # Error from nginx or apache?
                    message = '<b>{}</b><br><br>{}'.format(
                        json_response.get('errorMessage'), json_response.get('errorCode'))

                # Let's add some more context to help
                message += '<br><br>' + tr("Given context for the request") + ' : <br>'
                message += '<b>' + tr('Server') + '</b> : ' + server + '<br>'
                message += (
                        '<b>' + tr('Repository') + '</b> : ' + repository
                        + ', <b>' + tr('alias') + '</b> : ' + repository_label
                )
                message += '<br>'
                message += '<b>' + tr('Project') + '</b> : ' + project + '.qgs'
            else:
                message = tr("Unknown error : code {}").format(error)

            self.display_error(message)
            return

        response = request.reply().content()
        json_response = json.loads(response.data().decode('utf-8'))

        if json_response.get('errors'):
            # Looks like we are on LWC < 3.6.1
            # Shouldn't happen as well because of a previous check
            self.display_error(json_response.get('errors').get('title', 'Unknown error'))
            return

        if not json_response.get('data'):
            # Shouldn't happen ...
            self.display_error("Unknown error")
            return

        # Here, we are all good, we can finally display the plot.

        with open(resources_path('html', 'dataviz.html'), encoding='utf8') as f:
            html_template = f.read()

        html_content = html_template.format(
            plot_data=json.dumps(json_response['data']),
            plot_layout=json.dumps(json_response['layout']),
            plot_user_layout=json.dumps(plot_config.get('layout', '')),
            plot_config=json.dumps({
                "showLink": False,
                "scrollZoom": False,
                "locale": locale,
                "responsive": True,
            }),
            plotly=merge_strings(server, json_response['plotly']['script']),
            locale=merge_strings(server, json_response['plotly']['locale']),
        )
        base_url = QUrl.fromLocalFile(resources_path('images', 'non_existing_file.png'))
        self.parent.dataviz_viewer.setHtml(html_content, base_url)

        # Only when we are all good, we display the final tab
        self.parent.stacked_dataviz_preview.setCurrentWidget(self.parent.html_content)

    def dataviz_expression_filter(self, layer_id: str) -> Optional[str]:
        """ Return the expression filter if possible. """
        project = QgsProject.instance()
        layer = project.mapLayer(layer_id)
        if not layer:
            return

        relations = project.relationManager().referencingRelations(layer)
        if not relations:
            return

        if len(relations) >= 2:
            LOGGER.warning(
                "Many relations has been found for the dataviz preview with the layer ID '{}'. "
                "Only the first one is used.".format(layer_id)
            )

        parent_layer = relations[0].referencingLayer()
        child_layer = relations[0].referencedLayer()
        field = relations[0].referencingFields()

        # We use only the first field.
        field = parent_layer.fields().at(field[0])

        # Set the layer in the feature combobox if not set or if it's a different one
        previous_layer = self.parent.dataviz_feature_picker.layer()
        if previous_layer and previous_layer.id() != layer.id() or not previous_layer:
            self.parent.dataviz_feature_picker.setLayer(child_layer)

        # Make widget visible
        self.parent.dataviz_feature_picker.setVisible(True)

        feature = self.parent.dataviz_feature_picker.feature()
        if feature.isValid():
            # The current feature can be set to NULL because of "only_show_child"
            return "\"{}\" IN ('{}')".format(field.name(), feature.id())
