__copyright__ = "Copyright 2021, 3Liz"
__license__ = "GPL version 3"
__email__ = "info@3liz.org"

import json
import xml.etree.ElementTree as ET

from collections import namedtuple
from pathlib import Path
from typing import Generator, List, Tuple, Union

from qgis.core import (
    Qgis,
    QgsDistanceArea,
    QgsEditFormConfig,
    QgsExpression,
    QgsExpressionContext,
    QgsExpressionContextUtils,
    QgsFeature,
    QgsFeatureRequest,
    QgsMessageLog,
)
from qgis.server import QgsConfigCache, QgsServerFilter

from lizmap.server.core import find_vector_layer, server_feature_id_expression
from lizmap.tooltip import Tooltip

"""
QGIS Server filter for the GetFeatureInfo according to CFG config.
"""

Result = namedtuple('Result', ['layer', 'feature_id', 'expression'])


class GetFeatureInfoFilter(QgsServerFilter):

    @classmethod
    def parse_xml(cls, string: str) -> Generator[Tuple[str, str], None, None]:
        """ Generator for layer and feature found in the XML GetFeatureInfo. """
        root = ET.fromstring(string)
        for layer in root:
            for feature in layer:
                yield layer.attrib['name'], feature.attrib['id']

    @classmethod
    def append_maptip(cls, string: str, layer_name: str, feature_id: Union[str, int], maptip: str) -> str:
        """ Edit the XML GetFeatureInfo by adding a maptip for a given layer and feature ID. """
        root = ET.fromstring(string)
        for layer in root:
            if layer.attrib['name'] != layer_name:
                continue

            for feature in layer:
                # feature_id can be int if QgsFeature.id() is used
                # Otherwise it's string from QgsServerFeatureId
                if feature.attrib['id'] != str(feature_id):
                    continue

                item = feature.find("Attribute[@name='maptip']")
                if item is not None:
                    item.attrib['value'] = maptip
                else:
                    item = ET.Element('Attribute')
                    item.attrib['name'] = "maptip"
                    item.attrib['value'] = maptip
                    feature.append(item)

        xml_lines = ET.tostring(root, encoding='utf8', method='xml').decode("utf-8").split('\n')
        xml_string = '\n'.join(xml_lines[1:])
        return xml_string.strip()

    @classmethod
    def feature_list_to_replace(cls, cfg, project, relation_manager, xml) -> List[Result]:
        """ Parse the XML and check for each layer according to the Lizmap CFG file. """
        features = []
        for layer_name, feature_id in GetFeatureInfoFilter.parse_xml(xml):
            layer = find_vector_layer(layer_name, project)

            layer_config = cfg.get('layers').get(layer_name)
            if layer_config.get('popup') not in ['True', True]:
                continue

            if layer_config.get('popupSource') != 'form':
                continue

            config = layer.editFormConfig()
            if config.layout() != QgsEditFormConfig.TabLayout:
                QgsMessageLog.logMessage(
                    'The CFG is requesting a form popup, but the layer is not a form drag&drop layout',
                    'lizmap',
                    Qgis.Warning
                )
                continue

            root = config.invisibleRootContainer()

            # Need to eval the html_content
            html_content = Tooltip.create_popup_node_item_from_form(layer, root, 0, [], '', relation_manager)
            html_content = Tooltip.create_popup(html_content)

            # Maybe we can avoid the CSS on all features ?
            html_content += Tooltip.css()

            features.append(Result(layer, feature_id, html_content))
        return features

    def responseComplete(self):
        """ Intercept the GetFeatureInfo and add the form maptip if needed. """
        request = self.serverInterface().requestHandler()
        # request: QgsRequestHandler
        params = request.parameterMap()

        if params.get('SERVICE', '').upper() != 'WMS':
            return

        if params.get('REQUEST', '').upper() != 'GETFEATUREINFO':
            return

        if params.get('INFO_FORMAT', '').upper() != 'TEXT/XML':
            # Better to log something
            return

        project_path = Path(self.serverInterface().configFilePath())
        if not project_path.exists():
            # QGIS Project path does not exist as a file
            return

        config_path = Path(self.serverInterface().configFilePath() + '.cfg')
        if not config_path.exists():
            return

        with open(config_path, 'r', encoding='utf-8') as cfg_file:
            cfg = json.loads(cfg_file.read())

        project = QgsConfigCache.instance().project(str(project_path))
        relation_manager = project.relationManager()

        xml = request.body().data().decode("utf-8")

        # noinspection PyBroadException
        try:
            features = self.feature_list_to_replace(cfg, project, relation_manager, xml)
        except Exception:
            QgsMessageLog.logMessage(
                "Error while reading the XML response GetFeatureInfo, returning default response",
                'lizmap',
                Qgis.Critical
            )
            return

        if not features:
            return

        QgsMessageLog.logMessage(
            "Replacing the maptip from QGIS by the drag and drop expression for {} features on {}".format(
                len(features), ','.join([result.layer.name() for result in features])),
            'lizmap',
            Qgis.Info
        )

        # Let's evaluate each expression popup
        exp_context = QgsExpressionContext()
        exp_context.appendScope(QgsExpressionContextUtils.globalScope())
        exp_context.appendScope(QgsExpressionContextUtils.projectScope(project))

        # noinspection PyBroadException
        try:
            for result in features:
                distance_area = QgsDistanceArea()
                distance_area.setSourceCrs(result.layer.crs(), project.transformContext())
                distance_area.setEllipsoid(project.ellipsoid())
                exp_context.appendScope(QgsExpressionContextUtils.layerScope(result.layer))

                expression = server_feature_id_expression(
                    result.feature_id, result.layer.primaryKeyAttributes(), result.layer.fields())
                if expression:
                    request = QgsFeatureRequest(QgsExpression(expression))
                    request.setFlags(QgsFeatureRequest.NoGeometry)
                    feature = QgsFeature()
                    result.layer.getFeatures(request).nextFeature(feature)
                else:
                    # If not expression, the feature ID must be integer
                    feature = result.layer.getFeature(int(result.feature_id))

                exp_context.setFeature(feature)
                exp_context.setFields(feature.fields())

                value = QgsExpression.replaceExpressionText(result.expression, exp_context, distance_area)
                xml = self.append_maptip(xml, result.layer.name(), result.feature_id, value)

            request.clear()
            request.setResponseHeader('Content-Type', 'text/xml')
            request.appendBody(bytes(xml, 'utf-8'))

        except Exception:
            QgsMessageLog.logMessage(
                "Error while rewriting the XML response GetFeatureInfo, returning default response",
                'lizmap',
                Qgis.Critical
            )
            return
