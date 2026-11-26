"""Test code layout."""

import re

from pathlib import Path

from lizmap.toolbelt.resources import plugin_path, resources_path

from .compat import TestCase


class TestCodeLayout(TestCase):
    @staticmethod
    def ui_files():
        """List of UI files in the plugin."""
        return [x for x in Path(resources_path("ui")).iterdir() if x.suffix == ".ui"]

    def test_qgis_widgets(self):
        """Test imports are correct in UI file."""
        list_files = []
        expression = r"<header>qgs[a-z]*\.h<\/header>"
        for ui in self.ui_files():
            with open(ui) as ui_file:
                matches = re.findall(expression, ui_file.read(), re.MULTILINE)
                if len(matches):
                    list_files.append(str(ui))

        self.assertListEqual(list_files, [], "Some imports are wrong : {}".format(", ".join(list_files)))

    def test_no_connection_in_ui(self):
        """Test there is not connection in UI."""
        list_files = []
        expression = r"</connections>"
        for ui in self.ui_files():
            with open(ui) as ui_file:
                matches = re.findall(expression, ui_file.read(), re.MULTILINE)
                if len(matches):
                    list_files.append(str(ui))

        self.assertListEqual(
            list_files, [], "Use PyQt connect in Python files, not UI : {}".format(", ".join(list_files))
        )

    def test_panel_visibility(self):
        """Test panels are hidden with LizmapDialog.set_panel_visible, to stay hidden after a search."""
        list_files = []
        expression = r"mOptionsListWidget\.item\(Panels\.\w+\)\.setHidden\("
        plugin = plugin_path()
        for python_file in plugin.rglob("*.py"):
            if re.search(expression, python_file.read_text()):
                list_files.append(str(python_file.relative_to(plugin)))

        self.assertListEqual(
            list_files, [], "Use 'set_panel_visible' instead of 'setHidden' : {}".format(", ".join(list_files))
        )
