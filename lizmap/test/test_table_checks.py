import unittest

from lizmap.widgets.check_project import Checks, Error, TableCheck

__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


class TestProjectTable(unittest.TestCase):

    def test(self):
        table = TableCheck(None)
        table.setup()

        self.assertEqual(table.horizontalHeader().count(), 4)
        self.assertEqual(table.verticalHeader().count(), 0)

        self.assertEqual(table.rowCount(), 0)

        table.add_error(Error('my-tailor-is-rich', Checks.DuplicatedLayerNameOrGroup))
        table.add_error(Error('home-sweet-home', Checks.DuplicatedLayerNameOrGroup))
        table.add_error(Error('home-sweet-home', Checks.MissingPk))
        self.assertEqual(table.rowCount(), 3)

        expected = [
            {
                'error': 'duplicated_layer_name_or_group',
                'level': 'project',
                'severity': 1,
                'source': 'my-tailor-is-rich',
            }, {
                'severity': 1,
                'level': 'project',
                'source': 'home-sweet-home',
                'error': 'duplicated_layer_name_or_group',
            }, {
                'error': 'missing_primary_key',
                'level': 'layer',
                'severity': 1,
                'source': 'home-sweet-home',
            },
        ]
        self.assertListEqual(expected, table.to_json())

        expected = {
            'duplicated_layer_name_or_group': 2,
            'missing_primary_key': 1
        }
        self.assertDictEqual(expected, table.to_json_summarized())

        expected = (
            'Validation summarized :\n\n'
            '* Duplicated layer name or group → 2\n'
            '* Missing a proper primary key in the database. → 1\n'
            '\n')
        self.assertEqual(expected, table.to_markdown_summarized())


# if __name__ == '__main__':
#     app = QApplication([])
#     # view = CheckProjectView()
#     # view.show()
#     app.exec_()
