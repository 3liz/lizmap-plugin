__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import collections
import logging
import re

from typing import List, Tuple

from qgis.core import (
    QgsLayerTree,
    QgsLayerTreeGroup,
    QgsLayerTreeLayer,
    QgsLayerTreeNode,
    QgsProject,
)

from lizmap.tools import random_string, unaccent

LOGGER = logging.getLogger('Lizmap')


class OgcProjectValidity:

    """ To make a QGIS project valid according to OGC standards. """

    def __init__(self, project: QgsProject):
        """ Constructor. """
        self.project = project
        self.new_shortnames_added = []

    def add_shortnames(self):
        """ Add shortnames on all layers and groups. """
        existing, duplicated = self.existing_shortnames()
        layer_tree = self.project.layerTreeRoot()
        self._add_all_shortnames(layer_tree, existing, duplicated)
        LOGGER.info(f"New shortnames added : {len(self.new_shortnames_added)}")

    def _add_all_shortnames(self, layer_tree: QgsLayerTreeNode, existing_shortnames: List, duplicated: List):
        """ Recursive function to add shortnames. """
        for child in layer_tree.children():
            # noinspection PyArgumentList
            if QgsLayerTree.isLayer(child):
                child: QgsLayerTreeLayer
                layer = self.project.mapLayer(child.layerId())
                short_name = layer.shortName()
                if not short_name or short_name in duplicated:
                    source = short_name if short_name else layer.name()
                    new_shortname = self.short_name(source, existing_shortnames)
                    existing_shortnames.append(new_shortname)
                    layer.setShortName(new_shortname)
                    LOGGER.info(f"New shortname added on layer '{layer.name()}' : {new_shortname}")
                    self.new_shortnames_added.append(new_shortname)
            else:
                child: QgsLayerTreeGroup
                if not child.customProperty("wmsShortName"):
                    new_shortname = self.short_name(child.name(), existing_shortnames)
                    existing_shortnames.append(new_shortname)
                    child.setCustomProperty("wmsShortName", new_shortname)
                    LOGGER.info(f"New shortname added on group '{child.name()}' : {new_shortname}")
                    self.new_shortnames_added.append(new_shortname)
                self._add_all_shortnames(child, existing_shortnames, duplicated)

    def existing_shortnames(self) -> Tuple[List[str], List[str]]:
        """ Fetch all existing shortnames in the project. """
        layer_tree = self.project.layerTreeRoot()
        existing = self._read_all_shortnames(layer_tree, [])
        LOGGER.info('Existing shortnames detected before in project : ' + ', '.join(existing))

        duplicated = [item for item, count in collections.Counter(existing).items() if count > 1]
        return existing, duplicated

    def _read_all_shortnames(self, group: QgsLayerTreeNode, existing_shortnames: List[str]) -> List[str]:
        """ Recursive function to fetch all shortnames. """

        for child in group.children():
            # noinspection PyArgumentList
            if QgsLayerTree.isLayer(child):
                child: QgsLayerTreeLayer
                layer = self.project.mapLayer(child.layerId())
                if layer.shortName():
                    existing_shortnames.append(layer.shortName())
            else:
                child: QgsLayerTreeGroup
                group_shortname = child.customProperty("wmsShortName")
                if group_shortname:
                    existing_shortnames.append(group_shortname)
                self._read_all_shortnames(child, existing_shortnames)
        return existing_shortnames

    def set_project_short_name(self):
        """ Check and set the project short name. """
        # Inspired by QgsProjectServerValidator::validate()
        existing = self.existing_shortnames()

        root_layer_name = self.project.readEntry("WMSRootName", "/", "")[0]
        if not root_layer_name and self.project.title():
            # If short name is not defined, we take the project title
            root_layer_name = self.project.title()

        if not root_layer_name:
            root_layer_name = self.project.baseName()

        project_short_name = self.short_name(root_layer_name, existing, 'p')
        LOGGER.info("Setting a project shortname : {}".format(project_short_name))
        self.project.writeEntry("WMSRootName", "/", project_short_name)

    @classmethod
    def short_name(cls, layer_name: str, existing: List[str], prefix='l') -> str:
        """ Generate a layer short name.

        The default prefix is 'l' for layer.
        """
        layer_name = unaccent(layer_name)
        # Inspired by QgsMapLayer::generateId()
        # https://github.com/qgis/QGIS/blob/master/src/core/qgsmaplayer.cpp#L2181
        layer_short_name = re.sub(r'[^a-zA-Z0-9_-]', '_', layer_name)

        layer_short_name = layer_short_name.strip('_-')

        if len(layer_short_name) == 0:
            # No more chars left, let's add some
            layer_short_name = random_string(5)

        if layer_short_name[0].isdigit():
            layer_short_name = '{}_{}'.format(prefix, layer_short_name)

        if layer_short_name not in existing:
            return layer_short_name

        def increment(name, i, existing_list):
            tmp_name = '{}_{}'.format(name, i)
            if tmp_name not in existing_list:
                return tmp_name
            return increment(name, i + 1, existing_list)

        return increment(layer_short_name, 1, existing)
