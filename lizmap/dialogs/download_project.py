__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import logging

from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QVBoxLayout,
)

LOGGER = logging.getLogger('Lizmap')


class DownloadProject(QDialog):

    def __init__(self, metadata: dict):
        # noinspection PyArgumentList
        QDialog.__init__(self)

        layout = QVBoxLayout()

        self.metadata = metadata

        self.directory = QComboBox(self)
        # noinspection PyArgumentList
        layout.addWidget(self.directory)

        for directory in metadata['repositories']:
            label = metadata['repositories'][directory]["label"]
            self.directory.addItem(f'{label} : {directory}', directory)

        self.project = QComboBox(self)
        # noinspection PyArgumentList
        layout.addWidget(self.project)

        self.directory.currentIndexChanged.connect(self.update_project)
        self.update_project()

        self.button_box = QDialogButtonBox()
        self.button_box.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        # noinspection PyArgumentList
        layout.addWidget(self.button_box)

        self.setLayout(layout)

        accept_button = self.button_box.button(QDialogButtonBox.Ok)
        accept_button.clicked.connect(self.accept)
        cancel_button = self.button_box.button(QDialogButtonBox.Cancel)
        cancel_button.clicked.connect(self.reject)

    def update_project(self):
        directory = self.directory.currentData()
        for project in self.metadata['repositories'][directory]['projects']:
            label = self.metadata['repositories'][directory]['projects'][project]['title']
            self.project.addItem(f'{label} : {project}', project)


if __name__ == '__main__':
    """ For manual tests. """
    import json
    import sys

    from qgis.PyQt.QtWidgets import QApplication

    from lizmap.qgis_plugin_tools.tools.resources import plugin_test_data_path

    app = QApplication(sys.argv)
    with open(plugin_test_data_path('metadata', '10102023.json')) as f:
        content = json.load(f)

    dialog = DownloadProject(content)
    dialog.show()
    sys.exit(app.exec_())
