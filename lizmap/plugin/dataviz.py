from typing import (
    TYPE_CHECKING,
    Dict,
    Optional,
    Protocol,
)

from qgis.core import QgsApplication
from qgis.PyQt.QtGui import QIcon

if TYPE_CHECKING:
    from ..dialogs.main import LizmapDialog

from ..config import GlobalOptionsDefinitions
from ..definitions.dataviz import DatavizDefinitions, Theme
from ..definitions.definitions import (
    LwcVersions,
)
from ..drag_drop_dataviz_manager import DragDropDatavizManager
from ..forms.dataviz_edition import DatavizEditionDialog
from ..table_manager.dataviz import TableManagerDataviz
from ..toolbelt.i18n import tr


class LizmapProtocol(Protocol):
    dlg: "LizmapDialog"
    is_dev_version: bool

    @property
    def lwc_version(self) -> LwcVersions: ...


class DatavizManager(LizmapProtocol):
    drag_drop_dataviz: Optional[DragDropDatavizManager]

    def initialize_dataviz(self):
        self.drag_drop_dataviz = None

    def set_dataviz_options(self, global_options: GlobalOptionsDefinitions):
        for item in Theme:
            global_options["theme"]["widget"].addItem(item.value["label"], item.value["data"])
        index = global_options["theme"]["widget"].findData(Theme.Light.value["data"])
        global_options["theme"]["widget"].setCurrentIndex(index)

    # Called in `initGui`
    def dataviz_init_gui(self, item: Dict):
        definition = DatavizDefinitions()
        dialog = DatavizEditionDialog

        item["manager"] = TableManagerDataviz(
            self.dlg,
            definition,
            dialog,
            item["tableWidget"],
            item["editButton"],
            item.get("upButton"),
            item.get("downButton"),
        )
        # The drag&drop dataviz HTML layout
        drag_drop_dataviz = DragDropDatavizManager(
            self.dlg,
            definition,
            item["tableWidget"],
            self.dlg.tree_dd_plots,
            self.dlg.combo_plots,
        )

        self.dlg.button_add_dd_dataviz.setText("")
        self.dlg.button_add_dd_dataviz.setIcon(QIcon(QgsApplication.iconPath("symbologyAdd.svg")))
        self.dlg.button_add_dd_dataviz.setToolTip(tr("Add a new container in the layout"))
        self.dlg.button_add_dd_dataviz.clicked.connect(drag_drop_dataviz.add_container)

        self.dlg.button_remove_dd_dataviz.setText("")
        # noinspection PyCallByClass,PyArgumentList
        self.dlg.button_remove_dd_dataviz.setIcon(QIcon(QgsApplication.iconPath("symbologyRemove.svg")))
        self.dlg.button_remove_dd_dataviz.setToolTip(tr("Remove a container or a plot from the layout"))
        self.dlg.button_remove_dd_dataviz.clicked.connect(drag_drop_dataviz.remove_item)

        self.dlg.button_add_plot.setText("")
        self.dlg.button_add_plot.setIcon(QIcon(QgsApplication.iconPath("symbologyAdd.svg")))
        self.dlg.button_add_plot.setToolTip(tr("Add the plot in the layout"))
        self.dlg.button_add_plot.clicked.connect(drag_drop_dataviz.add_current_plot_from_combo)

        self.dlg.button_edit_dd_dataviz.setText("")
        self.dlg.button_edit_dd_dataviz.setIcon(QIcon(QgsApplication.iconPath("symbologyEdit.svg")))
        self.dlg.button_edit_dd_dataviz.setToolTip(tr("Edit the selected container/group"))
        self.dlg.button_edit_dd_dataviz.clicked.connect(drag_drop_dataviz.edit_row_container)

        self.drag_drop_dataviz = drag_drop_dataviz

    # Called by 'read_cfg_file'
    def read_cfg(self, json: Dict):
        # The drag&drop dataviz HTML layout
        # First load plots into the combobox, because the main dataviz table has already been loaded
        self.drag_drop_dataviz.load_dataviz_list_from_main_table()
        # Then populate the tree. Icons and titles will use the combobox.
        self.drag_drop_dataviz.load_tree_from_cfg(json["options"].get("dataviz_drag_drop", []))
