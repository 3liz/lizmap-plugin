__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import logging

from enum import Enum, unique
from typing import List, Optional, Tuple, Union

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QBrush, QIcon
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QInputDialog,
    QMessageBox,
    QTableWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QTreeWidgetItemIterator,
)

from lizmap.definitions.dataviz import DatavizDefinitions
from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.qgis_plugin_tools.tools.resources import resources_path

LOGGER = logging.getLogger('Lizmap')


@unique
class Container(Enum):
    Container = 'container'
    """container"""
    Plot = 'plot'
    """plot"""


class DragDropDatavizManager:

    """ Manage the tree widget for the drag&drop. """

    def __init__(
            self,
            parent: Optional[QDialog],
            definitions: DatavizDefinitions,
            table_widget: QTableWidget,
            tree_widget: QTreeWidget,
            combo: QComboBox,
    ):
        """ Constructor. """
        self.parent = parent
        self.definitions = definitions
        self.tree = tree_widget
        self.table = table_widget
        self.combo_plots = combo

        self.tree.itemDoubleClicked.connect(self.edit_row_container)

        # Drag and drop
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDragDropMode(QAbstractItemView.InternalMove)
        self.tree.setSelectionBehavior(QAbstractItemView.SelectRows)

    def add_current_plot_from_combo(self):
        """ Button to add the current plot from the combobox into the tree widget. """
        index = self.combo_plots.currentIndex()
        if index < 0:
            return

        text = self.combo_plots.itemText(index)
        icon = self.combo_plots.itemIcon(index)
        # noinspection PyUnresolvedReferences
        uuid = self.combo_plots.itemData(index, Qt.UserRole)
        self._add_plot_in_tree(text, icon, uuid)

    def metadata_from_uuid(self, uuid: str) -> Union[Tuple[None, None], Tuple[str, QIcon]]:
        """ Fetch title and icon from the plot UUID in the combobox.

        Because this information is not stored in the CFG in the D&D section.
        """
        if not self.parent:
            # In tests... :(
            return 'plot name', QIcon()

        # noinspection PyUnresolvedReferences
        index = self.combo_plots.findData(uuid, Qt.UserRole)
        if index < 0:
            return None, None

        text = self.combo_plots.itemText(index)
        icon = self.combo_plots.itemIcon(index)
        return text, icon

    def _add_plot_in_tree(self, text: str, icon: QIcon, uuid: str, name_parent=None):
        """ Internal function to add a plot in the tree. """
        if name_parent:
            # noinspection PyUnresolvedReferences
            parents = self.tree.findItems(name_parent, Qt.MatchContains | Qt.MatchRecursive, 0)
            parent_item = parents[0]
            item = QTreeWidgetItem(parent_item)
        else:
            item = QTreeWidgetItem(self.tree.invisibleRootItem())
            parent_item = None

        # Text
        item.setText(0, text)
        # Icon from the table
        item.setIcon(0, icon)
        # Row type
        # noinspection PyUnresolvedReferences
        item.setData(0, Qt.UserRole, Container.Plot)
        # UUID
        # noinspection PyUnresolvedReferences
        item.setData(0, Qt.UserRole + 1, uuid)
        # item.setBackground(0, QBrush(Qt.lightGray))
        # noinspection PyUnresolvedReferences
        item.setFlags(item.flags() & ~ Qt.ItemIsDropEnabled)
        # noinspection PyUnresolvedReferences
        item.setData(0, Qt.ToolTipRole, "Plot <b>{}</b><br>UUID {}".format(text, uuid))
        if name_parent:
            self.tree.addTopLevelItem(item)
            parent_item.setExpanded(True)
        else:
            self.tree.invisibleRootItem().addChild(item)

    def count_lines(self) -> int:
        """ Count the number of lines in the tree widget.

        Only used in test.
        """
        count = 0
        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            if item.parent():
                if item.parent().isExpanded():
                    count += 1
            else:
                # root item
                count += 1
            iterator += 1
        return count

    def load_dataviz_list_from_main_table(self):
        """ Load the combobox from the main dataviz table with all plots available. """
        # UUID column
        for i in range(self.table.columnCount()):
            if self.table.horizontalHeaderItem(i).text() == 'UUID':
                uuid_index = i
                break
        else:
            raise Exception('UUID must exist in dataviz definitions.')

        # Icon column
        icon_index = 0
        # Title column
        title_index = 1

        self.combo_plots.clear()

        for row in range(self.table.rowCount()):
            icon = self.table.item(row, icon_index).icon()
            title = self.table.item(row, title_index).text()
            # noinspection PyUnresolvedReferences
            uuid = self.table.item(row, uuid_index).data(Qt.UserRole)
            self.combo_plots.addItem(icon, title, uuid)
            index = self.combo_plots.findData(uuid)
            self.combo_plots.setItemData(index, uuid, Qt.ToolTipRole)

    def add_container(self):
        """ When the "add" container button is clicked, we add a new row in the tree widget. """
        new_name, ok = QInputDialog.getText(
            self.parent,
            tr("New tab or group"),
            tr("New name for the tab or group. You can drag and drop it after to create different kind of containers."),
            text="",
        )
        if not ok:
            return

        self._add_container(new_name, None)

    def edit_row_container(self):
        """ When a row is selected, and we click on the edit button. """
        selection = self.tree.selectedIndexes()
        if len(selection) <= 0:
            return

        item = self.tree.itemFromIndex(selection[0])
        # noinspection PyUnresolvedReferences
        if item.data(0, Qt.UserRole) == Container.Plot:
            return

        new_name, ok = QInputDialog.getText(
            self.parent,
            tr("Edit container name"),
            tr("New name"),
            text=item.text(0))
        if not ok:
            return

        item.setText(0, new_name)

    def remove_item(self):
        """ When the remove item button is clicked.

        It can be either a plot or a container.
        """
        # Alternative
        # QGIS with the D&D dialog
        # https://github.com/qgis/QGIS/blob/8a82afd79b35f7640373d3394214ecb6cb7db17c/src/gui/vector/qgsattributesformproperties.cpp#L743
        current_item = self.tree.currentItem()
        if not current_item:
            return

        children = []
        for child in range(current_item.childCount()):
            children.append(current_item.child(child))

        box = QMessageBox(self.parent)
        box.setIcon(QMessageBox.Question)
        box.setWindowIcon(QIcon(resources_path('icons', 'icon.png')), )
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.setDefaultButton(QMessageBox.No)

        if current_item.data(0, Qt.UserRole) == Container.Container:
            box.setWindowTitle(tr('Remove the container'))
            if children:
                box.setText(tr('Are you sure you want to remove the container and all elements inside?'))
            else:
                box.setText(tr('Are you sure you want to remove the container?'))
        else:
            box.setWindowTitle(tr('Remove the plot'))
            box.setText(tr('Are you sure you want to remove the plot from the layout?'))

        result = box.exec_()
        if result == QMessageBox.No:
            return

        for child in children:
            current_item.removeChild(child)

        parent_item = current_item.parent()
        if parent_item:
            parent_item.removeChild(current_item)
            return

        # We are at the first level already
        self.tree.invisibleRootItem().removeChild(current_item)

    def to_json(self) -> list:
        """ Serialize the tree to a JSON list. """
        current_parent = self.tree.invisibleRootItem()
        return self._to_json(current_parent)

    def _to_json(self, parent_item: QTreeWidgetItem) -> List:
        """ Recursive function to transform the tree into JSON. """
        data = []
        child_count = parent_item.childCount()
        for i in range(child_count):
            child = parent_item.child(i)
            child: QTreeWidgetItem

            # noinspection PyUnresolvedReferences
            row_type = child.data(0, Qt.UserRole)

            if row_type == Container.Container:
                tmp = {
                    'type': Container.Container.value,
                    'name': child.text(0),
                    'content': self._to_json(child),
                }
                data.append(tmp)
            else:
                # noinspection PyUnresolvedReferences
                data.append({
                    'type': Container.Plot.value,
                    # The name is not used and mustn't be used for reading the CFG, it's just easier to debug the CFG
                    # instead of dealing with a UUID
                    '_name': child.text(0),
                    'uuid': child.data(0, Qt.UserRole + 1),
                })
        return data

    def load_tree_from_cfg(self, data: list) -> bool:
        """ Load the tree data from the CFG. """
        self.tree.clear()
        self._container_from_cfg(data)
        return True

    def _container_from_cfg(self, data: list, parent: str = None) -> bool:
        """ Recursive function to read the container data. """
        for line in data:
            line: dict

            if line['type'] == Container.Container.value:
                self._add_container(line['name'], parent)
                self._container_from_cfg(line['content'], line['name'])

            elif line['type'] == Container.Plot.value:
                text, icon = self.metadata_from_uuid(line["uuid"])
                if not icon:
                    LOGGER.warning(
                        "Plot having UUID '{}' was not found in the plot combobox, D&D panel, skipping this plot for "
                        "the drag&drop layout, only : {}.".format(
                            line["uuid"],
                            ','.join(
                                [self.combo_plots.itemData(i, Qt.UserRole) for i in range(self.combo_plots.count())])
                        ))
                    continue

                self._add_plot_in_tree(text, icon, line["uuid"], parent)

            else:
                raise Exception(f'Unknown type : {line["type"]}')

        return True

    def _add_container(self, name: str, name_parent: str = None):
        """ Add a new container in the tree. """
        parent_item = None
        if name_parent:
            # noinspection PyUnresolvedReferences
            parents = self.tree.findItems(name_parent, Qt.MatchContains | Qt.MatchRecursive, 0)
            if not parents:
                # Strange, it shouldn't happen.
                return

            parent_item = parents[0]

            item = QTreeWidgetItem(parent_item)
            item.setBackground(0, QBrush(Qt.gray))

        else:
            # At the top
            item = QTreeWidgetItem(self.tree.invisibleRootItem())
            item.setBackground(0, QBrush(Qt.gray))

        item.setText(0, name)
        # noinspection PyUnresolvedReferences
        item.setData(0, Qt.UserRole, Container.Container)
        # noinspection PyUnresolvedReferences
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)
        if name_parent:
            self.tree.addTopLevelItem(item)
            parent_item.setExpanded(True)
        else:
            self.tree.invisibleRootItem().addChild(item)
