__copyright__ = "Copyright 2021, 3Liz"
__license__ = "GPL version 3"
__email__ = "info@3liz.org"

import json
import xml.etree.ElementTree as ET

from collections import namedtuple
from pathlib import Path
from typing import Generator, List, Tuple, Union

from qgis.core import (
    QgsDistanceArea,
    QgsEditFormConfig,
    QgsExpression,
    QgsExpressionContext,
    QgsExpressionContextUtils,
    QgsFeature,
    QgsFeatureRequest,
)
from qgis.server import QgsConfigCache, QgsServerFilter

from lizmap.server.core import find_vector_layer, server_feature_id_expression
from lizmap.server.logger import Logger
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
                Logger.warning(
                    'The CFG is requesting a form popup, but the layer is not a form drag&drop layout')
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
        logger = Logger()
        request = self.serverInterface().requestHandler()
        # request: QgsRequestHandler
        params = request.parameterMap()

        if params.get('SERVICE', '').upper() != 'WMS':
            return

        if params.get('REQUEST', '').upper() != 'GETFEATUREINFO':
            return

        if params.get('INFO_FORMAT', '').upper() != 'TEXT/XML':
            logger.info(
                "Lizmap is not only processing TEXT/XML INFO_FORMAT, not {}".format(
                    params.get('INFO_FORMAT', '').upper()))
            return

        project_path = Path(self.serverInterface().configFilePath())
        if not project_path.exists():
            logger.info(
                'The QGIS project {} does not exist as a file, not possible to process with Lizmap this '
                'request GetFeatureInfo'.format(self.serverInterface().configFilePath()))
            return

        config_path = Path(self.serverInterface().configFilePath() + '.cfg')
        if not config_path.exists():
            logger.info(
                'The QGIS project {} is not a Lizmap project, not possible to process with Lizmap this '
                'request GetFeatureInfo'.format(self.serverInterface().configFilePath()))
            return

        # str() because the plugin must be compatible Python 3.5
        with open(str(config_path), 'r', encoding='utf-8') as cfg_file:
            cfg = json.loads(cfg_file.read())

        project = QgsConfigCache.instance().project(str(project_path))
        relation_manager = project.relationManager()

        xml = request.body().data().decode("utf-8")

        # noinspection PyBroadException
        try:
            features = self.feature_list_to_replace(cfg, project, relation_manager, xml)
        except Exception as e:
            logger.critical(
                "Error while reading the XML response GetFeatureInfo for project {}, returning default "
                "response".format(project_path))
            logger.critical(str(e))
            return

        if not features:
            # This is not normal ...
            logger.warning(
                "No features found in the XML from QGIS Server for project {}".format(project_path)
            )
            return

        logger.info(
            "Replacing the maptip from QGIS by the drag and drop expression for {} features on {}".format(
                len(features), ','.join([result.layer.name() for result in features]))
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
                    expression_request = QgsFeatureRequest(QgsExpression(expression))
                    expression_request.setFlags(QgsFeatureRequest.NoGeometry)
                    feature = QgsFeature()
                    result.layer.getFeatures(expression_request).nextFeature(feature)
                else:
                    # If not expression, the feature ID must be integer
                    feature = result.layer.getFeature(int(result.feature_id))

                if not feature.isValid():
                    logger.warning(
                        "The feature {} for layer {} is not valid, skip replacing this XML "
                        "GetFeatureInfo, continue to the next feature".format(
                            result.feature_id, result.layer.id())
                    )
                    continue

                exp_context.setFeature(feature)
                exp_context.setFields(feature.fields())

                value = QgsExpression.replaceExpressionText(result.expression, exp_context, distance_area)
                if not value:
                    logger.warning(
                        "The GetFeatureInfo result for feature {} in layer {} is not valid, skip replacing "
                        "this XML GetFeatureInfo, , continue to the next feature".format(
                            result.feature_id, result.layer.id())
                    )
                    continue

                logger.info("Replacing feature {} in layer {} for the GetFeatureInfo by the drag&drop form".format(
                    result.feature_id, result.layer.name()))
                xml = self.append_maptip(xml, result.layer.name(), result.feature_id, value)

            # Safe guard, it shouldn't happen
            if not xml:
                logger.critical(
                    "The new XML for the GetFeatureInfo is empty. Let's return the default previous XML")
                return

            # When we are fine, we really replace the XML of the response
            request.clear()
            request.setResponseHeader('Content-Type', 'text/xml')
            request.appendBody(bytes(xml, 'utf-8'))
            logger.info("GetFeatureInfo replaced for project {}".format(project_path))

        except Exception as e:
            logger.critical(
                "Error while rewriting the XML response GetFeatureInfo, returning default response")
            logger.critical(str(e))
            return
