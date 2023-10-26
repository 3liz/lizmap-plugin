from qgis.PyQt.QtWidgets import QApplication

from lizmap.models.check_project import Checks, Error, TableCheck

# from lizmap.widgets.check_project import CheckProjectView


app = QApplication([])
view = TableCheck()
# model = TableModel()
# view = CheckProjectView()
# view.setModel(model)
identifier = '"bob" → count 2 layers'
view.add_error(Error(identifier, Checks.DuplicatedLayerNameOrGroup))
view.show()
app.exec_()
