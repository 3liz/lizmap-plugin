__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import logging

from enum import Enum, unique
from typing import List, Optional, Tuple, Union

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QBrush, QDragMoveEvent, QIcon
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QInputDialog,
    QTableWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QTreeWidgetItemIterator,
)

from lizmap.definitions.dataviz import DatavizDefinitions
from lizmap.dialogs.drag_drop_dataviz_container import ContainerDatavizDialog
from lizmap.qgis_plugin_tools.tools.i18n import tr

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

        # noinspection PyUnresolvedReferences
        self.table.model().rowsInserted.connect(self.dataviz_added)
        # noinspection PyUnresolvedReferences
        self.table.model().rowsRemoved.connect(self.dataviz_removed)

        # Drag and drop
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDragDropMode(QAbstractItemView.InternalMove)
        self.tree.setSelectionBehavior(QAbstractItemView.SelectRows)

        # Hide some buttons
        if self.parent:
            # Temporary until we implement these functions
            self.parent.button_up_dd_dataviz.setVisible(False)
            self.parent.button_down_dd_dataviz.setVisible(False)
            self.parent.button_remove_dd_dataviz.setVisible(False)

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

        Because this information is not stored in the CFG.
        """
        if not self.parent:
            # In tests... :(
            return 'plot name', QIcon()

        # noinspection PyUnresolvedReferences
        index = self.combo_plots.findData(uuid, Qt.UserRole)
        if not index:
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

    def drag_event(self, event: QDragMoveEvent):
        """ Drag event. """
        # print("Drag event")
        # print(event)
        pass

    def move_row_down(self):
        """ Button to move a row down. """
        pass

    def move_row_up(self):
        """ Button to move a row up. """
        pass

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

    def dataviz_added(self):
        """ When a dataviz has been added from the combobox into the tree. """
        pass
        # print("Dataviz added")

    def dataviz_removed(self):
        """ When a dataviz has been removed from the table. """
        # print("Dataviz removed")
        # TODO
        # Remove from the list
        # Remove from the tree
        pass

    def add_container(self):
        """ When the "add" container button is clicked, we add a new row in the tree widget. """
        # Loop for all tabs/groups
        tabs = []
        for row in range(0, self.tree.topLevelItemCount()):
            pass
            # item = self.tree.topLevelItem(row)
            # item_type = item.data(0, Qt.UserRole)
            # if item_type == Container.Tab.value:
            #     tabs.append(item.text(0))

        dialog = ContainerDatavizDialog(self.parent, tabs)
        if not dialog.exec_():
            return

        container_name = dialog.name()
        parent_container = dialog.parent_name()
        self._add_container(container_name, parent_container)

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
        # Copied from QGIS with the same button in the D&D dialog
        # https://github.com/qgis/QGIS/blob/8a82afd79b35f7640373d3394214ecb6cb7db17c/src/gui/vector/qgsattributesformproperties.cpp#L743
        # deleting an item may delete any number of nested child items -- so we delete
        # them one at a time and then see if there's any selection left
        # while True:
        #     items = self.tree.selectedIndexes()
        #     if not items:
        #         break
        #     self.tree.removeItemWidget(self.tree.itemFromIndex(items[0]), 0)
        pass

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
                    # The name is not used and must be used for reading the CFG, it's just easier to debug the CFG
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
                    LOGGER.warning("Plot having UUID '{}' was not found, skipping this plot for the drag&drop layout.")
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
