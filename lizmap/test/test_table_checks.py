import unittest

from qgis.PyQt.QtWidgets import QApplication

from lizmap.models.check_project import Levels, Severities, TableCheck
from lizmap.widgets.check_project import CheckProjectView


class TestProjectTable(unittest.TestCase):

    def setUp(self):
        self.app = QApplication([])

    def test(self):
        table = TableCheck(self.app.parent())

        self.assertEqual(table.horizontalHeader().count(), 4)
        self.assertEqual(table.verticalHeader().count(), 0)

        self.assertEqual(table.rowCount(), 0)

        table.add_row(Severities.Blocking, Levels.Project, "Classical mechanics", "bob")
        self.assertEqual(table.rowCount(), 1)


if __name__ == '__main__':
    app = QApplication([])
    view = CheckProjectView()
    view.show()
    app.exec_()
