"""Dialog for portfolio edition."""

from typing import TYPE_CHECKING

from qgis.core import QgsApplication
from qgis.PyQt.QtGui import QIcon

from lizmap.forms.base_edition_dialog import BaseEditionDialog
from lizmap.definitions.definitions import LwcVersions
from lizmap.definitions.portfolio import PortfolioDefinitions
from lizmap.toolbelt.i18n import tr
from lizmap.toolbelt.resources import load_ui

if TYPE_CHECKING:
    from lizmap.dialogs.main import LizmapDialog


CLASS = load_ui('ui_form_portfolio.ui')


class PortfolioEditionDialog(BaseEditionDialog, CLASS):

    def __init__(
        self,
        parent: Optional["LizmapDialog"] = None,
        unicity: Optional[Dict[str, str]] = None,
        lwc_version: Optional[LwcVersions] = None,
    ):
        super().__init__(parent, unicity, lwc_version)
        self.setupUi(self)
        self.parent = parent
        self.config = PortfolioDefinitions()
        self.config.add_layer_widget('title', self.title)
        self.config.add_layer_widget('description', self.text_description)
        self.config.add_layer_widget('geometry', self.geometry)
        self.config.add_layer_widget('margin', self.margin)
        self.config.add_layer_widget('scale', self.scale)
        self.config.add_layer_widget('templates', self.templates)

        # noinspection PyCallByClass,PyArgumentList
        self.add_template.setText('')
        self.add_template.setIcon(QIcon(QgsApplication.iconPath('symbologyAdd.svg')))
        self.add_template.setToolTip(tr('Add a new tempalte to the portfolio.'))
        self.remove_template.setText('')
        self.remove_template.setIcon(QIcon(QgsApplication.iconPath('symbologyRemove.svg')))
        self.remove_template.setToolTip(tr('Remove the selected template from the portfolio.'))

        # Set templates table
        items = self.config.layer_config['templates']['items']
        self.templates.setColumnCount(len(items))
        for i, item in enumerate(items):
            sub_definition = self.config.layer_config[item]
            column = QTableWidgetItem(sub_definition['header'])
            column.setToolTip(sub_definition['tooltip'])
            self.templates.setHorizontalHeaderItem(i, column)
        header = self.templates.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

        self.templates.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.templates.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.templates.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.templates.setAlternatingRowColors(True)
